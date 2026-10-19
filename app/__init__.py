import os
from pathlib import Path

from flask import Flask, send_from_directory, abort

from . import db
from .constantes import LABELS


def create_app(config=None):
    # Na Vercel só /tmp é gravável (e é apagado entre execuções)
    em_vercel = bool(os.environ.get("VERCEL"))
    app = Flask(__name__, instance_relative_config=True)
    instance = Path("/tmp/agentedecarga") if em_vercel else Path(app.instance_path)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "troque-esta-chave"),
        DATABASE=str(instance / "agentedecarga.sqlite"),
        UPLOAD_FOLDER=str(instance / "uploads"),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024 if em_vercel else 20 * 1024 * 1024,
        DADOS_TEMPORARIOS=em_vercel,
    )
    if config:
        app.config.update(config)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

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

    @app.context_processor
    def globais():
        return {"LABELS": LABELS, "empresa": db.empresa(),
                "dados_temporarios": app.config["DADOS_TEMPORARIOS"]}

    @app.route("/arquivos/<path:nome>")
    def arquivo(nome):
        if "/" in nome or nome.startswith("."):
            abort(404)
        return send_from_directory(app.config["UPLOAD_FOLDER"], nome)

    from .views import bp_principal, bp_clientes, bp_orcamentos, bp_embarques, bp_nfse

    for bp in (bp_principal, bp_clientes, bp_orcamentos, bp_embarques, bp_nfse):
        app.register_blueprint(bp)
    return app
