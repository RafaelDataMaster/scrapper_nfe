# Guia de Troubleshooting

Este guia documenta erros comuns encontrados durante o uso do sistema de extração e suas soluções.

---

## 🔄 Problemas de Rastreamento entre Sessões

### 1. Batch IDs Não Encontrados

**Sintoma:**

```
Batch email_20260129_084433_c5c04540 não encontrado
```

**Causa:** Batch IDs são voláteis! Eles mudam a cada `clean_dev` + `run_ingestion`.

**Solução:**

1. NUNCA use batch IDs de sessões anteriores
2. Use identificadores estáveis:
    - ✅ Fornecedor: "TUNNA ENTRETENIMENTO"
    - ✅ CNPJ: "12.345.678/9012-34"
    - ✅ Tipo: "FATURA"
    - ✅ Número do documento: "000.010.731"
    - ❌ Batch ID: "email_20260129_084433_c5c04540"

3. Para reencontrar casos em nova sessão:

```powershell
# Busque no CSV pelo fornecedor
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA" | Select-Object -Last 5

# Ou valide extrator diretamente
python scripts/validate_extraction_rules.py --batch-mode --temp-email
```

---

## 🔤 Problemas de OCR

### 1. Caracteres Corrompidos pelo OCR

**Sintoma:** Caracteres especiais aparecem como `�` ou símbolos estranhos

**Exemplo:**

```
Esperado:  "Nº.: 000.010.731"
OCR gerou: "N�.: 000.010.731"
```

**Solução:**

```python
# ❌ Regex rígido (falha com OCR)
pattern = r"Nº\s*:\s*(\d+)"

# ✅ Regex tolerante (funciona com OCR)
pattern = r"N[^\w\s]?\s*[:\.]\s*(\d+)"  # Aceita qualquer coisa após N
```

**Dica:** Use `[^\w\s]?` para tolerar caracteres corrompidos.

### 2. Dígitos Trocados pelo OCR

**Sintoma:** Números trocados (8↔9, 1↔l, 0↔O, 5↔6)

**Solução:**

```python
# ❌ Verificação estrita
if re.search(r"\b\d{44}\b", text):

# ✅ Verificação tolerante
digits = re.sub(r"\D", "", text)
if len(digits) >= 40:  # Tolerância a até 4 erros
    # Possível chave DANFE
```

---

## 🔒 PDFs Protegidos por Senha

### 1. PDF da Sabesp (Senha = CPF do Titular)

**Sintoma:**

```
PDF 01_fatura.pdf: senha desconhecida (pypdfium2)
❌ [OCR] Não foi possível abrir PDF: 01_fatura.pdf
```

**Causa:** PDFs da Sabesp são protegidos com os 3 primeiros dígitos do CPF.

**Solução:** O sistema detecta emails da Sabesp e extrai dados do corpo do email HTML via `SabespWaterBillExtractor`.

### 2. Outros PDFs Protegidos

**Possíveis soluções:**

1. O sistema tenta CNPJs do cadastro como senha automaticamente
2. Dados podem estar no corpo do email (`EmailBodyExtractor`)
3. Criar extrator específico como o `SabespWaterBillExtractor`

---

## 📄 Problemas de Classificação

### 1. Tipo "FATURA" Não Reconhecido

**Sintoma:** Sistema classifica documento como erro

**Causa:** Sistema só aceita: `NFSE`, `BOLETO`, `DANFE`, `OUTRO`

**Solução:**

```python
# ❌ Não funciona
data = {"tipo_documento": "FATURA"}

# ✅ Correto
data = {
    "tipo_documento": "OUTRO",
    "subtipo": "FATURA",
}
```

### 2. Campo `numero_nota` vs `numero_documento`

**Solução por tipo:**

```python
# Para NFSE/DANFE: usar numero_nota
data["numero_nota"] = numero_extraido

# Para BOLETO/OUTRO: usar numero_documento
data["numero_documento"] = numero_extraido

# Para compatibilidade, preencher ambos
data["numero_documento"] = numero_extraido
data["numero_nota"] = numero_extraido
```

---

## 🏗️ Problemas de Registry

### 1. Extrator Não é Selecionado

**Sintoma:** Extrator existe mas outro é selecionado

**Causa:** Ordem no `extractors/__init__.py`

**Diagnóstico:**

```bash
python scripts/test_extractor_routing.py arquivo.pdf
```

**Solução:** Extratores específicos devem vir ANTES dos genéricos:

