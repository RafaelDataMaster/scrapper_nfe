# Troubleshooting - Problemas Encontrados na Sessão 30/01/2026

> **Sessão:** Correção NFSE_SEM_NUMERO e Fornecedores Vazios  
> **Data:** 2026-01-30  
> **Problemas resolvidos:** 3 principais categorias

---

## 1. Tipo de Documento Não Mapeado no Processor

### Problema: EnergyBillExtractor retornava tipo não reconhecido

**Sintoma:**
- Extrator funcionava (extraía dados)
- Mas número não aparecia no CSV
- Tipo mostrado como `NFSE` em vez do tipo correto

**Causa:**
```python
# EnergyBillExtractor (ANTIGO)
return {"tipo_documento": "ENERGY_BILL", ...}  # ❌ Não mapeado!

# Processor (else cai em NFSE genérico)
else:
    return InvoiceData(...)  # Usa numero_nota, não numero_documento
```

**Solução - Duas abordagens:**

### Opção A: Mapear tipo no processor (Escolhida)
```python
# core/processor.py
elif extracted_data.get('tipo_documento') == 'UTILITY_BILL':
    return OtherDocumentData(
        numero_documento=extracted_data.get('numero_documento'),
        subtipo=extracted_data.get('subtipo'),
        ...
    )
```

### Opção B: Usar tipo existente
```python
# No extrator, retornar tipo já mapeado
return {"tipo_documento": "OUTRO", "subtipo": "ENERGY_BILL", ...}
```

**Lição:** Sempre verificar se o `tipo_documento` está mapeado em `processor.py`.

---

## 2. Extrator Precisa do Nome do Arquivo

### Problema: Boleto GOX sem número de documento

**Sintoma:**
- Boleto GOX não tem número no conteúdo
- Número está apenas no nome do arquivo: `receber_2041163.pdf`

**Solução - Passar contexto:**

```python
# 1. Processor passa contexto
def extract_with_extractor(extractor, text, context):
    try:
        return extractor.extract(text, context)  # Novos
    except TypeError:
        return extractor.extract(text)           # Legados (fallback)

# 2. Extrator usa contexto
class BoletoGoxExtractor:
    def extract(self, text, context=None):
        filename = context.get('arquivo_origem') if context else None
        numero = self._extract_from_filename(filename)
        return {"numero_documento": numero, ...}
```

**Uso:**
```python
# Contexto contém:
{
    'arquivo_origem': '01_cliente_35875_receber_2041163_562660517166001766670637.pdf',
    'file_path': 'temp_email/email_.../01_...pdf'
}
```

---

## 3. Extrator Rejeita Documentos Válidos

### Problema: UfinetExtractor rejeitava DANFEs da Ufinet

**Sintoma:**
- DANFEs da Ufinet iam para DanfeExtractor genérico
- Fornecedor não era extraído corretamente

**Causa:**
```python
# ❌ Problema
if "NOTA FISCAL" in text_upper:
    return False  # Rejeitava DANFEs também!
```

**Solução:**
```python
# ✅ Correto - verificar contexto completo
if "UFINET" not in text_upper:
    return False

# Aceita tanto faturas quanto NFs da Ufinet
return True
```

**Lição:** Restrições negativas (`if X: return False`) devem ser muito específicas.

---

## 4. Fornecedor Não Extraído (OCR Corrompido)

### Problema: Fornecedor extraído como "CNPJ: . Edi rt"

**Causa:** OCR corrompe caracteres, regex captura texto errado

**Solução - Mapeamento por CNPJ:**
```python
KNOWN_SUPPLIERS_BY_CNPJ = {
    "02.421.421": "TIM S.A.",          # TIM
    "02421421": "TIM S.A.",            # TIM sem formatação
    "07.543.400": "GOX S.A.",          # GOX
    "10.968.981": "MITelecom Ltda",    # Mi Telecom
}

def extract_fornecedor(self, text):
    # 1. Tenta identificar por CNPJ (mais confiável)
    for cnpj_key, supplier in KNOWN_SUPPLIERS_BY_CNPJ.items():
        if cnpj_key in text:
            return supplier
    
    # 2. Fallback para extração genérica
    return self._extract_fornecedor_generico(text)
```

