# Análise de Erros Restantes - 04/02/2026

> **Data:** 04/02/2026  
> **Contexto:** Após correções de fornecedores NFCom, restam 5 erros MÉDIA e 7 erros BAIXA  
> **Status:** Análise completa - plano de ação definido para próxima sessão

---

## Resumo Executivo

| Severidade | Quantidade | Valor Total | Análise |
|------------|------------|-------------|---------|
| CRÍTICA | 0 | - | ✅ |
| ALTA | 0 | - | ✅ |
| MÉDIA | 5 | R$ 3.049,79 | 2 problemas reais, 3 falsos positivos |
| BAIXA | 7 | R$ 25.759,22 | Comportamento esperado |

---

## Severidade MÉDIA (5 casos)

### 1. UTILITY_SEM_VENCIMENTO - PP EMPREENDIMENTOS LTDA (2 casos)

**Batch:** `email_20260204_115549_d58f01b9`  
**Valor reportado:** R$ 2,00 e R$ 9,00  
**Valor REAL:** R$ 22.396,17 e R$ 27.774,83  

**Problema REAL:** OCR com espaço no meio do número

O pdfplumber extrai o texto com espaço no número:
```
Esperado:  "R$ 22.396,17"
Extraído:  "R$ 2 2.396,17"
```

O regex atual captura apenas "R$ 2" como valor.

**Arquivos afetados:**
- `01_CARRIER 2.pdf` - Fatura de Locação PP EMPREENDIMENTOS (R$ 22.396,17)
- `02_CARRIER TELECOM SA - FATURA 192.pdf` - Boleto SICOOB (R$ 27.774,83)

**Causa raiz:** Regex de extração de valores não trata espaços dentro do número.

**Solução proposta:**
```python
# Em extractors/utils.py ou extractors/outros.py
# Antes de parsear valor, remover espaços internos:
valor_str = re.sub(r'(\d)\s+(\d)', r'\1\2', valor_str)
# "2 2.396,17" -> "22.396,17"
```

**Prioridade:** 🔴 ALTA - Afeta ~R$ 50K em valores

---

### 2. UTILITY_SEM_VENCIMENTO - JOYCE CRISTIANE DURAES MIRANDA (2 casos)

**Batches:** 
- `email_20260204_115550_b88513b0`
- `email_20260204_115552_63a17b09`

**Valor:** R$ 936,24 e R$ 902,55  
**Subject:** "RES: Consumo de energia POP MTC MCL"

**Análise:** ⚠️ FALSO POSITIVO

Os PDFs são **comprovantes de pagamento TED** (Banco Itaú), não faturas:
```
Banco Itaú - Comprovante de Pagamento
TED C – outra titularidade
Nome do favorecido: JOYCE CRISTIANE DURAES MIRANDA
Valor da TED: R$ 936,24
Finalidade: Pagamento a fornecedores
```

**Por que não tem vencimento:** Comprovantes de pagamento são registros de pagamentos JÁ REALIZADOS, não têm vencimento.

**Classificação atual:** UTILITY_ENERGY (incorreto)  
**Classificação correta:** COMPROVANTE_PAGAMENTO

**Solução proposta:**
- Melhorar detecção de comprovantes bancários (já existe `ComprovanteBancarioExtractor`)
- Verificar se está sendo chamado antes do `UtilityBillExtractor`
- Adicionar padrão "Comprovante de Pagamento" + "TED" na prioridade

**Prioridade:** 🟡 MÉDIA - Afeta classificação mas dados estão corretos

---

### 3. VENCIMENTO_AUSENTE - MERCES CLIMATIZACAO LTDA (1 caso)

**Batch:** `email_20260204_115546_abf2595c`  
**Arquivo:** `01_MERCES (1.200,00).pdf`  
**Valor:** R$ 1.200,00 (extraído do nome do arquivo!)  
**Subject:** "Re: RES: RES: RES: INFORMAÇÃO PAGAMENTO PEDIDO 016731"

**Análise:** ⚠️ LIMITAÇÃO TÉCNICA

O PDF é uma **imagem escaneada**:
```
Páginas: 1
Texto extraído: 0 caracteres
Imagens: 4
```

**Por que não extrai:** O sistema não tem OCR (Tesseract) ativo para converter imagens em texto.

**Solução proposta:**
1. **Curto prazo:** Aceitar como limitação conhecida
2. **Médio prazo:** Ativar OCR via Tesseract para PDFs sem texto
3. **Alternativa:** Extrair valor do nome do arquivo quando PDF falha

