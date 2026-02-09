# Documentação de Prompts do Sistema de Extração

> **Local:** `docs/context/`  
> **Propósito:** Prompts estruturados para facilitar diagnóstico, correção e criação de extratores

---

## 🚀 Comece Aqui

### Nova Sessão? Verifique o Status Anterior

```bash
# 1. Leia o snapshot atual
Get-Content docs/context/project_overview.md | Select-Object -First 100

# 2. Encontre a seção "## 📊 Status Atual do Projeto"
#    - Veja qual correção estava em andamento
#    - Verifique pendências da sessão anterior
```

### Fluxo Rápido por Objetivo

| Seu Objetivo                          | Documento                                                                       | Tempo Est. |
| ------------------------------------- | ------------------------------------------------------------------------------- | ---------- |
| **Corrigir um caso específico**       | [`diagnosis.md`](./diagnosis.md) → [`validation.md`](./validation.md)           | 15-30 min  |
| **Criar novo extrator**               | [`creation.md`](./creation.md) + [`coding_standards.md`](./coding_standards.md) | 1-2 horas  |
| **Correções em massa (automático)**   | [`automation_orchestrator.md`](./automation_orchestrator.md)                    | Variável   |
| **Problema estranho/erro inesperado** | [`troubleshooting.md`](./troubleshooting.md)                                    | 5-10 min   |
| **Comando falhou no Windows**         | [`commands_reference.md`](./commands_reference.md)                              | 1 min      |

---

## ⚠️ Antes de Começar (Leia Isso!)

### 1. Ambiente Windows

Este projeto é desenvolvido em **Windows** com **PowerShell**. Comandos Unix (`grep`, `head`, `awk`) **não funcionam**.

**Conversão rápida:**

```bash
# ❌ Unix (não funciona)
grep "termo" arquivo.txt | head -5

# ✅ PowerShell (funciona)
Select-String "termo" arquivo.txt | Select-Object -First 5
```

**Referência completa:** [`commands_reference.md`](./commands_reference.md)

---

### 2. Batch IDs São Voláteis! ⚠️ CRÍTICO

> **IDs de batch mudam a cada `clean_dev` + `run_ingestion`!**

```bash
# Você rodou isso hoje de manhã?
python scripts/clean_dev.py      # Limpa tudo
python run_ingestion.py          # IDs novos!
```

**Use identificadores estáveis:**

- ✅ **Fornecedor**: "TUNNA ENTRETENIMENTO"
- ✅ **Tipo**: "FATURA", "NFSE"
- ✅ **CNPJ**: "12.345.678/9012-34"
- ❌ **Batch ID**: `email_20260129_084433_c5c04540` (obsoleto!)

**Veja:** [`correction_tracking.md`](./correction_tracking.md) - Como rastrear correções entre sessões

---

### 3. Estrutura de Pastas Importante

```
scrapper/
├── temp_email/              ← Batches atuais (use este!)
│   └── email_YYYYMMDD_HHMMSS_hash/
│       ├── metadata.json
│       └── 01_*.pdf
├── failed_cases_pdf/        ← Casos antigos (legado)
├── data/output/             ← CSVs gerados
│   └── relatorio_lotes.csv  ← Principal
├── logs/
│   └── scrapper.log         ← Logs do sistema
└── docs/context/            ← Você está aqui!
```

---

## 🔄 Continuidade entre Sessões (SNAPSHOT)

### O Que É Um Snapshot?

Registro do estado do projeto ao final de cada sessão, incluindo:

- Correções concluídas e pendentes
- Decisões tomadas
- Comandos úteis para retomada

### Onde Encontrar?

**Arquivo:** `project_overview.md` → Seção `## 📊 Status Atual do Projeto`

### Por Que Isso Importa?

```
Sessão 1 (ontem):
  └─ Corrigi FishTV, faltava fazer Vencimento em Boletos
       └─ Registrei snapshot

Sessão 2 (hoje):
  ├─ Leio snapshot: "Correção #2 PENDENTE - Vencimento Boletos"
  ├─ Ignoro batch IDs antigos (já foram limpos)
  ├─ Busco por fornecedor/tipo nos dados atuais
  └─ Continuo de onde parei!
```

**Template:** [`project_status_template.md`](./project_status_template.md)  
**Estratégias:** [`correction_tracking.md`](./correction_tracking.md)

---

## 📋 Prompts por Fluxo de Trabalho

### 🔧 Fluxo 1: Corrigir Caso Específico

Para quando há um problema identificado no CSV:

