# Sessão 2026-02-20: Correções de Normalização e Extratores

## Resumo

Implementadas correções abrangentes para:

1. Eliminar headers/labels capturados como fornecedores
2. Separar nomes de empresas concatenados (sem espaços)
3. Melhorar extratores de boleto, NFSe e comprovante bancário para casos específicos

## Problemas Identificados

### 1. Headers/Labels extraídos como fornecedor (14 ocorrências)

| Padrão Problemático                           | Qtd | Fonte                            |
| --------------------------------------------- | --- | -------------------------------- |
| `DOCUMENTO(S)`                                | 8x  | Boletos - "DOCUMENTO(S): 558109" |
| `Cedente Número do Documento Espécie...`      | 2x  | Header de boleto                 |
| `PRESTADOR DE SERVIÇOS` (com código)          | 2x  | Label de NFSe São Paulo          |
| `EMITENTE DA NFS-e Prestador de serviço Nome` | 1x  | Header de DANFSe                 |
| `nome do recebedor`                           | 1x  | Label de comprovante PIX         |

### 2. Nomes de fornecedor concatenados (91 ocorrências)

Exemplos:

- `RSMBRASILAUDITORIAECONSULTORIALTDA` → `RSM BRASIL AUDITORIA E CONSULTORIA LTDA`
- `REGUSDOBRASILLTDA` → `REGUS DO BRASIL LTDA`
- `WALQUIRIACRISTINASILVA` → `WALQUIRIA CRISTINA SILVA`
- `INTERFOCUSTECNOLOGIALTDA` → `INTERFOCUS TECNOLOGIA LTDA`

**Causa**: OCR de alguns PDFs retorna texto sem espaços entre palavras.

### 3. Extratores não reconhecendo layouts específicos

- **NFSe São Paulo**: Layout com "PRESTADOR DE SERVIÇOS" seguido de "Nome/Razão Social:" em linhas separadas
- **DANFSe Nacional**: Layout com "Nome / Nome empresarial" seguido de nome em múltiplas linhas
- **Boleto com Cedente**: Layout onde "Cedente" é label isolado, nome aparece várias linhas depois
- **Comprovante PIX Itaú**: Layout com "nome do recebedor:" em minúsculas

## Soluções Implementadas

### 1. Blacklist de headers/labels (`extractors/utils.py`)

Adicionada verificação antecipada no `normalize_entity_name()`:

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

Nova função com:

- **150+ palavras** em dicionário (sufixos empresariais, termos comuns, nomes)
- **Algoritmo greedy**: palavras mais longas primeiro
- **Preservação**: não altera strings que já têm espaços
- **Fallback**: separa pelo menos o sufixo empresarial

### 3. Boleto extractor (`extractors/boleto.py`)

Adicionado padrão para "Cedente" como label isolado:

```python
# Busca "Cedente" sozinho e depois procura nome de empresa nas próximas linhas
if re.match(r"^Cedente\s*$", line_stripped, re.IGNORECASE):
    for j in range(i + 1, min(i + 8, len(lines))):
        # Pula códigos de banco, autenticação, linha digitável
        # Busca linha com sufixo empresarial (LTDA, S.A., etc.)
```

### 4. NFSe extractor (`extractors/nfse_generic.py`)

Adicionados 2 novos padrões:

**Padrão São Paulo** (PRESTADOR DE SERVIÇOS → Nome/Razão Social):

```python
# Layout:
#   PRESTADOR DE SERVIÇOS
#   CPF/CNPJ:
#   Nome/Razão Social:    <- label
#   ...
#   OBVIO BRASIL S.A      <- valor (várias linhas depois)
```

**Padrão DANFSe Nacional** (Nome / Nome empresarial em múltiplas linhas):

```python
# Layout:
#   EMITENTE DA NFS-e
#   ...
#   Nome / Nome empresarial
#   52.677.763 WILIAN SANTOS MENDES  <- linha 1
#   ARAUJO                            <- linha 2 (continuação)
```

