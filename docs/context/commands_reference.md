# Referência de Comandos - Unix vs PowerShell

> **Uso:** Guia rápido para converter comandos Unix (Linux/Mac) para PowerShell (Windows)  
> **Atualizado:** 2026-01-29

---

## 🔄 Tabela de Equivalência Rápida

### Busca e Filtro

| Unix                          | PowerShell                                                            | Descrição              | Exemplo                                                               |
| ----------------------------- | --------------------------------------------------------------------- | ---------------------- | --------------------------------------------------------------------- |
| `grep "termo" arquivo.txt`    | `Select-String "termo" arquivo.txt`                                   | Busca texto em arquivo | `Select-String "FISHTV" data/output/relatorio_lotes.csv`              |
| `grep -i "termo" arquivo.txt` | `Select-String "termo" arquivo.txt -CaseSensitive:$false`             | Busca case-insensitive | `Select-String "fishtv" arquivo.csv -CaseSensitive:$false`            |
| `grep -r "termo" pasta/`      | `Get-ChildItem -Re pasta/ \| Select-String "termo"`                   | Busca recursiva        | `Get-ChildItem -Re temp_email/ \| Select-String "TUNNA"`              |
| `grep -n "termo" arquivo.txt` | `Select-String "termo" arquivo.txt \| Select-Object LineNumber, Line` | Mostra número da linha | `Select-String "valor" arquivo.csv \| Select-Object LineNumber, Line` |

---

### Visualização de Arquivos

| Unix                     | PowerShell                                           | Descrição                | Exemplo                                              |
| ------------------------ | ---------------------------------------------------- | ------------------------ | ---------------------------------------------------- |
| `cat arquivo.txt`        | `Get-Content arquivo.txt`                            | Mostra conteúdo completo | `Get-Content data/output/relatorio_lotes.csv`        |
| `cat arquivo.txt`        | `type arquivo.txt`                                   | Alternativa curta        | `type arquivo.txt`                                   |
| `head -n 10 arquivo.txt` | `Get-Content arquivo.txt \| Select-Object -First 10` | Primeiras 10 linhas      | `Get-Content arquivo.csv \| Select-Object -First 10` |
| `tail -n 10 arquivo.txt` | `Get-Content arquivo.txt \| Select-Object -Last 10`  | Últimas 10 linhas        | `Get-Content arquivo.csv \| Select-Object -Last 10`  |
| `head -n 5 arquivo.txt`  | `Get-Content arquivo.txt -TotalCount 5`              | Alternativa direta       | `Get-Content arquivo.txt -TotalCount 5`              |
| `less arquivo.txt`       | `Get-Content arquivo.txt \| Out-Host -Paging`        | Paginação                | `Get-Content arquivo.txt \| Out-Host -Paging`        |
| `more arquivo.txt`       | `Get-Content arquivo.txt \| Out-Host -Paging`        | Paginação                | `Get-Content arquivo.txt \| Out-Host -Paging`        |

---

### Manipulação de Arquivos e Pastas

| Unix                    | PowerShell                            | Descrição                     | Exemplo                                    |
| ----------------------- | ------------------------------------- | ----------------------------- | ------------------------------------------ |
| `ls`                    | `Get-ChildItem` ou `dir` ou `gci`     | Lista arquivos                | `Get-ChildItem temp_email/`                |
| `ls -la`                | `Get-ChildItem`                       | Lista detalhada (já é padrão) | `Get-ChildItem`                            |
| `ls *.pdf`              | `Get-ChildItem *.pdf`                 | Lista com filtro              | `Get-ChildItem temp_email/*.pdf`           |
| `pwd`                   | `Get-Location` ou `pwd`               | Mostra diretório atual        | `Get-Location`                             |
| `cd pasta/`             | `cd pasta/` ou `Set-Location pasta/`  | Muda diretório                | `cd temp_email/`                           |
| `cp arquivo destino/`   | `Copy-Item arquivo destino/`          | Copia arquivo                 | `Copy-Item arquivo.txt backup/`            |
| `cp -r pasta/ destino/` | `Copy-Item pasta/ destino/ -Recurse`  | Copia recursivo               | `Copy-Item temp_email/ backup/ -Recurse`   |
| `mv arquivo destino/`   | `Move-Item arquivo destino/`          | Move arquivo                  | `Move-Item arquivo.txt pasta/`             |
| `rm arquivo.txt`        | `Remove-Item arquivo.txt`             | Remove arquivo                | `Remove-Item arquivo.txt`                  |
| `rm -r pasta/`          | `Remove-Item pasta/ -Recurse`         | Remove pasta                  | `Remove-Item temp_email/old/ -Recurse`     |
| `mkdir pasta/`          | `New-Item pasta/ -ItemType Directory` | Cria pasta                    | `New-Item nova_pasta/ -ItemType Directory` |
| `mkdir pasta/`          | `mkdir pasta/`                        | Alternativa curta             | `mkdir nova_pasta`                         |
| `touch arquivo.txt`     | `New-Item arquivo.txt -ItemType File` | Cria arquivo vazio            | `New-Item arquivo.txt -ItemType File`      |