```
diagnosis.md → creation.md (se novo extrator) → validation.md
```

| #   | Documento                          | Propósito              | Quando Usar                                     |
| --- | ---------------------------------- | ---------------------- | ----------------------------------------------- |
| 1.1 | [`diagnosis.md`](./diagnosis.md)   | Identificar causa raiz | Valor zero, campo vazio, classificação errada   |
| 1.2 | [`review.md`](./review.md)         | Análise aprofundada    | Caso complexo, decisão entre ajustar/criar novo |
| 1.3 | [`creation.md`](./creation.md)     | Criar novo extrator    | Layout único não coberto                        |
| 1.4 | [`validation.md`](./validation.md) | Validar correção       | Após implementar, antes de commitar             |

**Ferramentas usadas:**

```bash
python scripts/inspect_pdf.py --batch <batch_id>
python scripts/validate_extraction_rules.py --batch-mode --temp-email
```

---

### 🔍 Fluxo 2: Análise de Problemas em Massa

Para quando há muitos erros e precisa priorizar:

```
prioritization.md → log_correlation.md → [correções]
```

| #   | Documento                                                                    | Propósito                 | Quando Usar                                 |
| --- | ---------------------------------------------------------------------------- | ------------------------- | ------------------------------------------- |
| 2.1 | [`prioritization.md`](./prioritization.md)                                   | Priorizar por recorrência | Muitos erros, decidir o que atacar primeiro |
| 2.2 | [`log_correlation.md`](./log_correlation.md)                                 | Analisar logs vs CSV      | Erros no log causam problemas no CSV?       |
| 2.3 | [`example_prioritization_analysis.md`](./example_prioritization_analysis.md) | Exemplo real              | Ver análise real como referência            |

**Ferramentas usadas:**

```bash
python scripts/analyze_logs.py --output report.md
python scripts/check_problematic_pdfs.py
```

---

### 🤖 Fluxo 3: Correções Automatizadas

Para quando quer processar muitas correções de uma vez:

```
automation_orchestrator.md (engloba todos os outros)
```

| Documento                                                    | Propósito                    | Quando Usar                               |
| ------------------------------------------------------------ | ---------------------------- | ----------------------------------------- |
| [`automation_orchestrator.md`](./automation_orchestrator.md) | Orquestrar correções em lote | Já tem lista priorizada, quer automatizar |

**Como funciona:**

1. Verifica snapshot anterior (retoma se necessário)
2. Executa diagnóstico → review → creation → validation
3. Registra snapshot ao final

---

## 📚 Referência Rápida

### Resolução de Problemas

| Problema                   | Solução                                                                          |
| -------------------------- | -------------------------------------------------------------------------------- |
| Comando falhou no Windows  | [`commands_reference.md`](./commands_reference.md)                               |
| Erro específico do projeto | [`troubleshooting.md`](./troubleshooting.md)                                     |
| OCR corrompendo caracteres | [`troubleshooting.md`](./troubleshooting.md) → "Problemas de OCR"                |
| Batch ID não encontrado    | [`correction_tracking.md`](./correction_tracking.md)                             |
| Extrator não funciona      | [`logging_guide.md`](./logging_guide.md) → adicione logs                         |
| PDF protegido por senha    | [`pdf_password_handling.md`](./pdf_password_handling.md)                         |
| Problemas da sessão 30/01  | [`troubleshooting_sessao_30_01_2026.md`](./troubleshooting_sessao_30_01_2026.md) |

### Padrões de Código

| Situação                  | Documento                                                                                 |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| Criar novo extrator       | [`coding_standards.md`](./coding_standards.md) + [`logging_guide.md`](./logging_guide.md) |
| Type hints / basedpyright | [`coding_standards.md`](./coding_standards.md) → "Type Checking"                          |
| SOLID / DRY               | [`coding_standards.md`](./coding_standards.md) → "Princípios SOLID"                       |
| Adicionar logs            | [`logging_guide.md`](./logging_guide.md)                                                  |

### Conhecimento do Sistema

| Tópico                | Documento                                                                 |
| --------------------- | ------------------------------------------------------------------------- |
| Arquitetura geral     | [`project_overview.md`](./project_overview.md)                            |
| Modelos de dados      | [`project_overview.md`](./project_overview.md) → "Modelos de Dados"       |
| Registry e prioridade | [`project_overview.md`](./project_overview.md) → "Extratores Registrados" |
| Lições aprendidas     | [`improvements_analysis.md`](./improvements_analysis.md)                  |

---

## 🗂️ Índice Completo (Alfabético)

