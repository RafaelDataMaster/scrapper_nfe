# Troubleshooting Guide - Erros Comuns e Soluções

> **Uso:** Consulte este guia quando encontrar erros durante desenvolvimento ou orquestração  
> **Atualizado:** 2026-01-29 após primeira orquestração

---

## 🔄 Problemas de Rastreamento entre Sessões

### 1. Batch IDs Não Encontrados ("Batch não existe")

**Sintoma:** Você tenta usar um batch ID de uma sessão anterior e recebe erro:
```
Batch email_20260129_084433_c5c04540 não encontrado
```

**Causa:** Batch IDs são voláteis! Eles mudam a cada `clean_dev` + `run_ingestion`.

**Cenário típico:**
```
Sessão 1 (ontem):
  - Identifica erro no batch email_20260129_084433_c5c04540
  - Registra no snapshot

Usuário roda (hoje de manhã):
  $ python scripts/clean_dev.py      # Limpa tudo
  $ python run_ingestion.py          # Baixa emails novos

Sessão 2 (hoje):
  - Tenta usar batch email_20260129_084433_c5c04540
  - ❌ ERRO: Batch não existe mais!
```

**Solução:**

```markdown
1. NUNCA use batch IDs de sessões anteriores
2. Use identificadores estáveis:
   - ✅ Fornecedor: "TUNNA ENTRETENIMENTO"
   - ✅ CNPJ: "12.345.678/9012-34"
   - ✅ Tipo: "FATURA"
   - ✅ Número do documento: "000.010.731"
   - ❌ Batch ID: "email_20260129_084433_c5c04540"

3. Para reencontrar casos em nova sessão:
```

```powershell
# Busque no CSV pelo fornecedor (SEMPRE funciona)
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA" | Select-Object -Last 5

# Ou valide extrator diretamente
python scripts/validate_extraction_rules.py --batch-mode --temp-email
```

**Veja:** [`correction_tracking.md`](./correction_tracking.md) para estratégias completas.

---

## 🔤 Problemas de OCR (Optical Character Recognition)

### 1. Caracteres Corrompidos pelo OCR

**Sintoma:** Caracteres especiais aparecem como `�` ou símbolos estranhos

**Exemplo real:**
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

**Dica:** Use `[^\w\s]?` para tolerar caracteres corrompidos entre letras e símbolos.

---

### 2. Dígitos Trocados pelo OCR

**Sintoma:** Números trocados (8↔9, 1↔l, 0↔O, 5↔6)

**Contexto:** Em chaves de acesso DANFE (44 dígitos), OCR pode trocar dígitos

**Solução:**
```python
# ❌ Verificação estrita (pode falhar)
if re.search(r"\b\d{44}\b", text):
    
# ✅ Verificação tolerante (melhor para OCR)
digits = re.sub(r"\D", "", text)  # Remove não-dígitos
if len(digits) >= 40:  # Tolerância a até 4 erros
    # Possível chave DANFE
```

**Decisão arquitetural:** Se precisar identificar DANFE por chave de acesso, considere usar outros indicadores também (como fizemos movendo DanfeExtractor no registry).

---

## 📁 Problemas de Estrutura de Pastas

### 3. Não Encontra PDF para Inspeção

**Sintoma:**
```
ERRO: Arquivo não encontrado: email_20260129_084433_c5c04540
Buscado em:
  - failed_cases_pdf
  - temp_email
```

**Causa:** Passando apenas o batch_id sem o caminho completo

**Solução:**
```bash
# ❌ Incorreto
python scripts/inspect_pdf.py email_20260129_084433_c5c04540

# ✅ Correto - Caminho completo
python scripts/inspect_pdf.py temp_email/email_20260129_084433_c5c04540/01_arquivo.pdf

# ✅ Correto - Apenas nome do arquivo (busca automática)
python scripts/inspect_pdf.py 01_DANFEFAT0000010731.pdf

# ✅ Correto - Modo batch
python scripts/inspect_pdf.py --batch email_20260129_084433_c5c04540
```

**Estrutura correta:**
```
temp_email/
└── email_YYYYMMDD_HHMMSS_hash/
    ├── metadata.json
    └── 01_*.pdf
```

---

### 4. Validate Extraction Rules Falha (Diretório Errado)

**Sintoma:** Script processa `failed_cases_pdf/` mas queremos validar `temp_email/`

**Solução:**
```bash
# ❌ Modo legado (pasta antiga)
python scripts/validate_extraction_rules.py

# ✅ Modo batch com temp_email (RECOMENDADO)
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# ✅ Batches específicos (mais rápido)
python scripts/validate_extraction_rules.py --batch-mode --temp-email \
    --batches batch1,batch2,batch3
```

