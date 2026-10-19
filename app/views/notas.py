from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .. import nfse as fiscal
from ..constantes import STATUS_NFSE
from ..db import empresa, execute, get_db, query
from .util import extensao, num, remover_upload, salvar_bytes, salvar_upload, txt

bp = Blueprint("nfse", __name__, url_prefix="/nfse")


def obter(nota_id):
    nota = query(
        """SELECT n.*, c.nome cliente, c.cnpj_cpf cliente_doc, c.inscricao_municipal cliente_im,
                  c.endereco cliente_endereco, c.cidade cliente_cidade, c.uf cliente_uf, c.email cliente_email,
                  e.referencia embarque_ref
           FROM nfse n JOIN clientes c ON c.id=n.cliente_id LEFT JOIN embarques e ON e.id=n.embarque_id
           WHERE n.id=?""",
        (nota_id,), one=True,
    )
    if not nota:
        abort(404)
    return nota


@bp.route("/")
def lista():
    mes = request.args.get("mes", "")
    status = request.args.get("status", "")
    sql = """SELECT n.*, c.nome cliente, e.referencia embarque_ref FROM nfse n
             JOIN clientes c ON c.id=n.cliente_id LEFT JOIN embarques e ON e.id=n.embarque_id WHERE 1=1"""
    args = []
    if mes:
        sql += " AND substr(n.competencia,1,7)=?"
        args.append(mes)
    if status:
        sql += " AND n.status=?"
        args.append(status)
    notas = query(sql + " ORDER BY n.data_emissao DESC, n.id DESC", args)
    total = sum(n["valor_servicos"] for n in notas if n["status"] == "emitida")
    return render_template("nfse/lista.html", notas=notas, mes=mes, status=status, total=total)


def opcoes():
    return {
        "clientes": query("SELECT id, nome, cnpj_cpf FROM clientes ORDER BY nome"),
        "embarques": query(
            """SELECT e.id, e.referencia, c.nome cliente FROM embarques e JOIN clientes c ON c.id=e.cliente_id
               WHERE e.status != 'cancelado' ORDER BY e.id DESC"""
        ),
    }


@bp.route("/emitir", methods=["GET", "POST"])
def emitir():
    emp = empresa()
    if request.method == "POST":
        cliente_id = int(num("cliente_id"))
        valor = num("valor_servicos")
        if not cliente_id or valor <= 0 or not txt("discriminacao"):
            flash("Informe tomador, discriminação e valor do serviço.", "erro")
            return render_template("nfse/emitir.html", nota=request.form, **opcoes())
        tributos = fiscal.calcular_tributos(
            valor, num("deducoes"), num("aliquota_iss"), bool(request.form.get("iss_retido")),
            bool(request.form.get("reter_federais")), num("inss_pct"),
        )
        db = get_db()
        # numeração sequencial: lê e incrementa na mesma transação
        numero = db.execute("SELECT proximo_numero_nfse FROM empresa WHERE id=1").fetchone()[0]
        db.execute("UPDATE empresa SET proximo_numero_nfse=? WHERE id=1", (numero + 1,))
        nota = {
            "origem": "interna",
            "numero": str(numero),
            "serie_rps": emp["serie_rps"],
            "codigo_verificacao": fiscal.gerar_codigo_verificacao(),
            "data_emissao": datetime.now().isoformat(timespec="seconds"),
            "competencia": txt("competencia") or date.today().isoformat(),
            "cliente_id": cliente_id,
            "embarque_id": request.form.get("embarque_id", type=int) or None,
            "codigo_servico": txt("codigo_servico"),
            "discriminacao": txt("discriminacao"),
            "valor_servicos": valor,
            "deducoes": num("deducoes"),
            "aliquota_iss": num("aliquota_iss"),
            "iss_retido": 1 if request.form.get("iss_retido") else 0,
            **tributos,
        }
        cliente = query("SELECT * FROM clientes WHERE id=?", (cliente_id,), one=True)
        xml = fiscal.gerar_xml_dps(nota, emp, cliente)
        nota["arquivo_xml"] = salvar_bytes(xml, "xml")
        nota["arquivo_xml_nome"] = f"NFSe_{numero}.xml"
        cols = ", ".join(nota)
        marks = ", ".join("?" for _ in nota)
        nota_id = db.execute(f"INSERT INTO nfse ({cols}) VALUES ({marks})", list(nota.values())).lastrowid
        db.commit()
        retorno = fiscal.transmitir(xml)
        flash(f"NF-S nº {numero} emitida. {retorno['mensagem']}", "ok")
        return redirect(url_for("nfse.detalhe", nota_id=nota_id))

    nota = {
        "codigo_servico": emp["codigo_servico"], "aliquota_iss": emp["aliquota_iss"],
        "competencia": date.today().isoformat(), "cliente_id": request.args.get("cliente_id", type=int),
    }
    emb_id = request.args.get("embarque_id", type=int)
    if emb_id:
        emb = query("SELECT * FROM embarques WHERE id=?", (emb_id,), one=True)
        if emb:
            linhas = [f"{emp['descricao_servico']} - Ref. {emb['referencia']}"]
            if emb["house"] or emb["master"]:
                linhas.append(f"Conhecimento: {emb['house'] or emb['master']}")
            linhas.append(f"Trecho: {emb['origem']} x {emb['destino']}")
            nota.update({
                "embarque_id": emb_id, "cliente_id": emb["cliente_id"],
                "valor_servicos": emb["valor_servico_brl"], "discriminacao": "\n".join(linhas),
            })
    return render_template("nfse/emitir.html", nota=nota, **opcoes())