| #   | Documento                                                                        | Categoria    | Descrição                                  |
| --- | -------------------------------------------------------------------------------- | ------------ | ------------------------------------------ |
| 1   | [`automation_orchestrator.md`](./automation_orchestrator.md)                     | Fluxo        | Orquestrar correções em lote               |
| 2   | [`coding_standards.md`](./coding_standards.md)                                   | Referência   | Type hints, SOLID, DRY                     |
| 3   | [`commands_reference.md`](./commands_reference.md)                               | Referência   | Unix vs PowerShell                         |
| 4   | [`correction_tracking.md`](./correction_tracking.md)                             | Snapshot     | Rastrear correções entre sessões           |
| 5   | [`creation.md`](./creation.md)                                                   | Fluxo        | Criar novo extrator                        |
| 6   | [`diagnosis.md`](./diagnosis.md)                                                 | Fluxo        | Diagnóstico rápido de caso                 |
| 7   | [`example_prioritization_analysis.md`](./example_prioritization_analysis.md)     | Exemplo      | Análise real de priorização                |
| 8   | [`improvements_analysis.md`](./improvements_analysis.md)                         | Conhecimento | Lições da primeira orquestração            |
| 9   | [`log_correlation.md`](./log_correlation.md)                                     | Fluxo        | Analisar logs vs CSV                       |
| 10  | [`logging_guide.md`](./logging_guide.md)                                         | Referência   | Como adicionar logs                        |
| 11  | [`prioritization.md`](./prioritization.md)                                       | Fluxo        | Priorizar erros por recorrência            |
| 12  | [`project_overview.md`](./project_overview.md)                                   | Conhecimento | Arquitetura e estrutura                    |
| 13  | [`project_status_template.md`](./project_status_template.md)                     | Snapshot     | Template de snapshot                       |
| 14  | [`review.md`](./review.md)                                                       | Fluxo        | Análise aprofundada de caso                |
| 15  | [`troubleshooting.md`](./troubleshooting.md)                                     | Referência   | Resolver erros comuns                      |
| 16  | [`troubleshooting_sessao_30_01_2026.md`](./troubleshooting_sessao_30_01_2026.md) | Referência   | Problemas específicos da sessão 30/01/2026 |
| 17  | [`validation.md`](./validation.md)                                               | Fluxo        | Validar correções                          |
| 18  | [`logging_standards.md`](./logging_standards.md)                                 | Referência   | Evitar falsos positivos nos logs           |
| 19  | [`sessao_2026_01_30_nfse_sem_numero.md`](./sessao_2026_01_30_nfse_sem_numero.md) | Snapshot     | Sessão 30/01 - NFSE sem número             |
| 20  | [`ANALISE_ERROS_REAL_2026_01_30.md`](./ANALISE_ERROS_REAL_2026_01_30.md)         | Análise      | Análise de erros reais vs falsos positivos |
| 21  | [`analise_2026_01_29.md`](./analise_2026_01_29.md)                               | Análise      | Primeira análise de saúde detalhada        |

---

## 📊 Fontes de Verdade

### Arquivos de Dados

| Arquivo                                  | Propósito                       | Formato            |
| ---------------------------------------- | ------------------------------- | ------------------ |
| `data/output/relatorio_lotes.csv`        | **Principal** - Resumo por lote | CSV (; delimitado) |
| `data/output/relatorio_consolidado.csv`  | Detalhado por documento         | CSV (; delimitado) |
| `data/output/analise_pdfs_detalhada.txt` | Análise de problemas            | Texto              |
| `logs/scrapper.log`                      | Logs de processamento           | Texto              |

### Scripts Essenciais

| Script                         | Função             | Uso                                                                     |
| ------------------------------ | ------------------ | ----------------------------------------------------------------------- |
| `inspect_pdf.py`               | Inspeção de PDF    | `python scripts/inspect_pdf.py <pdf> --raw`                             |
| `analyze_logs.py`              | Análise de logs    | `python scripts/analyze_logs.py --today`                                |
| `validate_extraction_rules.py` | Teste de regressão | `python scripts/validate_extraction_rules.py --batch-mode --temp-email` |
| `run_ingestion.py`             | Reprocessar        | `python run_ingestion.py --batch-folder <id>`                           |

---

## 📝 Convenções Importantes

### Prioridade de Extratores

A ordem em `extractors/__init__.py` define a prioridade:

- **0-3:** Extratores muito específicos (CNPJ único)
- **4-7:** Extratores por tipo/empresa
- **8-11:** Extratores administrativos
- **12-14:** Genéricos (fallback)
- **15:** DANFE (sempre último)

