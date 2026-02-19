# Sessão 2026-02-19: Correções Finais de Normalização de Fornecedor

## Contexto

Após extração clean do dataset, foram identificados problemas remanescentes no `relatorio_lotes.csv`:

- **`Florida USA`**: 2 ocorrências (endereço americano capturado como fornecedor)
- **Sufixo `CNPJ`**: 4 ocorrências (ex: `Rede Mulher de Televisao Ltda CNPJ`)
- **Fornecedor vazio**: 92 ocorrências (alguns legítimos)

## Problema Principal: Ordem de Operações na Normalização

A função `normalize_entity_name()` em `extractors/utils.py` aplicava verificações de padrões inválidos **antes** da remoção de números. Isso causava:

1. `Florida 33134 USA` → verificação de `^Florida\s+USA$` falhava
2. Números removidos → `Florida USA`
3. Resultado incorreto passava porque a verificação já tinha sido feita

## Solução Implementada

### 1. Limpeza Final de Sufixos (linhas 916-922)

Adicionada remoção de `CNPJ`, `CPF`, `CEP` **após** toda a normalização:

```python
# Remove CNPJ/CPF/CEP que ficou no final após limpeza
name = re.sub(r"\s+CNPJ\s*$", "", name, flags=re.IGNORECASE)
name = re.sub(r"\s+CPF\s*$", "", name, flags=re.IGNORECASE)
name = re.sub(r"\s+CEP\s*$", "", name, flags=re.IGNORECASE)
```

Isso corrige casos como:
- `Rede Mulher de Televisao Ltda CNPJ: -8` → `Rede Mulher de Televisao Ltda`

### 2. Verificações Finais (linhas 928-961)

Adicionadas verificações **no final** da função, após toda limpeza:

```python
final_name = name.strip()

# Rejeita "Florida USA" após limpeza de números
if re.match(r"^Florida\s+USA\s*$", final_name, re.IGNORECASE):
    return ""

# Rejeita strings muito curtas (< 3 caracteres)
if len(final_name) < 3:
    return ""

# Rejeita siglas genéricas sozinhas
if re.match(r"^(MG|SP|RJ|PR|SC|RS|BA|GO|DF|ES|PE|CE|PA|MA|MT|MS|CNPJ|CPF|CEP|USA|BR)$",
            final_name.strip(), re.IGNORECASE):
    return ""

# Rejeita padrões de endereço americano
if re.match(r"^(Florida|California|Texas|New York)\s+(USA|US)?\s*$",
            final_name, re.IGNORECASE):
    return ""
```

## Resultados dos Testes

| Entrada                                    | Saída Esperada                      | Status |
| ------------------------------------------ | ----------------------------------- | ------ |
| `Florida USA`                              | `""`                                | ✅      |
| `Florida 33134 USA`                        | `""`                                | ✅      |
| `Florida33134USA`                          | `""`                                | ✅      |
| `Rede Mulher de Televisao Ltda CNPJ`       | `Rede Mulher de Televisao Ltda`     | ✅      |
| `Rede Mulher de Televisao Ltda CNPJ: -8`   | `Rede Mulher de Televisao Ltda`     | ✅      |
| `AGYONET LTDA`                             | `AGYONET LTDA`                      | ✅      |
| `TFCF LATIN AMERICAN CHANNEL LLC`          | `TFCF LATIN AMERICAN CHANNEL LLC`   | ✅      |
| `CNPJ`                                     | `""`                                | ✅      |
| `MG`                                       | `""`                                | ✅      |

## Arquivos Modificados

| Arquivo                         | Mudança                                                    |
| ------------------------------- | ---------------------------------------------------------- |
| `extractors/utils.py`           | Limpeza final de sufixos + verificações finais             |
| `tests/test_extractor_utils.py` | Testes adicionais para novos casos                         |

## Arquitetura Final de `normalize_entity_name()`

A função agora segue esta ordem:

1. **Verificação antecipada**: Rejeita formulários de entrega (`( ) Ausente`, etc.)
2. **Remoção de prefixos**: `E-mail`, `Beneficiário`, `CNPJ:`, etc.
3. **Remoção de sufixos**: `CONTATO`, `CNPJ`, `Florida USA`, etc.
4. **Validação de padrões inválidos**: Domínios, CEP, frases genéricas
5. **Limpeza de artefatos OCR**: Colchetes, caracteres duplicados
6. **Remoção de CNPJ/CPF embutidos**: Regex para formatos brasileiros
7. **Remoção de números**: Sequências numéricas longas, códigos
8. **Correção de caracteres problemáticos**: `□`, `■`, `�`
9. **🆕 Limpeza final de sufixos**: Remove `CNPJ`, `CPF`, `CEP` residuais
10. **🆕 Verificações finais**: Rejeita `Florida USA`, strings curtas, siglas

## Comandos de Verificação

```bash
# Testar normalização diretamente
python -c "
from extractors.utils import normalize_entity_name
print(normalize_entity_name('Florida 33134 USA'))  # ''
print(normalize_entity_name('Rede Mulher de Televisao Ltda CNPJ: -8'))  # 'Rede Mulher...'
"

# Rodar testes de normalização
python -m pytest tests/test_extractor_utils.py::TestNormalizeEntityName -v

# Verificar padrões problemáticos após reprocessamento
python -c "
import pandas as pd
df = pd.read_csv('data/output/relatorio_lotes.csv', sep=';')
for p in ['Florida USA', 'CNPJ\$', 'DOCUMENTO AUXILIAR']:
    mask = df['fornecedor'].fillna('').str.contains(p, case=False, regex=True)
    print(f'{p}: {mask.sum()}')
"
```

## Observações Importantes

1. **Fornecedor vazio é melhor que lixo**: Quando não conseguimos extrair um nome válido, retornar string vazia é o comportamento correto
2. **A normalização é aplicada em `to_summaries()`**: Os dados brutos extraídos podem conter lixo, mas o resumo final no CSV sempre passa pela normalização
3. **Casos de Disney/Fox**: O documento `Florida 33134 USA` é uma fatura internacional onde o extrator NFSe não consegue identificar o fornecedor correto (`TFCF Latin American Channel LLC`) - isso requer melhoria no extrator, não na normalização

## Testes - Total Atual

- **661 testes passando**
- **1 teste pulado** (requer arquivo específico)

---

_Criado: 2026-02-19_
_Relacionado: sessao_2026_02_19_pendencias.md, sessao_2026_02_18_nfcom_century_telecom.md_
