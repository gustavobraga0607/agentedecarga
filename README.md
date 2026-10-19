# Agente de Cargas

Sistema web para agentes de cargas internacionais (freight forwarders), com três módulos:

1. **Orçamentos de frete**: cotações aéreas, marítimas (FCL/LCL) e rodoviárias, com cálculo automático de cubagem e peso taxável, taxas em USD/EUR/BRL, mínimos, margem de lucro e proposta pronta para imprimir ou salvar em PDF.
2. **Controle de embarques**: cada embarque tem booking, MBL/HBL (ou MAWB/HAWB), contêineres e ETD/ETA. A linha do tempo mostra o status, há histórico de eventos e os documentos ficam anexados (BL, invoice, packing list etc.). Um orçamento aprovado vira embarque em um clique.
3. **NF-S (nota fiscal de serviço)**: emissão com numeração sequencial, ISS e retenções federais (PIS, COFINS, CSLL, IR e INSS), XML de DPS e versão para impressão. Também dá para **anexar** notas emitidas no portal da prefeitura ou no Emissor Nacional (PDF e XML). O XML é lido automaticamente nos padrões Nacional e ABRASF.

O painel mostra os embarques ativos, as chegadas dos próximos 7 dias, os embarques concluídos sem NF-S e o faturamento do mês.

## Como rodar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python seed.py      # opcional: dados de demonstração
.venv/bin/python run.py       # http://localhost:5000
```

Antes de usar, preencha em **Configurações** o CNPJ, a inscrição municipal, a alíquota de ISS, o item da LC 116 e o câmbio padrão.

Testes:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## Regras de cálculo

| Modal | Fator de cubagem | Peso taxável |
|---|---|---|
| Aéreo | 1:6000 (166,67 kg/m³) | maior entre peso bruto e peso cubado |
| Marítimo LCL/FCL | 1 m³ = 1.000 kg | W/M: maior entre toneladas e m³ |
| Rodoviário | 300 kg/m³ | maior entre peso bruto e peso cubado |

Cada taxa pode ser calculada de seis formas: valor fixo, por kg taxável, por m³, por W/M, por unidade/contêiner ou como % do valor da mercadoria. Se o valor calculado ficar abaixo do mínimo, vale o mínimo. A margem é aplicada sobre o custo em BRL.

## Sobre a emissão de NF-S

A emissão interna gera o número, o código de verificação e um XML de DPS baseado no leiaute do Padrão Nacional da NFS-e, em ambiente de homologação. **A nota não é transmitida à prefeitura.** Para que tenha validade fiscal, é preciso integrar:

- certificado digital A1 do prestador;
- webservice do município ou API do Ambiente de Dados Nacional (ADN);
- o ponto de integração é `transmitir()` em `app/nfse.py`.

Até essa integração existir, emita a nota no portal oficial e use **Anexar NF-S** para guardar o PDF e o XML vinculados ao embarque. Confirme com seu contador o item da LC 116, a alíquota e as retenções que se aplicam à sua empresa.

## Estrutura

```
app/
  calc.py         regras de frete (funções puras)
  nfse.py         tributos, geração e leitura de XML
  schema.sql      banco SQLite
  views/          rotas: painel, clientes, orçamentos, embarques, NF-S
  templates/      telas (Jinja)
  static/style.css
tests/
```

Os dados e os anexos ficam em `instance/`, que não vai para o git.

## Publicar na Vercel

O projeto já está configurado para a Vercel (`vercel.json` e `api/index.py`).

1. Em <https://vercel.com/new>, importe o repositório `agentedecarga` e clique em **Deploy** sem alterar nada.
2. No projeto, abra **Storage** e conecte:
   - **Neon (Postgres)**, que cria a variável `DATABASE_URL`;
   - **Blob**, que cria a variável `BLOB_READ_WRITE_TOKEN`.
3. Em **Settings → Environment Variables**, crie `APP_PASSWORD` com a senha de acesso ao sistema.
4. Em **Deployments**, clique em **Redeploy**.

As tabelas são criadas automaticamente no primeiro acesso. Sem `APP_PASSWORD`, o site publicado fica bloqueado e mostra essas instruções. Sem o Postgres e o Blob, ele funciona em "modo demonstração", com dados temporários.

| Variável | Para quê |
|---|---|
| `APP_PASSWORD` | senha de acesso (obrigatória na Vercel) |
| `DATABASE_URL` ou `POSTGRES_URL` | banco Postgres; sem ela, usa SQLite local |
| `BLOB_READ_WRITE_TOKEN` | anexos no Vercel Blob; sem ela, usa a pasta `instance/uploads` |
| `SECRET_KEY` | opcional; quando ausente, é derivada da senha |

Os anexos ficam em blobs privados, sempre que a loja Blob permitir, e são entregues pela própria aplicação, só para quem fez login. Cada arquivo pode ter até 4 MB, que é o limite das funções da Vercel.

Para rodar os testes também no Postgres, use `TEST_DATABASE_URL=postgresql://... .venv/bin/python -m pytest`.
