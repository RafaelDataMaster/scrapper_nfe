# Guia de Debug para Extração de PDFs e Lotes

Este guia apresenta o workflow e as ferramentas recomendadas para debugar problemas de extração, desde um único PDF até a lógica de correlação em lotes.

## Ferramentas Principais

O projeto agora conta com scripts dedicados que automatizam 90% do trabalho de debug. **Sempre comece por eles.**

### 1. `inspect_pdf.py`: O Canivete Suíço para PDFs Individuais

Esta é a **ferramenta de entrada** para qualquer problema de extração. Ela processa um único PDF e mostra um resumo completo dos dados extraídos, o tipo de documento detectado e o extrator utilizado.

**Recursos:**

- 🔍 **Busca automática**: Encontra o PDF em `failed_cases_pdf/` e `temp_email/` apenas pelo nome.
- 📊 **Campos por tipo**: Mostra apenas os campos relevantes para o documento (Boleto, DANFE, etc.).
- 📋 **Texto bruto**: Permite ver o texto exato que o sistema está lendo, crucial para criar regex.
- 🎯 **Filtro de campos**: Isola apenas os campos que você precisa analisar.

**Exemplos de Uso:**

```bash
# Busca automática e inspeção completa
python scripts/inspect_pdf.py exemplo.pdf

# Inspecionar campos específicos de um DANFE
python scripts/inspect_pdf.py danfe.pdf --fields fornecedor_nome valor_total vencimento

# Ver o texto bruto completo para criar uma regex
python scripts/inspect_pdf.py nota_complexa.pdf --raw
```

**Workflow:**

1.  **Identifique o PDF com problema.**
2.  Execute `python scripts/inspect_pdf.py nome_do_arquivo.pdf`.
3.  **Analise o output:**
    - O `[tipo]` detectado está correto? Se não, o problema está no método `can_handle()` do extrator.
    - O `[extrator]` selecionado é o correto?
    - Os campos extraídos estão corretos? Se não, o problema está no método `extract()` do extrator.
4.  Se precisar de mais detalhes, use a flag `--raw` para ver o texto completo.

### 2. `debug_batch.py`: O Diagnóstico para Lotes e Correlação

Use esta ferramenta quando a extração individual parece correta, mas o resultado final no CSV de lotes está errado (ex: status `DIVERGENTE`, `numero_nota` vazio).

Ela processa uma pasta de lote inteira e mostra:

- Detalhes de cada documento no lote.
- O resultado do pareamento de documentos (NF vs Boleto).
- A lógica de fallback para o `numero_nota`.
- Uma comparação entre o método de sumarização legado e o novo método de pareamento.

**Exemplos de Uso:**

```bash
# Analisar um lote específico
python scripts/debug_batch.py temp_email/email_20260105_125518_4e51c5e2
```

**Workflow:**

1.  **Identifique a pasta do lote com problema** (ex: `temp_email/email_...`).
2.  Execute `python scripts/debug_batch.py caminho_da_pasta`.
3.  **Analise o output:**
    - **Seção 3 (Detalhes dos Documentos):** Os campos de cada documento foram extraídos corretamente?
    - **Seção 5 (DocumentPairingService):** Os pares NF↔Boleto foram formados corretamente?
    - **Seção 7 (Análise de Fallbacks):** De onde veio o `numero_nota`? Foi do campo certo? O extrator pode estar falhando em extrair um campo prioritário.
    - **Seção 8 (Recomendações):** O script oferece avisos automáticos sobre problemas comuns.

## Técnicas Avançadas (Manuais)

Use estas técnicas quando os scripts automáticos não forem suficientes para identificar a causa raiz.

### 1. Extrair Texto Bruto com `repr()`

Visualize o texto exato que o `pdfplumber` está extraindo, incluindo caracteres invisíveis como `\n` (quebra de linha) e espaços múltiplos.

```python
import pdfplumber

with pdfplumber.open('caminho/do/arquivo.pdf') as pdf:
    page = pdf.pages[0]
    text = page.extract_text()
    print(repr(text))
```

Isso é fundamental para entender por que uma regex pode estar falhando (ex: um `\n` inesperado quebrando uma linha).

### 2. Testar Padrões Regex Iterativamente

Use um site como [regex101.com](https://regex101.com) (com o "flavor" Python) ou um script simples para testar suas expressões regulares de forma isolada.

```python
import re

text = "Nosso Número\n109/00000507-1"

# Padrão que falha com quebra de linha
pattern1 = r'Nosso Número.*?(\d+/\d+-\d+)'
match1 = re.search(pattern1, text)
print(f"Match 1: {match1}") # -> None

# Padrão correto com re.DOTALL para atravessar linhas
pattern2 = r'Nosso Número.*?(\d+/\d+-\d+)'
match2 = re.search(pattern2, text, re.DOTALL)
print(f"Match 2: {match2.group(1) if match2 else 'None'}") # -> 109/00000507-1
```

### 3. Validar Resultados com `pandas`

Após rodar o script `validate_extraction_rules.py`, use o `pandas` para analisar os CSVs de debug em `data/debug_output/`.

```python
import pandas as pd

df = pd.read_csv('data/debug_output/boletos_sucesso_debug.csv', sep=';')

# Ver campos vazios
print(df['nosso_numero'].isna().sum())

# Inspecionar uma linha específica
print(df[df['arquivo_origem'].str.contains('boleto_especifico')])
```

## Workflow de Debug Completo

1.  **Problema em um PDF?** Comece com `inspect_pdf.py`.
    - `python scripts/inspect_pdf.py nome_do_pdf.pdf`
    - Se os campos estiverem errados, use a flag `--raw` para copiar o texto e criar/ajustar a regex no extrator correspondente.

2.  **Problema no `relatorio_lotes.csv`?** Use `debug_batch.py`.
    - `python scripts/debug_batch.py temp_email/pasta_do_lote`
    - Verifique as seções de **Pareamento** e **Análise de Fallbacks** para entender a lógica.

3.  **Ainda não resolveu?** Use as técnicas avançadas.
    - Extraia o texto bruto com `repr()` para ver caracteres ocultos.
    - Teste a regex isoladamente no [regex101.com](https://regex101.com).
    - Faça uma alteração no extrator.
    - Rode `python scripts/validate_extraction_rules.py --batch-mode` para validar em lote.
    - Analise os CSVs de debug com `pandas`.

## Scripts de Diagnóstico Disponíveis

| Script                         | Descrição                                   | Quando Usar                                                                                          |
| ------------------------------ | ------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `inspect_pdf.py`               | Inspeção rápida de um PDF.                  | **Primeiro passo** para qualquer problema de extração em um arquivo.                                 |
| `debug_batch.py`               | Diagnóstico completo de um lote.            | Quando a extração individual parece OK, mas a correlação ou o resultado final do lote estão errados. |
| `validate_extraction_rules.py` | Valida todos os PDFs de teste.              | Após modificar um extrator, para garantir que não houve regressão.                                   |
| `analyze_all_batches.py`       | Analisa todos os lotes e reporta problemas. | Para ter uma visão geral da saúde de todos os lotes processados.                                     |