### Formatos de Dados

| Campo | Formato          | Exemplo              |
| ----- | ---------------- | -------------------- |
| Valor | float            | `700.00`             |
| Data  | ISO (YYYY-MM-DD) | `2026-01-15`         |
| CNPJ  | Formatado        | `12.345.678/9012-34` |
| Vazio | None             | `None` (nunca `""`)  |

---

## 🔄 Atualizando Esta Documentação

Ao criar novos prompts ou modificar existentes:

1. **Atualize este README.md**:
    - Adicione ao "Índice Completo"
    - Inclua no fluxo apropriado (se aplicável)
    - Atualize "Fluxo Rápido" se for documento primário

2. **Siga o padrão**:
    - Header com descrição breve
    - Seção "Quando usar"
    - Ferramentas/comandos
    - Output esperado

3. **Após correções**:
    - Atualize snapshot em `project_overview.md`
    - Use template `project_status_template.md`

---

---

## 🆕 Extratores Especiais e Novos

### Extratores Fora do Registry

Alguns extratores não estão no registry padrão pois processam dados de forma diferente:

| Extrator                   | Arquivo                              | Propósito                      | Chamado Por    |
| -------------------------- | ------------------------------------ | ------------------------------ | -------------- |
| `EmailBodyExtractor`       | `extractors/email_body_extractor.py` | Extrai dados do corpo do email | BatchProcessor |
| `SabespWaterBillExtractor` | `extractors/sabesp.py`               | Faturas Sabesp (PDF protegido) | BatchProcessor |
| `XmlExtractor`             | `extractors/xml_extractor.py`        | Processa XMLs fiscais          | BatchProcessor |

### Extratores Recentes no Registry

| Extrator                 | Arquivo                         | Propósito                            | Data       |
| ------------------------ | ------------------------------- | ------------------------------------ | ---------- |
| `CscNotaDebitoExtractor` | `extractors/csc_nota_debito.py` | Nota Débito/Recibo Fatura CSC GESTAO | 02/02/2026 |
| `BoletoGoxExtractor`     | `extractors/boleto_gox.py`      | Boletos GOX S.A. (extrai nº do nome) | 30/01/2026 |
| `UtilityBillExtractor`   | `extractors/utility_bill.py`    | Faturas energia/água (CEMIG, COPASA) | 30/01/2026 |
| `TIMFaturaExtractor`     | `extractors/tim_fatura.py`      | Faturas TIM S.A.                     | 05/02/2026 |

### Suporte a NFCom no XmlExtractor (06/02/2026)

Adicionado suporte para **NFCom (Nota Fiscal de Comunicação - modelo 62)** no `XmlExtractor`:

- Detecta namespace `http://www.portalfiscal.inf.br/nfcom`
- Extrai: fornecedor, CNPJ, número NF, valor total, vencimento
- Usado por operadoras de telecom (MITelecom, etc.)

**Arquivo:** `extractors/xml_extractor.py`

### Fix Timeout em PDFs com QR Code (06/02/2026)

**Problema:** PDFs com QR Codes vetoriais complexos causavam timeout de 90s no `pdfminer`.

**Causa:** `abrir_pdfplumber_com_senha()` chamava `extract_text()` para validar abertura do PDF.

**Solução:** Removido `extract_text()` do fluxo de validação - PDF que abre sem erro é retornado imediatamente.

**Arquivo:** `strategies/pdf_utils.py`

### Padrão CEMIG no UtilityBillExtractor (06/02/2026)

Adicionado padrão específico para faturas CEMIG que captura corretamente o "valor a pagar":

- Padrão: `MÊS/ANO DATA_VENCIMENTO VALOR_A_PAGAR`
- Exemplo: `JAN/26 10/02/2026 205,05`

**Arquivo:** `extractors/utility_bill.py`

### Correções de Fornecedores NFCom (04/02/2026)

Correções importantes nos extratores DANFE e Boleto para evitar captura de cabeçalhos de tabela como fornecedor:

**Problema corrigido:** Fornecedores extraídos incorretamente como:

- `"CNPJ/CPF INSCRIÇÃO ESTADUAL - CNPJ 01.492.641/0001-73"`
- `"(-) Desconto / Abatimentos (-) Outras deduções..."`
- `"BETIM / MG - CEP: 32669-895"`

**Soluções implementadas:**

