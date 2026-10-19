import pytest

from app.calc import calcular_orcamento, resumo_carga

VOLUMES = [{"quantidade": 2, "comprimento_cm": 120, "largura_cm": 100, "altura_cm": 100, "peso_kg": 150}]


def test_resumo_carga_aereo_usa_1_para_6000():
    carga = resumo_carga(VOLUMES, "aereo")
    assert carga["peso_bruto"] == 300
    assert carga["cubagem"] == pytest.approx(2.4)
    assert carga["peso_cubado"] == pytest.approx(400)
    assert carga["peso_taxavel"] == pytest.approx(400)


def test_resumo_carga_maritimo_wm():
    carga = resumo_carga(VOLUMES, "maritimo_lcl")
    assert carga["wm"] == pytest.approx(2.4)  # 2,4 m³ > 0,3 t
    assert carga["peso_taxavel"] == pytest.approx(2400)


def test_calcular_orcamento_minimo_cambio_e_margem():
    orc = {"modal": "maritimo_lcl", "valor_mercadoria": 10000, "moeda_mercadoria": "USD",
           "taxa_usd": 5.0, "taxa_eur": 6.0, "margem_pct": 10}
    itens = [
        {"descricao": "Frete", "tipo_calculo": "por_wm", "moeda": "USD", "valor_unitario": 10, "quantidade": 1, "minimo": 50},
        {"descricao": "THC", "tipo_calculo": "fixo", "moeda": "BRL", "valor_unitario": 100, "quantidade": 1, "minimo": 0},
        {"descricao": "Seguro", "tipo_calculo": "pct_mercadoria", "moeda": "USD", "valor_unitario": 0.5, "quantidade": 1, "minimo": 0},
        {"descricao": "Contêiner", "tipo_calculo": "por_unidade", "moeda": "EUR", "valor_unitario": 100, "quantidade": 2, "minimo": 0},
    ]
    res = calcular_orcamento(orc, VOLUMES, itens)
    frete, thc, seguro, cont = res["itens"]
    assert frete["custo_moeda"] == 50  # 2,4 W/M x 10 = 24 < mínimo 50
    assert frete["custo_brl"] == 250
    assert thc["custo_brl"] == 100
    assert seguro["custo_moeda"] == 50  # 0,5% de USD 10.000
    assert cont["custo_brl"] == 1200
    assert res["total_custo_brl"] == 1800
    assert res["total_venda_brl"] == pytest.approx(1980)
    assert res["lucro_brl"] == pytest.approx(180)