**Prioridade:** 🟢 BAIXA - Caso isolado, valor baixo

---

## Severidade BAIXA (7 casos)

### EMAIL_BODY_SEM_VENCIMENTO

**Fornecedores afetados:**
| Fornecedor | Valor | Causa |
|------------|-------|-------|
| NIPCABLE DO BRASIL TELECOM | R$ 6.000,00 | Email só redireciona para portal |
| GWG TELCO TELECOMUNICACOES | R$ 800,00 | Email só redireciona para portal |
| TIM S.A. | R$ 273,74 | PDF protegido por senha |
| + 4 casos similares | ... | ... |

**Análise:** ✅ COMPORTAMENTO ESPERADO

Esses casos têm uma das seguintes situações:
1. **Email redireciona para portal** - O email não contém os dados, apenas link para acessar portal do cliente
2. **PDF protegido por senha** - Não conseguimos extrair, usamos fallback para email body que não tem vencimento

**Exemplo - NIPCABLE:**
```
A NIPBR informa que sua fatura está disponível e já pode acessá-la 
em nosso portal do cliente clicando no link abaixo.
https://portal.nipbr.com.br/auth/login
```

**Exemplo - TIM:**
```
Erro ao abrir PDF: PdfiumError: Failed to load document 
(PDFium: Incorrect password error).
```

**Ação:** Nenhuma ação necessária - é limitação do formato de envio do fornecedor.

---

## Plano de Ação para Próxima Sessão

### Prioridade 1: Corrigir extração de valores com espaços (PP EMPREENDIMENTOS)

**Arquivos a modificar:** `extractors/utils.py` ou `extractors/outros.py`

**Implementação:**
```python
def normalize_money_string(valor_str: str) -> str:
    """Remove espaços internos em valores monetários.
    
    Trata casos de OCR corrompido onde espaços são inseridos:
    "R$ 2 2.396,17" -> "R$ 22.396,17"
    "1 234,56" -> "1234,56"
    """
    # Remove espaços entre dígitos
    return re.sub(r'(\d)\s+(\d)', r'\1\2', valor_str)
```

**Teste:**
```python
def test_normalize_money_with_spaces():
    assert normalize_money_string("R$ 2 2.396,17") == "R$ 22.396,17"
    assert normalize_money_string("1 234,56") == "1234,56"
    assert normalize_money_string("R$ 27.774,83") == "R$ 27.774,83"  # não altera
```

**Impacto esperado:** ~R$ 50K em valores que estão sendo extraídos incorretamente

---

### Prioridade 2: Melhorar classificação de comprovantes (JOYCE CRISTIANE)

**Problema:** Comprovantes de pagamento TED sendo classificados como UTILITY_ENERGY

**Verificar:**
1. Ordem do `ComprovanteBancarioExtractor` no registry
2. Se `can_handle()` detecta padrão "Comprovante de Pagamento" + "TED"

**Comando para diagnóstico:**
```bash
python scripts/inspect_pdf.py --batch email_20260204_115550_b88513b0
```

---

### Prioridade 3 (Opcional): Considerar OCR para PDFs escaneados

**Contexto:** 1 caso (MERCES) é PDF escaneado sem texto

**Opções:**
1. Ativar Tesseract OCR como fallback
2. Aceitar como limitação (valor baixo, caso isolado)

**Decisão sugerida:** Adiar - caso isolado não justifica complexidade de OCR

---

## Comandos Úteis

```powershell
# Verificar batch específico
python scripts/inspect_pdf.py --batch email_20260204_115549_d58f01b9

# Rodar análise de saúde
python scripts/analyze_batch_health.py

# Testar extrator em PDF específico
python -c "
from extractors.outros import OutrosExtractor
import pdfplumber
with pdfplumber.open('temp_email/email_20260204_115549_d58f01b9/01_CARRIER 2.pdf') as pdf:
    text = ''.join(p.extract_text() or '' for p in pdf.pages)
print(OutrosExtractor().extract(text))
"
```

---

## Resumo Final

| Tipo | Qtd | Ação Necessária |
|------|-----|-----------------|
| Problema REAL (espaços em valores) | 2 | ✅ Corrigir regex |
| Falso positivo (comprovantes TED) | 2 | 🟡 Verificar classificação |
| Limitação técnica (PDF escaneado) | 1 | ⏸️ Aceitar por agora |
| Comportamento esperado (email→portal) | 7 | ❌ Nenhuma ação |

**Tempo estimado para correções:** ~30 minutos
