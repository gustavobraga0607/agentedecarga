-- Versão Postgres de schema.sql (mantenha as duas em sincronia)
CREATE TABLE IF NOT EXISTS empresa (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    razao_social TEXT NOT NULL DEFAULT 'Minha Empresa de Cargas Ltda',
    nome_fantasia TEXT DEFAULT '',
    cnpj TEXT DEFAULT '',
    inscricao_municipal TEXT DEFAULT '',
    endereco TEXT DEFAULT '',
    municipio TEXT DEFAULT '',
    codigo_municipio_ibge TEXT DEFAULT '',
    uf TEXT DEFAULT '',
    email TEXT DEFAULT '',
    telefone TEXT DEFAULT '',
    regime_tributario TEXT DEFAULT 'simples_nacional',
    codigo_servico TEXT DEFAULT '10.05',
    descricao_servico TEXT DEFAULT 'Agenciamento, corretagem ou intermediação de bens móveis',
    aliquota_iss DOUBLE PRECISION DEFAULT 5.0,
    serie_rps TEXT DEFAULT '1',
    proximo_numero_nfse INTEGER DEFAULT 1,
    taxa_usd DOUBLE PRECISION DEFAULT 5.40,
    taxa_eur DOUBLE PRECISION DEFAULT 5.90
);

CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    cnpj_cpf TEXT DEFAULT '',
    inscricao_municipal TEXT DEFAULT '',
    email TEXT DEFAULT '',
    telefone TEXT DEFAULT '',
    contato TEXT DEFAULT '',
    endereco TEXT DEFAULT '',
    cidade TEXT DEFAULT '',
    uf TEXT DEFAULT '',
    cep TEXT DEFAULT '',
    pais TEXT DEFAULT 'Brasil',
    created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Sao_Paulo', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS orcamentos (
    id SERIAL PRIMARY KEY,
    numero TEXT NOT NULL UNIQUE,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    tipo_operacao TEXT NOT NULL DEFAULT 'importacao',
    modal TEXT NOT NULL DEFAULT 'maritimo_lcl',
    origem TEXT NOT NULL DEFAULT '',
    destino TEXT NOT NULL DEFAULT '',
    incoterm TEXT DEFAULT 'FOB',
    mercadoria TEXT DEFAULT '',
    valor_mercadoria DOUBLE PRECISION DEFAULT 0,
    moeda_mercadoria TEXT DEFAULT 'USD',
    taxa_usd DOUBLE PRECISION NOT NULL DEFAULT 5.40,
    taxa_eur DOUBLE PRECISION NOT NULL DEFAULT 5.90,
    margem_pct DOUBLE PRECISION NOT NULL DEFAULT 15,
    validade TEXT,
    transit_time TEXT DEFAULT '',
    observacoes TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'rascunho',
    peso_bruto DOUBLE PRECISION DEFAULT 0,
    cubagem DOUBLE PRECISION DEFAULT 0,
    peso_taxavel DOUBLE PRECISION DEFAULT 0,
    total_custo_brl DOUBLE PRECISION DEFAULT 0,
    total_venda_brl DOUBLE PRECISION DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Sao_Paulo', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS orcamento_volumes (
    id SERIAL PRIMARY KEY,
    orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    quantidade INTEGER NOT NULL DEFAULT 1,
    comprimento_cm DOUBLE PRECISION NOT NULL DEFAULT 0,
    largura_cm DOUBLE PRECISION NOT NULL DEFAULT 0,
    altura_cm DOUBLE PRECISION NOT NULL DEFAULT 0,
    peso_kg DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orcamento_itens (
    id SERIAL PRIMARY KEY,
    orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    tipo_calculo TEXT NOT NULL DEFAULT 'fixo',
    moeda TEXT NOT NULL DEFAULT 'USD',
    valor_unitario DOUBLE PRECISION NOT NULL DEFAULT 0,
    quantidade DOUBLE PRECISION NOT NULL DEFAULT 1,
    minimo DOUBLE PRECISION NOT NULL DEFAULT 0,
    custo_moeda DOUBLE PRECISION DEFAULT 0,
    custo_brl DOUBLE PRECISION DEFAULT 0,
    venda_brl DOUBLE PRECISION DEFAULT 0
);

