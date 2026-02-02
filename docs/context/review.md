# Prompt: Análise de Qualidade de Extração (Review)

> **Uso:** Análise aprofundada de casos problemáticos identificados em `data/output/analise_pdfs_detalhada.txt` ou `relatorio_lotes.csv`
>
> **Pre-requisitos:** Executar `scripts/check_problematic_pdfs.py` para gerar análise detalhada

---

## Contexto do Sistema

Pipeline de ETL que processa PDFs de documentos fiscais:

```
E-mail → PDF → Extração Texto (Native/OCR) → Classificação (Extratores) → Correlação NF↔Boleto → CSV → Google Sheets
```

**Extratores disponíveis:** 23 extratores especializados (incluindo CscNotaDebitoExtractor) + fallback genéricos
**Prioridade:** Ordem em `extractors/__init__.py` (0 = mais prioritário)
**Colunas críticas no CSV:** `fornecedor`, `vencimento`, `numero_nota`, `valor_compra`, `valor_boleto`

---

## Input do Caso para Análise

```yaml
CASO_ID: #[ex: CASO #220]
BATCH_ID: #[ex: email_20260129_084433_5fafb989]
ARQUIVO_PDF: #[ex: 01_nota_fiscal_tipo0_n521912_c128326_1767712922.pdf]

# Dados do CSV relatorio_lotes.csv
CSV_DATA:
    tipo_documento: #[NFSE/Boleto/Danfe/Outro]
    valor_compra: #[ex: R$ 0.00]
    valor_boleto: #[ex: R$ 0.00]
    vencimento: #[ex: "" ou "2026-01-15"]
    fornecedor: #[ex: "TCF Telecom"]
    numero_nota: #[ex: "" ou "521912"]
    numero_documento: #[ex: "" ou "12345"]
    status_conciliacao: #[CONCILIADO/PAREADO_FORCADO/CONFERIR]

# Conteúdo do PDF (texto bruto extraído)
TEXTO_BRUTO: |
    [COLE AQUI o texto bruto do PDF ou os trechos relevantes]
    [Use o comando: python scripts/inspect_pdf.py <arquivo.pdf> --raw]

# Problema reportado
PROBLEMA: |
    [Descreva o que está errado]
    [Ex: "Valor aparece 0 mas PDF tem R$ 700,00"]
    [Ex: "Classificado como Desconhecido mas é NFSe"]
```

---

## Template de Análise (preencha cada seção)

### 1. CLASSIFICAÇÃO DO ERRO

**Tipo de erro (marque todos que aplicam):**

- [ ] **OCR Failure:** Texto ilegível/corrupção de caracteres
- [ ] **Regex Failure:** Padrão não captura variação de layout
- [ ] **Routing Error:** Extrator genérico impediu o específico
- [ ] **Missing Field:** Informação existe mas não foi extraída
- [ ] **False Positive/Negative:** Classificação incorreta do documento
- [ ] **Correlation Error:** NF e Boleto não pareados corretamente
- [ ] **Validation Error:** Campo extraído mas inválido (data futura, valor negativo)
- [ ] **PDF Password:** Documento protegido por senha

**Severidade:**

- [ ] **ALTA:** Valor não extraído, exportação para Sheets bloqueada, impacto financeiro
- [ ] **MÉDIA:** Campo secundário faltando, fornecedor genérico, necessita revisão manual
- [ ] **BAIXA:** Aviso cosmético, não afeta processamento

### 2. ANÁLISE TÉCNICA DETALHADA

#### 2.1 Diagnóstico do Campo Problemático

| Campo           | Esperado       | Extraído    | Análise                                |
| --------------- | -------------- | ----------- | -------------------------------------- |
| **Valor**       | #[R$ 700,00]   | #[R$ 0,00]  | #[Pegou campo errado? Regex falhou?]   |
| **Número Nota** | #[521912]      | #[vazio]    | #[Padrão diferente? Campo não existe?] |
| **Vencimento**  | #[15/01/2026]  | #[vazio]    | #[Formato diferente? Não é boleto?]    |
| **Fornecedor**  | #[TCF Telecom] | #[genérico] | #[Pegou label ao invés do valor?]      |
| **Tipo**        | #[NFSE]        | #[OUTRO]    | #[can_handle muito restritivo?]        |

#### 2.2 Análise do Texto Bruto

**Trechos relevantes do PDF:**

```
#[Cole trechos do texto bruto onde a informação aparece]
#[Ex: "Valor Total dos Serviços R$ 700,00"]
#[Ex: "Nota Fiscal Nº 521912"]
```

**Onde está o padrão no texto:**

- Linha/Caractere: #[indique posição aproximada]
- Contexto: #[antes/depois de qual informação]
- Variações: #[ex: "Valor Total" vs "Valor Total dos Serviços"]

#### 2.3 Análise de Roteamento (se aplicável)

**Extrator que deveria ter sido usado:** #[NomeDoExtrator]
**Extrator que foi realmente usado:** #[NomeDoExtratorUsado]

**Teste de can_handle():**

```python
# Para cada extrator relevante, verificar:
[NomeExtrator].can_handle(texto) = #[True/False]

# Prioridade no registry:
#[0] BoletoRepromaqExtractor
#[1] EmcFaturaExtractor
# ...
#[N] [ExtratorUsado] ← Foi selecionado aqui
```

