# Sessão 30/01/2026 - Correção NFSE_SEM_NUMERO e Fornecedores Vazios

> **Data:** 2026-01-30  
> **Duração:** ~3 horas  
> **Tipo:** Análise + Correções Múltiplas  
> **Status:** ✅ CONCLUÍDA

---

## 📊 Resumo Executivo

**Problema Principal:** 80 documentos apareciam sem número no CSV, totalizando R$ 173K em valores não identificáveis.

**Causa Raiz:** `EnergyBillExtractor` retornava `tipo_documento="ENERGY_BILL"` não reconhecido pelo processador, fazendo documentos caírem em `InvoiceData` sem mapeamento correto de campos.

**Soluções Aplicadas:**
1. ✅ **Caso 3:** Criado `BoletoGoxExtractor` para boletos GOX
2. ✅ **Caso 2:** Refatorado `EnergyBillExtractor` → `UtilityBillExtractor` 
3. ✅ **Caso 1:** Corrigidos fornecedores vazios (Ufinet, Mi Telecom, TIM, Correios)

---

## 🔍 Análise Inicial

### Descobertas Principais

| Métrica | Valor |
|---------|-------|
| Total de batches | 832 |
| Casos NFSE_SEM_NUMERO | 80 (R$ 173K) |
| Fornecedores vazios | 14 (R$ 102K) |
| Fornecedores como email | 22 |
| Problemas CRÍTICOS | 14 |
| Problemas ALTA | 36 |

### Causas Identificadas

1. **EnergyBillExtractor** retornava `tipo_documento="ENERGY_BILL"` → não mapeado no processor
2. **Faturas GOX** sem número de documento (boletos, não NFs)
3. **UfinetExtractor** rejeitava documentos com "NOTA FISCAL"
4. **DanfeExtractor** não extraía fornecedor de NFCom (telecom)
5. **OutrosExtractor** não reconhecia Correios, TIM, etc.

---

## ✅ Correções Aplicadas

### Correção #1: BoletoGoxExtractor (Caso 3)

**Problema:** Boletos GOX sem número de documento, fornecedor extraído errado

**Solução:**
- Criado extrator específico `extractors/boleto_gox.py`
- Extrai número do documento do nome do arquivo (`receber_XXXXXXX`)
- Força fornecedor como "GOX S.A."

**Arquivos:**
```
- extractors/boleto_gox.py (NOVO)
- extractors/__init__.py (registro)
- core/processor.py (contexto para extractors)
```

**Resultado:**
- Antes: `numero_documento=vazio`, `fornecedor="CNPJ: . Edi rt"`
- Depois: `numero_documento="2041163"`, `fornecedor="GOX S.A."`

---

### Correção #2: UtilityBillExtractor (Caso 2)

**Problema:** Faturas de energia/saneamento classificadas incorretamente como NFSE

**Solução:**
- Refatorado `EnergyBillExtractor` → `UtilityBillExtractor`
- Retorna `tipo_documento="UTILITY_BILL"`
- Adicionado mapeamento no processor → `OtherDocumentData`
- Subtipos: `ENERGY`, `WATER`

**Arquivos:**
```
- extractors/utility_bill.py (NOVO - substitui energy_bill.py)
- extractors/energy_bill.py (REMOVIDO)
- extractors/__init__.py (atualizado)
- core/processor.py (mapeamento UTILITY_BILL)
```

**Resultado:**
- Antes: Tipo=`NFSE`, `numero_nota=vazio`
- Depois: Tipo=`OUTRO`, `numero_documento="15378497"`, `subtipo="ENERGY"`

**Fornecedores cobertos:**
- Energia: CEMIG, EDP, NEOENERGIA, COPEL, CPFL, ENERGISA, ENEL, LIGHT
- Água: COPASA, SABESP, SANEPAR

---

### Correção #3: Fornecedores Vazios (Caso 1)

**Problema:** Múltiplos casos com fornecedor não extraído

#### 3.1 Ufinet (R$ 55K, R$ 15K, R$ 1,5K)
**Causa:** `UfinetExtractor` rejeitava documentos com "NOTA FISCAL"
**Solução:** Removida restrição desnecessária
**Arquivo:** `extractors/ufinet.py`

#### 3.2 Mi Telecom (R$ 1,9K)
**Causa:** `DanfeExtractor` não extraía fornecedor de NFCom
**Solução:** Adicionado padrão "DOCUMENTO AUXILIAR...FATURA DE SERVIÇOS"
**Arquivo:** `extractors/danfe.py`

#### 3.3 TIM (R$ 52)
**Causa:** `NfseCustomMontesClarosExtractor` não reconhecia TIM
**Solução:** Adicionado mapeamento por CNPJ/nome
**Arquivo:** `extractors/nfse_custom_montes_claros.py`

