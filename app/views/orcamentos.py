from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..calc import calcular_orcamento
from ..constantes import INCOTERMS, MOEDAS, MODAIS, OPERACOES, STATUS_ORCAMENTO
from ..db import empresa, execute, get_db, proximo_codigo, query
from .util import num, para_float, txt

bp = Blueprint("orcamentos", __name__, url_prefix="/orcamentos")

# Taxas sugeridas ao criar um orçamento (o usuário ajusta os valores)
TAXAS_PADRAO = {
    "maritimo_lcl": [
        ("Frete marítimo internacional", "por_wm", "USD", 45, 1, 45),
        ("Taxas de origem (handling)", "fixo", "USD", 120, 1, 0),
        ("THC destino", "por_wm", "BRL", 95, 1, 250),
        ("Desconsolidação", "fixo", "BRL", 350, 1, 0),
        ("Seguro internacional", "pct_mercadoria", "USD", 0.3, 1, 30),
    ],
    "maritimo_fcl": [
        ("Frete marítimo internacional", "por_unidade", "USD", 1800, 1, 0),
        ("BAF / bunker", "por_unidade", "USD", 250, 1, 0),
        ("THC destino", "por_unidade", "BRL", 1300, 1, 0),
        ("Liberação de BL", "fixo", "BRL", 450, 1, 0),
        ("Seguro internacional", "pct_mercadoria", "USD", 0.3, 1, 30),
    ],
    "aereo": [
        ("Frete aéreo internacional", "por_kg", "USD", 3.8, 1, 75),
        ("Fuel surcharge", "por_kg", "USD", 0.9, 1, 0),
        ("Security surcharge", "por_kg", "USD", 0.15, 1, 0),
        ("Taxas de origem", "fixo", "USD", 85, 1, 0),
        ("Armazenagem / capatazia destino", "por_kg", "BRL", 0.6, 1, 150),
    ],
    "rodoviario": [
        ("Frete rodoviário internacional", "por_kg", "USD", 0.45, 1, 350),
        ("Cruce de fronteira", "fixo", "USD", 150, 1, 0),
        ("Seguro RCTR-VI", "pct_mercadoria", "USD", 0.15, 1, 20),
    ],
}


def obter(orc_id):
    orc = query(
        """SELECT o.*, c.nome cliente, c.email cliente_email, c.cnpj_cpf cliente_doc
           FROM orcamentos o JOIN clientes c ON c.id=o.cliente_id WHERE o.id=?""",
        (orc_id,), one=True,
    )
    if not orc:
        abort(404)
    return orc


def volumes_de(orc_id):
    return [dict(r) for r in query("SELECT * FROM orcamento_volumes WHERE orcamento_id=? ORDER BY id", (orc_id,))]


def itens_de(orc_id):
    return [dict(r) for r in query("SELECT * FROM orcamento_itens WHERE orcamento_id=? ORDER BY id", (orc_id,))]


def ler_linhas(prefixo, campos):
    """Lê listas paralelas do formulário (ex.: vol_peso_kg[]) e retorna linhas."""
    colunas = {c: request.form.getlist(f"{prefixo}_{c}[]") for c in campos}
    total = max((len(v) for v in colunas.values()), default=0)
    return [{c: (colunas[c][i] if i < len(colunas[c]) else "") for c in campos} for i in range(total)]


