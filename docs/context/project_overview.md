# Overview do Sistema de Extração de Documentos Fiscais

> **Data de geração:** 2026-01-27  
> **Versão do sistema:** v0.3.x  
> **Status da documentação:** Esta documentação complementa (e corrige onde necessário) a documentação oficial que está parcialmente desatualizada.

---

## 📊 Status Atual do Projeto

> **IMPORTANTE:** Esta seção contém snapshots das sessões de trabalho. Mantém apenas os últimos 3 snapshots.  
> **Template:** Ver `project_status_template.md` para o formato completo.

### Snapshot: 29/01/2026 - 12:30 - CORRECAO_CONCLUIDA

**Tipo:** CORRECAO_CONCLUIDA

**Contexto da Sessão:**
- Orquestração iniciada em: 29/01/2026 08:44
- Correções concluídas: #1 e #2
- Tempo total: ~3 horas 46 minutos

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | CSV Atualizado | Validado |
|---|------|--------|---------------------|----------------|----------|
| 1 | TunnaFaturaExtractor | ✅ CONCLUÍDA | tunna_fatura.py, __init__.py | Sim (29/01) | 3 batches FishTV |
| 2 | Vencimento em Boletos | ✅ CONCLUÍDA | boleto.py | - | Função implementada |
| 3 | (próximas do JSON) | ⏳ PENDENTE | - | - | Aguardando |

**Correção #1: TunnaFaturaExtractor** ✅ CONCLUÍDA
- **Fornecedor:** TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA
- **Tipo:** FATURA COMERCIAL (tipo_documento="OUTRO", subtipo="FATURA")
- **Padrão de detecção:** "TUNNA" + "FATURA" OU "FAT/XXXXX"
- **Números processados:** 000.010.731, 000.010.732, 000.010.733
- **E-mail:** faturamento@fishtv.com.br
- **Referência temporal:** 3 batches processados em 29/01/2026

**Correção #2: Vencimento em Boletos** ✅ CONCLUÍDA
- **Problema:** Boletos com vencimento vazio no CSV
- **Solução:** Função `_decode_vencimento_from_linha_digitavel()` no BoletoExtractor
- **Como funciona:** Extrai fator de vencimento da linha digitável (posições 33-36) e calcula data
- **Considera reinício do fator:** A cada 10000 dias (a partir de 22/02/2025)
- **Fallback:** Usado quando vencimento não encontrado no texto
- **Arquivo modificado:** `extractors/boleto.py`
- **Testes:** Validados com basepyright e ruff ✅

**Estado do Sistema:**
- **Extractors no Registry:** 15 total (1 novo: TunnaFaturaExtractor)
- **Ordem do Registry:** ✅ ATUALIZADA 
  - DanfeExtractor antes de NfseGenericExtractor
  - BoletoExtractor e SicoobExtractor antes de OutrosExtractor
- **Validate Script:** ✅ ATUALIZADO - Adicionado --temp-email e --batches
- **Código:** Validação basedpyright e ruff passando ✅

**Estado dos Dados:**
- **relatorio_lotes.csv:** Últimas entradas FishTV: 000.010.731, 000.010.732, 000.010.733
- **relatorio_consolidado.csv:** Novo fornecedor: TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA
- **Failed cases:** 0 novos (zero regressões confirmado)
- **✅ Nota:** Ordem do registry corrigida - boletos agora classificados corretamente como BOLETO

**Pendências Identificadas:**
1. ✅ Ordem do registry corrigida (BoletoExtractor antes de OutrosExtractor)
2. Próximas correções do JSON aguardando priorização
3. Commitar mudanças quando solicitado pelo usuário

**Decisões Tomadas:**
- FishTV são FATURAS COMERCIAIS (não fiscais) → usar tipo="OUTRO", subtipo="FATURA"
- OCR corrompe "Nº" para "N�" → usar regex tolerante `N[�º]?`
- Reordenar registry é preferível a regex complexo para DANFE vs NFSe
- Fator de vencimento em boletos: posições 33-36 da linha digitável, reinicia a cada 10000 dias

