PRAGMA foreign_keys = ON;

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
    aliquota_iss REAL DEFAULT 5.0,
    serie_rps TEXT DEFAULT '1',
    proximo_numero_nfse INTEGER DEFAULT 1,
    taxa_usd REAL DEFAULT 5.40,
    taxa_eur REAL DEFAULT 5.90
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS orcamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    tipo_operacao TEXT NOT NULL DEFAULT 'importacao',
    modal TEXT NOT NULL DEFAULT 'maritimo_lcl',
    origem TEXT NOT NULL DEFAULT '',
    destino TEXT NOT NULL DEFAULT '',
    incoterm TEXT DEFAULT 'FOB',
    mercadoria TEXT DEFAULT '',
    valor_mercadoria REAL DEFAULT 0,
    moeda_mercadoria TEXT DEFAULT 'USD',
    taxa_usd REAL NOT NULL DEFAULT 5.40,
    taxa_eur REAL NOT NULL DEFAULT 5.90,
    margem_pct REAL NOT NULL DEFAULT 15,
    validade TEXT,
    transit_time TEXT DEFAULT '',
    observacoes TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'rascunho',
    peso_bruto REAL DEFAULT 0,
    cubagem REAL DEFAULT 0,
    peso_taxavel REAL DEFAULT 0,
    total_custo_brl REAL DEFAULT 0,
    total_venda_brl REAL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS orcamento_volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    quantidade INTEGER NOT NULL DEFAULT 1,
    comprimento_cm REAL NOT NULL DEFAULT 0,
    largura_cm REAL NOT NULL DEFAULT 0,
    altura_cm REAL NOT NULL DEFAULT 0,
    peso_kg REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orcamento_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id INTEGER NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    tipo_calculo TEXT NOT NULL DEFAULT 'fixo',
    moeda TEXT NOT NULL DEFAULT 'USD',
    valor_unitario REAL NOT NULL DEFAULT 0,
    quantidade REAL NOT NULL DEFAULT 1,
    minimo REAL NOT NULL DEFAULT 0,
    custo_moeda REAL DEFAULT 0,
    custo_brl REAL DEFAULT 0,
    venda_brl REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS embarques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    peso_kg REAL DEFAULT 0,
    cubagem REAL DEFAULT 0,
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
    valor_servico_brl REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'aguardando_booking',
    observacoes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS embarque_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    embarque_id INTEGER NOT NULL REFERENCES embarques(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    status TEXT,
    local TEXT DEFAULT '',
    descricao TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS embarque_documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    embarque_id INTEGER NOT NULL REFERENCES embarques(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL DEFAULT 'outro',
    nome_original TEXT NOT NULL,
    arquivo TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS nfse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    valor_servicos REAL NOT NULL DEFAULT 0,
    deducoes REAL NOT NULL DEFAULT 0,
    base_calculo REAL NOT NULL DEFAULT 0,
    aliquota_iss REAL NOT NULL DEFAULT 0,
    valor_iss REAL NOT NULL DEFAULT 0,
    iss_retido INTEGER NOT NULL DEFAULT 0,
    valor_pis REAL NOT NULL DEFAULT 0,
    valor_cofins REAL NOT NULL DEFAULT 0,
    valor_csll REAL NOT NULL DEFAULT 0,
    valor_ir REAL NOT NULL DEFAULT 0,
    valor_inss REAL NOT NULL DEFAULT 0,
    valor_liquido REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'emitida',
    motivo_cancelamento TEXT DEFAULT '',
    arquivo_pdf TEXT,
    arquivo_pdf_nome TEXT,
    arquivo_xml TEXT,
    arquivo_xml_nome TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

INSERT OR IGNORE INTO empresa (id) VALUES (1);
