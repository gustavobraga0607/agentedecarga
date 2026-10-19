"""Popula o banco com dados de demonstração: python seed.py"""
from datetime import date, timedelta

from app import create_app
from app.db import execute, query
from app.views.orcamentos import TAXAS_PADRAO, salvar

app = create_app()
hoje = date.today()
d = lambda n: (hoje + timedelta(days=n)).isoformat()  # noqa: E731

with app.app_context():
    if query("SELECT 1 FROM clientes LIMIT 1", one=True):
        raise SystemExit("Banco já possui dados.")
    execute("""UPDATE empresa SET razao_social='Atlântico Cargo Agenciamento Ltda', nome_fantasia='Atlântico Cargo',
               cnpj='12.345.678/0001-90', inscricao_municipal='1.234.567-8', municipio='Santos', uf='SP',
               codigo_municipio_ibge='3548500', email='comercial@atlanticocargo.com.br' WHERE id=1""")
    clientes = [
        ("Conexão Comercial Atacadista Ltda", "11.222.333/0001-44", "São Paulo", "SP"),
        ("Evoluir Atacadista para Construção Ltda", "22.333.444/0001-55", "Curitiba", "PR"),
        ("Norte Sul Empreendimentos Ltda", "33.444.555/0001-66", "Recife", "PE"),
        ("Import Gym e Cia Ltda", "44.555.666/0001-77", "Campinas", "SP"),
    ]
    for nome, doc, cidade, uf in clientes:
        execute("INSERT INTO clientes (nome, cnpj_cpf, cidade, uf, email) VALUES (?,?,?,?,?)",
                (nome, doc, cidade, uf, "compras@" + nome.split()[0].lower() + ".com.br"))

    def orc(cliente, modal, origem, destino, vols, merc, valor):
        itens = [dict(zip(("descricao", "tipo_calculo", "moeda", "valor_unitario", "quantidade", "minimo"), t))
                 for t in TAXAS_PADRAO[modal]]
        dados = {"cliente_id": cliente, "tipo_operacao": "importacao", "modal": modal, "origem": origem,
                 "destino": destino, "incoterm": "FOB", "mercadoria": merc, "valor_mercadoria": valor,
                 "moeda_mercadoria": "USD", "taxa_usd": 5.40, "taxa_eur": 5.90, "margem_pct": 18,
                 "validade": d(15), "transit_time": "35 dias", "observacoes": ""}
        volumes = [dict(zip(("quantidade", "comprimento_cm", "largura_cm", "altura_cm", "peso_kg"), v)) for v in vols]
        return salvar(None, dados, volumes, itens)

    o1 = orc(1, "maritimo_lcl", "Shanghai, CN", "Santos, BR", [(10, 120, 100, 110, 180)], "Revestimentos cerâmicos", 18000)
    o2 = orc(2, "maritimo_fcl", "Ningbo, CN", "Paranaguá, BR", [(1, 1200, 235, 239, 18000)], "Ferragens", 42000)
    o3 = orc(3, "aereo", "Miami, US", "Viracopos, BR", [(4, 80, 60, 50, 35)], "Peças eletrônicas", 25000)
    orc(4, "maritimo_lcl", "Qingdao, CN", "Itajaí, BR", [(6, 100, 100, 120, 220)], "Equipamentos fitness", 15000)
    execute("UPDATE orcamentos SET status='enviado' WHERE id=4")

    embarques = [
        (o1, 1, "maritimo_lcl", "Shanghai, CN", "Santos, BR", "em_transito", "MSC", "MSC ARINA / 432W", "SHA0098812", "MEDU4412398", "ATL260045", "MSCU7781234", d(-20), d(6), d(-19), None),
        (o2, 2, "maritimo_fcl", "Ningbo, CN", "Paranaguá, BR", "entregue", "COSCO", "COSCO TAICANG / 019E", "COSU6508593010", "COSU6508593010", "ATL260031", "CSNU1234567", d(-60), d(-20), d(-60), d(-21)),
        (o3, 3, "aereo", "Miami, US", "Viracopos, BR", "booking_confirmado", "LATAM Cargo", "LA8181", "", "045-12345675", "ATL-H-2210", "", d(2), d(3), None, None),
    ]
    for (oid, cid, modal, ori, dst, st, transp, nv, bk, mst, hs, cont, etd, eta, atd, ata) in embarques:
        o = query("SELECT * FROM orcamentos WHERE id=?", (oid,), one=True)
        ref = f"EMB-{hoje.year}-{oid:04d}"
        eid = execute("""INSERT INTO embarques (referencia, cliente_id, orcamento_id, modal, origem, destino, status,
            transportador, navio_voo, booking, master, house, containers, etd, eta, atd, ata, mercadoria, peso_kg,
            cubagem, valor_servico_brl, incoterm, volumes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ref, cid, oid, modal, ori, dst, st, transp, nv, bk, mst, hs, cont, etd, eta, atd, ata, o["mercadoria"],
             o["peso_bruto"], o["cubagem"], o["total_venda_brl"], "FOB", 10))
        execute("UPDATE orcamentos SET status='aprovado' WHERE id=?", (oid,))
        execute("INSERT INTO embarque_eventos (embarque_id, data, status, descricao) VALUES (?,?,?,?)",
                (eid, d(-30), "aguardando_booking", "Embarque aberto"))
        if atd:
            execute("INSERT INTO embarque_eventos (embarque_id, data, status, local, descricao) VALUES (?,?,?,?,?)",
                    (eid, atd, "embarcado", ori, "Carga embarcada"))
        execute("INSERT INTO embarque_eventos (embarque_id, data, status, descricao) VALUES (?,?,?,?)",
                (eid, d(-1), st, "Atualização de status"))
    print("Dados de demonstração criados.")
