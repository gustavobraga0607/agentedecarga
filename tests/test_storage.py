import io
import json
from unittest import mock

from app import storage

TOKEN = "vercel_blob_rw_LojaTeste123_segredo"


class Resposta(io.BytesIO):
    def __init__(self, corpo, tipo="application/json"):
        super().__init__(corpo)
        self.headers = {"content-type": tipo}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_blob_envia_le_e_remove(app):
    app.config["BLOB_READ_WRITE_TOKEN"] = TOKEN
    url_blob = "https://lojateste123.private.blob.vercel-storage.com/agentedecarga/x-abc.pdf"
    chamadas = []

    def falso(req, timeout):
        chamadas.append(req)
        if req.get_method() == "PUT":
            return Resposta(json.dumps({"url": url_blob}).encode())
        if req.full_url == url_blob:
            return Resposta(b"%PDF", "application/pdf")
        return Resposta(b"{}")

    with app.app_context(), mock.patch("urllib.request.urlopen", falso):
        ref = storage.salvar(b"%PDF", "pdf")
        assert ref == url_blob
        put = chamadas[0]
        assert put.full_url.startswith("https://vercel.com/api/blob/?pathname=agentedecarga%2F")
        assert put.get_header("Authorization") == f"Bearer {TOKEN}"
        assert put.get_header("X-vercel-blob-access") == "private"
        assert storage.ler(ref) == (b"%PDF", "application/pdf")
        storage.remover(ref)
        assert chamadas[-1].full_url == "https://vercel.com/api/blob/delete"
        assert json.loads(chamadas[-1].data) == {"urls": [url_blob]}
        # referências fora do domínio do Blob nunca são buscadas
        assert storage.ler("https://exemplo.com/x.pdf") is None


def test_armazenamento_local(app):
    with app.app_context():
        ref = storage.salvar(b"conteudo", "txt")
        assert storage.ler(ref) == (b"conteudo", "text/plain")
        storage.remover(ref)
        assert storage.ler(ref) is None