def ler_formulario():
    orc = {
        "cliente_id": int(num("cliente_id")),
        "tipo_operacao": txt("tipo_operacao") or "importacao",
        "modal": txt("modal") or "maritimo_lcl",
        "origem": txt("origem"),
        "destino": txt("destino"),
        "incoterm": txt("incoterm"),
        "mercadoria": txt("mercadoria"),
        "valor_mercadoria": num("valor_mercadoria"),
        "moeda_mercadoria": txt("moeda_mercadoria") or "USD",
        "taxa_usd": num("taxa_usd", 1),
        "taxa_eur": num("taxa_eur", 1),
        "margem_pct": num("margem_pct"),
        "validade": txt("validade") or None,
        "transit_time": txt("transit_time"),
        "observacoes": txt("observacoes"),
    }
    volumes = []
    for linha in ler_linhas("vol", ["quantidade", "comprimento_cm", "largura_cm", "altura_cm", "peso_kg"]):
        v = {k: para_float(x) for k, x in linha.items()}
        if v["quantidade"] > 0 and (v["peso_kg"] or v["comprimento_cm"]):
            v["quantidade"] = int(v["quantidade"])
            volumes.append(v)
    itens = []
    for linha in ler_linhas("item", ["descricao", "tipo_calculo", "moeda", "valor_unitario", "quantidade", "minimo"]):
        if not linha["descricao"].strip():
            continue
        itens.append({
            "descricao": linha["descricao"].strip(),
            "tipo_calculo": linha["tipo_calculo"] or "fixo",
            "moeda": linha["moeda"] or "USD",
            "valor_unitario": para_float(linha["valor_unitario"]),
            "quantidade": para_float(linha["quantidade"], 1) or 1,
            "minimo": para_float(linha["minimo"]),
        })
    return orc, volumes, itens


