from .calc import TIPOS_CALCULO

MODAIS = {
    "maritimo_fcl": "Marítimo FCL",
    "maritimo_lcl": "Marítimo LCL",
    "aereo": "Aéreo",
    "rodoviario": "Rodoviário",
}

OPERACOES = {"importacao": "Importação", "exportacao": "Exportação"}

INCOTERMS = ["EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"]

MOEDAS = {"USD": "USD", "EUR": "EUR", "BRL": "BRL"}

STATUS_ORCAMENTO = {
    "rascunho": "Rascunho",
    "enviado": "Enviado ao cliente",
    "aprovado": "Aprovado",
    "recusado": "Recusado",
    "expirado": "Expirado",
}

# Ordem importa: é a linha do tempo do embarque
STATUS_EMBARQUE = {
    "aguardando_booking": "Aguardando booking",
    "booking_confirmado": "Booking confirmado",
    "coletado": "Carga coletada",
    "embarcado": "Embarcado",
    "em_transito": "Em trânsito",
    "chegada_destino": "Chegou ao destino",
    "desembaracado": "Desembaraçado",
    "entregue": "Entregue",
    "cancelado": "Cancelado",
}

TIPOS_DOCUMENTO = {
    "bl": "BL / AWB / CRT",
    "invoice": "Commercial Invoice",
    "packing_list": "Packing List",
    "certificado_origem": "Certificado de Origem",
    "di_due": "DI / DUIMP / DU-E",
    "seguro": "Apólice de Seguro",
    "nfse": "NF-S",
    "outro": "Outro",
}

STATUS_NFSE = {"emitida": "Emitida", "cancelada": "Cancelada"}
ORIGEM_NFSE = {"interna": "Emitida no sistema", "externa": "Anexada (emitida externamente)"}

LABELS = {
    "modal": MODAIS,
    "operacao": OPERACOES,
    "status_orcamento": STATUS_ORCAMENTO,
    "status_embarque": STATUS_EMBARQUE,
    "tipo_documento": TIPOS_DOCUMENTO,
    "tipo_calculo": TIPOS_CALCULO,
    "status_nfse": STATUS_NFSE,
    "origem_nfse": ORIGEM_NFSE,
}