---

### Contagem e Estatísticas

| Unix                          | PowerShell                                        | Descrição                  | Exemplo                                           |
| ----------------------------- | ------------------------------------------------- | -------------------------- | ------------------------------------------------- |
| `wc -l arquivo.txt`           | `(Get-Content arquivo.txt).Count`                 | Conta linhas               | `(Get-Content arquivo.csv).Count`                 |
| `wc -l arquivo.txt`           | `Get-Content arquivo.txt \| Measure-Object -Line` | Conta linhas (alternativa) | `Get-Content arquivo.csv \| Measure-Object -Line` |
| `wc -w arquivo.txt`           | `Get-Content arquivo.txt \| Measure-Object -Word` | Conta palavras             | `Get-Content arquivo.txt \| Measure-Object -Word` |
| `ls \| wc -l`                 | `(Get-ChildItem).Count`                           | Conta arquivos na pasta    | `(Get-ChildItem temp_email/).Count`               |
| `grep -c "termo" arquivo.txt` | `(Select-String "termo" arquivo.txt).Count`       | Conta ocorrências          | `(Select-String "CONFERIR" arquivo.csv).Count`    |

---

### Comparação e Diff

| Unix                             | PowerShell                                                             | Descrição         | Exemplo                                                  |
| -------------------------------- | ---------------------------------------------------------------------- | ----------------- | -------------------------------------------------------- |
| `diff arquivo1.txt arquivo2.txt` | `Compare-Object (Get-Content arquivo1.txt) (Get-Content arquivo2.txt)` | Compara arquivos  | `Compare-Object (Get-Content a.csv) (Get-Content b.csv)` |
| `diff -u arquivo1 arquivo2`      | `Compare-Object (gc arquivo1) (gc arquivo2) -PassThru`                 | Mostra diferenças | `Compare-Object (gc a.csv) (gc b.csv) -PassThru`         |

---

### Processamento de Texto

| Unix                                   | PowerShell                                                                      | Descrição          | Exemplo                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------- | ------------------ | ---------------------------------------------------------------- |
| `awk -F';' '{print $1}' arquivo.csv`   | `Get-Content arquivo.csv \| ForEach-Object { $_.Split(';')[0] }`                | Extrai coluna CSV  | `Get-Content arquivo.csv \| ForEach-Object { $_.Split(';')[0] }` |
| `cut -d';' -f1 arquivo.csv`            | `Get-Content arquivo.csv \| ForEach-Object { $_.Split(';')[0] }`                | Extrai coluna      | `Get-Content arquivo.csv \| ForEach-Object { $_.Split(';')[0] }` |
| `sort arquivo.txt`                     | `Get-Content arquivo.txt \| Sort-Object`                                        | Ordena linhas      | `Get-Content arquivo.txt \| Sort-Object`                         |
| `sort -r arquivo.txt`                  | `Get-Content arquivo.txt \| Sort-Object -Descending`                            | Ordena reversa     | `Get-Content arquivo.txt \| Sort-Object -Descending`             |
| `uniq arquivo.txt`                     | `Get-Content arquivo.txt \| Sort-Object -Unique`                                | Remove duplicatas  | `Get-Content arquivo.txt \| Sort-Object -Unique`                 |
| `sed 's/antigo/novo/g' arquivo.txt`    | `(Get-Content arquivo.txt) -replace 'antigo','novo'`                            | Substituição       | `(Get-Content arquivo.txt) -replace 'antigo','novo'`             |
| `sed -i 's/antigo/novo/g' arquivo.txt` | `(Get-Content arquivo.txt) -replace 'antigo','novo' \| Set-Content arquivo.txt` | Substitui in-place | `(gc arquivo.txt) -replace 'a','b' \| sc arquivo.txt`            |

---

