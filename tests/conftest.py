import os

import pytest

from app import create_app

# Para rodar os testes também no Postgres: TEST_DATABASE_URL=postgresql://... pytest
BANCOS = ["sqlite"] + (["postgres"] if os.environ.get("TEST_DATABASE_URL") else [])


def limpar_postgres(url):
    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


@pytest.fixture(params=BANCOS)
def app(request, tmp_path):
    config = {
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "DATABASE_URL": None,
        "BLOB_READ_WRITE_TOKEN": None,
        "APP_PASSWORD": "",
        "EXIGIR_SENHA": False,
    }
    if request.param == "postgres":
        config["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
        limpar_postgres(config["DATABASE_URL"])
    return create_app(config)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def cliente_id(client):
    client.post("/clientes/novo", data={"nome": "Importadora Teste Ltda", "cnpj_cpf": "12.345.678/0001-90"})
    return 1
