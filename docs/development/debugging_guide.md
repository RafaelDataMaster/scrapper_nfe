# Guia de Debug para Extração de PDFs

Este guia apresenta técnicas práticas para debugar e resolver problemas na extração de dados de boletos e outros PDFs.

## 1. Extrair o Texto Bruto do PDF

A primeira etapa é sempre visualizar o texto exato que o pdfplumber está extraindo:

```python
import pdfplumber

# Abrir e ver o texto exato
with pdfplumber.open('caminho/do/arquivo.pdf') as pdf:
    page = pdf.pages[0]
    text = page.extract_text()
    print(repr(text))  # repr() mostra \n, \t, espaços
```

**Por que usar `repr()`?** 

A função `repr()` mostra caracteres invisíveis como:
- Quebras de linha: `\n`
- Tabs: `\t`
- Espaços múltiplos: `'  '`

Isso é crucial para entender o layout real do documento.

## 2. Identificar Padrões de Layout

Diferentes PDFs têm diferentes estruturas. Identifique o tipo de layout:

### Layout Tabular
```python
# Exemplo: label e valor na mesma linha com outros dados
text = """
Nº Documento  Espécie  Moeda  Valor
08/11/2025    2/1      DM     R$ 4.789,00
"""
# Desafio: pode capturar data em vez do valor correto
```

### Layout Multi-linha
```python
# Exemplo: label em uma linha, valor em outra
text = """
Nosso Número
CARRIER TELECOM - CNPJ
109/00000507-1
"""
# Desafio: precisa de re.DOTALL para capturar através de \n
```

### Layout com Label como Imagem
```python
# Exemplo: label não está no texto OCR
text = """
[imagem do label]
109/42150105-8
2938/0053345-8
"""
# Desafio: precisa de fallback genérico sem depender do label
```

## 3. Testar Padrões Regex Iterativamente

Sempre teste padrões isoladamente antes de implementar:

```python
import re

text = """
Nosso Número
CARRIER TELECOM - CNPJ
109/00000507-1
230.159.230/0001-64
"""

# Teste 1: padrão simples (não funciona com multi-linha)
pattern1 = r'Nosso\s+Número.*?(\d+/\d+-\d+)'
match = re.search(pattern1, text)
print(match)  # None - não pegou!

# Teste 2: com re.DOTALL (. captura \n também)
pattern2 = r'Nosso\s+Número.*?(\d+/\d+-\d+)'
match = re.search(pattern2, text, re.DOTALL)
print(match.group(1) if match else None)  # Risco: pode pegar CNPJ!

# Teste 3: formato específico (3/8-1 digits)
pattern3 = r'\b(\d{3}/\d{8}-\d)\b'
match = re.search(pattern3, text)
print(match.group(1))  # 109/00000507-1 ✓
```

## 4. Diferenciar Formatos Similares

Quando há múltiplos números no mesmo formato, use características distintivas:

```python
# Formatos parecidos em boletos:
# - CNPJ: 12.345.678/0001-90 (tem pontos)
# - Agência/Conta: 1234/0012345-6 (4 dígitos antes da barra)
# - Nosso Número: 109/00000507-1 (2-3 dígitos antes da barra)

def is_nosso_numero(text):
    """Valida se é realmente um Nosso Número"""
    # Não tem pontos (exclui CNPJ)
    if '.' in text:
        return False
    
    # Formato banco: XX ou XXX / XXXXXXX+ - X
    match = re.match(r'\d{2,3}/\d{7,}-\d', text)
    return bool(match)

# Aplicar nos padrões:
pattern = r'(?i)Nosso\s+N.mero.*?(\d{2,3}/\d{7,}-\d+)'  # Específico
```

### Tabela de Diferenciação

| Campo | Formato | Dígitos antes da / | Características |
|-------|---------|-------------------|-----------------|
| CNPJ | XX.XXX.XXX/XXXX-XX | 8 (com pontos) | Sempre tem `.` |
| Agência/Conta | XXXX/XXXXXXX-X | 4 | Código de agência |
| Nosso Número | XXX/XXXXXXXX-X | 2-3 | Código bancário |

## 5. Script de Debug Rápido

Crie um arquivo `scripts/debug_pdf.py`:

```python
import pdfplumber
import re
from pathlib import Path

def debug_boleto(pdf_path, field_name):
    """Extrai e testa campo específico de um PDF"""
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()
        
    print(f"{'='*60}")
    print(f"PDF: {Path(pdf_path).name}")
    print(f"Campo: {field_name}")
    print(f"{'='*60}\n")
    
    # Mostra contexto do campo (50 chars antes e 100 depois)
    patterns = {
        'nosso_numero': r'Nosso.{0,20}Número',
        'numero_documento': r'N.{0,5}Documento',
        'vencimento': r'Vencimento',
        'valor': r'Valor.{0,10}Documento'
    }
    
    if field_name in patterns:
        match = re.search(patterns[field_name], text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 100)
            context = text[start:end]
            print(f"CONTEXTO:\n{repr(context)}\n")
    
    # Testa vários padrões
    test_patterns = [
        (r'\b(\d{3}/\d{8}-\d)\b', 'Nosso Número (3/8-1)'),
        (r'\b(\d{2,3}/\d{7,}-\d+)\b', 'Nosso Número (2-3/7+-1+)'),
        (r'(?i)Nosso.*?(\d+/\d+-\d+)', 'Nosso com label'),
        (r'\d{2}/\d{2}/\d{4}', 'Data DD/MM/YYYY'),
        (r'\d{4}\.\d+', 'Doc formato ano.número'),
    ]
    
    print("TESTES DE PADRÕES:")
    for pattern, desc in test_patterns:
        try:
            match = re.search(pattern, text, re.DOTALL)
            result = match.group(1 if '(' in pattern else 0) if match else "❌ Não encontrado"
            print(f"  {desc:30} → {result}")
        except Exception as e:
            print(f"  {desc:30} → Erro: {e}")
    
    print(f"\n{'='*60}\n")

# Uso:
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Uso: python debug_pdf.py <arquivo.pdf> [campo]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    field_name = sys.argv[2] if len(sys.argv) > 2 else 'nosso_numero'
    debug_boleto(pdf_path, field_name)
```

**Como usar:**

```bash
# Debug de campo específico
python scripts/debug_pdf.py failed_cases_pdf/37e40903.pdf nosso_numero

# Ver todos os padrões
python scripts/debug_pdf.py failed_cases_pdf/fe43b71e.pdf
```

## 6. Validar com CSV Real

Após fazer mudanças, valide os resultados no CSV:

```python
import pandas as pd

# Carregar resultados
df = pd.read_csv('data/debug_output/boletos_sucesso.csv', encoding='utf-8-sig')

# Ver linha específica
row = df[df['codigo_arquivo'] == '37e40903']
print(row[['numero_documento', 'nosso_numero', 'vencimento']])

# Ver todos os valores de um campo
print("\nDistribuição de valores:")
print(df['nosso_numero'].value_counts())

# Campos vazios
print(f"\nCampos vazios: {df['nosso_numero'].isna().sum()}")

# Ver múltiplas linhas
problematic = ['37e40903', 'fe43b71e', '0ea3c4be']
print("\nLinhas problemáticas:")
print(df[df['codigo_arquivo'].isin(problematic)][
    ['codigo_arquivo', 'numero_documento', 'nosso_numero', 'vencimento']
])
```

## 7. Técnicas que Economizam Tempo

### a) Encontrar TODOS os padrões de um formato

```python
# Achar TODOS os padrões XXX/XXXXXXXX-X no documento
all_matches = re.findall(r'\d{2,4}/\d{7,}-\d', text)
print(all_matches)  
# ['109/00000507-1', '2938/0053345-8', '230/0001-64']

# Isso ajuda a ver quais valores estão disponíveis e escolher o correto
```

### b) Usar `re.DOTALL` seletivamente

```python
# Aplicar DOTALL apenas no primeiro padrão (mais custoso)
patterns = [
    r'(?i)N.?\s*Documento.*?\d{2}/\d{2}/\d{4}\s+(\d+/\d+)',  # Multi-linha
    r'(?i)N.?\s*Documento[:\s]+(\d{4}\.\d+)',                # Mesma linha
    r'(\d{4}\.\d+)',                                         # Genérico
]

for i, pattern in enumerate(patterns):
    flags = re.DOTALL if i == 0 else 0  # Só o primeiro
    match = re.search(pattern, text, flags)
    if match:
        return match.group(1)
```

### c) Pular colunas intermediárias em layouts tabulares

```python
# Layout: "Nº Doc  Data       Valor"
#         "        08/11/2025 2/1"

# Padrão que pula a data DD/MM/YYYY:
pattern = r'N.?\s*Documento.*?\d{2}/\d{2}/\d{4}\s+(\d+/\d+)'
#                            └─ pula a data ─┘ └─ captura ─┘
```

### d) Testar encoding de caracteres especiais

```python
# Alguns PDFs têm variações de acentuação
patterns_with_encoding = [
    r'Número',   # UTF-8 correto
    r'N.mero',   # Qualquer char no lugar de ú
    r'Numero',   # Sem acento
]

# Use . ou \w para flexibilidade:
pattern = r'N[uú]mero'  # Aceita u ou ú
```

## 8. Workflow Completo de Debug

```bash
# 1. Identificar PDFs com problema
cd failed_cases_pdf/
ls *.pdf

# 2. Extrair texto bruto e verificar
python -c "
import pdfplumber
with pdfplumber.open('37e40903.pdf') as pdf:
    print(repr(pdf.pages[0].extract_text()[:500]))
"

# 3. Rodar script de debug personalizado
python scripts/debug_pdf.py 37e40903.pdf nosso_numero

# 4. Testar mudança no código
python scripts/test_boleto_extractor.py

# 5. Verificar resultado no CSV
python -c "
import pandas as pd
df = pd.read_csv('data/debug_output/boletos_sucesso.csv', encoding='utf-8-sig')
print(df[df['codigo_arquivo'] == '37e40903'][['numero_documento', 'nosso_numero']])
"

# 6. Validar com processador completo
python run_ingestion.py
```

