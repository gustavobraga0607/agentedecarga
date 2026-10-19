from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..db import execute, query
from .util import num, txt

bp = Blueprint("principal", __name__)


@bp.route("/")
def dashboard():
    hoje = date.today()
    mes = hoje.strftime("%Y-%m")
    indicadores = {
        "orcamentos_abertos": query(
            "SELECT COUNT(*) c FROM orcamentos WHERE status IN ('rascunho','enviado')", one=True
        )["c"],
        "embarques_ativos": query(
            "SELECT COUNT(*) c FROM embarques WHERE status NOT IN ('entregue','cancelado')", one=True
        )["c"],
        "nfse_mes_qtd": query(
            "SELECT COUNT(*) c FROM nfse WHERE status='emitida' AND substr(competencia,1,7)=?",
            (mes,), one=True,
        )["c"],
        "nfse_mes_valor": query(
            "SELECT COALESCE(SUM(valor_servicos),0) v FROM nfse WHERE status='emitida' AND substr(competencia,1,7)=?",
            (mes,), one=True,
        )["v"],
    }
    chegadas = query(
        """SELECT e.*, c.nome cliente FROM embarques e JOIN clientes c ON c.id=e.cliente_id
           WHERE e.status NOT IN ('entregue','cancelado','chegada_destino','desembaracado')
             AND e.eta IS NOT NULL AND e.eta <= ? ORDER BY e.eta""",
        ((hoje + timedelta(days=7)).isoformat(),),
    )
    sem_nfse = query(
        """SELECT e.*, c.nome cliente FROM embarques e JOIN clientes c ON c.id=e.cliente_id
           WHERE e.status IN ('chegada_destino','desembaracado','entregue')
             AND NOT EXISTS (SELECT 1 FROM nfse n WHERE n.embarque_id=e.id AND n.status='emitida')
           ORDER BY e.ata DESC, e.id DESC"""
    )
    orcamentos = query(
        """SELECT o.*, c.nome cliente FROM orcamentos o JOIN clientes c ON c.id=o.cliente_id
           ORDER BY o.id DESC LIMIT 5"""
    )
    return render_template(
        "dashboard.html", ind=indicadores, chegadas=chegadas, sem_nfse=sem_nfse,
        orcamentos=orcamentos, hoje=hoje.isoformat(),
    )


CAMPOS_EMPRESA = [
    "razao_social", "nome_fantasia", "cnpj", "inscricao_municipal", "endereco", "municipio",
    "codigo_municipio_ibge", "uf", "email", "telefone", "regime_tributario", "codigo_servico",
    "descricao_servico", "serie_rps",
]


@bp.route("/empresa", methods=["GET", "POST"])
def empresa():
    if request.method == "POST":
        valores = [txt(c) for c in CAMPOS_EMPRESA]
        valores += [
            num("aliquota_iss"),
            max(int(num("proximo_numero_nfse", 1)), 1),
            num("taxa_usd", 1),
            num("taxa_eur", 1),
        ]
        sets = ", ".join(f"{c}=?" for c in CAMPOS_EMPRESA)
        execute(
            f"UPDATE empresa SET {sets}, aliquota_iss=?, proximo_numero_nfse=?, taxa_usd=?, taxa_eur=? WHERE id=1",
            valores,
        )
        flash("Dados da empresa atualizados.", "ok")
        return redirect(url_for("principal.empresa"))
    return render_template("empresa/form.html")