```python
# ✅ Correto
from .tunna_fatura import TunnaFaturaExtractor      # Específico
from .nfse_generic import NfseGenericExtractor      # Genérico

# ❌ Incorreto
from .nfse_generic import NfseGenericExtractor      # Pega tudo!
from .tunna_fatura import TunnaFaturaExtractor      # Nunca chega
```

---

## 💻 Comandos Windows (PowerShell)

### Comandos Unix que Falham

```powershell
# ❌ Falha no PowerShell
grep "termo" arquivo.txt
head -n 10 arquivo.txt

# ✅ Alternativas PowerShell
Select-String "termo" arquivo.txt
Get-Content arquivo.txt | Select-Object -First 10
```

**Tabela de equivalência:**

| Unix    | PowerShell                                    |
| ------- | --------------------------------------------- |
| `grep`  | `Select-String`                               |
| `head`  | `Select-Object -First N`                      |
| `tail`  | `Select-Object -Last N`                       |
| `wc -l` | `(Get-Content arquivo).Count`                 |
| `cat`   | `Get-Content`                                 |
| `diff`  | `Compare-Object (gc f1) (gc f2)`              |

---

## 📁 Problemas de Estrutura

### 1. Não Encontra PDF para Inspeção

**Sintoma:**

```
ERRO: Arquivo não encontrado: email_20260129_084433_c5c04540
```

**Solução:**

```bash
# ❌ Incorreto - apenas batch_id
python scripts/inspect_pdf.py email_20260129_084433_c5c04540

# ✅ Correto - caminho completo
python scripts/inspect_pdf.py temp_email/email_20260129_084433_c5c04540/01_arquivo.pdf

# ✅ Correto - apenas nome do arquivo (busca automática)
python scripts/inspect_pdf.py 01_DANFEFAT0000010731.pdf
```

### 2. Validação Usa Diretório Errado

**Sintoma:** Script processa `failed_cases_pdf/` mas queremos `temp_email/`

**Solução:**

```bash
# ✅ Modo batch com temp_email
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# ✅ Batches específicos (mais rápido)
python scripts/validate_extraction_rules.py --batch-mode --temp-email --batches batch1,batch2
```

---

## 🧪 Problemas de Validação

### 1. Validação Demora Muito

**Solução:** Use batches específicos:

```bash
# ❌ Lento - todos os batches
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# ✅ Rápido - apenas afetados
python scripts/validate_extraction_rules.py --batch-mode --temp-email --batches batch1,batch2
```

---

## 📊 Problemas de CSV

### 1. CSV Mostra Dados Antigos

**Causa:** CSV é append-only

**Solução:**

```bash
# Reprocessar tudo
python run_ingestion.py --reprocess

# Ou reprocessar batch específico
python run_ingestion.py --batch-folder temp_email/<batch_id>
```

---

## 🐛 Erros de Execução

### 1. ImportError ao Carregar Extrator

**Checklist:**

1. Extrator registrado em `extractors/__init__.py`
2. Nome da classe igual ao import
3. Adicionado ao `__all__`
4. Sem erros de sintaxe no arquivo

---

## 📝 Checklist de Debug

Quando algo não funciona, verifique:

- [ ] Caminho do arquivo está correto? (`temp_email/` vs `failed_cases_pdf/`)
- [ ] Comando é compatível com Windows? (PowerShell vs Unix)
- [ ] Extrator está registrado? (`__init__.py` e `__all__`)
- [ ] Ordem no registry está correta? (específico antes do genérico)
- [ ] Tipo do documento é válido? (`NFSE`/`BOLETO`/`DANFE`/`OUTRO`)
- [ ] Campos do modelo estão preenchidos? (`numero_nota` vs `numero_documento`)
- [ ] OCR pode estar corrompendo caracteres? (testar regex tolerante)

---

## 🔗 Referências Rápidas

| Problema          | Comando/Solução                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------- |
| Buscar no CSV     | `Select-String "termo" data/output/relatorio_lotes.csv`                                        |
| Listar batches    | `Get-ChildItem temp_email/`                                                                    |
| Inspecionar PDF   | `python scripts/inspect_pdf.py arquivo.pdf --raw`                                              |
| Validar regressão | `python scripts/validate_extraction_rules.py --batch-mode --temp-email --batches <lista>`      |
| Reprocessar batch | `python run_ingestion.py --batch-folder temp_email/<batch_id>`                                 |
| Ver logs          | `python scripts/analyze_logs.py --today`                                                       |

---

## Ver Também

- [Guia de Debug](../development/debugging_guide.md) - Workflows detalhados
- [Referência de Scripts](../debug/scripts_quick_reference.md) - Comandos essenciais
- [Como Estender](extending.md) - Criar novos extratores

---

**Última atualização:** 2026-02-02
