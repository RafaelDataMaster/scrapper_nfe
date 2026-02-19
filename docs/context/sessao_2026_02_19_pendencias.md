# Sessão 2026-02-19: Pendências para Correção

## Resumo

Após reprocessamento em 18/02/2026, foram identificados problemas remanescentes que não foram corrigidos pelas regras implementadas.

**Atualização 19/02/2026 (Final):** Todas as correções principais implementadas, incluindo normalização final para padrões que só aparecem após limpeza de números.

## Status do Relatório

### Antes das Correções (18/02)

| Status          | Quantidade |
| --------------- | ---------- |
| CONFERIR        | 1.281      |
| CONCILIADO      | 145        |
| PAREADO_FORCADO | 16         |
| DIVERGENTE      | 6          |

### Após Extração Clean (19/02)

| Status          | Quantidade |
| --------------- | ---------- |
| CONFERIR        | 1.327      |
| CONCILIADO      | 146        |
| PAREADO_FORCADO | 17         |
| DIVERGENTE      | 7          |
| **TOTAL**       | 1.497      |

## ✅ Correções Implementadas (19/02/2026)

### 1. NFCom - Cabeçalho capturado como fornecedor (23 casos) ✅ CORRIGIDO

**Problema:** O extrator `nfcom.py` estava capturando o cabeçalho "DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA" como nome do fornecedor.

**Solução implementada:**

- Nova estratégia de extração em `_extract_fornecedor_nome()`: busca o nome na segunda linha após o cabeçalho
- Novo método `_is_valid_supplier_name()` para validar se uma linha parece nome de empresa
- Rejeita cabeçalhos, endereços e CNPJs

**Arquivos modificados:**

- `extractors/nfcom.py`

**Testes adicionados:**

- `tests/test_nfcom_extractor.py` (17 testes)

---

### 2. Boletos Reclame Aqui - "( ) Ausente" (8 casos) ✅ CORRIGIDO

**Problema:** Boletos com "Comprovante de Entrega" tinham o padrão `( ) Ausente` sendo capturado como fornecedor.

**Solução implementada:**

- Adicionados padrões de formulário de entrega à blacklist em `_looks_like_header_or_label()`
- Verificação antecipada em `normalize_entity_name()` para rejeitar completamente esses padrões

**Padrões rejeitados:**

- `( ) Ausente`
- `( ) Mudou-se`
- `( ) Recusado`
- `( ) Desconhecido`
- `( ) Falecido`
- `( ) Não existe`
- `( ) Não procurado`
- `( ) Endereço insuficiente`
- `( ) Outros`

**Arquivos modificados:**

- `extractors/boleto.py`
- `extractors/utils.py`

---

### 3. Sufixo "CNPJ" não removido (4 casos) ✅ CORRIGIDO

**Problema:** `Rede Mulher de Televisao Ltda CNPJ` - o sufixo "CNPJ" não estava sendo removido.

**Solução implementada:**

- Adicionado regex `r"\bCNPJ\s*$"` em `suffixes_to_remove`
- **NOVO:** Limpeza final após toda normalização para remover `CNPJ`, `CPF`, `CEP` que ficaram no final após remoção de números/pontuação (ex: `Empresa CNPJ: -8` → `Empresa CNPJ` → `Empresa`)

**Arquivos modificados:**

- `extractors/utils.py` (linhas 916-922)

---

### 4. "CNPJ" / "cnpj" sozinho como fornecedor (5 casos) ✅ CORRIGIDO

**Problema:** A regra de rejeição de "CNPJ" sozinho não funcionava para todos os casos (incluindo minúsculo).

**Solução implementada:**

- Regex case-insensitive em `_looks_like_header_or_label()`
- Verificação explícita em `normalize_entity_name()` para rejeitar "CNPJ", "cnpj", "CPF", etc.
- **NOVO:** Verificação final (após toda limpeza) para siglas genéricas sozinhas

**Arquivos modificados:**

- `extractors/boleto.py`
- `extractors/utils.py`

---

### 5. "Florida USA" e "Florida 33134 USA" (2 casos) ✅ CORRIGIDO

**Problema:**

- `Florida USA` (sem números) não era rejeitado
- `Florida 33134 USA` após remoção de números virava `Florida USA` mas já tinha passado pela verificação

**Solução implementada:**

- Adicionado padrão `r"^Florida\s+USA\s*$"` em `suffixes_to_remove`
- **NOVO:** Verificações finais após toda a normalização (linhas 928-961):
    - Rejeita `Florida USA` após limpeza de números
    - Rejeita strings muito curtas (< 3 caracteres)
    - Rejeita siglas genéricas sozinhas (MG, SP, RJ, USA, CNPJ, CPF, etc.)
    - Rejeita padrões de endereço americano (`California USA`, `Texas US`, etc.)

**Arquivos modificados:**

- `extractors/utils.py`

**Testes adicionados:**

- `test_rejeita_florida_usa`: inclui caso `Florida 33134 USA`
- `test_remove_sufixo_cnpj`: inclui caso `Rede Mulher de Televisao Ltda CNPJ: -8`

---

## ⚠️ Problemas Remanescentes (Baixa Prioridade)

### 6. Lixo OCR "ÇÃO" (1 caso)

**Problema:** Fragmento de palavra capturado como fornecedor.

**Solução sugerida:** Já implementada parcialmente (verificação de strings < 3 caracteres). Pode precisar aumentar para 4.

**Status:** Pendente - baixa prioridade (apenas 1 caso)

---

### 7. Frase capturada como fornecedor (1 caso)

**Problema:** `que o valor da prestação de serviços de monitoramento do sistema de alarme` capturado como fornecedor.