---

## 🔧 Problemas de Modelagem de Dados

### 5. Tipo "FATURA" Não Reconhecido

**Sintoma:** Extrator retorna `"tipo_documento": "FATURA"` mas sistema classifica como erro

**Causa:** Sistema só aceita tipos: `NFSE`, `BOLETO`, `DANFE`, `OUTRO`

**Solução:**
```python
# ❌ Não funciona
data: Dict[str, Any] = {"tipo_documento": "FATURA"}

# ✅ Correto - Usar OUTRO com subtipo
data: Dict[str, Any] = {
    "tipo_documento": "OUTRO",
    "subtipo": "FATURA",
    "descricao": "Fatura comercial"
}
```

**Referência de tipos válidos:**
| Tipo | Uso | Modelo |
|------|-----|--------|
| NFSE | Notas Fiscais de Serviço | InvoiceData |
| BOLETO | Boletos bancários | BoletoData |
| DANFE | Notas Fiscais de Produto | DanfeData |
| OUTRO | Documentos diversos | OtherDocumentData |

---

### 6. Campo `numero_nota` vs `numero_documento`

**Sintoma:** Número extraído não aparece no CSV

**Causa:** Sistema espera campo específico por tipo

**Solução por tipo:**
```python
# Para NFSE: usar numero_nota
data["numero_nota"] = numero_extraido

# Para BOLETO: usar numero_documento ou nosso_numero
data["numero_documento"] = numero_extraido

# Para DANFE: usar numero_nota
data["numero_nota"] = numero_extraido

# Para OUTRO: usar numero_documento
data["numero_documento"] = numero_extraido

# 💡 Dica: Para compatibilidade máxima, preencher ambos
if numero_extraido:
    data["numero_documento"] = numero_extraido
    data["numero_nota"] = numero_extraido  # Fallback
```

---

## 🏗️ Problemas de Arquitetura/Registry

### 7. Extrator Não é Selecionado (Prioridade Errada)

**Sintoma:** Extrator existe, `can_handle` retorna True, mas outro extrator é selecionado

**Causa:** Ordem no `extractors/__init__.py` - extratores são testados em ordem

**Diagnóstico:**
```bash
python scripts/inspect_pdf.py <arquivo.pdf>
# Verificar saída "TESTE DE EXTRATORES" para ver ordem
```

**Solução:**
```python
# Em extractors/__init__.py
# Extratores específicos DEVEM vir antes dos genéricos

# ✅ Correto - Específico antes
from .tunna_fatura import TunnaFaturaExtractor      # 10
from .admin_document import AdminDocumentExtractor  # 11
from .danfe import DanfeExtractor                   # 12
from .outros import OutrosExtractor                 # 13
from .nfse_generic import NfseGenericExtractor      # 14

# ❌ Incorreto - Genérico primeiro
from .nfse_generic import NfseGenericExtractor      # Pega tudo!
from .tunna_fatura import TunnaFaturaExtractor      # Nunca chega aqui
```

**Regra:** Extratores específicos (CNPJ único, padrão único) → Extratores por tipo → Genéricos

---

### 8. Diagnóstico Incorreto do Tipo de Documento

**Sintoma:** Tratando documento como tipo errado (ex: DANFE quando é FATURA)

**Exemplo real:**
```
Nome arquivo: 01_DANFEFAT0000010731.pdf  ← Contém "DANFE"
Assunto: Nota Fiscal FAT/10731           ← Contém "Nota Fiscal"
Conteúdo: Demonstrativo/Fatura comercial ← É uma fatura!
```

**Checklist de inspeção obrigatória:**
```bash
# 1. Verificar nome do arquivo
ls temp_email/<batch_id>/

# 2. Verificar conteúdo do PDF
python scripts/inspect_pdf.py <arquivo.pdf> --raw

# 3. Identificar tipo REAL:
# - DANFE fiscal: Tem chave de acesso (44 dígitos), valor dos produtos
# - Fatura: Tem número FAT/XXXX, demonstrativo, valor de serviços
# - NFSe: Tem código de verificação, prefeitura
```

**Decisão:**
| Características | Tipo Provável |
|-----------------|---------------|
| Chave 44 dígitos + Valor Produtos | DANFE |
| Código verificação + Prefeitura | NFSe |
| Linha digitável + Vencimento | BOLETO |
| FAT/XXX + Demonstrativo | OUTRO (Fatura) |

---

## 💻 Problemas de Comandos (Windows)

### 9. Comandos Unix Falham no PowerShell