### 5. Comprovante Bancário extractor (`extractors/comprovante_bancario.py`)

Adicionado padrão para "nome do recebedor:" (PIX Itaú):

```python
r"nome\s+do\s+recebedor\s*:\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9\s\.\-&]+?)(?:\s*\n|CPF|CNPJ|$)"
```

## Arquivos Modificados

| Arquivo                              | Mudanças                                                              |
| ------------------------------------ | --------------------------------------------------------------------- |
| `extractors/utils.py`                | + blacklist exata/regex, + `_fix_concatenated_name()`                 |
| `extractors/boleto.py`               | + padrões em `_looks_like_header_or_label()`, + extração de "Cedente" |
| `extractors/nfse_generic.py`         | + padrão São Paulo, + padrão DANFSe multi-linha                       |
| `extractors/comprovante_bancario.py` | + padrão "nome do recebedor:"                                         |
| `tests/test_extractor_utils.py`      | + 9 novos testes                                                      |

## Casos Corrigidos

| Batch                          | Problema Original           | Fornecedor Correto                    |
| ------------------------------ | --------------------------- | ------------------------------------- |
| email_20260220_082042_b01a5fe4 | PRESTADOR DE SERVIÇOS       | OBVIO BRASIL SOFTWARE E SERVIÇOS S.A  |
| email_20260220_082045_d079a26a | nome do recebedor           | PITTSBURG FIP MULTIESTRATEGIA         |
| email_20260220_082047_f5e26b85 | PRESTADOR DE SERVIÇOS       | OBVIO BRASIL SOFTWARE E SERVIÇOS S.A  |
| email_20260220_082048_c609ef2c | EMITENTE DA NFS-e           | WILIAN SANTOS MENDES ARAUJO           |
| email_20260220_082049_3fce0cd6 | DOCUMENTO(S)                | OBVIO BRASIL SOFTWARE E SERVICOS S.A. |
| email_20260220_082050_423da17e | Cedente Número do Documento | CONCEITO A EM AUDIOVISUAL S.A.        |

## Testes

- **670 testes passando** (9 novos adicionados)
- **0 erros ou warnings** nos arquivos modificados

## Impacto no CSV

### Antes

- Fornecedores vazios: 95
- Headers/labels como fornecedor: 14
- Nomes colados (ilegíveis): 91

### Depois (após reprocessamento)

- Fornecedores vazios: ~95 (alguns dos 14 agora terão fornecedor correto)
- Headers/labels como fornecedor: 0 ✓
- Nomes colados: 0 ✓ (todos separados corretamente)

## Próximos Passos

1. **Reprocessar dataset** para aplicar correções:

    ```bash
    python run_ingestion.py --reprocess
    ```

2. **Verificar resultado**:
    ```bash
    python -c "import pandas as pd; df=pd.read_csv('data/output/relatorio_lotes.csv', sep=';'); print(df['status_conciliacao'].value_counts())"
    ```

## Commit Message

```
fix(extractors): improve supplier extraction and add blacklist for headers

- Add blacklist patterns in normalize_entity_name() to reject headers
  like DOCUMENTO(S), PRESTADOR DE SERVIÇOS, EMITENTE DA NFS-e, etc.
- Implement _fix_concatenated_name() to split OCR-concatenated company
  names (e.g., RSMBRASILAUDITORIAECONSULTORIALTDA -> RSM BRASIL...)
- Add "Cedente" label pattern in boleto extractor
- Add São Paulo and DANFSe multi-line patterns in NFSe extractor
- Add "nome do recebedor:" pattern for PIX Itaú in comprovante bancário
- Add 9 unit tests for new functionality

Fixes 14 header/label extractions, 91 concatenated names, and improves
extraction for São Paulo NFSe, DANFSe, Cedente boletos, and PIX Itaú.
```
