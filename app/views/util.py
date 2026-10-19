import uuid
from pathlib import Path

from flask import current_app, request
from werkzeug.utils import secure_filename

EXTENSOES_PERMITIDAS = {"pdf", "xml", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx", "txt", "zip"}


def num(nome, padrao=0.0, origem=None):
    """Lê um número do formulário aceitando vírgula ou ponto decimal."""
    valor = (origem or request.form).get(nome, "")
    return para_float(valor, padrao)


def para_float(valor, padrao=0.0):
    valor = str(valor or "").strip()
    if not valor:
        return padrao
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except ValueError:
        return padrao


def txt(nome):
    return request.form.get(nome, "").strip()


def data_ou_none(nome):
    return request.form.get(nome, "").strip() or None


def extensao(nome):
    return nome.rsplit(".", 1)[-1].lower() if "." in nome else ""


def salvar_upload(arquivo):
    """Salva um arquivo enviado e retorna (nome_armazenado, nome_original).

    Retorna None quando não há arquivo ou a extensão não é permitida.
    """
    if not arquivo or not arquivo.filename:
        return None
    ext = extensao(arquivo.filename)
    if ext not in EXTENSOES_PERMITIDAS:
        return None
    nome = f"{uuid.uuid4().hex}.{ext}"
    arquivo.save(Path(current_app.config["UPLOAD_FOLDER"]) / nome)
    return nome, secure_filename(arquivo.filename) or nome


def salvar_bytes(conteudo, ext):
    nome = f"{uuid.uuid4().hex}.{ext}"
    (Path(current_app.config["UPLOAD_FOLDER"]) / nome).write_bytes(conteudo)
    return nome


def remover_upload(nome):
    if nome:
        (Path(current_app.config["UPLOAD_FOLDER"]) / nome).unlink(missing_ok=True)