def salvar(orc_id, orc, volumes, itens):
    res = calcular_orcamento(orc, volumes, itens)
    dados = {
        **orc,
        "peso_bruto": res["carga"]["peso_bruto"],
        "cubagem": res["carga"]["cubagem"],
        "peso_taxavel": res["carga"]["peso_taxavel"],
        "total_custo_brl": res["total_custo_brl"],
        "total_venda_brl": res["total_venda_brl"],
    }
    db = get_db()
    if orc_id:
        sets = ", ".join(f"{k}=?" for k in dados)
        db.execute(f"UPDATE orcamentos SET {sets} WHERE id=?", [*dados.values(), orc_id])
        db.execute("DELETE FROM orcamento_volumes WHERE orcamento_id=?", (orc_id,))
        db.execute("DELETE FROM orcamento_itens WHERE orcamento_id=?", (orc_id,))
    else:
        dados["numero"] = proximo_codigo("orcamentos", "numero", "ORC")
        cols = ", ".join(dados)
        marks = ", ".join("?" for _ in dados)
        orc_id = db.execute(f"INSERT INTO orcamentos ({cols}) VALUES ({marks})", list(dados.values())).lastrowid
    for v in volumes:
        db.execute(
            """INSERT INTO orcamento_volumes (orcamento_id, quantidade, comprimento_cm, largura_cm, altura_cm, peso_kg)
               VALUES (?,?,?,?,?,?)""",
            (orc_id, v["quantidade"], v["comprimento_cm"], v["largura_cm"], v["altura_cm"], v["peso_kg"]),
        )
    for i in res["itens"]:
        db.execute(
            """INSERT INTO orcamento_itens (orcamento_id, descricao, tipo_calculo, moeda, valor_unitario,
               quantidade, minimo, custo_moeda, custo_brl, venda_brl) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (orc_id, i["descricao"], i["tipo_calculo"], i["moeda"], i["valor_unitario"], i["quantidade"],
             i["minimo"], i["custo_moeda"], i["custo_brl"], i["venda_brl"]),
        )
    db.commit()
    return orc_id


@bp.route("/")
def lista():
    status = request.args.get("status", "")
    sql = "SELECT o.*, c.nome cliente FROM orcamentos o JOIN clientes c ON c.id=o.cliente_id"
    args = ()
    if status:
        sql += " WHERE o.status=?"
        args = (status,)
    orcamentos = query(sql + " ORDER BY o.id DESC", args)
    return render_template("orcamentos/lista.html", orcamentos=orcamentos, status=status)


def contexto_form(orc, volumes, itens):
    return {
        "orc": orc, "volumes": volumes, "itens": itens,
        "clientes": query("SELECT id, nome FROM clientes ORDER BY nome"),
        "MODAIS": MODAIS, "OPERACOES": OPERACOES, "INCOTERMS": INCOTERMS, "MOEDAS": MOEDAS,
        "TAXAS_PADRAO": TAXAS_PADRAO,
    }


@bp.route("/novo", methods=["GET", "POST"])
@bp.route("/<int:orc_id>/editar", methods=["GET", "POST"])
def form(orc_id=None):
    existente = obter(orc_id) if orc_id else None
    if request.method == "POST":
        orc, volumes, itens = ler_formulario()
        if not orc["cliente_id"]:
            flash("Selecione o cliente.", "erro")
            return render_template("orcamentos/form.html", **contexto_form(orc, volumes, itens))
        orc_id = salvar(orc_id, orc, volumes, itens)
        flash("Orçamento salvo e recalculado.", "ok")
        return redirect(url_for("orcamentos.detalhe", orc_id=orc_id))

    if existente:
        return render_template(
            "orcamentos/form.html", **contexto_form(dict(existente), volumes_de(orc_id), itens_de(orc_id))
        )
    emp = empresa()
    modal = request.args.get("modal", "maritimo_lcl")
    orc = {
        "cliente_id": request.args.get("cliente_id", type=int), "modal": modal,
        "tipo_operacao": "importacao", "incoterm": "FOB", "moeda_mercadoria": "USD",
        "taxa_usd": emp["taxa_usd"], "taxa_eur": emp["taxa_eur"], "margem_pct": 15,
        "validade": (date.today() + timedelta(days=15)).isoformat(),
    }
    itens = [
        dict(zip(("descricao", "tipo_calculo", "moeda", "valor_unitario", "quantidade", "minimo"), t))
        for t in TAXAS_PADRAO.get(modal, [])
    ]
    volumes = [{"quantidade": 1, "comprimento_cm": "", "largura_cm": "", "altura_cm": "", "peso_kg": ""}]
    return render_template("orcamentos/form.html", **contexto_form(orc, volumes, itens))


@bp.route("/<int:orc_id>")
def detalhe(orc_id):
    orc = obter(orc_id)
    res = calcular_orcamento(dict(orc), volumes_de(orc_id), itens_de(orc_id))
    embarque = query("SELECT id, referencia FROM embarques WHERE orcamento_id=?", (orc_id,), one=True)
    return render_template(
        "orcamentos/detalhe.html", orc=orc, res=res, volumes=volumes_de(orc_id), embarque=embarque,
        STATUS=STATUS_ORCAMENTO,
    )


@bp.route("/<int:orc_id>/imprimir")
def imprimir(orc_id):
    orc = obter(orc_id)
    res = calcular_orcamento(dict(orc), volumes_de(orc_id), itens_de(orc_id))
    return render_template("orcamentos/imprimir.html", orc=orc, res=res, volumes=volumes_de(orc_id))


@bp.route("/<int:orc_id>/status", methods=["POST"])
def alterar_status(orc_id):
    obter(orc_id)
    status = request.form.get("status")
    if status in STATUS_ORCAMENTO:
        execute("UPDATE orcamentos SET status=? WHERE id=?", (status, orc_id))
        flash(f"Status alterado para “{STATUS_ORCAMENTO[status]}”.", "ok")
    return redirect(url_for("orcamentos.detalhe", orc_id=orc_id))


@bp.route("/<int:orc_id>/duplicar", methods=["POST"])
def duplicar(orc_id):
    orc = dict(obter(orc_id))
    campos = ["cliente_id", "tipo_operacao", "modal", "origem", "destino", "incoterm", "mercadoria",
              "valor_mercadoria", "moeda_mercadoria", "taxa_usd", "taxa_eur", "margem_pct",
              "transit_time", "observacoes"]
    novo = {c: orc[c] for c in campos}
    novo["validade"] = (date.today() + timedelta(days=15)).isoformat()
    novo_id = salvar(None, novo, volumes_de(orc_id), itens_de(orc_id))
    flash("Orçamento duplicado.", "ok")
    return redirect(url_for("orcamentos.form", orc_id=novo_id))


@bp.route("/<int:orc_id>/excluir", methods=["POST"])
def excluir(orc_id):
    obter(orc_id)
    if query("SELECT 1 FROM embarques WHERE orcamento_id=?", (orc_id,), one=True):
        flash("Orçamento já virou embarque e não pode ser excluído.", "erro")
        return redirect(url_for("orcamentos.detalhe", orc_id=orc_id))
    execute("DELETE FROM orcamentos WHERE id=?", (orc_id,))
    flash("Orçamento excluído.", "ok")
    return redirect(url_for("orcamentos.lista"))