#### 3.4 Correios (R$ 120, R$ 149)
**Causa:** `OutrosExtractor` não reconhecia Correios
**Solução:** Adicionado mapeamento de fornecedores conhecidos
**Arquivo:** `extractors/outros.py`

---

## 📁 Arquivos Modificados

### Novos Arquivos
```
extractors/boleto_gox.py          # Extrator boletos GOX
extractors/utility_bill.py        # Extrator unificado utilidades
```

### Arquivos Modificados
```
core/processor.py                 # Mapeamento UTILITY_BILL + contexto
extractors/__init__.py            # Registro novos extractors
extractors/ufinet.py              # Permite NF, corrige campos
extractors/danfe.py               # Padrão NFCom telecom
extractors/nfse_custom_montes_claros.py  # Mapeamento TIM
extractors/outros.py              # Fornecedores conhecidos
```

### Arquivos Removidos
```
extractors/energy_bill.py         # Substituído por utility_bill.py
```

---

## 🧪 Validação

### Testes Realizados

| Caso | Batch (referência) | Resultado |
|------|-------------------|-----------|
| GOX | email_20260129_084431_ee451c4d | ✅ numero_documento=2041163 |
| COPASA | email_20260129_084431_0ef2554a | ✅ numero_documento=00169106977 |
| NEOENERGIA | email_20260129_084432_02f27d41 | ✅ numero_documento=15378497 |
| CEMIG | email_20260129_084431_040f3727 | ✅ numero_documento=342714119 |
| Ufinet | email_20260129_084433_d3e5bc21 | ✅ fornecedor="Ufinet Brasil S.A" |
| Mi Telecom | email_20260129_084432_cef9ced2 | ✅ fornecedor="MITelecom Ltda" |
| TIM | email_20260129_084436_6ea340aa | ✅ fornecedor="TIM S.A." |
| Correios | email_20260129_084431_6138cd60 | ✅ fornecedor="CORREIOS" |

---

## 📋 Decisões Técnicas

### 1. Arquitetura UtilityBillExtractor
```
UtilityBillExtractor
    ├── Subtipo ENERGY (CEMIG, EDP, etc.)
    ├── Subtipo WATER (COPASA, SABESP, etc.)
    └── Retorna tipo_documento="UTILITY_BILL"
            ↓
    Processor → OtherDocumentData
            ↓
    CSV: numero_documento (funciona!)
```

### 2. Mapeamento de Tipos no Processor
```python
# Antes: ENERGY_BILL caía no else → InvoiceData
# Depois: UTILITY_BILL mapeado explicitamente → OtherDocumentData

elif extracted_data.get('tipo_documento') == 'UTILITY_BILL':
    return OtherDocumentData(
        numero_documento=extracted_data.get('numero_documento'),
        subtipo=extracted_data.get('subtipo'),
        ...
    )
```

### 3. Contexto para Extractors
```python
# Processor agora passa contexto (nome do arquivo)
def extract_with_extractor(extractor, text, context):
    try:
        return extractor.extract(text, context)  # Novos
    except TypeError:
        return extractor.extract(text)           # Legados
```

---

## 🔄 Para Reencontrar em Nova Sessão

### Buscar casos corrigidos no CSV
```powershell
# GOX
Get-Content data/output/relatorio_lotes.csv | Select-String "GOX"

# Utilidades (energia/água) - procure por subtipo ou fornecedor
Get-Content data/output/relatorio_lotes.csv | Select-String "COPASA|CEMIG|EDP|NEOENERGIA"

# Fornecedores que estavam vazios
Get-Content data/output/relatorio_lotes.csv | Select-String "UFINET|MITelecom|TIM|CORREIOS"
```

### Validar extractores
```powershell
# Validar todos os batches
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# Inspecionar caso específico
python scripts/inspect_pdf.py "temp_email/<batch>/arquivo.pdf" --text
```

---

## ⚠️ Pontos de Atenção

### 1. Batch IDs Voláteis
> **AVISO:** IDs mudam a cada `clean_dev` + `run_ingestion`!
> Use fornecedor/tipo para rastreamento, nunca batch IDs.

### 2. Encoding no Windows
Caracteres acentuados podem aparecer como `�` no PowerShell. Isso é normal (Windows-1252/ISO-8859-1).

### 3. Comandos PowerShell vs Unix
- ❌ `head`, `grep`, `find` (não funcionam no Windows)
- ✅ `Select-Object -First`, `Select-String`, `Get-ChildItem`

---

## 📚 Documentação Relacionada

- [`correction_tracking.md`](./correction_tracking.md) - Rastreamento entre sessões
- [`commands_reference.md`](./commands_reference.md) - Comandos Unix vs PowerShell
- [`project_overview.md`](./project_overview.md) - Visão geral do sistema

---

**Próximos Passos Sugeridos:**
1. Reprocessar lotes para validar correções no CSV final
2. Verificar se há regressões (casos que pararam de funcionar)
3. Commitar mudanças quando solicitado pelo usuário
