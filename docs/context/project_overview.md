# Overview do Sistema de Extração de Documentos Fiscais

> **Data de geração:** 2026-02-02  
> **Versão do sistema:** v0.3.x  
> **Status da documentação:** Esta documentação complementa (e corrige onde necessário) a documentação oficial que está parcialmente desatualizada.

---

## 📊 Status Atual do Projeto

> **IMPORTANTE:** Esta seção contém snapshots das sessões de trabalho. Mantém apenas os últimos 3 snapshots.  
> **Template:** Ver `project_status_template.md` para o formato completo.

### Snapshot: 02/02/2026 - 15:00 - CSC_NOTA_DEBITO_EXTRACTOR

**Tipo:** EXTRATOR_NOVO_IMPLEMENTADO

**Contexto da Sessão:**

- Sessão continuação de: 02/02/2026 14:30 (REPROMAQ_LOCACAO_EXTRACTOR_FIX)
- Foco: Implementar extrator para documentos CSC/Linnia (Nota Débito/Recibo Fatura)
- Tempo total: ~25 minutos

**Estado das Correções:**
| # | Nome | Status | Arquivos Criados/Modificados | Categoria |
|---|------|--------|------------------------------|-----------|
| 1 | CSC Nota Débito Extractor | ✅ CONCLUÍDA | csc_nota_debito.py, **init**.py | Novo Extrator |

**Correção #1: CscNotaDebitoExtractor** ✅ CONCLUÍDA

- **Problema:** Documentos CSC/Linnia tipo "NOTA DÉBITO / RECIBO FATURA" não eram reconhecidos por nenhum extrator
- **Causa raiz:** Não existia extrator específico para este tipo de documento da CSC GESTAO INTEGRADA S/A
- **Solução:**
    - Criado `extractors/csc_nota_debito.py` com classe `CscNotaDebitoExtractor`
    - Registrado no `extractors/__init__.py` (antes dos genéricos)
    - Identifica documentos por:
        - Texto "NOTA DÉBITO / RECIBO FATURA" ou variantes
        - CNPJ da CSC: 38.323.227/0001-40
        - Nome "CSC GESTAO" no texto
    - Extrai campos:
        - `tipo_documento`: OUTRO
        - `subtipo`: NOTA_DEBITO
        - `numero_documento`: Número da nota (ex: 347, 348)
        - `fornecedor_nome`: CSC GESTAO INTEGRADA S/A
        - `cnpj_fornecedor`: 38.323.227/0001-40
        - `data_emissao`: Data no formato ISO
        - `competencia`: Mês/ano de referência
        - `tomador_nome` e `cnpj_tomador`: Dados do cliente
        - `valor_total`: Valor total da nota
        - `observacoes`: Descrição dos itens
- **Arquivos:** `extractors/csc_nota_debito.py`, `extractors/__init__.py`

**Casos Corrigidos (3 do CSC/Linnia - R$ 24.966):**

| Batch ID                       | Arquivo                                 | Antes           | Depois                          |
| ------------------------------ | --------------------------------------- | --------------- | ------------------------------- |
| email_20260202_104618_ca26052f | 01_01_08 - 347- CSC Tarifa Bradesco ... | NFSE sem número | OUTRO/NOTA_DEBITO #347          |
| email_20260202_104618_ca26052f | 02_01_08 - 348- CSC Tarifa Itau ...     | NFSE sem número | OUTRO/NOTA_DEBITO #348          |
| email_20260202_104618_ca26052f | Outros 5 PDFs CSC Tarifa ...            | NFSE sem número | OUTRO/NOTA_DEBITO #349-350, etc |

**Testes:**

- 25 novos testes criados em `tests/test_csc_nota_debito_extractor.py`
- Suite completa: **589 passed, 1 skipped** (nenhum teste quebrou)

---

### Snapshot: 02/02/2026 - 14:30 - REPROMAQ_LOCACAO_EXTRACTOR_FIX

**Tipo:** CORRECAO_EXTRATOR

**Contexto da Sessão:**

- Sessão continuação de: 02/02/2026 14:00 (LOGGING_ADJUSTMENT_SABESP)
- Foco: Corrigir extração de documentos REPROMAQ de locação
- Tempo total: ~40 minutos

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | Categoria |
|---|------|--------|---------------------|-----------|
| 1 | Logging Adjustment (sessão anterior) | ✅ CONCLUÍDA | analyze_logs.py, docs | Melhoria |
| 2 | REPROMAQ Extrato de Locação | ✅ CONCLUÍDA | nfse_generic.py, outros.py | Correção |

**Correção #2: REPROMAQ Extrato de Locação** ✅ CONCLUÍDA

- **Problema:** Documentos REPROMAQ de locação eram classificados como NFSE sem número
- **Causa raiz:**
    1. `NfseGenericExtractor` aceitava "EXTRATO DE LOCAÇÃO" como NFSE
    2. `OutrosExtractor` não reconhecia "EXTRATO DE LOCAÇÃO" nem "FATURA DE LOCAÇÃO"
    3. Documentos com impostos (PIS, COFINS, ISS, CSLL) eram bloqueados mesmo sendo faturas de locação
    4. Não havia extração de número do recibo/fatura para documentos de locação
- **Solução:**
    - `nfse_generic.py`: Adicionado "EXTRATO DE LOCAÇÃO/LOCACAO" em `other_keywords` para rejeição
    - `outros.py`: Adicionado suporte para detectar "EXTRATO DE LOCAÇÃO" e "FATURA DE LOCAÇÃO"
    - `outros.py`: Exceção na regra de impostos para faturas/extratos de locação
    - `outros.py`: Novos padrões para extrair `numero_documento`:
        - `NÚMERO DO RECIBO:S09679`
        - `Nº S09679`
        - `NÚMERO DA FATURA ... S09679`
        - `NÚMERO DO CONTRATO :4152` (fallback com prefixo CONTRATO-)
    - `outros.py`: Novos padrões para extrair `valor_total`:
        - `VALOR TOTAL : 267,81`
        - `R$ TOTAL : 267,81`
    - `outros.py`: Subtipo LOCACAO para "FATURA DE LOCAÇÃO"

**Casos Corrigidos:**