## 📂 Comandos Específicos do Projeto

### Inspeção de PDFs

```powershell
# Unix (não funciona no Windows sem adaptação)
grep "termo" arquivo.pdf

# PowerShell - Inspecionar PDF específico
python scripts/inspect_pdf.py nome_arquivo.pdf

# PowerShell - Inspecionar batch completo
python scripts/inspect_pdf.py --batch email_20260129_084433_c5c04540

# PowerShell - Com texto bruto completo
python scripts/inspect_pdf.py nome_arquivo.pdf --raw
```

---

### Validação de Extração

```powershell
# Unix (não funciona no Windows)
find temp_email/ -name "*.pdf" -exec validate {} \;

# PowerShell - Validar batches específicos (RECOMENDADO)
python scripts/validate_extraction_rules.py --batch-mode --temp-email `
    --batches email_20260129_084433_c5c04540,email_20260129_084430_187f758c

# PowerShell - Validar todos os batches (mais lento)
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# PowerShell - Com correlação e validações completas
python scripts/validate_extraction_rules.py --batch-mode --temp-email `
    --validar-prazo --exigir-nf --apply-correlation
```

---

### Busca no CSV

```powershell
# Unix
grep "termo" data/output/relatorio_lotes.csv
awk -F';' '$6 ~ /FORNECEDOR/ {print}' arquivo.csv

# PowerShell - Busca simples
Select-String "termo" data/output/relatorio_lotes.csv

# PowerShell - Busca case-insensitive
Select-String "fishtv" data/output/relatorio_lotes.csv -CaseSensitive:$false

# PowerShell - Extrair coluna específica (fornecedor = coluna 6)
Get-Content data/output/relatorio_lotes.csv |
    ForEach-Object { $_.Split(';')[5] }  # índice 5 = 6ª coluna

# PowerShell - Busca e mostra linha completa formatada
Select-String "TUNNA" data/output/relatorio_lotes.csv |
    ForEach-Object { "Batch: $($_.Line.Split(';')[0])" }
```

---

### Análise de Logs

```powershell
# Unix
tail -f logs/scrapper.log
grep "ERROR" logs/scrapper.log | head -20

# PowerShell - Últimas linhas do log
Get-Content logs/scrapper.log -Tail 20

# PowerShell - Buscar erros
Select-String "ERROR" logs/scrapper.log | Select-Object -Last 20

# PowerShell - Análise completa
python scripts/analyze_logs.py --today
python scripts/analyze_logs.py --errors-only
python scripts/analyze_logs.py --batch email_20260129_084433_c5c04540
```

---

### Reprocessamento

```powershell
# Unix
for batch in temp_email/*/; do python run_ingestion.py --batch-folder "$batch"; done

# PowerShell - Reprocessar batch específico
python run_ingestion.py --batch-folder temp_email/email_20260129_084433_c5c04540

# PowerShell - Reprocessar todos (com backup primeiro)
Copy-Item data/output/relatorio_lotes.csv data/output/relatorio_lotes.csv.bak
python run_ingestion.py --reprocess
```

---

## 💡 Aliases Úteis

Adicione ao seu perfil do PowerShell (`$PROFILE`) para facilitar:

```powershell
# Aliases Unix-like para PowerShell
Set-Alias -Name grep -Value Select-String
Set-Alias -Name cat -Value Get-Content
Set-Alias -Name ls -Value Get-ChildItem
Set-Alias -Name pwd -Value Get-Location
Set-Alias -Name cd -Value Set-Location
Set-Alias -Name cp -Value Copy-Item
Set-Alias -Name mv -Value Move-Item
Set-Alias -Name rm -Value Remove-Item
Set-Alias -Name mkdir -Value New-Item
Set-Alias -Name touch -Value New-Item
Set-Alias -Name head -Value Select-First  # Não funciona diretamente, ver funções abaixo

# Funções helper
function grep-csv($termo, $arquivo = "data/output/relatorio_lotes.csv") {
    Select-String $termo $arquivo
}

function head($arquivo, $n = 10) {
    Get-Content $arquivo | Select-Object -First $n
}

function tail($arquivo, $n = 10) {
    Get-Content $arquivo | Select-Object -Last $n
}

function wc-l($arquivo) {
    (Get-Content $arquivo).Count
}

function list-batch($batchId) {
    Get-ChildItem "temp_email/$batchId/*.pdf"
}

function inspect-batch($batchId) {
    python scripts/inspect_pdf.py --batch $batchId
}

function grep-csv($termo) {
    Select-String $termo data/output/relatorio_lotes.csv
}
```