1. **Mapeamento CNPJ→Nome** (`extractors/danfe.py`):

    ```python
    CNPJ_TO_NOME = {
        "05.872.814/0007-25": "VOGEL SOL. EM TEL. E INF. S.A.",
        "01.492.641/0001-73": "Century Telecom LTDA",
        "71.208.516/0001-74": "ALGAR TELECOM S/A",
        "05.334.864/0001-63": "NIPCABLE DO BRASIL TELECOM LTDA",
    }
    ```

2. **Padrões inválidos** em `_is_invalid_fornecedor()`:
    - Cabeçalhos: `CPF/CNPJ INSCRIÇÃO`, `Nº DO CLIENTE:`
    - Endereços: `CIDADE / UF - CEP`
    - Descontos: `(-) Desconto`, `Abatimentos`, `Outras deduções`

3. **Tokens inválidos em Boleto** (`_looks_like_header_or_label()`):
    - "DESCONTO", "ABATIMENTO", "OUTRAS DEDUÇÕES", "(=)", "(-)", "(+)"

**Resultado:** 29 → 0 fornecedores problemáticos no DANFE, 9 → 0 no relatório de lotes.

### SabespWaterBillExtractor (02/02/2026)

PDFs da Sabesp são protegidos por senha (CPF do titular). Este extrator:

- Detecta emails pelo sender (`sabesp.com.br`) ou subject
- Extrai dados do corpo HTML: valor, vencimento, fornecimento, código de barras
- Retorna `tipo_documento="UTILITY_BILL"` com `subtipo="WATER"`

```python
# Uso automático pelo BatchProcessor quando detecta email Sabesp
from extractors.sabesp import SabespWaterBillExtractor

if SabespWaterBillExtractor.can_handle_email(email_subject, email_sender, email_body):
    data = SabespWaterBillExtractor().extract(email_body)
```

### CscNotaDebitoExtractor (02/02/2026)

Processa documentos "NOTA DÉBITO / RECIBO FATURA" da CSC GESTAO INTEGRADA S/A (CNPJ: 38.323.227/0001-40).
Estes documentos são usados para cobrança de tarifas bancárias e enviados por Linnia Barreto.

- Detecta por texto "NOTA DÉBITO / RECIBO FATURA" + CNPJ/nome da CSC
- Suporta variações de OCR (espaços entre letras)
- Extrai: número, valor, data emissão, competência, tomador, CNPJ tomador
- Retorna `tipo_documento="OUTRO"` com `subtipo="NOTA_DEBITO"`

```python
# Uso automático via EXTRACTOR_REGISTRY (posição 13)
from extractors.csc_nota_debito import CscNotaDebitoExtractor

if CscNotaDebitoExtractor.can_handle(texto):
    data = CscNotaDebitoExtractor().extract(texto)
    # data["numero_documento"] = "347"
    # data["valor_total"] = 2163.60
    # data["subtipo"] = "NOTA_DEBITO"
```

### Normalização de Fornecedores e Sanitização CSV (09/02/2026)

**Problema 1:** CSV `relatorio_lotes.csv` com linhas quebradas por `\n` no campo `email_subject`.

**Solução:** Sanitização em `run_ingestion.py` - remove `\n`, `\r`, `;` antes de exportar.

**Problema 2:** Fornecedores extraídos com prefixos/sufixos inválidos:

- `E-mail RSMBRASILAUDITORIAECONSULTORIALTDA CONTATO`
- `PITTSBURG FIP MULTIESTRATEGIA CPF ou CNPJ`
- `forma, voc assegura que seu pagamento é seguro.`

**Soluções implementadas:**

1. **`extractors/utils.py` → `normalize_entity_name()`**:
    - Remove prefixos: `E-mail`, `Beneficiario`, `Nome/NomeEmpresarial`
    - Remove sufixos: `CONTATO`, `CPF ou CNPJ`, `- CNPJ`, `| CNPJ`, `- Endereço...`

2. **`extractors/boleto.py` → `_looks_like_header_or_label()`**:
    - Blacklist: `PAGAMENTO`, `SEGURO`, `ASSEGURA`, `FORMA,`, `E-MAIL`, `ENDEREÇO`

3. **Centralização**: `batch_result.py` e `document_pairing.py` agora usam `normalize_entity_name()` centralizado.

**Arquivos modificados:**

- `run_ingestion.py`
- `extractors/utils.py`
- `extractors/boleto.py`
- `core/batch_result.py`
- `core/document_pairing.py`

**Sessão completa:** `docs/context/sessao_2026_02_09_saude_extracao.md`

---

> 💡 **Dica:** Guarde este README como favorito. Ele é o mapa para navegar toda a documentação!
