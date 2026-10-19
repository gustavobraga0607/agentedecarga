"""Cálculo de tributos, geração e leitura de XML de NFS-e.

A emissão interna gera o número da nota, o código de verificação e um XML de
DPS inspirado no leiaute do Padrão Nacional da NFS-e (ambiente de
homologação). A transmissão real à prefeitura / Ambiente de Dados Nacional
exige certificado digital A1 e credenciamento, e deve ser plugada em
`transmitir()`.
"""

import secrets
import xml.etree.ElementTree as ET

# Alíquotas padrão de retenções federais (Lei 10.833/2003 e IN RFB 1.234/2012)
RETENCOES_PADRAO = {"pis": 0.65, "cofins": 3.0, "csll": 1.0, "ir": 1.5}


def calcular_tributos(valor_servicos, deducoes, aliquota_iss, iss_retido, reter_federais, inss_pct=0.0):
    base = max(valor_servicos - deducoes, 0)
    iss = round(base * aliquota_iss / 100, 2)
    ret = {k: 0.0 for k in RETENCOES_PADRAO}
    if reter_federais:
        ret = {k: round(valor_servicos * p / 100, 2) for k, p in RETENCOES_PADRAO.items()}
    inss = round(valor_servicos * inss_pct / 100, 2)
    total_retido = sum(ret.values()) + inss + (iss if iss_retido else 0)
    return {
        "base_calculo": round(base, 2),
        "valor_iss": iss,
        "valor_pis": ret["pis"],
        "valor_cofins": ret["cofins"],
        "valor_csll": ret["csll"],
        "valor_ir": ret["ir"],
        "valor_inss": inss,
        "valor_liquido": round(valor_servicos - total_retido, 2),
    }


def gerar_codigo_verificacao():
    return secrets.token_hex(4).upper()


def _so_digitos(s):
    return "".join(c for c in (s or "") if c.isdigit())


def gerar_xml_dps(nota, empresa, cliente):
    """Monta um XML de DPS (Declaração de Prestação de Serviço)."""
    ns = "http://www.sped.fazenda.gov.br/nfse"
    ET.register_namespace("", ns)
    q = lambda tag: f"{{{ns}}}{tag}"  # noqa: E731

    dps = ET.Element(q("DPS"), {"versao": "1.00"})
    inf = ET.SubElement(dps, q("infDPS"), {"Id": f"DPS{nota['numero']}"})

    def sub(parent, tag, text=None):
        el = ET.SubElement(parent, q(tag))
        if text is not None:
            el.text = str(text)
        return el

    sub(inf, "tpAmb", "2")  # 2 = homologação
    sub(inf, "dhEmi", nota["data_emissao"])
    sub(inf, "serie", nota["serie_rps"])
    sub(inf, "nDPS", nota["numero"])
    sub(inf, "dCompet", nota["competencia"])
    sub(inf, "cLocEmi", empresa["codigo_municipio_ibge"] or "")

    prest = sub(inf, "prest")
    sub(prest, "CNPJ", _so_digitos(empresa["cnpj"]))
    sub(prest, "IM", empresa["inscricao_municipal"])
    sub(prest, "xNome", empresa["razao_social"])

    toma = sub(inf, "toma")
    doc = _so_digitos(cliente["cnpj_cpf"])
    sub(toma, "CNPJ" if len(doc) == 14 else "CPF", doc)
    sub(toma, "xNome", cliente["nome"])
    if cliente["email"]:
        sub(toma, "email", cliente["email"])

    serv = sub(inf, "serv")
    cserv = sub(serv, "cServ")
    sub(cserv, "cTribNac", _so_digitos(nota["codigo_servico"]).ljust(6, "0"))
    sub(cserv, "xDescServ", nota["discriminacao"])

    valores = sub(inf, "valores")
    vsp = sub(valores, "vServPrest")
    sub(vsp, "vServ", f"{nota['valor_servicos']:.2f}")
    if nota["deducoes"]:
        sub(sub(valores, "vDedRed"), "vDR", f"{nota['deducoes']:.2f}")
    trib = sub(valores, "trib")
    tmun = sub(trib, "tribMun")
    sub(tmun, "tribISSQN", "1")
    sub(tmun, "pAliq", f"{nota['aliquota_iss']:.2f}")
    sub(tmun, "tpRetISSQN", "2" if nota["iss_retido"] else "1")
    fed = sub(trib, "tribFed")
    for tag, campo in (("vRetIRRF", "valor_ir"), ("vRetCSLL", "valor_csll"),
                       ("vPIS", "valor_pis"), ("vCOFINS", "valor_cofins"), ("vRetCP", "valor_inss")):
        if nota[campo]:
            sub(fed, tag, f"{nota[campo]:.2f}")

    ET.indent(dps)
    return ET.tostring(dps, encoding="utf-8", xml_declaration=True)


def transmitir(xml_bytes):
    """Ponto de integração com o webservice da prefeitura / ADN.

    Sem integração configurada, a nota fica registrada apenas no sistema.
    """
    return {"transmitida": False, "mensagem": "Integração com webservice não configurada."}


# ---------------------------------------------------------------- leitura
_CAMPOS_XML = {
    # Padrão Nacional | ABRASF
    "numero": ("nNFSe", "Numero"),
    "codigo_verificacao": ("cVerif", "CodigoVerificacao"),
    "data_emissao": ("dhProc", "dhEmi", "DataEmissao"),
    "competencia": ("dCompet", "Competencia"),
    "valor_servicos": ("vServ", "ValorServicos"),
    "valor_iss": ("vISSQN", "ValorIss"),
    "aliquota_iss": ("pAliq", "pAliqAplic", "Aliquota"),
    "valor_liquido": ("vLiq", "ValorLiquidoNfse"),
    "discriminacao": ("xDescServ", "Discriminacao"),
    "documento_tomador": ("CNPJ", "Cnpj", "CPF", "Cpf"),
}


def ler_xml_nfse(conteudo):
    """Extrai os principais campos de um XML de NFS-e (Padrão Nacional ou ABRASF).

    Retorna um dict apenas com os campos encontrados; nunca levanta exceção
    para XML com estrutura desconhecida.
    """
    try:
        raiz = ET.fromstring(conteudo)
    except ET.ParseError:
        return {}
    encontrados = {}
    for el in raiz.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if el.text is None or not el.text.strip():
            continue
        for campo, nomes in _CAMPOS_XML.items():
            if tag in nomes and campo not in encontrados:
                encontrados[campo] = el.text.strip()
    # o primeiro CNPJ costuma ser o do prestador; buscamos o do tomador
    for bloco in raiz.iter():
        tag = bloco.tag.rsplit("}", 1)[-1]
        if tag in ("toma", "Tomador", "TomadorServico"):
            for el in bloco.iter():
                t = el.tag.rsplit("}", 1)[-1]
                if t in ("CNPJ", "Cnpj", "CPF", "Cpf") and el.text:
                    encontrados["documento_tomador"] = el.text.strip()
                    break
            break
    for campo in ("valor_servicos", "valor_iss", "aliquota_iss", "valor_liquido"):
        if campo in encontrados:
            try:
                encontrados[campo] = float(encontrados[campo].replace(",", "."))
            except ValueError:
                del encontrados[campo]
    for campo in ("data_emissao", "competencia"):
        if campo in encontrados:
            encontrados[campo] = encontrados[campo][:10]
    return encontrados