| Batch ID                       | Arquivo          | Antes               | Depois               |
| ------------------------------ | ---------------- | ------------------- | -------------------- |
| email_20260202_104620_d8eb864c | 01_A00003739.PDF | NFSE sem número     | OUTRO/LOCACAO S09679 |
| email_20260202_104620_d8eb864c | 03_RECS09679.PDF | Erro (sem extrator) | OUTRO/LOCACAO S09679 |

**Testes:**

- 564 testes passando ✅

**Arquivos Modificados:**

- `extractors/nfse_generic.py` (rejeita EXTRATO DE LOCAÇÃO)
- `extractors/outros.py` (suporte completo para documentos de locação REPROMAQ)
- `docs/context/pdf_password_handling.md` (NOVO - sessão anterior)
- `docs/context/README.md` (atualizado referência)
- `scripts/analyze_logs.py` (ajustes de regex - sessão anterior)
- `docs/context/log_correlation.md` (atualizado exemplos - sessão anterior)

---

### Snapshot: 02/02/2026 - 12:20 - REGEX_NUMERO_NOTA_CORRIGIDO

**Tipo:** CORRECAO_REGEX

**Contexto da Sessão:**

- Sessão continuação de: 02/02/2026 12:00 (SABESP_EXTRACTOR_IMPLEMENTADO)
- Foco: Resolver 19 casos de NFSE_SEM_NUMERO com valor > 0
- Tempo total: ~20 minutos

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | Categoria |
|---|------|--------|---------------------|-----------|
| 1 | NfseGenericExtractor regex | ✅ CONCLUÍDA | nfse_generic.py | Regex melhorado |
| 2 | MugoExtractor regex | ✅ CONCLUÍDA | mugo_extractor.py | Regex melhorado |

**Correção #1: NfseGenericExtractor** ✅ CONCLUÍDA

- **Problema:** NFSe com número em linha separada (TCF Services) ou números curtos (CSC) não extraídos
- **Causa raiz:**
    1. Número de 15 dígitos em linha separada do "Nº" não capturado
    2. Padrões não aceitavam números de 3 dígitos (ex: "Numero: 347")
    3. "Recibo número:" removido pela limpeza de texto antes da extração
- **Solução:**
    - Adicionados 4 novos padrões regex:
        - `N[º°o]\s*\n\s*(?:Emitida|Compet|Data).*?\n\s*(\d{10,15})` - número em linha separada
        - `^\s*(\d{10,15})\s+\d{2}/\d{2}/\d{4}` - número longo seguido de data
        - `(?i)(?:Numero|Número)\s*:\s*(\d{3,15})\b` - "Numero: 347" com 3+ dígitos
        - `(?i)N[º°o]\s*documento\s*:\s*(\d{4,15})\b` - "Nº documento: 71039"
    - Adicionado padrão composto: `Recibo\s+n[úu]mero\s*:\s*(\d{1,6}[/\-]\d{4})` - "Recibo número: 59/2026"
    - Ajustado regex de limpeza para preservar "Recibo número:" com negative lookahead
- **Casos corrigidos:**
    - TCF Services (6 casos): número 202600000000068 (15 dígitos)
    - CSC/Linnia (3 casos): número 347, 348, etc. (3 dígitos)
    - GAC Contabilidade (1 caso): número 59/2026 (formato composto)
- **Arquivos:** extractors/nfse_generic.py

**Correção #2: MugoExtractor** ✅ CONCLUÍDA

- **Problema:** Número "71039" (5 dígitos) não extraído
- **Causa raiz:** Regex usava `\d{6,12}` (mínimo 6 dígitos)
- **Solução:** Alterado para `\d{4,15}` em todos os padrões
- **Casos corrigidos:**
    - MUGO (2 casos): número 71039 (5 dígitos)
- **Arquivos:** extractors/mugo_extractor.py

**Análise dos 19 casos NFSE_SEM_NUMERO:**
| Categoria | Qtd | Valor | Status |
|-----------|-----|-------|--------|
| Sabesp | 3 | R$ 424 | ✅ Já resolvido (SabespExtractor) |
| TCF Services | 6 | R$ 222 | ✅ Corrigido (regex 15 dígitos) |
| MUGO | 2 | R$ 2.980 | ✅ Corrigido (regex 5 dígitos) |
| CSC/Linnia | 3 | R$ 24.966 | ⚠️ Docs sem extrator compatível |
| REPROMAQ | 3 | R$ 807 | ⚠️ Extratos locação, NF vazia |
| ATIVE | 1 | R$ 77 | ✅ Corrigido (regex 15 dígitos) |
| GAC | 1 | R$ 1.378 | ✅ Corrigido (Recibo número:) |

**Testes:**

- 564 testes passando ✅
- Todos os testes NfseGenericExtractor passando ✅

**Problemas Pendentes:**

1. CSC/Linnia: "NOTA DÉBITO / RECIBO FATURA" não reconhecido por nenhum extrator
2. REPROMAQ: Extratos de locação com campo NF vazio no PDF

**Documentação Atualizada:**

- docs/context/commands_reference.md: Adicionadas dicas para agentes IA sobre comandos problemáticos

---

### Snapshot: 02/02/2026 - 12:00 - SABESP_EXTRACTOR_IMPLEMENTADO

**Tipo:** EXTRATOR_NOVO_IMPLEMENTADO

**Contexto da Sessão:**

- Sessão iniciada em: 02/02/2026 11:45
- Foco: Análise de saúde geral + Resolver 3 erros reais da Sabesp (PDFs protegidos por senha)
- Tempo total: ~30 minutos
- Metodologia: Processo limpo (clean_dev → run_ingestion → analyze_health)

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | Categoria |
|---|------|--------|---------------------|-----------|
| 1 | SabespWaterBillExtractor | ✅ CONCLUÍDA | sabesp.py (novo), **init**.py, batch_processor.py | Extrator novo |

**Correção #1: SabespWaterBillExtractor** ✅ CONCLUÍDA

- **Problema:** 3 erros reais da Sabesp - PDFs protegidos por senha (CPF do titular)
- **Causa raiz:**
    1. PDFs da Sabesp são encriptados e não podem ser lidos
    2. Todos os dados estão no corpo do email HTML, não no PDF
    3. O sistema registrava erro mesmo quando EmailBodyExtractor extraía dados
