# Relatório de Saúde das Extrações - 09/02/2026

> **Atualização:** Correções críticas implementadas nesta sessão (ver seção 5).

## Resumo Executivo

| Métrica                              | Valor | %     |
| ------------------------------------ | ----- | ----- |
| **Total de lotes processados**       | 1.225 | 100%  |
| **Lotes com valor extraído**         | 1.113 | 90,9% |
| **Lotes CONCILIADO**                 | 116   | 9,5%  |
| **Lotes CONFERIR**                   | 1.086 | 88,7% |
| **Lotes DIVERGENTE**                 | 5     | 0,4%  |
| **Lotes PAREADO_FORCADO**            | 18    | 1,5%  |
| **Lotes com erros de processamento** | 7     | 0,6%  |

---

## 1. Problemas Críticos Identificados

### 1.1 CSV Corrompido por Quebras de Linha (CRÍTICO)

**Impacto:** 26 linhas do CSV estão quebradas em 2 partes, causando desalinhamento de colunas.

**Causa:** O campo `email_subject` contém caracteres de quebra de linha (`\n`) que não estão sendo escapados ao exportar para CSV.

**Exemplo:**

```
"NEOENERGIA ELEKTRO | Fatura / Conta de luz por email | N.
 01-20259829800793.0"
```

**Correção Necessária:**

- Sanitizar `email_subject` removendo `\n`, `\r` e aspas antes da exportação
- Implementar em `run_ingestion.py` na função `export_batch_results`

**Arquivo:** `scrapper/run_ingestion.py` linha ~237

```python
# Antes de criar o DataFrame, sanitizar email_subject
for resumo in resumos_lotes:
    if resumo.get('email_subject'):
        resumo['email_subject'] = resumo['email_subject'].replace('\n', ' ').replace('\r', ' ').strip()
```

✅ **CORRIGIDO** - Implementado em `run_ingestion.py` (linhas 210-235)

---

### 1.2 Fornecedor Incorreto - Giga+ Empresas (ALTA)

**Impacto:** 15 boletos com fornecedor extraído incorretamente.

**Problema:** O `BoletoExtractor` está extraindo a frase "forma, voc assegura que seu pagamento é seguro." como nome do fornecedor, quando deveria ser "DB3 SERVICOS".

**Texto do PDF:**

```
FIQUE ATENTO! Sempre que pagar sua fatura por boleto ou PIX, confira se o nome do beneficiário é "DB3 SERVICOS - CE - FORTALEZA - 23 | 0001-35" Dessa forma, você assegura que seu pagamento é seguro.
```

**Causa:** A regex de extração de fornecedor está capturando texto após o padrão de CNPJ de forma incorreta.

**Correção Proposta:**

- Criar extrator específico `BoletoGigaMaisExtractor` para faturas Giga+/DB3 Serviços
- Ou ajustar `_extract_fornecedor_nome` em `boleto.py` para blacklist de termos como "pagamento", "seguro", "assegura"

**Lotes afetados (amostra):**

- `email_20260209_125005_7e90478e_bol`
- `email_20260209_125005_2c058ef1_bol`

✅ **CORRIGIDO** - Adicionada blacklist em `_looks_like_header_or_label` (`boleto.py` linhas 376-387)

- Termos adicionados: "PAGAMENTO", "SEGURO", "ASSEGURA", "FORMA,", "DESSA FORMA", "CPF OU CNPJ", "CONTATO CNPJ", "E-MAIL", "ENDEREÇO", "MUNICÍPIO", "CEP "
- Testado: Fornecedor agora extrai corretamente "DB3 SERVICOS - CE - FORTALEZA - 23"

---

### 1.3 Fornecedores com Nome Corrompido (MÉDIA)

**Padrões identificados:**

| Padrão Extraído                                             | Ocorrências | Fornecedor Real                          |
| ----------------------------------------------------------- | ----------- | ---------------------------------------- |
| `E-mail RSMBRASILAUDITORIAECONSULTORIALTDA CONTATO`         | 10          | RSM BRASIL AUDITORIA E CONSULTORIA LTDA  |
| `E-mail REGUSDOBRASILLTDA - Endereço Município CEP PARAIBA` | 9           | REGUS DO BRASIL LTDA                     |
| `PITTSBURG FIP MULTIESTRATEGIA CPF ou CNPJ`                 | 23          | Documento administrativo (OK)            |
| `Beneficiario NEWCO PROGRAMADORA...`                        | 9           | NEWCO PROGRAMADORA E P. COMUNICACAO LTDA |
| (vazio)                                                     | 29          | —                                        |