**Erros comuns:**
```powershell
# ❌ Falha
grep "termo" arquivo.txt
head -n 10 arquivo.txt
ls -la
diff arquivo1 arquivo2
wc -l arquivo.txt
```

**Soluções PowerShell:**
```powershell
# ✅ Alternativas
# grep → Select-String (ou sls)
Select-String "termo" arquivo.txt

# head → Select-Object -First
Get-Content arquivo.txt | Select-Object -First 10

# ls → Get-ChildItem (ou dir, gci)
Get-ChildItem

# diff → Compare-Object
Compare-Object (Get-Content arquivo1) (Get-Content arquivo2)

# wc -l → Measure-Object
(Get-Content arquivo.txt).Count
# ou
Get-Content arquivo.txt | Measure-Object -Line

# cat → Get-Content (ou gc)
Get-Content arquivo.txt

# cp → Copy-Item
Copy-Item origem destino
```

**Referência completa:** Ver `commands_reference.md`

---

## 🧪 Problemas de Validação

### 10. Validação de Regressão Demora Muito

**Sintoma:** `validate_extraction_rules.py --batch-mode` processa todos os batches (centenas)

**Solução:** Use batches específicos
```bash
# ❌ Lento - todos os batches
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# ✅ Rápido - apenas afetados
python scripts/validate_extraction_rules.py --batch-mode --temp-email \
    --batches batch_afetado_1,batch_afetado_2,batch_similar_1
```

**Estratégia de seleção:**
- Sempre incluir batches que foram modificados
- Incluir 1-2 batches de cada tipo (NFSe, Boleto, DANFE, OUTRO)
- Priorizar batches de fornecedores similares

---

## 📊 Problemas de CSV/Saída

### 11. CSV Mostra Dados Antigos Após Reprocessamento

**Sintoma:** Reprocessou batch mas CSV não atualizou

**Causa:** CSV é append-only, não sobrescreve automaticamente

**Solução:**
```bash
# Backup antes de reprocessar
cp data/output/relatorio_lotes.csv data/output/relatorio_lotes.csv.bak

# Reprocessar TUDO (limpa e recria)
python run_ingestion.py --reprocess

# Ou reprocessar batch específico
python run_ingestion.py --batch-folder temp_email/<batch_id>

# Verificar
Select-String "<batch_id>" data/output/relatorio_lotes.csv
```

---

## 🐛 Erros de Execução

### 12. ImportError ao Carregar Extrator

**Sintoma:**
```
ImportError: cannot import name 'TunnaFaturaExtractor' from 'extractors'
```

**Causas:**
1. Extrator não registrado em `extractors/__init__.py`
2. Erro de sintaxe no arquivo do extrator
3. Nome da classe diferente do import

**Checklist:**
```python
# 1. Verificar nome do arquivo
# extractors/tunna_fatura.py

# 2. Verificar nome da classe
class TunnaFaturaExtractor(BaseExtractor):

# 3. Verificar registro em __init__.py
from .tunna_fatura import TunnaFaturaExtractor

# 4. Verificar __all__
__all__ = [
    ...,
    "TunnaFaturaExtractor",
]
```

---

## 📝 Checklist de Debug

Quando algo não funciona, verifique:

- [ ] **Caminho do arquivo está correto?** (temp_email/ vs failed_cases_pdf/)
- [ ] **Comando é compatível com Windows?** (PowerShell vs Unix)
- [ ] **Extrator está registrado?** (__init__.py e __all__)
- [ ] **Ordem no registry está correta?** (específico antes do genérico)
- [ ] **Tipo do documento é válido?** (NFSE/BOLETO/DANFE/OUTRO)
- [ ] **Campos do modelo estão preenchidos?** (numero_nota vs numero_documento)
- [ ] **OCR pode estar corrompendo caracteres?** (testar regex tolerante)
- [ ] **Documento é realmente do tipo esperado?** (inspecionar conteúdo)

---

## 🔗 Referências Rápidas

| Problema | Comando/Solução |
|----------|-----------------|
| Buscar no CSV | `Select-String "termo" data/output/relatorio_lotes.csv` |
| Listar batches | `Get-ChildItem temp_email/` |
| Inspecionar PDF | `python scripts/inspect_pdf.py --batch <batch_id>` |
| Validar regressão | `python scripts/validate_extraction_rules.py --batch-mode --temp-email --batches <lista>` |
| Reprocessar batch | `python run_ingestion.py --batch-folder temp_email/<batch_id>` |
| Ver logs | `python scripts/analyze_logs.py --today` |

---

*Última atualização: 2026-01-29 - Após Orquestração #1 (TunnaFaturaExtractor)*
