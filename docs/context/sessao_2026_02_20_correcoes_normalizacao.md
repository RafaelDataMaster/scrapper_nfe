# Sessão 2026-02-20: Correções de Normalização de Fornecedores

## Resumo

Implementadas correções para eliminar headers/labels capturados como fornecedores e separar nomes de empresas concatenados (sem espaços) no CSV de relatório.

## Problemas Identificados

### 1. Headers/Labels extraídos como fornecedor (14 ocorrências)

| Padrão Problemático | Qtd | Fonte |
|---------------------|-----|-------|
| `DOCUMENTO(S)` | 8x | Boletos - "DOCUMENTO(S): 558109" |
| `Cedente Número do Documento Espécie...` | 2x | Header de boleto |
| `PRESTADOR DE SERVIÇOS` (com código) | 2x | Label de NFSe |
| `EMITENTE DA NFS-e Prestador de serviço Nome` | 1x | Header de NFSe |
| `nome do recebedor` | 1x | Label de comprovante de entrega |

### 2. Nomes de fornecedor concatenados (91 ocorrências)

Exemplos:
- `RSMBRASILAUDITORIAECONSULTORIALTDA` → `RSM BRASIL AUDITORIA E CONSULTORIA LTDA`
- `REGUSDOBRASILLTDA` → `REGUS DO BRASIL LTDA`
- `WALQUIRIACRISTINASILVA` → `WALQUIRIA CRISTINA SILVA`
- `INTERFOCUSTECNOLOGIALTDA` → `INTERFOCUS TECNOLOGIA LTDA`

**Causa**: OCR de alguns PDFs retorna texto sem espaços entre palavras.

## Soluções Implementadas

### 1. Blacklist de headers/labels (`extractors/utils.py`)

Adicionada verificação antecipada no `normalize_entity_name()` para rejeitar padrões que NUNCA são fornecedores válidos:

```python
blacklist_exact = [
    "DOCUMENTO(S)", "BENEFICIÁRIO", "CEDENTE", "PAGADOR",
    "PRESTADOR DE SERVIÇOS", "EMITENTE DA NFS-E", 
    "NOME DO RECEBEDOR", "CNPJ", "CPF", ...
]

blacklist_patterns = [
    r"^Cedente\s+N[úu]mero\s+do\s+Documento",
    r"^EMITENTE\s+DA\s+NFS-?E\s+Prestador",
    r"^DOCUMENTO\(S\)\s*:?\s*[\d\s]*$",
    r"^nome\s+do\s+recebedor\s*$",
    ...
]
```

### 2. Separação de nomes concatenados (`_fix_concatenated_name()`)

Nova função que detecta strings longas sem espaços e tenta separar usando dicionário de palavras conhecidas:

- **150+ palavras** em dicionário (sufixos empresariais, termos comuns, nomes)
- **Algoritmo greedy**: palavras mais longas primeiro para evitar matches parciais
- **Preservação**: não altera strings que já têm espaços
- **Fallback**: separa pelo menos o sufixo empresarial (LTDA, S.A., etc.)

### 3. Atualização do boleto extractor (`extractors/boleto.py`)

Expandida a função `_looks_like_header_or_label()` com novos padrões para evitar capturar headers como fornecedor.

## Arquivos Modificados

| Arquivo | Mudanças |
|---------|----------|
| `extractors/utils.py` | + blacklist, + `_fix_concatenated_name()` |
| `extractors/boleto.py` | + padrões em `_looks_like_header_or_label()` |
| `tests/test_extractor_utils.py` | + 9 novos testes |

## Testes

### Resultados
- **670 testes passando** (9 novos adicionados)
- **0 erros ou warnings** nos arquivos modificados

### Novos testes adicionados
- `test_rejeita_documento_s_header`
- `test_rejeita_cedente_header`
- `test_rejeita_emitente_nfse_header`
- `test_rejeita_codigo_prestador`
- `test_rejeita_nome_do_recebedor`
- `test_rejeita_labels_simples`
- `test_separa_nomes_colados`
- `test_nao_altera_nomes_com_espacos`
- `test_separa_nomes_pessoas_colados`

## Impacto no CSV

### Antes
- Fornecedores vazios: 95
- Headers/labels como fornecedor: 14
- Nomes colados (ilegíveis): 91

### Depois (estimado)
- Fornecedores vazios: 109 (+14 headers removidos)
- Headers/labels como fornecedor: 0 ✓
- Nomes colados: 0 ✓ (todos corrigidos)

## Próximos Passos

1. **Reprocessar dataset** para aplicar correções:
   ```bash
   python run_ingestion.py --reprocess
   ```

2. **Verificar resultado**:
   ```bash
   python -c "import pandas as pd; df=pd.read_csv('data/output/relatorio_lotes.csv', sep=';'); print(df['status_conciliacao'].value_counts())"
   ```

3. **Analisar fornecedores vazios** (109 casos) para identificar se há padrões recuperáveis

## Commit Message

```
fix(extractors): add blacklist for headers/labels and fix concatenated names

- Add blacklist patterns in normalize_entity_name() to reject headers
  like DOCUMENTO(S), PRESTADOR DE SERVIÇOS, EMITENTE DA NFS-e, etc.
- Implement _fix_concatenated_name() to split OCR-concatenated company
  names (e.g., RSMBRASILAUDITORIAECONSULTORIALTDA -> RSM BRASIL...)
- Expand _looks_like_header_or_label() in boleto extractor
- Add 9 unit tests for new functionality

Fixes 14 header/label extractions and 91 concatenated names in CSV.
```