**Para Reencontrar em Nova Sessão:**
> ⚠️ **AVISO:** Batch IDs mudam a cada `clean_dev` + `run_ingestion`!
> Use fornecedor/tipo para reencontrar casos:

```powershell
# Opção 1: Buscar no CSV por fornecedor (SEMPRE funciona)
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA" | Select-Object -Last 5

# Opção 2: Validar extrator em todos os batches atuais
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# Opção 3: Procurar por padrão de assunto nos metadados
Get-ChildItem temp_email/ | ForEach-Object { 
    $m = Get-Content "$($_.FullName)\metadata.json" | ConvertFrom-Json
    if ($m.subject -like "*FishTV*") { $_.Name }
}

# Opção 4: Buscar boletos com vencimento extraído
Get-Content data/output/relatorio_lotes.csv | Select-String "boleto" | Where-Object { $_ -match "vencimento" }
```

**Arquivos em Modificação:**
- [x] extractors/tunna_fatura.py (novo extrator)
- [x] extractors/boleto.py (função decode vencimento da linha digitável)
- [x] extractors/__init__.py (ordem do registry)
- [x] scripts/validate_extraction_rules.py (novas flags)
- [x] strategies/pdf_utils.py (logs revisados - evitar falsos positivos)
- [x] core/processor.py (logs revisados - reduzir verbosidade)
- [x] docs/context/* (documentação atualizada - README, coding_standards, logging_guide, logging_standards, etc)

---

## 1. Objetivo do Projeto

Sistema para extração e processamento automatizado de documentos fiscais (DANFE, NFSe e Boletos) a partir de PDFs recebidos por e-mail. O sistema realiza:

- **Ingestão de e-mails** via IMAP
- **Extração de dados** de PDFs (texto nativo + OCR quando necessário)
- **Correlação automática** entre documentos (NF + Boleto)
- **Exportação** para Google Sheets e CSVs
- **Geração de relatórios** para controle de faturamento (PAF)

### Colunas Exportadas (Planilha PAF)

**Aba "anexos" (com PDF):**

- PROCESSADO | RECEBIDO | ASSUNTO | N_PEDIDO | EMPRESA | VENCIMENTO | FORNECEDOR | NF | VALOR | SITUACAO | AVISOS

**Aba "sem_anexos" (apenas link):**

- PROCESSADO | RECEBIDO | ASSUNTO | N_PEDIDO | EMPRESA | FORNECEDOR | NF | LINK | CODIGO

---

## 2. Arquitetura Geral

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   E-mail IMAP   │────▶│  Ingestão       │────▶│  Lotes/Temp     │
│   (Entrada)     │     │  (Ingestion     │     │  (Pastas com    │
│                 │     │   Service)      │     │   metadata.json)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐              │
│   CSVs/Saída    │◀────│  Exportação     │◀─────────────┘
│   (relatórios)  │     │  (Exporters)    │
└─────────────────┘     └─────────────────┘
                               ▲
                               │
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Google Sheets  │◀────│  Correlação     │◀────│  Processamento  │
│  (API)          │     │  (NF↔Boleto)    │     │  (Batch Proc.)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 3. Estrutura de Diretórios

```
config/              # Configurações (.env, settings.py, feriados, empresas, bancos)
  ├── settings.py         # Configurações principais
  ├── empresas.py         # Configuração de empresas
  ├── bancos.py           # Configuração de bancos
  └── feriados_sp.py      # Feriados de São Paulo
core/                # Núcleo do sistema
  ├── models.py           # Modelos de dados (InvoiceData, DanfeData, etc.)
  ├── batch_processor.py  # Processador de lotes
  ├── batch_result.py     # Resultados de processamento de lote
  ├── correlation_service.py  # Correlação NF↔Boleto
  ├── document_pairing.py     # Pareamento por número/valor
  ├── metadata.py         # Metadados do e-mail
  ├── empresa_matcher.py  # Detecção de empresa no texto
  ├── empresa_matcher_email.py  # Matcher específico para e-mails
  ├── exporters.py        # Exportação CSV/Drive
  ├── extractors.py       # Interface base de extratores
  ├── interfaces.py       # Interfaces do sistema
  ├── filters.py          # Filtros de processamento
  ├── processor.py        # Processador principal
  ├── diagnostics.py      # Diagnósticos do sistema
  ├── metrics.py          # Métricas de performance
  ├── exceptions.py       # Exceções customizadas
  └── __init__.py         # Inicialização do core

extractors/          # Extratores especializados por tipo
  ├── acimoc_extractor.py         # Boletos ACIMOC específicos
  ├── admin_document.py           # Documentos administrativos
  ├── boleto.py                   # Extrator genérico de boletos
  ├── boleto_repromaq.py          # Extrator específico REPROMAQ
  ├── danfe.py                    # Extrator de DANFE (NF-e)
  ├── email_body_extractor.py     # Extrator de corpo de e-mail (sem anexos)
  ├── emc_fatura.py               # Faturas EMC Tecnologia
  ├── energy_bill.py              # Contas de energia (EDP, CEMIG, COPEL)
  ├── mugo_extractor.py           # Faturas MUGO Telecom
  ├── net_center.py               # NFSe específica Net Center
  ├── nfcom_telcables_extractor.py # NFCom/Telcables (faturas de telecom)
  ├── nfse_custom_montes_claros.py # NFSe Montes Claros-MG
  ├── nfse_custom_vila_velha.py   # NFSe Vila Velha-ES
  ├── nfse_generic.py             # Extrator genérico de NFSe
  ├── outros.py                   # Documentos diversos (faturas)
  ├── pro_painel_extractor.py     # Faturas PRÓ - PAINEL LTDA
  ├── sicoob.py                   # Boletos Sicoob específicos
  ├── utils.py                    # Utilitários de extração
  └── xml_extractor.py            # Extração de XMLs fiscais

strategies/          # Estratégias de extração de texto
  ├── native.py           # PDF vetorial (pdfplumber)
  ├── ocr.py              # OCR (Tesseract)
  ├── table.py            # Extração de tabelas
  ├── fallback.py         # Fallback entre estratégias
  └── pdf_utils.py        # Utilitários PDF (senhas, etc.)

ingestors/           # Ingestão de e-mails
  ├── imap.py             # Cliente IMAP
  └── utils.py            # Utilitários

services/            # Serviços de alto nível
  ├── ingestion_service.py    # Orquestração de ingestão
  └── email_ingestion_orchestrator.py  # Checkpoint/resume

scripts/             # Ferramentas utilitárias
  ├── inspect_pdf.py          # Inspeção de PDFs
  ├── validate_extraction_rules.py  # Validação de regras
  ├── export_to_sheets.py     # Exportação para Google Sheets
  ├── analyze_logs.py               # Análise de logs do sistema
  ├── check_problematic_pdfs.py     # Verifica PDFs problemáticos
  ├── clean_dev.py                  # Limpa ambiente de dev
  ├── consolidate_batches.py        # Consolida lotes
  ├── diagnose_inbox_patterns.py    # Diagnostica padrões de inbox
  ├── example_batch_processing.py   # Exemplo de processamento
  ├── generate_report.py            # Gera relatórios
  ├── ingest_emails_no_attachment.py  # Ingestão sem anexo
  ├── list_problematic.py           # Lista casos problemáticos
  ├── repro_extraction_failure.py   # Reproduz falhas de extração
  ├── simple_list.py                # Listagem simples
  ├── test_admin_detection.py       # Testa detecção de admin
  ├── test_docker_setup.py          # Testa setup Docker
  ├── test_extractor_routing.py     # Testa roteamento de extratores
  └── _init_env.py                  # Inicialização de ambiente

temp_email/          # Pasta de lotes (criada dinamicamente)
data/
  ├── output/         # CSVs gerados
  └── debug_output/   # Relatórios de debug

failed_cases_pdf/    # PDFs para testes/validação
logs/                # Logs do sistema (scrapper.log)
```

---

## 4. Modelos de Dados Principais

### DocumentData (Classe Base)

Classe abstrata que define o contrato para todos os documentos:

- `arquivo_origem`, `data_processamento`, `empresa`, `setor`
- `batch_id`, `source_email_subject`, `source_email_sender`
- `email_date` - Data de recebimento do e-mail

### InvoiceData (NFSe)

Notas Fiscais de Serviço:

- `cnpj_prestador`, `fornecedor_nome`, `numero_nota`
- `valor_total`, `valor_ir`, `valor_inss`, `valor_csll`, `valor_iss`
- `vencimento`, `data_emissao`, `forma_pagamento`

### DanfeData (NF-e)

Notas Fiscais de Produto:

- Similar ao InvoiceData
- `chave_acesso` (44 dígitos)

### BoletoData

Boletos bancários:

- `linha_digitavel`, `codigo_barras`
- `vencimento`, `valor_documento`
- `referencia_nfse` (vinculação com NF)

### OtherDocumentData

Documentos diversos (faturas, ordens de serviço):

- `subtipo` (para categorização)
- `numero_documento`

### EmailAvisoData

E-mails sem anexo (apenas links):

- `link_nfe`, `codigo_verificacao`
- `email_subject_full`, `email_body_preview`

---

## 5. Extratores Registrados (Ordem de Prioridade)

A ordem de importação em `extractors/__init__.py` define a prioridade:

1. **BoletoRepromaqExtractor** - Boletos REPROMAQ/Bradesco (evita catastrophic backtracking)
2. **EmcFaturaExtractor** - Faturas EMC Tecnologia (multi-página)
3. **NetCenterExtractor** - NFSe específica Net Center
4. **NfseCustomMontesClarosExtractor** - NFSe Montes Claros-MG
5. **NfseCustomVilaVelhaExtractor** - NFSe Vila Velha-ES
6. **EnergyBillExtractor** - Contas de energia (EDP, CEMIG, COPEL)
7. **NfcomTelcablesExtractor** - NFCom/Telcables (faturas de telecom)
8. **AcimocExtractor** - Boletos ACIMOC específicos
9. **MugoExtractor** - Faturas MUGO Telecom
10. **ProPainelExtractor** - Faturas PRÓ - PAINEL LTDA
11. **AdminDocumentExtractor** - Documentos administrativos (evita falsos positivos)
12. **OutrosExtractor** - Documentos diversos (faturas, ordens de serviço)
13. **NfseGenericExtractor** - NFSe genérico (fallback)
14. **BoletoExtractor** - Boletos genéricos
15. **SicoobExtractor** - Boletos Sicoob
16. **DanfeExtractor** - DANFE/DF-e

**Nota:** Além dos extratores acima, o sistema também inclui:

- **EmailBodyExtractor** - Extração de corpo de e-mail (chamado diretamente, não via registry)
- **XmlExtractor** - Extração de XMLs fiscais (chamado diretamente, não via registry)

**Regra:** Extratores específicos devem vir ANTES dos genéricos para evitar classificação incorreta.

---

## 6. Estratégias de Extração de Texto

### NativePdfStrategy

- Usa `pdfplumber` para extrair texto nativo do PDF
- Mais rápida (~90% dos casos)
- Suporte a PDFs protegidos por senha (tenta CNPJs)
- Fallback automático se extrair < 50 caracteres

### TesseractOcrStrategy

- Usa Tesseract OCR para PDFs em imagem
- Configuração: `--psm 6` (bloco único uniforme)
- Otimizado para números/códigos (desativa dicionários)

### TablePdfStrategy

- Preserva layout tabular para documentos estruturados
- Útil para boletos e documentos com colunas

### FallbackChain

- Orquestra múltiplas estratégias
- `HYBRID_OCR_COMPLEMENT`: combina nativo + OCR quando necessário

---

## 7. Fluxo de Processamento

### 7.1 Ingestão

```python
# 1. Conecta ao IMAP e baixa e-mails
# 2. Cria pasta em temp_email/ com formato: email_YYYYMMDD_HHMMSS_<hash>
# 3. Salva anexos e metadata.json
# 4. Registra checkpoint para resume
```

### 7.2 Processamento de Lote (Batch)

```python
# 1. Lê metadata.json
# 2. Prioriza XML se estiver completo (todos os campos obrigatórios)
# 3. Processa PDFs com estratégia de extração
# 4. Roteia para extrator apropriado (can_handle())
# 5. Aplica correlação entre documentos do mesmo lote
```

### 7.3 Correlação NF ↔ Boleto

```python
# 1. Pareamento por número da nota no nome do arquivo
# 2. Pareamento por referência no boleto (número documento)
# 3. Pareamento por valor (fallback)
# 4. Validação: valores devem conferir (com tolerância)
# 5. Herança de campos: NF herda vencimento do boleto, boleto herda fornecedor da NF
```

### 7.4 Exportação

```python
# Gera CSVs:
# - relatorio_nfse.csv
# - relatorio_boleto.csv
# - relatorio_danfe.csv
# - relatorio_outro.csv
# - relatorio_consolidado.csv (todos os documentos)
# - relatorio_lotes.csv (resumo por lote - uma linha por par NF↔Boleto)
```

---

## 8. Configurações Importantes (.env)

```bash
# E-mail (IMAP)
EMAIL_HOST=imap.gmail.com
EMAIL_USER=usuario@empresa.com
EMAIL_PASS=senha_app
EMAIL_FOLDER=INBOX

# Google Sheets
GOOGLE_SPREADSHEET_ID=1ABC...
GOOGLE_CREDENTIALS_PATH=credentials.json

# OCR (caminhos Windows/Linux)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\Poppler\...\bin

# Comportamento
HYBRID_OCR_COMPLEMENT=1  # Combina nativo + OCR
PAF_EXPORT_NF_EMPTY=0    # Exporta número NF na planilha
PAF_EXIGIR_NUMERO_NF=0   # Validação exige número NF

# Timeouts
BATCH_TIMEOUT_SECONDS=300
FILE_TIMEOUT_SECONDS=90
```

---

## 9. Scripts Principais

### run_ingestion.py

Script principal de orquestração:

```bash
python run_ingestion.py                    # Ingestão completa
python run_ingestion.py --reprocess        # Reprocessa lotes existentes
python run_ingestion.py --batch-folder X   # Processa pasta específica
python run_ingestion.py --cleanup          # Limpa lotes antigos (>48h)
python run_ingestion.py --status           # Mostra status do checkpoint
```

### scripts/inspect_pdf.py

Inspeção rápida de PDFs:

```bash
python scripts/inspect_pdf.py arquivo.pdf        # Campos extraídos
python scripts/inspect_pdf.py arquivo.pdf --raw  # Texto bruto
python scripts/inspect_pdf.py arquivo.pdf --batch # Análise de lote completo
```

### scripts/validate_extraction_rules.py

Validação de regras em lote:

```bash
python scripts/validate_extraction_rules.py --batch-mode --apply-correlation
```

### scripts/export_to_sheets.py

Exportação para Google Sheets:

```bash
python scripts/export_to_sheets.py              # Exporta relatorio_lotes.csv
python scripts/export_to_sheets.py --use-consolidado  # Modo detalhado
```

### scripts/analyze_logs.py

Análise de logs do sistema:

```bash
python scripts/analyze_logs.py                    # Análise completa
python scripts/analyze_logs.py --today            # Apenas logs de hoje
python scripts/analyze_logs.py --errors-only      # Apenas erros
python scripts/analyze_logs.py --batch <id>       # Buscar lote específico
python scripts/analyze_logs.py --summary          # Resumo estatístico
python scripts/analyze_logs.py --output report.md # Salvar relatório
```

---

## 10. Testes

```bash
# Rodar todos os testes
pytest

# Com cobertura
pytest --cov=.

# Testes específicos
pytest tests/test_energy_extractor.py -v
```

**Cobertura:** Testes abrangendo extratores, processamento, correlação e exportação.

---

## 11. Docker

```bash
# Build e run
docker-compose up --build

# Modo desenvolvimento (volume montado)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## 12. Pontos de Atenção / Documentação Desatualizada

### Documentação possivelmente desatualizada:

1. **docs/guide/** - Guias de uso podem não refletir flags mais recentes
2. **docs/development/** - Padrões de código podem estar desatualizados
3. **docs/api/** - APIs internas podem ter mudado
4. **README.md** - Seção de estrutura está simplificada

### Comportamentos importantes não documentados:

1. **Prioridade XML:** XML só é usado se tiver TODOS os campos obrigatórios (`fornecedor_nome`, `vencimento`, `numero_nota`, `valor_total`). Se incompleto, processa PDFs.

2. **EnergyBillExtractor:** Criado recentemente (26/01/2026) para resolver conflito entre Carrier Telecom (empresa) e faturas de energia. Detecta distribuidoras por múltiplos indicadores.

3. **AdminDocumentExtractor:** Extrator especializado para documentos administrativos com padrões negativos para evitar falsos positivos em documentos fiscais.

4. **Sistema de Avisos:** A coluna AVISOS pode conter:
    - `[CONCILIADO]` - NF e boleto pareados com sucesso
    - `[DIVERGENTE]` - Campos faltando ou valores não conferem
    - `[VENCIMENTO_PROXIMO]` - Menos de 4 dias úteis
    - `[VENCIDO]` - Data de vencimento já passou
    - `[SEM ANEXO]` - E-mail sem PDF anexado

5. **Pareamento Inteligente:** Quando há múltiplas NFs no mesmo e-mail, o sistema gera uma linha no relatório para cada par NF↔Boleto (não uma linha por e-mail).

6. **Coluna RECEBIDO:** Nova coluna (adicionada 14/01/2026) que mostra a data de recebimento do e-mail, separada da data de processamento.

## 13. Dependências Principais

> **Nota:** Versões testadas e compatíveis. Atualizações devem ser validadas.

```
# Extração de PDF e texto
pdfplumber      # Extração nativa de PDF
pytesseract     # OCR
pdf2image       # Conversão PDF->imagem
pypdfium2       # Manipulação de PDF
pillow          # Processamento de imagens (PIL)

# Processamento de dados
pandas          # Processamento de CSV/DataFrames
python-dateutil # Manipulação de datas

# Configuração e ambiente
python-dotenv   # Carregamento de variáveis de ambiente

# Google Sheets API
gspread         # Integração com Google Sheets

# Utilitários
tenacity        # Retry automático para falhas
workalendar     # Cálculo de dias úteis e feriados

# Testes
pytest          # Framework de testes

# Análise estática (desenvolvimento)
basedpyright    # Verificação de tipos (opcional)

# Documentação (Netlify)
mkdocs          # Geração de documentação
mkdocs-material # Tema Material para MkDocs
mkdocstrings[python] # Documentação automática de código
mkdocs-encryptcontent-plugin # Plugin de criptografia
pymdown-extensions # Extensões Markdown
mkdocs-panzoom-plugin # Plugin zoom para imagens
```

---

## 14. Roadmap / To Do Atual

Baseado no README.md:

- [x] Script para automatizar análise de logs (`scripts/analyze_logs.py`)
- [x] Correções de tipos e qualidade de código (basedpyright/pyright) ✅
- [ ] Verificar funcionamento em container Docker
- [ ] Atualizar dados IMAP para e-mail da empresa (não de teste)
- [ ] Pesquisar APIs da OpenAI para OCR e validação
- [ ] Tratar casos de PDF não anexado (link de prefeitura/terceiros)

---

_Documento gerado automaticamente para manter contexto do projeto._