**Causa do roteamento errado:**

- [ ] Extrator específico recusou (can_handle=False)
- [ ] Extrator específico não existe
- [ ] Extrator específico vem DEPOIS do genérico no registry
- [ ] Padrão negativo está bloqueando documento válido

### 3. MATRIZ DE IMPACTO

| Critério                 | Avaliação                           | Detalhes                          |
| ------------------------ | ----------------------------------- | --------------------------------- |
| **Severidade**           | #[ALTA/MÉDIA/BAIXA]                 | #[Justificativa]                  |
| **Frequência**           | #[Único/Padrão frequente/Episódico] | #[Quantos casos similares?]       |
| **Bloqueia Sheets**      | #[Sim/Não]                          | #[Coluna afetada na planilha PAF] |
| **Bloqueia Conciliação** | #[Sim/Não]                          | #[NF↔Boleto pareados?]            |
| **Regressão**            | #[Sim/Não]                          | #[Quebra casos que funcionavam?]  |

**Casos similares encontrados:**

```bash
# Comando para buscar casos similares no CSV
grep -E "<padrao>" data/output/relatorio_lotes.csv | wc -l
#[N] casos com padrão similar detectados
```

### 4. RECOMENDAÇÃO DE CORREÇÃO

#### Opção A: Ajustar Regex/Campo em Extrator Existente

```yaml
Arquivo: extractors/[nome_extrator.py]
Método:
    [
        can_handle / _extract_valor / _extract_numero_nota / _extract_vencimento / _extract_fornecedor,
    ]

Regex Atual:
    pattern: r"..."
    problema: "[por que falha]"

Regex Sugerido:
    pattern: r"..."
    melhoria: "[por que resolve]"

Testes de Regressão:
    - ["caso_1.pdf", "valor_esperado_1"]
    - ["caso_2.pdf", "valor_esperado_2"]
```

#### Opção B: Criar Novo Extrator

```yaml
Necessidade: #[Sim/Não - justifique]
Prioridade no Registry: #[0-15]
Justificativa: #[Por que extrator específico é necessário]
Padrão Identificador: #[CNPJ único, termo específico, layout distinto]
Campos Especiais: #[Lista de campos com padrões únicos]
```

**Use o prompt `creation.md` para gerar o código do novo extrator.**

#### Opção C: Correção de Dados (sem código)

```yaml
Aplicável: #[Sim/Não]
Justificativa: #[Por que não vale automatizar]
Quantidade de casos: #[N]
Ação manual: #[O que fazer com estes casos específicos]
```

### 5. PLANO DE VALIDAÇÃO

**Testes a executar após correção:**

```bash
# 1. Teste unitário do caso específico
python scripts/inspect_pdf.py <ARQUIVO_PDF>

# 2. Verificar que não quebrou casos existentes (regressão)
python scripts/validate_extraction_rules.py --batch-mode

# 3. Reprocessar batch afetado
python run_ingestion.py --batch-folder <PASTA_BATCH>

# 4. Validar CSV de saída
grep <BATCH_ID> data/output/relatorio_lotes.csv

# 5. Validar exportação (dry-run)
python scripts/export_to_sheets.py --dry-run
```

**Critérios de Aceitação:**

- [ ] Campo problemático extraído corretamente
- [ ] Tipo de documento classificado corretamente
- [ ] Correlação NF↔Boleto funcionando (se aplicável)
- [ ] Exportação para Sheets com dados completos
- [ ] Nenhuma regressão em casos existentes

---

## Checklist de Análise Completa

Antes de finalizar a análise, verifique:

- [ ] Coletei o texto bruto do PDF com `--raw`
- [ ] Identifiquei o extrator que foi realmente usado
- [ ] Testei os extratores candidatos com `inspect_pdf.py`
- [ ] Verifiquei se há casos similares no CSV
- [ ] Analisei logs específicos do batch
- [ ] Defini severidade baseada em impacto real
- [ ] Proposta de correção é mínima e focada
- [ ] Plano de validação está claro

---

## Referência Rápida de Padrões

### Padrões Comuns de Problemas

| Sintoma no CSV                | Causa Provável                 | Ação                         |
| ----------------------------- | ------------------------------ | ---------------------------- |
| Valor = 0 com PDF tendo valor | Regex pegou campo errado       | Ajustar `_extract_valor`     |
| Vencimento vazio              | Formato de data diferente      | Adicionar padrão de parse    |
| Fornecedor = "CNPJ..."        | Pegou label do campo           | Melhorar regex de fornecedor |
| Tipo = OUTRO                  | Extrator específico não existe | Criar novo extrator          |
| Status = CONFERIR             | Divergência NF↔Boleto          | Verificar correlação         |

### Comandos Úteis para Debug

```bash
# Verificar extração de um PDF específico
python scripts/inspect_pdf.py <arquivo.pdf>

# Ver texto bruto
python scripts/inspect_pdf.py <arquivo.pdf> --raw

# Buscar no CSV
grep -i "<termo>" data/output/relatorio_lotes.csv

# Analisar logs do batch
python scripts/analyze_logs.py --batch <batch_id>

# Listar batches problemáticos
python scripts/list_problematic.py
```
