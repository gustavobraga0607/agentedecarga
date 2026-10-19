from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..db import IntegrityError, execute, query
from .util import txt

bp = Blueprint("clientes", __name__, url_prefix="/clientes")

CAMPOS = ["nome", "cnpj_cpf", "inscricao_municipal", "email", "telefone", "contato",
          "endereco", "cidade", "uf", "cep", "pais"]


def obter(cliente_id):
    cliente = query("SELECT * FROM clientes WHERE id=?", (cliente_id,), one=True)
    if not cliente:
        abort(404)
    return cliente


@bp.route("/")
def lista():
    busca = request.args.get("q", "").strip()
    if busca:
        like = f"%{busca}%"
        clientes = query(
            "SELECT * FROM clientes WHERE nome LIKE ? OR cnpj_cpf LIKE ? OR email LIKE ? ORDER BY nome",
            (like, like, like),
        )
    else:
        clientes = query("SELECT * FROM clientes ORDER BY nome")
    return render_template("clientes/lista.html", clientes=clientes, busca=busca)


@bp.route("/novo", methods=["GET", "POST"])
@bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
def form(cliente_id=None):
    cliente = obter(cliente_id) if cliente_id else None
    if request.method == "POST":
        valores = [txt(c) for c in CAMPOS]
        if not valores[0]:
            flash("Informe o nome do cliente.", "erro")
            return render_template("clientes/form.html", cliente=request.form)
        if cliente:
            sets = ", ".join(f"{c}=?" for c in CAMPOS)
            execute(f"UPDATE clientes SET {sets} WHERE id=?", valores + [cliente_id])
        else:
            cols = ", ".join(CAMPOS)
            marks = ", ".join("?" for _ in CAMPOS)
            cliente_id = execute(f"INSERT INTO clientes ({cols}) VALUES ({marks})", valores)
        flash("Cliente salvo.", "ok")
        destino = request.args.get("voltar")
        if destino and destino.startswith("/"):
            return redirect(destino)
        return redirect(url_for("clientes.lista"))
    return render_template("clientes/form.html", cliente=cliente)


@bp.route("/<int:cliente_id>/excluir", methods=["POST"])
def excluir(cliente_id):
    obter(cliente_id)
    try:
        execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
        flash("Cliente excluído.", "ok")
    except IntegrityError:
        flash("Cliente possui orçamentos, embarques ou notas vinculados e não pode ser excluído.", "erro")
    return redirect(url_for("clientes.lista"))