---

## ⚠️ Armadilhas Comuns

### 0. Para o Agente IA (Claude/Assistente)

**Problema com `list_directory` e `find_path`:**

```powershell
# ❌ ERRADO - Se você já está no diretório scrapper, não repita o nome
list_directory("scrapper/temp_email")  # Vai procurar scrapper/scrapper/temp_email

# ✅ CORRETO - Use apenas o caminho relativo ao diretório atual
list_directory("temp_email")
```

**Problema com PowerShell complexo via terminal:**

```powershell
# ❌ EVITE - Comandos PowerShell complexos dão erro frequente
powershell -Command "Get-ChildItem temp_email -Directory | Where-Object { ... }"

# ✅ PREFIRA - Use Python para listagens complexas
python -c "import os; dirs = [d for d in os.listdir('temp_email') if os.path.isdir(f'temp_email/{d}') and os.listdir(f'temp_email/{d}')]; print('\n'.join(dirs[:20]))"

# ✅ ALTERNATIVA - Comandos simples funcionam
dir temp_email
ls temp_email
```

**Listagem de pastas não-vazias (comando confiável):**

```powershell
# ✅ FUNCIONA - Listar batches com arquivos
python -c "
import os
batches = []
for d in os.listdir('temp_email'):
    path = f'temp_email/{d}'
    if os.path.isdir(path) and os.listdir(path):
        batches.append(d)
print(f'Batches com arquivos: {len(batches)}')
for b in batches[:20]:
    print(b)
"
```

---

### 1. Aspas e Escape

```powershell
# ❌ Errado - aspas simples não funcionam como no bash
grep 'termo' arquivo.txt

# ✅ Correto - aspas duplas
Select-String "termo" arquivo.txt
```

### 2. Pipe `|` vs `

```powershell
# No PowerShell, o pipe funciona igual
comando1 | comando2

# Mas em strings, use crase para escape
"Texto com `"aspas`""
```

### 3. Case Sensitivity

```powershell
# PowerShell é case-insensitive por padrão em comandos
# Mas Select-String é case-insensitive por padrão (diferente do grep)

# Para case-sensitive no Select-String:
Select-String "termo" arquivo.txt -CaseSensitive
```

### 4. Paths com Espaços

```powershell
# ❌ Pode falhar
cd Minha Pasta/

# ✅ Sempre use aspas
cd "Minha Pasta/"
```

---

## 🤖 Dicas para Sessões de IA (Claude/Assistentes)

### Paths Relativos vs Absolutos

1. **Ao usar ferramentas `list_directory`, `read_file`, `find_path`:**
    - O path deve começar com o nome do diretório raiz do projeto (ex: `scrapper/`)
    - MAS se o terminal já está dentro de `scrapper/`, não repita o nome

2. **Ao usar comandos no terminal:**
    - Use paths relativos ao diretório de trabalho atual (`cd` do terminal)
    - Verifique o `cd` do comando antes de montar o path

### Comandos Problemáticos (Evitar)

| Comando                                                    | Problema                   | Alternativa        |
| ---------------------------------------------------------- | -------------------------- | ------------------ |
| `powershell -Command "Get-ChildItem ... Where-Object { }"` | Erro de sintaxe frequente  | Usar Python        |
| `Get-ChildItem $_.FullName`                                | Expansão de variável falha | Usar loop Python   |
| `Select-String` com regex complexo                         | Escape problemático        | Usar Python + `re` |

### Comandos Confiáveis

```powershell
# Listar diretórios simples
dir temp_email

# Buscar em CSV
python -c "import pandas as pd; df = pd.read_csv('arquivo.csv', sep=';'); print(df.head())"

# Contar arquivos
python -c "import os; print(len(os.listdir('temp_email')))"

# Inspecionar batch
python scripts/inspect_pdf.py --batch BATCH_ID
```

---

## 📚 Referências Externas

- [Documentação Microsoft - PowerShell](https://docs.microsoft.com/powershell/)
- [PowerShell equivalents for Linux commands](https://mathieubuisson.github.io/powershell-linux-gnu/)
- [Unix to PowerShell Cheat Sheet](https://pureinfotech.com/powershell-equivalent-cmd-commands/)

---

_Atualizado: 2026-02-02 - Adicionadas dicas para agentes IA sobre comandos problemáticos_