## 9. Como Fazer Prompts Eficientes

Quando pedir ajuda (humana ou IA), sempre inclua:

### ✅ Prompt Eficiente

```
O boleto 37e40903 não está extraindo o nosso_numero corretamente.

Texto extraído (repr):
'Nosso Número\nCARRIER TELECOM - CNPJ\n109/00000507-1\n230.159.230/0001-64'

Padrão atual:
r'Nosso.*?(\d+/\d+-\d+)'

Resultado atual: captura '230/0001-64' (CNPJ) em vez de '109/00000507-1'

Formato esperado: 3 dígitos / 8 dígitos - 1 dígito

Outros números no documento:
- Agência/Conta: 2938/0053345-8 (4 dígitos)
- CNPJ: 230.159.230/0001-64 (com pontos)
```

### ❌ Prompt Ineficiente

```
O campo nosso_numero não está funcionando, pode consertar?
```

## 10. Casos Reais Resolvidos

### Caso 1: Layout Tabular (boleto 37e40903)

**Problema:** Capturava "08" (da data 08/11/2025) em vez de "2/1"

**Texto:**
```
Nº Documento  Espécie  Moeda  Valor
08/11/2025    2/1      DM     R$ 4.789,00
```

**Solução:**
```python
# Padrão que pula a data completa DD/MM/YYYY
pattern = r'(?i)N.?\s*Documento.*?\d{2}/\d{2}/\d{4}\s+(\d+/\d+)'
```

### Caso 2: Multi-linha com CNPJ (boleto 37e40903)

**Problema:** Capturava "230/0001-64" (fragmento do CNPJ) em vez de "109/00000507-1"

**Texto:**
```
Nosso Número
CARRIER TELECOM - CNPJ
109/00000507-1
230.159.230/0001-64
```

**Solução:**
```python
# Formato bancário específico: 2-3 dígitos / 7+ dígitos - dígito
pattern = r'(?i)Nosso\s+N.mero.*?(\d{2,3}/\d{7,}-\d+)'
# Validação: excluir matches com pontos (CNPJ tem pontos)
```

### Caso 3: Label como Imagem (boleto fe43b71e)

**Problema:** Label "Nosso Número" estava renderizado como imagem (OCR não pegou)

**Texto:**
```
[imagem]
109/42150105-8
2938/0053345-8
```

**Solução:**
```python
# Fallback genérico: formato preciso sem depender de label
pattern = r'\b(\d{3}/\d{8}-\d)\b'
# 3 dígitos (não 4 como Agência) / 8 dígitos - 1 dígito
```

## 11. Checklist de Debug

Antes de implementar uma correção, verifique:

- [ ] Extraí o texto com `repr()` para ver caracteres invisíveis?
- [ ] Testei o padrão regex isoladamente com `re.search()`?
- [ ] Verifiquei se há outros números similares que podem ser capturados?
- [ ] Considerei layouts multi-linha (precisa `re.DOTALL`)?
- [ ] Testei com múltiplos PDFs, não apenas um?
- [ ] Validei o resultado no CSV final?
- [ ] Documentei o caso no código ou na documentação?

## 12. Ferramentas Úteis

### Online Regex Tester
- [regex101.com](https://regex101.com) - Testa padrões com explicação visual
- Configure para Python flavor e use flag `DOTALL` quando necessário

### VS Code Extensions
- **Regex Preview** - Testa regex diretamente no editor
- **PDF Viewer** - Visualiza PDFs lado a lado com código

### Python One-liners Úteis

```bash
# Ver primeiras linhas de texto do PDF
python -c "import pdfplumber; print(pdfplumber.open('file.pdf').pages[0].extract_text()[:200])"

# Buscar padrão em PDF
python -c "import pdfplumber, re; text=pdfplumber.open('file.pdf').pages[0].extract_text(); print(re.findall(r'\d+/\d+-\d+', text))"

# Comparar dois PDFs
python -c "import pdfplumber; p1=pdfplumber.open('f1.pdf').pages[0].extract_text(); p2=pdfplumber.open('f2.pdf').pages[0].extract_text(); print('IGUAL' if p1==p2 else 'DIFERENTE')"
```

## Conclusão

Debug de PDFs é um processo iterativo. As chaves do sucesso são:

1. **Ver o texto real** com `repr()`
2. **Testar isoladamente** antes de implementar
3. **Diferenciar formatos** similares com precisão
4. **Validar resultados** no CSV final

Com prática, você desenvolverá intuição para identificar padrões rapidamente e criar regex robustos na primeira tentativa.