**Causa:** O extrator genérico `OutrosExtractor` está capturando texto poluído do PDF em vez de limpar o nome do fornecedor.

**Correção Proposta:**

- Adicionar função `sanitize_fornecedor_nome()` em `extractors/utils.py`
- Remover prefixos como "E-mail", "Beneficiario", sufixos como "CPF ou CNPJ", "CONTATO"
- Remover caracteres estranhos e normalizar espaços

✅ **CORRIGIDO** - Implementado em `normalize_entity_name()` (`utils.py` linhas 526-548)

- Prefixos removidos: "E-mail", "Beneficiario", "Nome/NomeEmpresarial", "Razão Social"
- Sufixos removidos: "CONTATO", "CPF ou CNPJ", "- Endereço", "- Município", "- CEP"
- Resultados de teste:
    - "E-mail RSMBRASILAUDITORIAECONSULTORIALTDA CONTATO" → "RSMBRASILAUDITORIAECONSULTORIALTDA"
    - "Beneficiario NEWCO PROGRAMADORA E P. COMUNICACAO LTDA" → "NEWCO PROGRAMADORA E P. COMUNICACAO LTDA"

---

## 2. Problemas de Extração de Dados

### 2.1 Vencimento Não Encontrado (ALTA)

**Impacto:** 298 lotes marcados com `[VENCIMENTO NÃO ENCONTRADO - verificar urgente]`

**Detalhamento:**

- Vencimento vazio ou inválido: 321 lotes (26,2%)

**Causas Prováveis:**

1. PDFs de documentos administrativos sem data de vencimento (esperado)
2. Faturas de energia/água com layout não reconhecido
3. Documentos OUTRO sem padrão de vencimento

**Ação:** Revisar extratores `UtilityBillExtractor`, `OutrosExtractor` e verificar cobertura de padrões de vencimento.

---

### 2.2 NF sem Valor Encontrada (MÉDIA)

**Impacto:** 295 lotes com boleto, mas sem valor na nota fiscal correspondente.

**Significado:** O sistema encontrou um boleto, mas não conseguiu parear com NF que tivesse valor extraído.

**Causas Prováveis:**

1. Boletos enviados sem NF correspondente (comportamento legítimo)
2. NF classificada como OUTRO sem extração de valor
3. Erro na correlação por número de nota diferente

---

### 2.3 Documentos Classificados como OUTRO (INFORMATIVO)

**Total:** 427 lotes com apenas documentos OUTRO (sem NF/DANFE/BOLETO identificados)

**Subtipos mais comuns:**

| Subtipo              | Quantidade |
| -------------------- | ---------- |
| ENERGY               | 268        |
| COMPROVANTE_BANCARIO | 40         |
| WATER                | 39         |
| FATURA               | 25         |
| FATURA_UFINET        | 22         |
| LOCACAO              | 17         |
| ADMINISTRATIVO       | 17         |
| FATURA_LOCACAO_EMC   | 16         |
| DISTRATO             | 10         |
| TELECOM              | 7          |

**Análise:** A maioria são faturas de concessionárias (energia, água) corretamente classificadas com subtipo. Isso é comportamento esperado do `UtilityBillExtractor`.

---

## 3. Distribuição de Tipos de Documentos

| Tipo    | Quantidade |
| ------- | ---------- |
| NFSEs   | 440        |
| DANFEs  | 190        |
| Boletos | 476        |
| Outros  | 493        |

**Total de documentos processados:** 1.599

---

## 4. Lotes com Erros de Processamento

7 lotes apresentaram erros durante o processamento:

| Batch ID                         | Provável Causa         |
| -------------------------------- | ---------------------- |
| `email_20260209_125003_f01902cf` | SABESP - PDF protegido |
| `email_20260209_125006_03098e69` | PDF protegido          |
| `email_20260209_125010_7a7ef557` | PDF protegido          |
| `email_20260209_125014_6ea8d2b6` | PDF protegido          |
| `email_20260209_125014_d0da430b` | PDF protegido          |
| `email_20260209_125014_3a9a1f7a` | PDF protegido          |
| `email_20260209_125014_3f188a62` | PDF protegido          |

