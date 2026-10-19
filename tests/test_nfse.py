from app.nfse import calcular_tributos, ler_xml_nfse


def test_tributos_sem_retencao():
    t = calcular_tributos(1000, 0, 5, iss_retido=False, reter_federais=False)
    assert t["valor_iss"] == 50
    assert t["valor_liquido"] == 1000


def test_tributos_com_retencoes():
    t = calcular_tributos(1000, 100, 2, iss_retido=True, reter_federais=True)
    assert t["base_calculo"] == 900
    assert t["valor_iss"] == 18
    assert (t["valor_pis"], t["valor_cofins"], t["valor_csll"], t["valor_ir"]) == (6.5, 30, 10, 15)
    assert t["valor_liquido"] == 1000 - 61.5 - 18


def test_ler_xml_abrasf():
    xml = b"""<?xml version="1.0"?>
    <CompNfse><Nfse><InfNfse>
      <Numero>987</Numero><CodigoVerificacao>AB12</CodigoVerificacao>
      <DataEmissao>2026-10-01T10:00:00</DataEmissao>
      <Servico><Valores><ValorServicos>1500.00</ValorServicos><ValorIss>75.00</ValorIss><Aliquota>5</Aliquota></Valores>
      <Discriminacao>Agenciamento</Discriminacao></Servico>
      <PrestadorServico><IdentificacaoPrestador><Cnpj>11111111000111</Cnpj></IdentificacaoPrestador></PrestadorServico>
      <TomadorServico><IdentificacaoTomador><CpfCnpj><Cnpj>12345678000190</Cnpj></CpfCnpj></IdentificacaoTomador></TomadorServico>
    </InfNfse></Nfse></CompNfse>"""
    d = ler_xml_nfse(xml)
    assert d["numero"] == "987"
    assert d["valor_servicos"] == 1500.0
    assert d["data_emissao"] == "2026-10-01"
    assert d["documento_tomador"] == "12345678000190"


def test_ler_xml_invalido():
    assert ler_xml_nfse(b"nao e xml") == {}
