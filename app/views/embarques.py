from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..constantes import INCOTERMS, MODAIS, OPERACOES, STATUS_EMBARQUE, TIPOS_DOCUMENTO
from ..db import execute, proximo_codigo, query
from .util import data_ou_none, num, remover_upload, salvar_upload, txt

bp = Blueprint("embarques", __name__, url_prefix="/embarques")

CAMPOS_TEXTO = ["tipo_operacao", "modal", "origem", "destino", "incoterm", "mercadoria", "exportador",
                "importador", "transportador", "navio_voo", "booking", "master", "house", "containers",
                "observacoes"]
CAMPOS_DATA = ["etd", "eta", "atd", "ata"]

# Ao registrar estes status, preenchemos a data real correspondente se vazia
DATA_REAL_POR_STATUS = {"embarcado": "atd", "chegada_destino": "ata"}


def obter(emb_id):
    emb = query(
        """SELECT e.*, c.nome cliente, o.numero orcamento_numero FROM embarques e
           JOIN clientes c ON c.id=e.cliente_id LEFT JOIN orcamentos o ON o.id=e.orcamento_id
           WHERE e.id=?""",
        (emb_id,), one=True,
    )
    if not emb:
        abort(404)
    return emb


@bp.route("/")
def lista():
    status = request.args.get("status", "")
    busca = request.args.get("q", "").strip()
    sql = """SELECT e.*, c.nome cliente FROM embarques e JOIN clientes c ON c.id=e.cliente_id WHERE 1=1"""
    args = []
    if status == "ativos":
        sql += " AND e.status NOT IN ('entregue','cancelado')"
    elif status:
        sql += " AND e.status=?"
        args.append(status)
    if busca:
        like = f"%{busca}%"
        sql += """ AND (e.referencia LIKE ? OR e.master LIKE ? OR e.house LIKE ? OR e.booking LIKE ?
                   OR e.containers LIKE ? OR c.nome LIKE ?)"""
        args += [like] * 6
    embarques = query(sql + " ORDER BY e.id DESC", args)
    return render_template(
        "embarques/lista.html", embarques=embarques, status=status, busca=busca, hoje=date.today().isoformat()
    )


def contexto_form(emb):
    return {
        "emb": emb, "clientes": query("SELECT id, nome FROM clientes ORDER BY nome"),
        "MODAIS": MODAIS, "OPERACOES": OPERACOES, "INCOTERMS": INCOTERMS, "STATUS": STATUS_EMBARQUE,
    }


@bp.route("/novo", methods=["GET", "POST"])
@bp.route("/<int:emb_id>/editar", methods=["GET", "POST"])
def form(emb_id=None):
    existente = obter(emb_id) if emb_id else None
    if request.method == "POST":
        dados = {c: txt(c) for c in CAMPOS_TEXTO}
        dados.update({c: data_ou_none(c) for c in CAMPOS_DATA})
        dados.update({
            "cliente_id": int(num("cliente_id")),
            "volumes": int(num("volumes")),
            "peso_kg": num("peso_kg"),
            "cubagem": num("cubagem"),
            "valor_servico_brl": num("valor_servico_brl"),
        })
        if not dados["cliente_id"]:
            flash("Selecione o cliente.", "erro")
            return render_template("embarques/form.html", **contexto_form(dados))
        if existente:
            sets = ", ".join(f"{k}=?" for k in dados)
            execute(f"UPDATE embarques SET {sets} WHERE id=?", [*dados.values(), emb_id])
        else:
            dados["referencia"] = proximo_codigo("embarques", "referencia", "EMB")
            dados["orcamento_id"] = request.form.get("orcamento_id", type=int)
            cols = ", ".join(dados)
            marks = ", ".join("?" for _ in dados)
            emb_id = execute(f"INSERT INTO embarques ({cols}) VALUES ({marks})", list(dados.values()))
            execute(
                "INSERT INTO embarque_eventos (embarque_id, data, status, descricao) VALUES (?,?,?,?)",
                (emb_id, date.today().isoformat(), "aguardando_booking", "Embarque aberto"),
            )
            if dados["orcamento_id"]:
                execute("UPDATE orcamentos SET status='aprovado' WHERE id=?", (dados["orcamento_id"],))
        flash("Embarque salvo.", "ok")
        return redirect(url_for("embarques.detalhe", emb_id=emb_id))

    if existente:
        return render_template("embarques/form.html", **contexto_form(dict(existente)))

    emb = {"tipo_operacao": "importacao", "modal": "maritimo_lcl"}
    orc_id = request.args.get("orcamento_id", type=int)
    if orc_id:
        orc = query("SELECT * FROM orcamentos WHERE id=?", (orc_id,), one=True)
        if orc:
            volumes = query("SELECT COALESCE(SUM(quantidade),0) q FROM orcamento_volumes WHERE orcamento_id=?",
                            (orc_id,), one=True)["q"]
            emb.update({
                "orcamento_id": orc_id, "cliente_id": orc["cliente_id"], "tipo_operacao": orc["tipo_operacao"],
                "modal": orc["modal"], "origem": orc["origem"], "destino": orc["destino"],
                "incoterm": orc["incoterm"], "mercadoria": orc["mercadoria"], "volumes": volumes,
                "peso_kg": orc["peso_bruto"], "cubagem": orc["cubagem"],
                "valor_servico_brl": orc["total_venda_brl"],
            })
    return render_template("embarques/form.html", **contexto_form(emb))


