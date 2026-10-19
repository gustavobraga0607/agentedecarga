"""Regras de cálculo de frete (funções puras, sem acesso a banco)."""

# Fator de cubagem em kg por m³ usado para obter o peso cubado.
FATOR_CUBAGEM = {
    "aereo": 1_000_000 / 6000,  # IATA 1:6000 -> 166,67 kg/m³
    "maritimo_lcl": 1000,  # 1 m³ = 1 t (W/M)
    "maritimo_fcl": 1000,
    "rodoviario": 300,  # padrão rodoviário internacional
}

TIPOS_CALCULO = {
    "fixo": "Valor fixo",
    "por_kg": "Por kg taxável",
    "por_cbm": "Por m³",
    "por_wm": "Por W/M (t ou m³, o maior)",
    "por_unidade": "Por unidade/contêiner",
    "pct_mercadoria": "% sobre valor da mercadoria",
}


def resumo_carga(volumes, modal):
    """Retorna peso bruto, cubagem (m³), peso cubado e peso taxável."""
    peso = sum(v["quantidade"] * v["peso_kg"] for v in volumes)
    cbm = sum(
        v["quantidade"] * v["comprimento_cm"] * v["largura_cm"] * v["altura_cm"] / 1_000_000
        for v in volumes
    )
    peso_cubado = cbm * FATOR_CUBAGEM.get(modal, 1000)
    return {
        "peso_bruto": round(peso, 2),
        "cubagem": round(cbm, 4),
        "peso_cubado": round(peso_cubado, 2),
        "peso_taxavel": round(max(peso, peso_cubado), 2),
        "wm": round(max(cbm, peso / 1000), 4),
    }


def taxa_para_brl(moeda, taxa_usd, taxa_eur):
    return {"BRL": 1.0, "USD": taxa_usd, "EUR": taxa_eur}.get(moeda, 1.0)


def calcular_item(item, carga, valor_mercadoria_brl, taxa_usd, taxa_eur, margem_pct):
    """Calcula custo (moeda original e BRL) e preço de venda em BRL de uma taxa."""
    tipo = item["tipo_calculo"]
    vu = item["valor_unitario"]
    taxa = taxa_para_brl(item["moeda"], taxa_usd, taxa_eur)
    if tipo == "por_kg":
        custo = vu * carga["peso_taxavel"]
    elif tipo == "por_cbm":
        custo = vu * carga["cubagem"]
    elif tipo == "por_wm":
        custo = vu * carga["wm"]
    elif tipo == "por_unidade":
        custo = vu * item["quantidade"]
    elif tipo == "pct_mercadoria":
        # percentual sobre o valor da mercadoria, convertido para a moeda da taxa
        custo = (valor_mercadoria_brl * vu / 100) / taxa
    else:
        custo = vu
    custo = max(custo, item.get("minimo") or 0)
    custo_brl = custo * taxa
    return {
        "custo_moeda": round(custo, 2),
        "custo_brl": round(custo_brl, 2),
        "venda_brl": round(custo_brl * (1 + margem_pct / 100), 2),
    }


def calcular_orcamento(orc, volumes, itens):
    carga = resumo_carga(volumes, orc["modal"])
    valor_merc_brl = orc["valor_mercadoria"] * taxa_para_brl(
        orc["moeda_mercadoria"], orc["taxa_usd"], orc["taxa_eur"]
    )
    calculados = []
    for item in itens:
        res = calcular_item(
            item, carga, valor_merc_brl, orc["taxa_usd"], orc["taxa_eur"], orc["margem_pct"]
        )
        calculados.append({**item, **res})
    total_custo = round(sum(i["custo_brl"] for i in calculados), 2)
    total_venda = round(sum(i["venda_brl"] for i in calculados), 2)
    return {
        "carga": carga,
        "itens": calculados,
        "total_custo_brl": total_custo,
        "total_venda_brl": total_venda,
        "lucro_brl": round(total_venda - total_custo, 2),
    }