**Solução - Mapeamento por palavra-chave:**
```python
KNOWN_SUPPLIERS = {
    "CORREIOS": "CORREIOS",
    "EXTRATO SINTETICO": "CORREIOS",
    "TIM": "TIM",
    "UFINET": "UFINET BRASIL S.A.",
}
```

---

## 5. Prioridade de Extrator (Registry)

### Problema: BoletoGoxExtractor nunca era selecionado

**Sintoma:**
- Boleto GOX ia para BoletoExtractor genérico
- Fornecedor extraído errado

**Causa:** Ordem no registry
```python
# ❌ Errado - genérico antes do específico
from .boleto import BoletoExtractor
from .boleto_gox import BoletoGoxExtractor  # Nunca chamado!
```

**Solução:**
```python
# ✅ Correto - específico primeiro
from .boleto_gox import BoletoGoxExtractor  # Prioridade 2
from .boleto import BoletoExtractor         # Prioridade 14
```

**Como diagnosticar:**
```bash
python scripts/inspect_pdf.py arquivo.pdf
# Ver "TESTE DE EXTRATORES" - ordem deve ser:
# 2. BoletoGoxExtractor [CHECK] Compatível
# 14. BoletoExtractor [X] Não compatível
```

---

## 6. Encoding no Windows (Não é Bug!)

### Problema: Caracteres aparecem como `�`

**Exemplo:**
```
Fornecedor: TIM S�
Extrator: EnergyBillExtrator
```

**Causa:** Windows usa Windows-1252/ISO-8859-1 para saída do terminal

**Solução:**
```powershell
# Não é bug - é comportamento normal
# O dado está correto no CSV (UTF-8)

# Para forçar UTF-8 no terminal:
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

**Verificação:**
```powershell
# Verifique o CSV - caracteres estarão corretos
Get-Content data/output/relatorio_lotes.csv | Select-String "TIM"
# Resultado: TIM S.A. (correto)
```

---

## 7. Extrair Coluna Específica do CSV

### Tarefa: Extrair valores da coluna "fornecedor"

**Solução PowerShell:**
```powershell
# Método 1: ForEach-Object com Split
Get-Content data/output/relatorio_lotes.csv | 
    Select-Object -Skip 1 |  # Pula header
    ForEach-Object { $_.Split(';')[6] }  # Coluna 7 (índice 6)

# Método 2: Import-Csv (melhor)
Import-Csv -Path data/output/relatorio_lotes.csv -Delimiter ';' |
    Select-Object -ExpandProperty fornecedor

# Método 3: Com filtro
Import-Csv -Path data/output/relatorio_lotes.csv -Delimiter ';' |
    Where-Object { $_.valor_compra -gt 1000 } |
    Select-Object fornecedor, valor_compra
```

---

## Checklist de Debugging

Quando um extrator não funciona:

- [ ] `can_handle()` retorna `True` para o documento?
- [ ] Extrator está registrado em `__init__.py`?
- [ ] Ordem no registry está correta (antes de genéricos)?
- [ ] `tipo_documento` está mapeado em `processor.py`?
- [ ] Campos retornados correspondem ao modelo (numero_nota vs numero_documento)?
- [ ] Se precisa do nome do arquivo, está usando `context`?
- [ ] Valores são do tipo correto (float para valores, não string)?

---

## Comandos Úteis para Debugging

```powershell
# Testar extrator isoladamente
python -c "
from extractors.utility_bill import UtilityBillExtractor
e = UtilityBillExtractor()
print('Registrado:', 'UtilityBillExtractor' in str(e.__class__))
"

# Ver ordem do registry
Select-String -Path extractors/__init__.py -Pattern "from \." | Select-Object -First 20

# Testar can_handle em um PDF
python scripts/inspect_pdf.py arquivo.pdf --text 2>&1 | Select-String "can_handle|SELECIONADO"

# Contar casos no CSV
Import-Csv data/output/relatorio_lotes.csv -Delimiter ';' | Where-Object { $_.fornecedor -eq '' } | Measure-Object
```
