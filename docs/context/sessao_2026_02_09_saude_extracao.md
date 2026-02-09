# Sessão 2026-02-09: Análise de Saúde das Extrações

## Resumo

Análise completa do `relatorio_lotes.csv` para identificar problemas de qualidade nas extrações e implementar correções.

---

## Problemas Identificados e Corrigidos

### 1. CSV Corrompido por Quebras de Linha (CRÍTICO) ✅

**Problema:** 26 linhas do CSV estavam quebradas por `\n` no campo `email_subject`.

**Correção Implementada:** `run_ingestion.py` (linhas 210-235)
```python
# Sanitiza campos de texto para evitar quebras de linha no CSV
for resumo in resumos_lotes:
    if resumo.get("email_subject"):
        resumo["email_subject"] = (
            resumo["email_subject"]
            .replace("\n", " ")
            .replace("\r", " ")
            .replace(";", ",")  # Evita conflito com delimitador CSV
            .strip()
        )
    # Similar para email_sender e divergencia
```

**Status:** ✅ Aplicado e verificado (0 linhas quebradas)

---

### 2. Fornecedor "forma, voc assegura que seu pagamento é seguro" ✅

**Problema:** 15 boletos Giga+/DB3 com fornecedor extraído incorretamente.

**Causa:** O `BoletoExtractor` capturava texto genérico de aviso de segurança como nome do fornecedor.

**Correção Implementada:** `extractors/boleto.py` → `_looks_like_header_or_label()` (linhas 376-387)
```python
# Frases genéricas que não são nomes de fornecedor
bad_tokens = [
    # ... tokens existentes ...
    "PAGAMENTO",
    "SEGURO",
    "ASSEGURA",
    "FORMA,",
    "DESSA FORMA",
    "CPF OU CNPJ",
    "CONTATO CNPJ",
    "E-MAIL",
    "ENDEREÇO",
    "MUNICÍPIO",
    "CEP ",
]
```

**Status:** ✅ Aplicado e verificado (0 ocorrências)

---

### 3. Fornecedores com Prefixos/Sufixos Inválidos ✅

**Problema:** Fornecedores como:
- `E-mail RSMBRASILAUDITORIAECONSULTORIALTDA CONTATO`
- `Beneficiario NEWCO PROGRAMADORA...`
- `PITTSBURG FIP MULTIESTRATEGIA CPF ou CNPJ`

**Correção Implementada:** `extractors/utils.py` → `normalize_entity_name()` (linhas 526-553)
```python
# Remove prefixos genéricos
prefixes_to_remove = [
    r"^E-mail\s+",
    r"^Beneficiario\s+",
    r"^Beneficiário\s+",
    r"^Nome/NomeEmpresarial\s+",
    r"^Nome\s+/\s*Nome\s+Empresarial\s+E-mail\s+",
    r"^Nome\s+Empresarial\s+",
    r"^Razão\s+Social\s+",
    r"^Razao\s+Social\s+",
]

# Remove sufixos genéricos
suffixes_to_remove = [
    r"\s+CONTATO\s*$",
    r"\s+CONTATO@[^\s]+\s*$",
    r"\s+CPF\s+ou\s+CNPJ\s*$",
    r"\s+-\s+CNPJ\s*$",
    r"\s+-\s+CNPJ\s+\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s*$",
    r"\s+\|\s*CNPJ\s+-\s+CNPJ\s*$",
    r"\s+\|\s*CNPJ\s*$",
    r"\s+\|\s*$",  # "|" solto no final
    r"\s+-\s+Endereço.*$",
    r"\s+-\s+Município.*$",
    r"\s+-\s+CEP.*$",
    r"\s+Endereço\s+Município\s+CEP.*$",
]
```

**Status:** ✅ Código implementado, aguardando reprocessamento

---

### 4. Centralização da Normalização de Fornecedor ✅

**Problema:** Funções `_normalize_fornecedor` duplicadas em `batch_result.py` e `document_pairing.py`.

**Correção Implementada:** 
- Ambos arquivos agora importam e usam `normalize_entity_name` de `extractors/utils.py`
- Removido código duplicado