**Solução sugerida:** Adicionar à blacklist ou rejeitar frases que começam com "que o" ou "que a".

**Status:** Pendente - baixa prioridade (apenas 1 caso)

---

### 8. Fornecedores vazios (92 casos)

**Observação:** Muitos são legítimos (ex: boletos sem beneficiário identificável, emails sem anexo, documentos não suportados). Com as correções, alguns casos (ex: Florida USA) agora retornam vazio em vez de lixo - isso é o comportamento correto.

**Status:** Pendente - requer análise caso a caso

---

## Resumo dos Testes

| Fase                        | Testes |
| --------------------------- | ------ |
| Antes das correções (18/02) | 639    |
| Após NFCom fixes            | 656    |
| Após normalize fixes        | 661    |
| **Total atual**             | 661    |

**Testes adicionados:**

- 17 testes em `tests/test_nfcom_extractor.py`
- 7 testes em `tests/test_extractor_utils.py` (classe `TestNormalizeEntityName`)

---

## Arquitetura da Solução de Normalização

A função `normalize_entity_name()` em `extractors/utils.py` agora segue esta ordem:

1. **Verificação antecipada**: Rejeita formulários de entrega (`( ) Ausente`, etc.)
2. **Remoção de prefixos**: `E-mail`, `Beneficiário`, `CNPJ:`, etc.
3. **Remoção de sufixos**: `CONTATO`, `CNPJ`, `Florida USA`, etc.
4. **Validação de padrões inválidos**: Domínios, CEP, frases genéricas
5. **Limpeza de artefatos OCR**: Colchetes, caracteres duplicados
6. **Remoção de CNPJ/CPF embutidos**: Regex para formatos brasileiros
7. **Remoção de números**: Sequências numéricas longas, códigos
8. **Correção de caracteres problemáticos**: `□`, `■`, `�`
9. **🆕 Limpeza final de sufixos**: Remove `CNPJ`, `CPF`, `CEP` que sobraram
10. **🆕 Verificações finais**: Rejeita `Florida USA`, strings curtas, siglas

---

## Próximos Passos

1. ✅ **Reprocessar o dataset** com as correções implementadas
2. **Verificar métricas** após reprocessamento:
    - Espera-se: `Florida USA` → fornecedor vazio (2 casos)
    - Espera-se: `Rede Mulher... CNPJ` → `Rede Mulher de Televisao Ltda` (4 casos)
3. **Avaliar casos remanescentes** de baixa prioridade

---

## Comandos Úteis

```bash
# Rodar testes
python -m pytest tests/ -q

# Rodar testes de normalização específicos
python -m pytest tests/test_extractor_utils.py::TestNormalizeEntityName -v

# Reprocessar
python run_ingestion.py --reprocess

# Ver distribuição de status
python -c "import pandas as pd; df=pd.read_csv('data/output/relatorio_lotes.csv', sep=';'); print(df['status_conciliacao'].value_counts())"

# Verificar padrões problemáticos no fornecedor
python -c "
import pandas as pd
df = pd.read_csv('data/output/relatorio_lotes.csv', sep=';')
problemas = ['DOCUMENTO AUXILIAR', '( ) Ausente', 'Florida USA', 'CNPJ$']
for p in problemas:
    mask = df['fornecedor'].fillna('').str.contains(p, case=False, regex=True)
    print(f'{p}: {mask.sum()} ocorrências')
"

# Testar normalização diretamente
python -c "
from extractors.utils import normalize_entity_name
print(normalize_entity_name('Florida 33134 USA'))  # Deve retornar ''
print(normalize_entity_name('Rede Mulher de Televisao Ltda CNPJ: -8'))  # Deve retornar 'Rede Mulher de Televisao Ltda'
"
```

---

## Arquivos Modificados

| Arquivo                         | Mudanças                                                      |
| ------------------------------- | ------------------------------------------------------------- |
| `extractors/nfcom.py`           | Nova estratégia de extração de fornecedor                     |
| `extractors/boleto.py`          | Blacklist expandida com padrões de formulário de entrega      |
| `extractors/utils.py`           | Limpeza final + verificações finais após toda normalização    |
| `tests/test_nfcom_extractor.py` | **Novo** - 17 testes para NFCom                               |
| `tests/test_extractor_utils.py` | 7 testes para `normalize_entity_name` (incluindo novos casos) |

---

## Detalhes Técnicos da Correção Final

### Problema: Ordem de Operações

O texto `Florida 33134 USA` passava pela verificação `^Florida\s+USA$` **antes** da remoção de números. Após remover `33134`, sobrava `Florida USA`, mas a verificação já tinha passado.

### Solução: Verificações Finais

```python
# extractors/utils.py - linhas 916-961

# LIMPEZA FINAL DE SUFIXOS (após toda normalização)
name = re.sub(r"\s+CNPJ\s*$", "", name, flags=re.IGNORECASE)
name = re.sub(r"\s+CPF\s*$", "", name, flags=re.IGNORECASE)
name = re.sub(r"\s+CEP\s*$", "", name, flags=re.IGNORECASE)

# VERIFICAÇÕES FINAIS (após toda a limpeza)
final_name = name.strip()

# Rejeita "Florida USA" após limpeza de números
if re.match(r"^Florida\s+USA\s*$", final_name, re.IGNORECASE):
    return ""

# Rejeita strings muito curtas
if len(final_name) < 3:
    return ""

# Rejeita siglas genéricas sozinhas
if re.match(r"^(MG|SP|RJ|...|CNPJ|CPF|CEP|USA|BR)$", final_name, re.IGNORECASE):
    return ""
```

---

_Última atualização: 2026-02-19 17:15_
