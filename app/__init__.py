import hashlib
import hmac
import os
from pathlib import Path

from flask import (Flask, Response, abort, redirect, render_template, request, session,
                   url_for)

from . import db, storage
from .constantes import LABELS

ROTAS_PUBLICAS = {"login", "static"}


def create_app(config=None):
    # Na Vercel só /tmp é gravável (e é apagado entre execuções)
    em_vercel = bool(os.environ.get("VERCEL"))
    app = Flask(__name__, instance_relative_config=True)
    instance = Path("/tmp/agentedecarga") if em_vercel else Path(app.instance_path)
    senha = os.environ.get("APP_PASSWORD", "")
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY")
        or (hashlib.sha256(f"agentedecarga:{senha}".encode()).hexdigest() if senha else "troque-esta-chave"),
        APP_PASSWORD=senha,
        EXIGIR_SENHA=em_vercel,
        DATABASE_URL=os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"),
        BLOB_READ_WRITE_TOKEN=os.environ.get("BLOB_READ_WRITE_TOKEN"),
        DATABASE=str(instance / "agentedecarga.sqlite"),
        UPLOAD_FOLDER=str(instance / "uploads"),
        # funções da Vercel aceitam no máximo 4,5 MB por requisição
        MAX_CONTENT_LENGTH=4 * 1024 * 1024 if em_vercel else 20 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=em_vercel,
    )
    if config:
        app.config.update(config)
    app.config.setdefault(
        "DADOS_TEMPORARIOS",
        em_vercel and not (app.config["DATABASE_URL"] and app.config["BLOB_READ_WRITE_TOKEN"]),
    )
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

    @app.before_request
    def exigir_login():
        if request.endpoint in ROTAS_PUBLICAS:
            return None
        if not app.config["APP_PASSWORD"]:
            if app.config["EXIGIR_SENHA"]:
                return render_template("configurar.html"), 503
            return None  # uso local sem senha
        if not session.get("logado"):
            return redirect(url_for("login", proximo=request.full_path))
        return None

    @app.route("/login", methods=["GET", "POST"])
    def login():
        erro = None
        if request.method == "POST":
            if app.config["APP_PASSWORD"] and hmac.compare_digest(
                request.form.get("senha", "").encode(), app.config["APP_PASSWORD"].encode()
            ):
                session.clear()
                session["logado"] = True
                session.permanent = True
                destino = request.args.get("proximo", "")
                return redirect(destino if destino.startswith("/") and not destino.startswith("//") else "/")
            erro = "Senha incorreta."
        return render_template("login.html", erro=erro)

    @app.route("/sair", methods=["POST"])
    def sair():
        session.clear()
        return redirect(url_for("login"))

    @app.template_filter("brl")
    def brl(valor):
        valor = valor or 0
        s = f"{valor:,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

    @app.template_filter("num")
    def num(valor, casas=2):
        s = f"{(valor or 0):,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    @app.template_filter("data")
    def data(valor):
        if not valor:
            return "—"
        partes = str(valor)[:10].split("-")
        return "/".join(reversed(partes)) if len(partes) == 3 else valor

    @app.template_filter("label")
    def label(valor, grupo):
        return LABELS.get(grupo, {}).get(valor, valor)

    @app.template_global()
    def url_arquivo(ref):
        return url_for("arquivo", ref=ref) if ref else None

    @app.context_processor
    def globais():
        return {
            "LABELS": LABELS,
            "empresa": db.empresa(),
            "dados_temporarios": app.config["DADOS_TEMPORARIOS"],
            "com_login": bool(app.config["APP_PASSWORD"]),
        }

    @app.route("/arquivos")
    def arquivo():
        ref = request.args.get("ref", "")
        lido = storage.ler(ref)
        if lido is None:
            abort(404)
        conteudo, tipo = lido
        tipo = tipo or "application/octet-stream"
        cabecalhos = {"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"}
        # só PDF e imagens abrem no navegador; o resto (XML, Office...) é baixado
        if not (tipo == "application/pdf" or tipo.startswith("image/")):
            cabecalhos["Content-Disposition"] = "attachment"
        return Response(conteudo, mimetype=tipo, headers=cabecalhos)

    from .views import bp_principal, bp_clientes, bp_orcamentos, bp_embarques, bp_nfse

    for bp in (bp_principal, bp_clientes, bp_orcamentos, bp_embarques, bp_nfse):
        app.register_blueprint(bp)
    return app