@bp.route("/anexar", methods=["GET", "POST"])
def anexar():
    if request.method == "POST":
        pdf = request.files.get("arquivo_pdf")
        xml = request.files.get("arquivo_xml")
        if (not pdf or not pdf.filename) and (not xml or not xml.filename):
            flash("Envie o PDF e/ou o XML da nota.", "erro")
            return render_template("nfse/anexar.html", nota=request.form, **opcoes())
        if pdf and pdf.filename and extensao(pdf.filename) != "pdf":
            flash("O arquivo da nota deve ser PDF.", "erro")
            return render_template("nfse/anexar.html", nota=request.form, **opcoes())
        if xml and xml.filename and extensao(xml.filename) != "xml":
            flash("O arquivo XML deve ter extensão .xml.", "erro")
            return render_template("nfse/anexar.html", nota=request.form, **opcoes())

        lidos = {}
        if xml and xml.filename:
            lidos = fiscal.ler_xml_nfse(xml.read())
            xml.seek(0)

        cliente_id = int(num("cliente_id"))
        if not cliente_id and lidos.get("documento_tomador"):
            doc = lidos["documento_tomador"]
            for c in query("SELECT id, cnpj_cpf FROM clientes"):
                if "".join(ch for ch in c["cnpj_cpf"] if ch.isdigit()) == doc:
                    cliente_id = c["id"]
                    break
        numero = txt("numero") or lidos.get("numero", "")
        valor = num("valor_servicos") or lidos.get("valor_servicos", 0)
        if not cliente_id or not numero or not valor:
            flash("Não foi possível identificar tomador, número ou valor — preencha os campos.", "erro")
            return render_template("nfse/anexar.html", nota={**lidos, **request.form.to_dict()}, **opcoes())

        aliquota = num("aliquota_iss") or lidos.get("aliquota_iss", 0)
        valor_iss = num("valor_iss") or lidos.get("valor_iss") or round(valor * aliquota / 100, 2)
        hoje = date.today().isoformat()
        salvo_pdf = salvar_upload(pdf) if pdf and pdf.filename else None
        salvo_xml = salvar_upload(xml) if xml and xml.filename else None
        nota = {
            "origem": "externa",
            "numero": numero,
            "codigo_verificacao": txt("codigo_verificacao") or lidos.get("codigo_verificacao", ""),
            "data_emissao": txt("data_emissao") or lidos.get("data_emissao", hoje),
            "competencia": txt("competencia") or lidos.get("competencia", hoje),
            "cliente_id": cliente_id,
            "embarque_id": request.form.get("embarque_id", type=int) or None,
            "discriminacao": txt("discriminacao") or lidos.get("discriminacao", ""),
            "valor_servicos": valor,
            "base_calculo": valor,
            "aliquota_iss": aliquota,
            "valor_iss": valor_iss,
            "valor_liquido": num("valor_liquido") or lidos.get("valor_liquido", valor),
            "arquivo_pdf": salvo_pdf[0] if salvo_pdf else None,
            "arquivo_pdf_nome": salvo_pdf[1] if salvo_pdf else None,
            "arquivo_xml": salvo_xml[0] if salvo_xml else None,
            "arquivo_xml_nome": salvo_xml[1] if salvo_xml else None,
        }
        cols = ", ".join(nota)
        marks = ", ".join("?" for _ in nota)
        nota_id = execute(f"INSERT INTO nfse ({cols}) VALUES ({marks})", list(nota.values()))
        flash(f"NF-S nº {numero} anexada.", "ok")
        return redirect(url_for("nfse.detalhe", nota_id=nota_id))

    nota = {"embarque_id": request.args.get("embarque_id", type=int)}
    if nota["embarque_id"]:
        emb = query("SELECT cliente_id FROM embarques WHERE id=?", (nota["embarque_id"],), one=True)
        nota["cliente_id"] = emb["cliente_id"] if emb else None
    return render_template("nfse/anexar.html", nota=nota, **opcoes())