- **Solução:**
    - Novo extrator especializado `SabespWaterBillExtractor` para emails da Sabesp
    - Detecta Sabesp pelo sender (sabesp.com.br), subject ou conteúdo do corpo
    - Extrai: valor, vencimento, número de fornecimento, código de barras, unidade
    - Retorna `tipo_documento="UTILITY_BILL"` com `subtipo="WATER"`
    - CNPJ fixo: 43.776.517/0001-80
    - BatchProcessor modificado para usar SabespExtractor antes do EmailBodyExtractor genérico
- **Casos corrigidos:**
    - email_20260202_104616_65ce707b: R$ 138,56 - venc 2026-01-20
    - email_20260202_104619_54afbcf8: R$ 140,65 - venc 2026-01-25
    - email_20260202_104621_c1921810: R$ 145,15 - venc 2026-02-20
- **Arquivos:**
    - extractors/sabesp.py (NOVO)
    - extractors/**init**.py (atualizado)
    - core/batch_processor.py (atualizado)
    - tests/test_sabesp_extractor.py (NOVO - 18 testes)

**Análise de Saúde Atual (02/02/2026):**
| Métrica | Valor | Status |
|---------|-------|--------|
| Total de Lotes | 919 | ✅ |
| Total de Documentos | 1.258 | ✅ |
| Valor Total Processado | R$ 5.840.661,33 | ✅ |
| Taxa de Conciliação | 25% (315/1258) | ⚠️ |
| Fornecedor Válido | 84,8% | ✅ |
| Erros Reais | 3 → 0 (corrigidos) | ✅ |

**Distribuição por Tipo:**

- NFSE: 412 (32,7%)
- OUTRO: 398 (31,6%)
- BOLETO: 369 (29,3%)
- DANFE: 79 (6,3%)

**Subtipos de OUTRO:**

- ENERGY: 240 (60,3%)
- COMPROVANTE_BANCARIO: 33 (8,3%)
- WATER: 31 → 34 após correção (7,8%)
- FATURA: 23 (5,8%)
- FATURA_UFINET: 17 (4,3%)

**Problemas Pendentes (para próximas sessões):**

1. **FORNECEDOR_TEXTO_PDF** (~120 docs): Parsing incorreto extrai texto bruto do PDF
2. **NFSE_SEM_NUMERO** (16 casos): NFSEs sem número da nota
3. **VENCIMENTO_AUSENTE** (57 casos): Documentos sem data de vencimento

**Testes:**

- 564 testes passando ✅
- 18 novos testes para SabespExtractor ✅

**Para Reencontrar em Nova Sessão:**

```powershell
# Buscar lotes Sabesp
Get-Content data/output/relatorio_lotes.csv | Select-String "Sabesp"

# Verificar tipo WATER
python -c "import pandas as pd; df = pd.read_csv('data/output/relatorio_consolidado.csv', sep=';'); print(df[df['subtipo']=='WATER'][['fornecedor_nome','valor_total','vencimento']].head(10))"
```

---

### Snapshot: 30/01/2026 - 13:00 - CORRECOES_ADITIVOS_OCR_CONCLUIDAS

**Tipo:** CORRECOES_ADITIVOS_OCR_CONCLUIDAS

**Contexto da Sessão:**

- Sessão iniciada em: 30/01/2026 08:57
- Foco: Resolver casos FORNECEDOR_VAZIO (R$ 27K) + Aditivos ALARES + OCR corrompido
- Tempo total: ~4 horas
- Continuação de: Snapshot 30/01/2026 - 11:00

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | Categoria |
|---|------|--------|---------------------|-----------|
| 1 | AditivoContratoExtractor | ✅ CONCLUÍDA | aditivo_contrato.py, **init**.py | Extrator novo |
| 2 | OcrDanfeExtractor | ✅ CONCLUÍDA | ocr_danfe.py, **init**.py | Extrator novo |
| 3 | BatchProcessor Email Body | ✅ CONCLUÍDA | batch_processor.py | Lógica de correlação |
| 4 | NfseGenericExtractor | ✅ CONCLUÍDA | nfse_generic.py | Regex melhorado |

**Correção #1: AditivoContratoExtractor** ✅ CONCLUÍDA

- **Problema:** Aditivos de contrato (ALARES) com fornecedor vazio - sistema usava dados do email
- **Causa raiz:**
    1. Extrator retornava `valor` em vez de `valor_total` (processor ignorava)
    2. BatchProcessor adicionava documento do email quando valor=0
- **Solução:**
    - Novo extrator específico para aditivos de contrato
    - Detecta CNPJs conhecidos (ALARES: 02.952.192/0001-61, 02.952.192/0029-62)
    - Corrigido campo `valor` → `valor_total` para compatibilidade
    - BatchProcessor modificado para não sobrescrever PDF válido com email
- **Casos:**
    - ALARES aditivos (R$ 2.518 cada) - 4 casos
    - Aditivos locação (Elton Messias) - 1 caso
- **Arquivos:** extractors/aditivo_contrato.py (novo)

**Correção #2: OcrDanfeExtractor** ✅ CONCLUÍDA

- **Problema:** DANFEs com OCR corrompido (Auto Posto) - texto truncado, fornecedor vazio
- **Solução:** Extrator específico que detecta corrupção e usa padrões OCR-tolerantes
- **Padrões:** "RECEHEMOS" (corrompido), "HINAT", "CIVCRE", "VANGAS"
- **Casos:** Auto Posto Portal de Minas (R$ 1.460,84)
- **Arquivos:** extractors/ocr_danfe.py (novo)

**Correção #3: BatchProcessor Email Body** ✅ CONCLUÍDA

- **Problema:** Documentos válidos do PDF sendo sobrescritos por dados do email
- **Causa:** `_has_nota_with_valor()` retornava False quando valor=0 (mesmo com fornecedor)
- **Solução:** Nova lógica `has_valid_pdf_doc` verifica `fornecedor_nome` OR `valor_total > 0`
- **Impacto:** Aditivos ALARES agora mantêm fornecedor correto
- **Arquivos:** core/batch_processor.py

**Correção #4: NfseGenericExtractor** ✅ CONCLUÍDA

- **Problema:** Fornecedor extraído como "PRESTADOR DE SERVIÇOS" (texto genérico)
- **Solução:** Rejeitar textos genéricos no padrão de Prestador
- **Arquivos:** extractors/nfse_generic.py

**Estado do Sistema:**

- **Extractors no Registry:** 20 total (4 novos: AditivoContratoExtractor, OcrDanfeExtractor)
- **Ordem do Registry:** ✅ ATUALIZADA
    - OcrDanfeExtractor (prioridade 14, antes de DanfeExtractor)
    - AditivoContratoExtractor (prioridade 18, antes de OutrosExtractor)
- **Código:** Validação basedpyright passando ✅

**Estado dos Dados (ANTES - aguardando reprocessamento):**

- **FORNECEDOR_VAZIO:** 5 ocorrências | Valor: R$ 27.911,47
    - Auto Posto R$ 1.460,84 → OcrDanfeExtractor ✅
    - ALARES aditivos R$ 2.518,00 → AditivoContratoExtractor ✅
- **FORNECEDOR_CURTO (E-mail):** 11 ocorrências → BatchProcessor fix ✅
- **FORNECEDOR_TEXTO_PDF:** "PRESTADOR DE SERVIÇOS" → NfseGenericExtractor fix ✅

**Casos Esperados após Reprocessamento:**
| Documento | Fornecedor Esperado | Valor | Extrator |
|-----------|---------------------|-------|----------|
| ALARES aditivos (4x) | ALARES INTERNET S/A | R$ 2.518 cada | AditivoContratoExtractor |
| Auto Posto | AUTO POSTO PORTAL DE MINAS | R$ 1.460 | OcrDanfeExtractor |
| MOC Comunicação | (vazio - comprovante TED) | R$ 21.274 | N/A (saída) |

**Decisões Tomadas:**

- Aditivos de contrato não têm valor monetário próprio → usar dados do boleto/email, mas manter fornecedor do PDF
- OCR corrompido precisa de extrator separado (não modificar DanfeExtractor genérico)
- BatchProcessor deve priorizar PDF sobre email quando PDF tem fornecedor válido
- Textos genéricos tipo "PRESTADOR DE SERVIÇOS" devem ser rejeitados

**Para Reencontrar em Nova Sessão:**

> ⚠️ **AVISO:** Batch IDs mudam a cada `clean_dev` + `run_ingestion`!

```powershell
# Buscar aditivos ALARES
Get-Content data/output/relatorio_lotes.csv | Select-String "ALARES"

# Buscar Auto Posto
Get-Content data/output/relatorio_lotes.csv | Select-String "AUTO POSTO"

# Validar extractores
python scripts/validate_extraction_rules.py --batch-mode --temp-email
```

---

### Snapshot: 30/01/2026 - 11:00 - CORRECOES_MULTIPLAS_CONCLUIDAS

**Tipo:** CORRECOES_MULTIPLAS_CONCLUIDAS

**Contexto da Sessão:**

- Sessão iniciada em: 30/01/2026 08:57
- Foco: Resolver 80 casos NFSE_SEM_NUMERO (R$ 173K) + 14 fornecedores vazios (R$ 102K)
- Tempo total: ~3 horas

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | Categoria |
|---|------|--------|---------------------|-----------|
| 1 | BoletoGoxExtractor | ✅ CONCLUÍDA | boleto_gox.py, processor.py | Extrator novo |
| 2 | UtilityBillExtractor | ✅ CONCLUÍDA | utility_bill.py, processor.py, **init**.py | Refatoração |
| 3 | Fornecedores Vazios | ✅ CONCLUÍDA | ufinet.py, danfe.py, nfse_custom_montes_claros.py, outros.py | Correções |

**Correção #1: BoletoGoxExtractor** ✅ CONCLUÍDA

- **Fornecedor:** GOX S.A.
- **Tipo:** BOLETO (tipo_documento="BOLETO")
- **Padrão de detecção:** CNPJ 07.543.400/0001-92 + "GOXINTERNET.COM.BR"
- **Número do documento:** Extraído do nome do arquivo (padrão `receber_XXXXXXX`)
- **Problema resolvido:** Boletos sem número e fornecedor corrompido pelo OCR
- **Arquivos:** extractors/boleto_gox.py (novo), core/processor.py (contexto)

**Correção #2: UtilityBillExtractor** ✅ CONCLUÍDA

- **Problema:** EnergyBillExtractor retornava tipo não mapeado ("ENERGY_BILL")
- **Solução:** Refatoração completa para UtilityBillExtractor
- **Tipo:** UTILITY_BILL → mapeado para OtherDocumentData
- **Subtipos:** "ENERGY" (energia), "WATER" (água/saneamento)
- **Fornecedores cobertos:**
    - ENERGY: CEMIG, EDP, NEOENERGIA, COPEL, CPFL, ENERGISA, ENEL, LIGHT
    - WATER: COPASA, SABESP, SANEPAR
- **Arquivos:**
    - extractors/utility_bill.py (novo)
    - extractors/energy_bill.py (removido)
    - extractors/**init**.py (atualizado)
    - core/processor.py (mapeamento UTILITY_BILL)

**Correção #3: Fornecedores Vazios** ✅ CONCLUÍDA

- **Casos corrigidos:**
  | Fornecedor | Valor | Causa | Solução |
  |------------|-------|-------|---------|
  | Ufinet | R$ 55K | Rejeitava "NOTA FISCAL" | Removida restrição |
  | Mi Telecom | R$ 1,9K | NFCom não extraía fornecedor | Padrão NFCom telecom |
  | TIM | R$ 52 | Não reconhecido | Mapeamento CNPJ/nome |
  | Correios | R$ 120 | Não reconhecido | Mapeamento fornecedores |
- **Arquivos:** ufinet.py, danfe.py, nfse_custom_montes_claros.py, outros.py

**Estado do Sistema:**

- **Extractors no Registry:** 17 total (2 novos: BoletoGoxExtractor, UtilityBillExtractor)
- **Extrator removido:** EnergyBillExtractor
- **Ordem do Registry:** ✅ ATUALIZADA
    - BoletoGoxExtractor (prioridade 2)
    - UtilityBillExtractor (prioridade 6)
- **Código:** Validação basedpyright passando ✅

**Estado dos Dados:**

- **Casos NFSE_SEM_NUMERO:** Reduzidos de 80 para ~0 (validar no reprocessamento)
- **Fornecedores vazios:** Reduzidos de 14 para ~0 (casos de saída/pagamento permanecem)
- **Failed cases:** 0 novos confirmados

**Decisões Tomadas:**

- `tipo_documento` deve ser um dos valores mapeados no processor (BOLETO, DANFE, UTILITY_BILL, OUTRO, ou NFSE genérico)
- Faturas de utilidade (energia, água) → OUTRO com subtipo (não NFSE)
- Contexto (arquivo_origem) passado para extractores que precisam do nome do arquivo
- Mapeamento por CNPJ mais confiável que regex para fornecedores conhecidos

**Para Reencontrar em Nova Sessão:**

> ⚠️ **AVISO:** Batch IDs mudam a cada `clean_dev` + `run_ingestion`!
> Use fornecedor/tipo para reencontrar casos:

```powershell
# Buscar no CSV por fornecedor
Get-Content data/output/relatorio_lotes.csv | Select-String "GOX|COPASA|CEMIG|UFINET|TIM|CORREIOS"

# Validar extractores em todos os batches
python scripts/validate_extraction_rules.py --batch-mode --temp-email
```

**Referência completa:** Veja [`sessao_2026_01_30_nfse_sem_numero.md`](./sessao_2026_01_30_nfse_sem_numero.md)

---

### Snapshot: 29/01/2026 - 12:30 - CORRECAO_CONCLUIDA

**Tipo:** CORRECAO_CONCLUIDA

**Contexto da Sessão:**

- Orquestração iniciada em: 29/01/2026 08:44
- Correções concluídas: #1 e #2
- Tempo total: ~3 horas 46 minutos

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | CSV Atualizado | Validado |
|---|------|--------|---------------------|----------------|----------|
| 1 | TunnaFaturaExtractor | ✅ CONCLUÍDA | tunna_fatura.py, **init**.py | Sim (29/01) | 3 batches FishTV |
| 2 | Vencimento em Boletos | ✅ CONCLUÍDA | boleto.py | - | Função implementada |
| 3 | (próximas do JSON) | ⏳ PENDENTE | - | - | Aguardando |

**Correção #1: TunnaFaturaExtractor** ✅ CONCLUÍDA

- **Fornecedor:** TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA
- **Tipo:** FATURA COMERCIAL (tipo_documento="OUTRO", subtipo="FATURA")
- **Padrão de detecção:** "TUNNA" + "FATURA" OU "FAT/XXXXX"
- **Números processados:** 000.010.731, 000.010.732, 000.010.733
- **E-mail:** faturamento@fishtv.com.br
- **Referência temporal:** 3 batches processados em 29/01/2026

**Correção #2: Vencimento em Boletos** ✅ CONCLUÍDA

- **Problema:** Boletos com vencimento vazio no CSV
- **Solução:** Função `_decode_vencimento_from_linha_digitavel()` no BoletoExtractor
- **Como funciona:** Extrai fator de vencimento da linha digitável (posições 33-36) e calcula data
- **Considera reinício do fator:** A cada 10000 dias (a partir de 22/02/2025)
- **Fallback:** Usado quando vencimento não encontrado no texto
- **Arquivo modificado:** `extractors/boleto.py`
- **Testes:** Validados com basepyright e ruff ✅

**Estado do Sistema:**

- **Extractors no Registry:** 15 total (1 novo: TunnaFaturaExtractor)
- **Ordem do Registry:** ✅ ATUALIZADA
    - DanfeExtractor antes de NfseGenericExtractor
    - BoletoExtractor e SicoobExtractor antes de OutrosExtractor
- **Validate Script:** ✅ ATUALIZADO - Adicionado --temp-email e --batches
- **Código:** Validação basedpyright e ruff passando ✅

**Estado dos Dados:**

- **relatorio_lotes.csv:** Últimas entradas FishTV: 000.010.731, 000.010.732, 000.010.733
- **relatorio_consolidado.csv:** Novo fornecedor: TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA
- **Failed cases:** 0 novos (zero regressões confirmado)
- **✅ Nota:** Ordem do registry corrigida - boletos agora classificados corretamente como BOLETO

**Pendências Identificadas:**

1. ✅ Ordem do registry corrigida (BoletoExtractor antes de OutrosExtractor)
2. Próximas correções do JSON aguardando priorização
3. Commitar mudanças quando solicitado pelo usuário

**Decisões Tomadas:**

- FishTV são FATURAS COMERCIAIS (não fiscais) → usar tipo="OUTRO", subtipo="FATURA"
- OCR corrompe "Nº" para "N�" → usar regex tolerante `N[�º]?`
- Reordenar registry é preferível a regex complexo para DANFE vs NFSe
- Fator de vencimento em boletos: posições 33-36 da linha digitável, reinicia a cada 10000 dias

**Para Reencontrar em Nova Sessão:**

> ⚠️ **AVISO:** Batch IDs mudam a cada `clean_dev` + `run_ingestion`!
> Use fornecedor/tipo para reencontrar casos:

```powershell
# Opção 1: Buscar no CSV por fornecedor (SEMPRE funciona)
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA" | Select-Object -Last 5

# Opção 2: Validar extrator em todos os batches atuais
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# Opção 3: Procurar por padrão de assunto nos metadados
Get-ChildItem temp_email/ | ForEach-Object {
    $m = Get-Content "$($_.FullName)\metadata.json" | ConvertFrom-Json
    if ($m.subject -like "*FishTV*") { $_.Name }
}

# Opção 4: Buscar boletos com vencimento extraído
Get-Content data/output/relatorio_lotes.csv | Select-String "boleto" | Where-Object { $_ -match "vencimento" }
```

**Arquivos em Modificação:**

- [x] extractors/tunna_fatura.py (novo extrator)
- [x] extractors/boleto.py (função decode vencimento da linha digitável)
- [x] extractors/**init**.py (ordem do registry)
- [x] scripts/validate_extraction_rules.py (novas flags)
- [x] strategies/pdf_utils.py (logs revisados - evitar falsos positivos)
- [x] core/processor.py (logs revisados - reduzir verbosidade)
- [x] docs/context/\* (documentação atualizada - README, coding_standards, logging_guide, logging_standards, etc)

---

## 1. Objetivo do Projeto

Sistema para extração e processamento automatizado de documentos fiscais (DANFE, NFSe e Boletos) a partir de PDFs recebidos por e-mail. O sistema realiza:

- **Ingestão de e-mails** via IMAP
- **Extração de dados** de PDFs (texto nativo + OCR quando necessário)
- **Correlação automática** entre documentos (NF + Boleto)
- **Exportação** para Google Sheets e CSVs
- **Geração de relatórios** para controle de faturamento (PAF)

### Colunas Exportadas (Planilha PAF)

**Aba "anexos" (com PDF):**

- PROCESSADO | RECEBIDO | ASSUNTO | N_PEDIDO | EMPRESA | VENCIMENTO | FORNECEDOR | NF | VALOR | SITUACAO | AVISOS

**Aba "sem_anexos" (apenas link):**

- PROCESSADO | RECEBIDO | ASSUNTO | N_PEDIDO | EMPRESA | FORNECEDOR | NF | LINK | CODIGO

---

## 2. Arquitetura Geral

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   E-mail IMAP   │────▶│  Ingestão       │────▶│  Lotes/Temp     │
│   (Entrada)     │     │  (Ingestion     │     │  (Pastas com    │
│                 │     │   Service)      │     │   metadata.json)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐              │
│   CSVs/Saída    │◀────│  Exportação     │◀─────────────┘
│   (relatórios)  │     │  (Exporters)    │
└─────────────────┘     └─────────────────┘
                               ▲
                               │
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Google Sheets  │◀────│  Correlação     │◀────│  Processamento  │
│  (API)          │     │  (NF↔Boleto)    │     │  (Batch Proc.)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 3. Estrutura de Diretórios

```
config/              # Configurações (.env, settings.py, feriados, empresas, bancos)
  ├── settings.py         # Configurações principais
  ├── empresas.py         # Configuração de empresas
  ├── bancos.py           # Configuração de bancos
  └── feriados_sp.py      # Feriados de São Paulo
core/                # Núcleo do sistema
  ├── models.py           # Modelos de dados (InvoiceData, DanfeData, etc.)
  ├── batch_processor.py  # Processador de lotes
  ├── batch_result.py     # Resultados de processamento de lote
  ├── correlation_service.py  # Correlação NF↔Boleto
  ├── document_pairing.py     # Pareamento por número/valor
  ├── metadata.py         # Metadados do e-mail
  ├── empresa_matcher.py  # Detecção de empresa no texto
  ├── empresa_matcher_email.py  # Matcher específico para e-mails
  ├── exporters.py        # Exportação CSV/Drive
  ├── extractors.py       # Interface base de extratores
  ├── interfaces.py       # Interfaces do sistema
  ├── filters.py          # Filtros de processamento
  ├── processor.py        # Processador principal
  ├── diagnostics.py      # Diagnósticos do sistema
  ├── metrics.py          # Métricas de performance
  ├── exceptions.py       # Exceções customizadas
  └── __init__.py         # Inicialização do core

extractors/          # Extratores especializados por tipo
  ├── acimoc_extractor.py         # Boletos ACIMOC específicos
  ├── admin_document.py           # Documentos administrativos
  ├── aditivo_contrato.py         # Aditivos de contrato (ALARES, etc.)
  ├── boleto.py                   # Extrator genérico de boletos
  ├── boleto_gox.py               # Boletos GOX S.A. específicos
  ├── boleto_repromaq.py          # Extrator específico REPROMAQ
  ├── danfe.py                    # Extrator de DANFE (NF-e)
  ├── email_body_extractor.py     # Extrator de corpo de e-mail (sem anexos)
  ├── emc_fatura.py               # Faturas EMC Tecnologia
  ├── mugo_extractor.py           # Faturas MUGO Telecom
  ├── net_center.py               # NFSe específica Net Center
  ├── nfcom_telcables_extractor.py # NFCom/Telcables (faturas de telecom)
  ├── nfse_custom_montes_claros.py # NFSe Montes Claros-MG
  ├── nfse_custom_vila_velha.py   # NFSe Vila Velha-ES
  ├── nfse_generic.py             # Extrator genérico de NFSe
  ├── ocr_danfe.py                # DANFEs com OCR corrompido
  ├── outros.py                   # Documentos diversos (faturas)
  ├── pro_painel_extractor.py     # Faturas PRÓ - PAINEL LTDA
  ├── sicoob.py                   # Boletos Sicoob específicos
  ├── tunna_fatura.py             # Faturas FishTV/Tunna
  ├── ufinet.py                   # Faturas Ufinet
  ├── utility_bill.py             # Contas de utilidade (energia, água)
  ├── utils.py                    # Utilitários de extração
  └── xml_extractor.py            # Extração de XMLs fiscais

strategies/          # Estratégias de extração de texto
  ├── native.py           # PDF vetorial (pdfplumber)
  ├── ocr.py              # OCR (Tesseract)
  ├── table.py            # Extração de tabelas
  ├── fallback.py         # Fallback entre estratégias
  └── pdf_utils.py        # Utilitários PDF (senhas, etc.)

ingestors/           # Ingestão de e-mails
  ├── imap.py             # Cliente IMAP
  └── utils.py            # Utilitários

services/            # Serviços de alto nível
  ├── ingestion_service.py    # Orquestração de ingestão
  └── email_ingestion_orchestrator.py  # Checkpoint/resume

scripts/             # Ferramentas utilitárias
  ├── inspect_pdf.py          # Inspeção de PDFs
  ├── validate_extraction_rules.py  # Validação de regras
  ├── export_to_sheets.py     # Exportação para Google Sheets
  ├── analyze_logs.py               # Análise de logs do sistema
  ├── check_problematic_pdfs.py     # Verifica PDFs problemáticos
  ├── clean_dev.py                  # Limpa ambiente de dev
  ├── consolidate_batches.py        # Consolida lotes
  ├── diagnose_inbox_patterns.py    # Diagnostica padrões de inbox
  ├── example_batch_processing.py   # Exemplo de processamento
  ├── generate_report.py            # Gera relatórios
  ├── ingest_emails_no_attachment.py  # Ingestão sem anexo
  ├── list_problematic.py           # Lista casos problemáticos
  ├── repro_extraction_failure.py   # Reproduz falhas de extração
  ├── simple_list.py                # Listagem simples
  ├── test_admin_detection.py       # Testa detecção de admin
  ├── test_docker_setup.py          # Testa setup Docker
  ├── test_extractor_routing.py     # Testa roteamento de extratores
  └── _init_env.py                  # Inicialização de ambiente

temp_email/          # Pasta de lotes (criada dinamicamente)
data/
  ├── output/         # CSVs gerados
  └── debug_output/   # Relatórios de debug

failed_cases_pdf/    # PDFs para testes/validação
logs/                # Logs do sistema (scrapper.log)
```

---

## 4. Modelos de Dados Principais

### DocumentData (Classe Base)

Classe abstrata que define o contrato para todos os documentos:

- `arquivo_origem`, `data_processamento`, `empresa`, `setor`
- `batch_id`, `source_email_subject`, `source_email_sender`
- `email_date` - Data de recebimento do e-mail

### InvoiceData (NFSe)

Notas Fiscais de Serviço:

- `cnpj_prestador`, `fornecedor_nome`, `numero_nota`
- `valor_total`, `valor_ir`, `valor_inss`, `valor_csll`, `valor_iss`
- `vencimento`, `data_emissao`, `forma_pagamento`

### DanfeData (NF-e)

Notas Fiscais de Produto:

- Similar ao InvoiceData
- `chave_acesso` (44 dígitos)

### BoletoData

Boletos bancários:

- `linha_digitavel`, `codigo_barras`
- `vencimento`, `valor_documento`
- `referencia_nfse` (vinculação com NF)

### OtherDocumentData

Documentos diversos (faturas, ordens de serviço):

- `subtipo` (para categorização)
- `numero_documento`

### EmailAvisoData

E-mails sem anexo (apenas links):

- `link_nfe`, `codigo_verificacao`
- `email_subject_full`, `email_body_preview`

---

## 5. Extratores Registrados (Ordem de Prioridade)

A ordem de importação em `extractors/__init__.py` define a prioridade:

1. **BoletoRepromaqExtractor** - Boletos REPROMAQ/Bradesco (evita catastrophic backtracking)
2. **BoletoGoxExtractor** - Boletos GOX S.A. específicos
3. **EmcFaturaExtractor** - Faturas EMC Tecnologia (multi-página)
4. **NetCenterExtractor** - NFSe específica Net Center
5. **NfseCustomMontesClarosExtractor** - NFSe Montes Claros-MG
6. **NfseCustomVilaVelhaExtractor** - NFSe Vila Velha-ES
7. **UtilityBillExtractor** - Contas de utilidade (energia, água)
8. **NfcomTelcablesExtractor** - NFCom/Telcables (faturas de telecom)
9. **AcimocExtractor** - Boletos ACIMOC específicos
10. **MugoExtractor** - Faturas MUGO Telecom
11. **ProPainelExtractor** - Faturas PRÓ - PAINEL LTDA
12. **TunnaFaturaExtractor** - Faturas FishTV/Tunna
13. **UfinetExtractor** - Faturas Ufinet
14. **AdminDocumentExtractor** - Documentos administrativos (evita falsos positivos)
15. **ComprovanteBancarioExtractor** - Comprovantes TED/PIX/DOC
16. **OcrDanfeExtractor** - DANFEs com OCR corrompido (antes do DanfeExtractor)
17. **DanfeExtractor** - DANFE/DF-e genérico
18. **BoletoExtractor** - Boletos genéricos
19. **SicoobExtractor** - Boletos Sicoob
20. **AditivoContratoExtractor** - Aditivos de contrato (antes de OutrosExtractor)
21. **OutrosExtractor** - Documentos diversos (faturas, ordens de serviço)
22. **NfseGenericExtractor** - NFSe genérico (fallback)

**Nota:** Além dos extratores acima, o sistema também inclui:

- **EmailBodyExtractor** - Extração de corpo de e-mail (chamado diretamente, não via registry)
- **SabespWaterBillExtractor** - Faturas de água Sabesp via email body (chamado pelo BatchProcessor quando PDF encriptado)
- **XmlExtractor** - Extração de XMLs fiscais (chamado diretamente, não via registry)

**Regra:** Extratores específicos devem vir ANTES dos genéricos para evitar classificação incorreta.

---

## 6. Estratégias de Extração de Texto

### NativePdfStrategy

- Usa `pdfplumber` para extrair texto nativo do PDF
- Mais rápida (~90% dos casos)
- Suporte a PDFs protegidos por senha (tenta CNPJs)
- Fallback automático se extrair < 50 caracteres

### TesseractOcrStrategy

- Usa Tesseract OCR para PDFs em imagem
- Configuração: `--psm 6` (bloco único uniforme)
- Otimizado para números/códigos (desativa dicionários)

### TablePdfStrategy

- Preserva layout tabular para documentos estruturados
- Útil para boletos e documentos com colunas

### FallbackChain

- Orquestra múltiplas estratégias
- `HYBRID_OCR_COMPLEMENT`: combina nativo + OCR quando necessário

---

## 7. Fluxo de Processamento

### 7.1 Ingestão

```python
# 1. Conecta ao IMAP e baixa e-mails
# 2. Cria pasta em temp_email/ com formato: email_YYYYMMDD_HHMMSS_<hash>
# 3. Salva anexos e metadata.json
# 4. Registra checkpoint para resume
```

### 7.2 Processamento de Lote (Batch)

```python
# 1. Lê metadata.json
# 2. Prioriza XML se estiver completo (todos os campos obrigatórios)
# 3. Processa PDFs com estratégia de extração
# 4. Roteia para extrator apropriado (can_handle())
# 5. Aplica correlação entre documentos do mesmo lote
```

### 7.3 Correlação NF ↔ Boleto

```python
# 1. Pareamento por número da nota no nome do arquivo
# 2. Pareamento por referência no boleto (número documento)
# 3. Pareamento por valor (fallback)
# 4. Validação: valores devem conferir (com tolerância)
# 5. Herança de campos: NF herda vencimento do boleto, boleto herda fornecedor da NF
```

### 7.4 Exportação

```python
# Gera CSVs:
# - relatorio_nfse.csv
# - relatorio_boleto.csv
# - relatorio_danfe.csv
# - relatorio_outro.csv
# - relatorio_consolidado.csv (todos os documentos)
# - relatorio_lotes.csv (resumo por lote - uma linha por par NF↔Boleto)
```

---

## 8. Configurações Importantes (.env)

```bash
# E-mail (IMAP)
EMAIL_HOST=imap.gmail.com
EMAIL_USER=usuario@empresa.com
EMAIL_PASS=senha_app
EMAIL_FOLDER=INBOX

# Google Sheets
GOOGLE_SPREADSHEET_ID=1ABC...
GOOGLE_CREDENTIALS_PATH=credentials.json

# OCR (caminhos Windows/Linux)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\Poppler\...\bin

# Comportamento
HYBRID_OCR_COMPLEMENT=1  # Combina nativo + OCR
PAF_EXPORT_NF_EMPTY=0    # Exporta número NF na planilha
PAF_EXIGIR_NUMERO_NF=0   # Validação exige número NF

# Timeouts
BATCH_TIMEOUT_SECONDS=300
FILE_TIMEOUT_SECONDS=90
```

---

## 9. Scripts Principais

### run_ingestion.py

Script principal de orquestração:

```bash
python run_ingestion.py                    # Ingestão completa
python run_ingestion.py --reprocess        # Reprocessa lotes existentes
python run_ingestion.py --batch-folder X   # Processa pasta específica
python run_ingestion.py --cleanup          # Limpa lotes antigos (>48h)
python run_ingestion.py --status           # Mostra status do checkpoint
```

### scripts/inspect_pdf.py

Inspeção rápida de PDFs:

```bash
python scripts/inspect_pdf.py arquivo.pdf        # Campos extraídos
python scripts/inspect_pdf.py arquivo.pdf --raw  # Texto bruto
python scripts/inspect_pdf.py arquivo.pdf --batch # Análise de lote completo
```

### scripts/validate_extraction_rules.py

Validação de regras em lote:

```bash
python scripts/validate_extraction_rules.py --batch-mode --apply-correlation
```

### scripts/export_to_sheets.py

Exportação para Google Sheets:

```bash
python scripts/export_to_sheets.py              # Exporta relatorio_lotes.csv
python scripts/export_to_sheets.py --use-consolidado  # Modo detalhado
```

### scripts/analyze_logs.py

Análise de logs do sistema:

```bash
python scripts/analyze_logs.py                    # Análise completa
python scripts/analyze_logs.py --today            # Apenas logs de hoje
python scripts/analyze_logs.py --errors-only      # Apenas erros
python scripts/analyze_logs.py --batch <id>       # Buscar lote específico
python scripts/analyze_logs.py --summary          # Resumo estatístico
python scripts/analyze_logs.py --output report.md # Salvar relatório
```

---

## 10. Testes

```bash
# Rodar todos os testes
pytest

# Com cobertura
pytest --cov=.

# Testes específicos
pytest tests/test_energy_extractor.py -v
```

**Cobertura:** Testes abrangendo extratores, processamento, correlação e exportação.

---

## 11. Docker

```bash
# Build e run
docker-compose up --build

# Modo desenvolvimento (volume montado)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## 12. Pontos de Atenção / Documentação Desatualizada

### Documentação possivelmente desatualizada:

1. **docs/guide/** - Guias de uso podem não refletir flags mais recentes
2. **docs/development/** - Padrões de código podem estar desatualizados
3. **docs/api/** - APIs internas podem ter mudado
4. **README.md** - Seção de estrutura está simplificada

### Comportamentos importantes não documentados:

1. **Prioridade XML:** XML só é usado se tiver TODOS os campos obrigatórios (`fornecedor_nome`, `vencimento`, `numero_nota`, `valor_total`). Se incompleto, processa PDFs.

2. **UtilityBillExtractor:** Refatoração de EnergyBillExtractor (30/01/2026) para resolver conflito entre Carrier Telecom (empresa) e faturas de energia. Unifica ENERGY e WATER em um único extrator.

3. **AdminDocumentExtractor:** Extrator especializado para documentos administrativos com padrões negativos para evitar falsos positivos em documentos fiscais.

4. **AditivoContratoExtractor:** Criado (30/01/2026) para extrair dados de aditivos contratuais (ALARES, contratos de locação). Detecta pelo padrão "ADITIVO AO CONTRATO" + CNPJs conhecidos.

5. **OcrDanfeExtractor:** Criado (30/01/2026) para DANFEs com texto corrompido por OCR. Detecta padrões como "RECEHEMOS" (corrompido), "HINAT" e usa regex tolerantes.

6. **Sistema de Avisos:** A coluna AVISOS pode conter:
    - `[CONCILIADO]` - NF e boleto pareados com sucesso
    - `[DIVERGENTE]` - Campos faltando ou valores não conferem
    - `[VENCIMENTO_PROXIMO]` - Menos de 4 dias úteis
    - `[VENCIDO]` - Data de vencimento já passou
    - `[SEM ANEXO]` - E-mail sem PDF anexado

7. **Pareamento Inteligente:** Quando há múltiplas NFs no mesmo e-mail, o sistema gera uma linha no relatório para cada par NF↔Boleto (não uma linha por e-mail).

8. **Coluna RECEBIDO:** Nova coluna (adicionada 14/01/2026) que mostra a data de recebimento do e-mail, separada da data de processamento.

## 13. Dependências Principais

> **Nota:** Versões testadas e compatíveis. Atualizações devem ser validadas.

```
# Extração de PDF e texto
pdfplumber      # Extração nativa de PDF
pytesseract     # OCR
pdf2image       # Conversão PDF->imagem
pypdfium2       # Manipulação de PDF
pillow          # Processamento de imagens (PIL)

# Processamento de dados
pandas          # Processamento de CSV/DataFrames
python-dateutil # Manipulação de datas

# Configuração e ambiente
python-dotenv   # Carregamento de variáveis de ambiente

# Google Sheets API
gspread         # Integração com Google Sheets

# Utilitários
tenacity        # Retry automático para falhas
workalendar     # Cálculo de dias úteis e feriados

# Testes
pytest          # Framework de testes

# Análise estática (desenvolvimento)
basedpyright    # Verificação de tipos (opcional)

# Documentação (Netlify)
mkdocs          # Geração de documentação
mkdocs-material # Tema Material para MkDocs
mkdocstrings[python] # Documentação automática de código
mkdocs-encryptcontent-plugin # Plugin de criptografia
pymdown-extensions # Extensões Markdown
mkdocs-panzoom-plugin # Plugin zoom para imagens
```

---

## 14. Roadmap / To Do Atual

Baseado no README.md:

- [x] Script para automatizar análise de logs (`scripts/analyze_logs.py`)
- [x] Correções de tipos e qualidade de código (basedpyright/pyright) ✅
- [ ] Verificar funcionamento em container Docker
- [ ] Atualizar dados IMAP para e-mail da empresa (não de teste)
- [ ] Pesquisar APIs da OpenAI para OCR e validação
- [ ] Tratar casos de PDF não anexado (link de prefeitura/terceiros)

---

_Documento gerado automaticamente para manter contexto do projeto._
