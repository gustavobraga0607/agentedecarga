import io

from app.db import query


def form_orcamento(cliente_id):
    return {
        "cliente_id": cliente_id, "tipo_operacao": "importacao", "modal": "aereo",
        "origem": "Miami, US", "destino": "Viracopos, BR", "incoterm": "FCA",
        "taxa_usd": "5", "taxa_eur": "6", "margem_pct": "20", "valor_mercadoria": "0",
        "vol_quantidade[]": ["1"], "vol_comprimento_cm[]": ["100"], "vol_largura_cm[]": ["60"],
        "vol_altura_cm[]": ["50"], "vol_peso_kg[]": ["40"],
        "item_descricao[]": ["Frete aéreo"], "item_tipo_calculo[]": ["por_kg"], "item_moeda[]": ["USD"],
        "item_valor_unitario[]": ["2"], "item_quantidade[]": ["1"], "item_minimo[]": ["0"],
    }


def test_paginas_principais(client):
    for url in ["/", "/clientes/", "/orcamentos/", "/orcamentos/novo", "/embarques/", "/embarques/novo",
                "/nfse/", "/nfse/emitir", "/nfse/anexar", "/empresa"]:
        assert client.get(url).status_code == 200, url


def test_fluxo_orcamento_embarque_nfse(app, client, cliente_id):
    r = client.post("/orcamentos/novo", data=form_orcamento(cliente_id))
    assert r.status_code == 302
    with app.app_context():
        orc = query("SELECT * FROM orcamentos", one=True)
    # 0,3 m³ x 166,67 = 50 kg cubado > 40 kg reais -> 50 kg x USD 2 x 5 = R$ 500, +20%
    assert orc["numero"].startswith("ORC-")
    assert orc["peso_taxavel"] == 50
    assert orc["total_venda_brl"] == 600
    assert client.get(f"/orcamentos/{orc['id']}").status_code == 200
    assert client.get(f"/orcamentos/{orc['id']}/imprimir").status_code == 200

    r = client.get(f"/embarques/novo?orcamento_id={orc['id']}")
    assert b"Miami, US" in r.data
    r = client.post("/embarques/novo", data={
        "orcamento_id": orc["id"], "cliente_id": cliente_id, "modal": "aereo", "tipo_operacao": "importacao",
        "origem": "Miami, US", "destino": "Viracopos, BR", "valor_servico_brl": "600", "house": "HAWB123",
    })
    assert r.status_code == 302
    with app.app_context():
        emb = query("SELECT * FROM embarques", one=True)
        assert query("SELECT status FROM orcamentos", one=True)["status"] == "aprovado"
    assert emb["referencia"].startswith("EMB-")

    client.post(f"/embarques/{emb['id']}/eventos", data={"status": "embarcado", "data": "2026-10-10"})
    client.post(f"/embarques/{emb['id']}/documentos", data={
        "tipo": "bl", "arquivos": (io.BytesIO(b"%PDF-1.4"), "hawb.pdf")}, content_type="multipart/form-data")
    with app.app_context():
        emb = query("SELECT * FROM embarques", one=True)
        assert emb["status"] == "embarcado" and emb["atd"] == "2026-10-10"
        assert query("SELECT COUNT(*) c FROM embarque_documentos", one=True)["c"] == 1
    assert client.get(f"/embarques/{emb['id']}").status_code == 200

    r = client.get(f"/nfse/emitir?embarque_id={emb['id']}")
    assert b"HAWB123" in r.data
    r = client.post("/nfse/emitir", data={
        "cliente_id": cliente_id, "embarque_id": emb["id"], "valor_servicos": "600", "aliquota_iss": "5",
        "discriminacao": "Agenciamento de carga", "competencia": "2026-10-19", "codigo_servico": "10.05",
    })
    assert r.status_code == 302
    with app.app_context():
        nota = query("SELECT * FROM nfse", one=True)
        assert query("SELECT proximo_numero_nfse n FROM empresa", one=True)["n"] == 2
    assert nota["numero"] == "1" and nota["valor_iss"] == 30 and nota["arquivo_xml"]
    assert client.get(f"/nfse/{nota['id']}").status_code == 200
    assert client.get(f"/nfse/{nota['id']}/imprimir").status_code == 200
    xml = client.get("/arquivos", query_string={"ref": nota["arquivo_xml"]})
    assert b"<vServ>600.00</vServ>" in xml.data

    client.post(f"/nfse/{nota['id']}/cancelar", data={"motivo": "curto"})
    with app.app_context():
        assert query("SELECT status FROM nfse", one=True)["status"] == "emitida"
    client.post(f"/nfse/{nota['id']}/cancelar", data={"motivo": "Valor incorreto informado na nota"})
    with app.app_context():
        assert query("SELECT status FROM nfse", one=True)["status"] == "cancelada"


def test_anexar_nfse_por_xml_identifica_tomador(app, client, cliente_id):
    xml = b"""<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse"><infNFSe><nNFSe>555</nNFSe>
      <DPS><infDPS><dCompet>2026-09-30</dCompet><prest><CNPJ>99999999000199</CNPJ></prest>
      <toma><CNPJ>12345678000190</CNPJ></toma><serv><cServ><xDescServ>Frete</xDescServ></cServ></serv>
      <valores><vServPrest><vServ>2500.00</vServ></vServPrest></valores></infDPS></DPS></infNFSe></NFSe>"""
    r = client.post("/nfse/anexar", data={
        "arquivo_xml": (io.BytesIO(xml), "nota555.xml"),
        "arquivo_pdf": (io.BytesIO(b"%PDF-1.4"), "nota555.pdf"),
    }, content_type="multipart/form-data")
    assert r.status_code == 302
    with app.app_context():
        nota = query("SELECT * FROM nfse", one=True)
    assert nota["numero"] == "555"
    assert nota["cliente_id"] == cliente_id
    assert nota["valor_servicos"] == 2500
    assert nota["origem"] == "externa" and nota["arquivo_pdf"] and nota["arquivo_xml"]


def test_arquivo_bloqueia_path_traversal(client):
    assert client.get("/arquivos", query_string={"ref": "../segredo"}).status_code == 404
    assert client.get("/arquivos", query_string={"ref": "/etc/passwd"}).status_code == 404


def test_login_exigido_quando_ha_senha(app, client):
    app.config["APP_PASSWORD"] = "segredo123"
    r = client.get("/embarques/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert client.post("/login", data={"senha": "errada"}).status_code == 200
    r = client.post("/login?proximo=/embarques/", data={"senha": "segredo123"})
    assert r.headers["Location"] == "/embarques/"
    assert client.get("/embarques/").status_code == 200
    client.post("/sair")
    assert client.get("/embarques/").status_code == 302


def test_login_nao_redireciona_para_outro_site(app, client):
    app.config["APP_PASSWORD"] = "segredo123"
    r = client.post("/login?proximo=//evil.example", data={"senha": "segredo123"})
    assert r.headers["Location"] == "/"


def test_publicado_sem_senha_fica_bloqueado(app, client):
    app.config["EXIGIR_SENHA"] = True
    r = client.get("/")
    assert r.status_code == 503 and b"APP_PASSWORD" in r.data
