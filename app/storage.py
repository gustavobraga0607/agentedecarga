"""Armazenamento de anexos: pasta local ou Vercel Blob (quando há BLOB_READ_WRITE_TOKEN).

Cada arquivo é identificado por uma referência guardada no banco:
- local: o nome do arquivo na pasta de uploads (ex.: "3f2a....pdf");
- Vercel Blob: a URL completa do blob.
Os arquivos são sempre servidos pela aplicação (rota /arquivos), que
exige login, mesmo quando o blob é privado.
"""

import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from flask import current_app

API_BLOB = "https://vercel.com/api/blob"
VERSAO_API_BLOB = "13"
PASTA_BLOB = "agentedecarga"


def _token():
    return current_app.config.get("BLOB_READ_WRITE_TOKEN")


def usa_blob():
    return bool(_token())


def tipo_mime(nome):
    return mimetypes.guess_type(nome)[0] or "application/octet-stream"


def _requisicao_blob(url, metodo="GET", corpo=None, cabecalhos=None):
    req = urllib.request.Request(url, data=corpo, method=metodo, headers={
        "authorization": f"Bearer {_token()}",
        "x-api-version": VERSAO_API_BLOB,
        **(cabecalhos or {}),
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), resp.headers.get("content-type")


def _enviar_blob(nome, conteudo, content_type):
    caminho = urllib.parse.urlencode({"pathname": f"{PASTA_BLOB}/{nome}"})
    erro = None
    # Lojas novas aceitam blobs privados; lojas públicas recusam e usamos "public"
    for acesso in ("private", "public"):
        try:
            corpo, _ = _requisicao_blob(f"{API_BLOB}/?{caminho}", "PUT", conteudo, {
                "x-vercel-blob-access": acesso,
                "x-content-type": content_type,
                "x-add-random-suffix": "1",
            })
            return json.loads(corpo)["url"]
        except urllib.error.HTTPError as exc:
            erro = exc
            if exc.code not in (400, 403):
                break
    raise RuntimeError(f"Falha ao enviar arquivo ao Vercel Blob: {erro}")


def salvar(conteudo, extensao):
    """Grava os bytes e retorna a referência do arquivo."""
    nome = f"{uuid.uuid4().hex}.{extensao}"
    if usa_blob():
        return _enviar_blob(nome, conteudo, tipo_mime(nome))
    (Path(current_app.config["UPLOAD_FOLDER"]) / nome).write_bytes(conteudo)
    return nome


def referencia_valida(ref):
    if not ref:
        return False
    if usa_blob():
        url = urllib.parse.urlparse(ref)
        return url.scheme == "https" and url.hostname.endswith(".blob.vercel-storage.com")
    return "/" not in ref and "\\" not in ref and not ref.startswith(".")


def ler(ref):
    """Retorna (bytes, content_type) do arquivo, ou None se não existir."""
    if not referencia_valida(ref):
        return None
    if usa_blob():
        try:
            return _requisicao_blob(ref)
        except urllib.error.HTTPError:
            return None
    caminho = Path(current_app.config["UPLOAD_FOLDER"]) / ref
    if not caminho.is_file():
        return None
    return caminho.read_bytes(), tipo_mime(ref)


def remover(ref):
    if not referencia_valida(ref):
        return
    if usa_blob():
        try:
            _requisicao_blob(f"{API_BLOB}/delete", "POST", json.dumps({"urls": [ref]}).encode(),
                             {"content-type": "application/json"})
        except urllib.error.URLError:
            pass  # arquivo órfão no Blob não impede a exclusão do registro
        return
    (Path(current_app.config["UPLOAD_FOLDER"]) / ref).unlink(missing_ok=True)