@bp.route("/<int:nota_id>")
def detalhe(nota_id):
    return render_template("nfse/detalhe.html", nota=obter(nota_id), STATUS=STATUS_NFSE)


@bp.route("/<int:nota_id>/imprimir")
def imprimir(nota_id):
    return render_template("nfse/imprimir.html", nota=obter(nota_id))


@bp.route("/<int:nota_id>/arquivos", methods=["POST"])
def substituir_arquivos(nota_id):
    """Anexa (ou substitui) o PDF/XML oficial de uma nota já registrada."""
    nota = obter(nota_id)
    alterou = False
    for campo, ext in (("arquivo_pdf", "pdf"), ("arquivo_xml", "xml")):
        arquivo = request.files.get(campo)
        if arquivo and arquivo.filename and extensao(arquivo.filename) == ext:
            salvo = salvar_upload(arquivo)
            remover_upload(nota[campo])
            execute(f"UPDATE nfse SET {campo}=?, {campo}_nome=? WHERE id=?", (salvo[0], salvo[1], nota_id))
            alterou = True
    flash("Arquivo(s) anexado(s)." if alterou else "Nenhum arquivo PDF/XML válido enviado.",
          "ok" if alterou else "erro")
    return redirect(url_for("nfse.detalhe", nota_id=nota_id))


@bp.route("/<int:nota_id>/cancelar", methods=["POST"])
def cancelar(nota_id):
    nota = obter(nota_id)
    motivo = txt("motivo")
    if nota["status"] == "cancelada":
        flash("Nota já está cancelada.", "erro")
    elif len(motivo) < 15:
        flash("Informe o motivo do cancelamento (mínimo 15 caracteres).", "erro")
    else:
        execute("UPDATE nfse SET status='cancelada', motivo_cancelamento=? WHERE id=?", (motivo, nota_id))
        flash(f"NF-S nº {nota['numero']} cancelada.", "ok")
    return redirect(url_for("nfse.detalhe", nota_id=nota_id))


@bp.app_template_global()
def url_arquivo(nome):
    return url_for("arquivo", nome=nome) if nome else None