**Arquivos alterados:**
- `core/batch_result.py` (linha 34, 225-227)
- `core/document_pairing.py` (linha 36, 1095-1100)

**Status:** ✅ Código implementado, aguardando reprocessamento

---

## Correções a Serem Aplicadas no Próximo Reprocessamento

Após executar `python run_ingestion.py --reprocess`, os seguintes fornecedores serão corrigidos:

| Antes | Depois |
|-------|--------|
| `REGUSDOBRASILLTDA - Endereço Município CEP PARAIBA` | `REGUSDOBRASILLTDA` |
| `NEWCO PROGRAMADORA E P. COMUNICACAO LTDA - CNPJ` | `NEWCO PROGRAMADORA E P. COMUNICACAO LTDA` |
| `VERO S.A. CNL. \| CNPJ - CNPJ` | `VERO S.A. CNL.` |
| `Nome / Nome Empresarial E-mail RSM BRASIL...` | `RSM BRASIL...` |
| `DB3 SERVICOS - CE - FORTALEZA - 23 \|` | `DB3 SERVICOS - CE - FORTALEZA` |

---

## Métricas do CSV Atual (antes do reprocessamento final)

| Métrica | Valor |
|---------|-------|
| Total de lotes | 1.238 |
| CONCILIADO | 118 (9,5%) |
| CONFERIR | 1.097 (88,6%) |
| PAREADO_FORCADO | 18 |
| DIVERGENTE | 5 |
| Linhas com problema de estrutura | **0** ✅ |
| Lotes com valor extraído | 90,9% ✅ |
| Lotes com erros de processamento | 7 (0,6%) ✅ |

---

## Problemas Pendentes (Prioridade Média)

### Vencimento Não Encontrado
- **Impacto:** 298 lotes (24%)
- **Ação:** Revisar padrões de regex em `utility_bill.py` e `outros.py`

### Fornecedores Vazios
- **Impacto:** ~27 lotes
- **Ação:** Investigar casos específicos para identificar padrão

### Nome de Fornecedor sem Espaços (OCR ruim)
- **Exemplo:** `RSMBRASILAUDITORIAECONSULTORIALTDA` ao invés de `RSM BRASIL AUDITORIA E CONSULTORIA LTDA`
- **Causa:** PDF gerado com texto sem espaços (problema de origem, não de OCR)
- **Ação:** Baixa prioridade - nome está correto, apenas concatenado

---

## Arquivos Modificados Nesta Sessão

| Arquivo | Tipo de Alteração |
|---------|-------------------|
| `run_ingestion.py` | Sanitização de campos CSV |
| `extractors/boleto.py` | Blacklist de termos genéricos |
| `extractors/utils.py` | Remoção de prefixos/sufixos em `normalize_entity_name` |
| `core/batch_result.py` | Uso de `normalize_entity_name` centralizado |
| `core/document_pairing.py` | Uso de `normalize_entity_name` centralizado |
| `data/output/RELATORIO_SAUDE_EXTRACAO.md` | Relatório detalhado gerado |

---

## Comandos de Verificação Pós-Reprocessamento

```bash
# Verificar linhas quebradas (deve ser 0)
awk -F';' 'NF!=21 && NR>1 {print NR}' data/output/relatorio_lotes.csv | wc -l

# Verificar fornecedores problemáticos (deve ser 0 ou próximo)
grep -cE "forma, voc|E-mail [A-Z]|CONTATO$|CPF ou CNPJ$|Beneficiario |\| CNPJ" data/output/relatorio_lotes.csv

# Listar top 30 fornecedores para revisão manual
awk -F';' 'NR>1 {print $6}' data/output/relatorio_lotes.csv | sort | uniq -c | sort -rn | head -30
```

---

## Próximos Passos

1. **Reprocessar lotes** quando possível:
   ```bash
   python run_ingestion.py --reprocess
   ```

2. **Verificar métricas** após reprocessamento

3. **Investigar vencimentos ausentes** se taxa continuar baixa

---

*Sessão realizada em 09/02/2026*
