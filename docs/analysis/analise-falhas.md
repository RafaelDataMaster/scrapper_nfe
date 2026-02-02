# Análise de Falhas de Extração

Este documento cataloga os padrões de falha mais comuns encontrados no sistema de extração e suas resoluções.

---

## 📊 Categorias de Falhas

### 1. Falhas de Extração de Campos

| Sintoma | Causa Provável | Solução |
| ------- | -------------- | ------- |
| Campo `valor_total` = 0 | Regex não encontrou padrão | Verificar texto com `inspect_pdf.py --raw` |
| Campo `numero_nota` vazio | Padrão OCR corrompido | Usar regex OCR-tolerante |
| Campo `vencimento` incorreto | Formato de data não reconhecido | Adicionar padrão em `parse_date_br()` |
| Campo `fornecedor_nome` errado | Extrator genérico capturou label | Criar extrator específico |

---

### 2. Falhas de Classificação

| Sintoma | Causa Provável | Solução |
| ------- | -------------- | ------- |
| NFSe classificada como "OUTRO" | Extrator genérico muito restritivo | Ajustar `can_handle()` |
| Fatura classificada como "NFSE" | Extrator genérico muito permissivo | Criar extrator específico |
| Boleto classificado como "NFSE" | Falta indicadores de boleto | Verificar padrões de linha digitável |
| DANFE não reconhecida | Chave de acesso corrompida | Usar `OcrDanfeExtractor` |

---

### 3. Falhas de OCR

| Sintoma | Causa Provável | Solução |
| ------- | -------------- | ------- |
| Caractere `�` no texto | OCR corrompeu caractere especial | Usar `[^\w\s]?` na regex |
| Números trocados (8↔9) | OCR confundiu dígitos similares | Validação com dígito verificador |
| Espaços como `Ê` | Codificação incorreta | `text.replace('Ê', ' ')` |
| Texto todo junto | PDF é imagem sem OCR | Forçar `TesseractOcrStrategy` |

---

### 4. Falhas de Registry/Prioridade

| Sintoma | Causa Provável | Solução |
| ------- | -------------- | ------- |
| Extrator específico não usado | Ordem incorreta no `__init__.py` | Mover específico antes do genérico |
| Múltiplos extratores aceitam | `can_handle()` muito permissivo | Tornar critérios mais específicos |
| Extrator nunca é chamado | Não registrado no `__init__.py` | Adicionar import e `__all__` |

---

## 🔍 Workflow de Diagnóstico

### Passo 1: Identificar o Problema

```bash
# Ver lotes com problemas
python scripts/simple_list.py

# Análise detalhada
python scripts/list_problematic.py
```

### Passo 2: Inspecionar Documento

```bash
# Ver campos extraídos
python scripts/inspect_pdf.py arquivo.pdf

# Ver texto bruto para debug de regex
python scripts/inspect_pdf.py arquivo.pdf --raw

# Testar qual extrator é usado
python scripts/test_extractor_routing.py arquivo.pdf
```

### Passo 3: Corrigir e Validar

```bash
# Após modificar extrator, validar
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# Validar apenas batches afetados (mais rápido)
python scripts/validate_extraction_rules.py --batch-mode --temp-email --batches batch1,batch2
```

---

## 📈 Histórico de Correções

### Correções Implementadas (2026-02)

| Data       | Problema                                    | Solução                        | Extrator                    |
| ---------- | ------------------------------------------- | ------------------------------ | --------------------------- |
| 02/02/2026 | CSC GESTAO classificada como NFSe sem nº    | Criado extrator específico     | `CscNotaDebitoExtractor`    |
| 02/02/2026 | Sabesp PDF protegido                        | Extração via email body        | `SabespWaterBillExtractor`  |
| 02/02/2026 | DANFE com OCR corrompido                    | Criado extrator tolerante      | `OcrDanfeExtractor`         |
| 30/01/2026 | Aditivos classificados incorretamente       | Criado extrator específico     | `AditivoContratoExtractor`  |
| 30/01/2026 | Regex de número de nota muito rígida        | Padrão OCR-tolerante           | Múltiplos                   |
| 29/01/2026 | Tunna/FishTV sem extrator                   | Criado extrator específico     | `TunnaFaturaExtractor`      |

---

## 🎯 Padrões de Regex OCR-Tolerantes

### Número de Documento

```python
# ❌ Falha com OCR
pattern = r"Nº\s*:\s*(\d+)"

# ✅ Tolerante
pattern = r"N[^\w\s]?\s*[:\.]\s*(\d+)"
```

### Valor Monetário

```python
# ❌ Falha com OCR
pattern = r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})"

# ✅ Tolerante
pattern = r"R[\$5S]?\s*([\d\.,]+)"
```

### CNPJ

```python
# ✅ Padrão robusto
pattern = r"(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})"
```

---

## 📋 Checklist de Análise

Ao investigar uma falha, verifique:

- [ ] Qual extrator foi selecionado? (`test_extractor_routing.py`)
- [ ] O texto bruto contém os dados esperados? (`inspect_pdf.py --raw`)
- [ ] A regex está capturando corretamente? (testar em regex101.com)
- [ ] O OCR corrompeu caracteres? (procurar `�`, `Ê`, etc.)
- [ ] O tipo de documento está correto? (NFSE/BOLETO/DANFE/OUTRO)
- [ ] Os campos obrigatórios estão preenchidos?

---

## 🔗 Ver Também

- [Troubleshooting](../guide/troubleshooting.md) - Soluções rápidas
- [Guia de Debug](../development/debugging_guide.md) - Workflows detalhados
- [Referência de Scripts](../debug/scripts_quick_reference.md) - Comandos essenciais
- [API Extractors](../api/extractors.md) - Lista completa de extratores

---

**Última atualização:** 2026-02-02