CREATE TABLE IF NOT EXISTS embarques (
    id SERIAL PRIMARY KEY,
    referencia TEXT NOT NULL UNIQUE,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    orcamento_id INTEGER REFERENCES orcamentos(id),
    tipo_operacao TEXT NOT NULL DEFAULT 'importacao',
    modal TEXT NOT NULL DEFAULT 'maritimo_lcl',
    origem TEXT DEFAULT '',
    destino TEXT DEFAULT '',
    incoterm TEXT DEFAULT '',
    mercadoria TEXT DEFAULT '',
    volumes INTEGER DEFAULT 0,
    peso_kg DOUBLE PRECISION DEFAULT 0,
    cubagem DOUBLE PRECISION DEFAULT 0,
    exportador TEXT DEFAULT '',
    importador TEXT DEFAULT '',
    transportador TEXT DEFAULT '',
    navio_voo TEXT DEFAULT '',
    booking TEXT DEFAULT '',
    master TEXT DEFAULT '',
    house TEXT DEFAULT '',
    containers TEXT DEFAULT '',
    etd TEXT,
    eta TEXT,
    atd TEXT,
    ata TEXT,
    valor_servico_brl DOUBLE PRECISION DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'aguardando_booking',
    observacoes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Sao_Paulo', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS embarque_eventos (
    id SERIAL PRIMARY KEY,
    embarque_id INTEGER NOT NULL REFERENCES embarques(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    status TEXT,
    local TEXT DEFAULT '',
    descricao TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS embarque_documentos (
    id SERIAL PRIMARY KEY,
    embarque_id INTEGER NOT NULL REFERENCES embarques(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL DEFAULT 'outro',
    nome_original TEXT NOT NULL,
    arquivo TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Sao_Paulo', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE IF NOT EXISTS nfse (
    id SERIAL PRIMARY KEY,
    origem TEXT NOT NULL DEFAULT 'interna',
    numero TEXT NOT NULL,
    serie_rps TEXT DEFAULT '',
    codigo_verificacao TEXT DEFAULT '',
    data_emissao TEXT NOT NULL,
    competencia TEXT NOT NULL,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    embarque_id INTEGER REFERENCES embarques(id),
    codigo_servico TEXT DEFAULT '',
    discriminacao TEXT DEFAULT '',
    valor_servicos DOUBLE PRECISION NOT NULL DEFAULT 0,
    deducoes DOUBLE PRECISION NOT NULL DEFAULT 0,
    base_calculo DOUBLE PRECISION NOT NULL DEFAULT 0,
    aliquota_iss DOUBLE PRECISION NOT NULL DEFAULT 0,
    valor_iss DOUBLE PRECISION NOT NULL DEFAULT 0,
    iss_retido INTEGER NOT NULL DEFAULT 0,
    valor_pis DOUBLE PRECISION NOT NULL DEFAULT 0,
    valor_cofins DOUBLE PRECISION NOT NULL DEFAULT 0,
    valor_csll DOUBLE PRECISION NOT NULL DEFAULT 0,
    valor_ir DOUBLE PRECISION NOT NULL DEFAULT 0,
    valor_inss DOUBLE PRECISION NOT NULL DEFAULT 0,
    valor_liquido DOUBLE PRECISION NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'emitida',
    motivo_cancelamento TEXT DEFAULT '',
    arquivo_pdf TEXT,
    arquivo_pdf_nome TEXT,
    arquivo_xml TEXT,
    arquivo_xml_nome TEXT,
    created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'America/Sao_Paulo', 'YYYY-MM-DD HH24:MI:SS'))
);

INSERT INTO empresa (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