@bp.route("/<int:emb_id>")
def detalhe(emb_id):
    emb = obter(emb_id)
    eventos = query("SELECT * FROM embarque_eventos WHERE embarque_id=? ORDER BY data DESC, id DESC", (emb_id,))
    documentos = query("SELECT * FROM embarque_documentos WHERE embarque_id=? ORDER BY id DESC", (emb_id,))
    notas = query("SELECT * FROM nfse WHERE embarque_id=? ORDER BY id DESC", (emb_id,))
    etapas = [s for s in STATUS_EMBARQUE if s != "cancelado"]
    return render_template(
        "embarques/detalhe.html", emb=emb, eventos=eventos, documentos=documentos, notas=notas,
        etapas=etapas, STATUS=STATUS_EMBARQUE, TIPOS_DOCUMENTO=TIPOS_DOCUMENTO, hoje=date.today().isoformat(),
    )


@bp.route("/<int:emb_id>/eventos", methods=["POST"])
def novo_evento(emb_id):
    emb = obter(emb_id)
    status = txt("status")
    data_evento = txt("data") or date.today().isoformat()
    if status and status not in STATUS_EMBARQUE:
        abort(400)
    execute(
        "INSERT INTO embarque_eventos (embarque_id, data, status, local, descricao) VALUES (?,?,?,?,?)",
        (emb_id, data_evento, status or None, txt("local"), txt("descricao")),
    )
    if status:
        execute("UPDATE embarques SET status=? WHERE id=?", (status, emb_id))
        campo = DATA_REAL_POR_STATUS.get(status)
        if campo and not emb[campo]:
            execute(f"UPDATE embarques SET {campo}=? WHERE id=?", (data_evento, emb_id))
    flash("Evento registrado.", "ok")
    return redirect(url_for("embarques.detalhe", emb_id=emb_id))


@bp.route("/<int:emb_id>/eventos/<int:evento_id>/excluir", methods=["POST"])
def excluir_evento(emb_id, evento_id):
    execute("DELETE FROM embarque_eventos WHERE id=? AND embarque_id=?", (evento_id, emb_id))
    flash("Evento removido.", "ok")
    return redirect(url_for("embarques.detalhe", emb_id=emb_id))


@bp.route("/<int:emb_id>/documentos", methods=["POST"])
def anexar_documento(emb_id):
    obter(emb_id)
    tipo = txt("tipo") if txt("tipo") in TIPOS_DOCUMENTO else "outro"
    enviados = 0
    for arquivo in request.files.getlist("arquivos"):
        salvo = salvar_upload(arquivo)
        if salvo:
            execute(
                "INSERT INTO embarque_documentos (embarque_id, tipo, nome_original, arquivo) VALUES (?,?,?,?)",
                (emb_id, tipo, salvo[1], salvo[0]),
            )
            enviados += 1
    if enviados:
        flash(f"{enviados} documento(s) anexado(s).", "ok")
    else:
        flash("Nenhum arquivo válido enviado (PDF, XML, imagens, Office, TXT ou ZIP).", "erro")
    return redirect(url_for("embarques.detalhe", emb_id=emb_id))


@bp.route("/<int:emb_id>/documentos/<int:doc_id>/excluir", methods=["POST"])
def excluir_documento(emb_id, doc_id):
    doc = query("SELECT * FROM embarque_documentos WHERE id=? AND embarque_id=?", (doc_id, emb_id), one=True)
    if doc:
        remover_upload(doc["arquivo"])
        execute("DELETE FROM embarque_documentos WHERE id=?", (doc_id,))
        flash("Documento removido.", "ok")
    return redirect(url_for("embarques.detalhe", emb_id=emb_id))