**Nota:** Estes lotes têm fallback para extração do corpo do email (implementado para SABESP).

---

## 5. Plano de Correções Prioritárias

### Prioridade 1 - CRÍTICA ✅ CONCLUÍDO

1. ~~**Sanitizar email_subject no CSV**~~ ✅
    - Arquivo: `run_ingestion.py`
    - Ação: Remover `\n`, `\r` antes de exportar
    - **Status: IMPLEMENTADO**

### Prioridade 2 - ALTA ✅ CONCLUÍDO

2. ~~**Corrigir extração de fornecedor Giga+**~~ ✅
    - Arquivo: `extractors/boleto.py`
    - Ação: Adicionar blacklist de termos ("pagamento", "seguro", "assegura", "forma")
    - **Status: IMPLEMENTADO E TESTADO**

3. ~~**Sanitizar nomes de fornecedor**~~ ✅
    - Arquivo: `extractors/utils.py`
    - Ação: Criar função `sanitize_fornecedor_nome()` para remover prefixos/sufixos inválidos
    - **Status: IMPLEMENTADO E TESTADO**

### Prioridade 3 - MÉDIA (fazer este mês)

4. **Revisar padrões de vencimento** ⏳ PENDENTE
    - Arquivos: `extractors/utility_bill.py`, `extractors/outros.py`
    - Ação: Adicionar mais padrões de regex para capturar vencimentos
    - Tempo estimado: 2h

5. **Criar extrator específico para RSM/Regus** ⏳ PENDENTE (baixa prioridade)
    - Ação: Criar `NfseRsmExtractor` para NFSes deste fornecedor
    - Nota: O problema é de OCR (texto sem espaços), não de extração
    - Tempo estimado: 1h

---

## 6. Métricas de Qualidade

| Indicador                      | Valor | Meta | Status   |
| ------------------------------ | ----- | ---- | -------- |
| Taxa de extração de valor      | 90,9% | >85% | ✅ OK    |
| Taxa de conciliação NF↔Boleto  | 9,5%  | >50% | ⚠️ Baixo |
| Taxa de vencimento extraído    | 73,8% | >90% | ⚠️ Baixo |
| Taxa de fornecedor válido      | 95,1% | >95% | ✅ OK    |
| Taxa de erros de processamento | 0,6%  | <2%  | ✅ OK    |

---

## 7. Comandos para Diagnóstico

### Verificar linhas com problema no CSV:

```bash
awk -F';' 'NF!=21 && NR>1 {print NR": linha com "NF" campos"}' data/output/relatorio_lotes.csv
```

### Listar fornecedores problemáticos:

```bash
awk -F';' 'NR>1 && NF==21 {print $6}' data/output/relatorio_lotes.csv | sort | uniq -c | sort -rn | head -30
```

### Contar lotes sem vencimento:

```bash
awk -F';' 'NR>1 && ($7 == "" || $7 == "0") {count++} END {print count}' data/output/relatorio_lotes.csv
```

### Reprocessar lote específico:

```bash
cd scripts && python inspect_pdf.py ../temp_email/BATCH_ID/arquivo.pdf
```

---

## 8. Arquivos Modificados Nesta Sessão

| Arquivo                | Modificação                                                      |
| ---------------------- | ---------------------------------------------------------------- |
| `run_ingestion.py`     | Sanitização de `email_subject`, `email_sender`, `divergencia`    |
| `extractors/boleto.py` | Blacklist de termos genéricos em `_looks_like_header_or_label`   |
| `extractors/utils.py`  | Remoção de prefixos/sufixos inválidos em `normalize_entity_name` |

---

## 9. Próximos Passos

1. **Reprocessar os lotes** para aplicar as correções:

    ```bash
    python run_ingestion.py --reprocess
    ```

2. **Verificar CSV corrigido**:

    ```bash
    awk -F';' 'NF!=21 && NR>1 {print NR}' data/output/relatorio_lotes.csv | wc -l
    # Deve retornar 0
    ```

3. **Verificar fornecedores corrigidos**:
    ```bash
    grep "forma, voc" data/output/relatorio_lotes.csv | wc -l
    # Deve retornar 0
    ```

---

_Relatório gerado automaticamente em 09/02/2026_
_Atualizado com correções implementadas_
