import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def cliente_id(client):
    client.post("/clientes/novo", data={"nome": "Importadora Teste Ltda", "cnpj_cpf": "12.345.678/0001-90"})
    return 1
