# Padrões de Logging do Projeto

> **Objetivo:** Logs claros, estruturados e sem falsos positivos
> 
> **Problema atual:** Mensagens de "erro ao abrir PDF" quando há fallback bem-sucedido

---

## 1. Níveis de Log Corretos

### 🔴 ERROR - Erro Real (Falha Completa)

Use quando:
- O processamento do documento falhou completamente
- Não há fallback possível
- Dados críticos não puderam ser extraídos

```python
# ❌ ERRADO - Isto é apenas um fallback
logger.error(f"Erro ao abrir PDF {pdf_name} (pdfplumber)")

# ✅ CERTO - Apenas quando falha completamente
logger.error(f"Falha ao processar PDF {pdf_name}: nenhuma estratégia funcionou")
```

### 🟡 WARNING - Atenção (Mas Funcionou)

Use quando:
- Houve um problema MAS houve fallback bem-sucedido
- Dados parciais foram extraídos
- A estratégia primária falhou, mas secundária funcionou

```python
# ❌ ERRADO - Parece que falhou, mas tinha fallback
logger.warning(f"Erro ao abrir PDF {pdf_name} (pdfplumber)")

# ✅ CERTO - Deixa claro que houve fallback
logger.info(f"PDF {pdf_name}: pdfplumber falhou, usando OCR")
# Ou se não precisa de log:
logger.debug(f"PDF {pdf_name}: tentativa pdfplumber falhou, OCR funcionou")
```

### 🟢 INFO - Sucesso

Use quando:
- Processamento foi bem-sucedido
- Quer registrar milestone importante
- Extrator foi selecionado corretamente

```python
# ✅ CERTO
logger.info(f"Extrator {extrator.__name__} selecionado para {pdf_name}")
logger.info(f"Documento processado: {tipo} - {fornecedor} - R$ {valor}")
```

### 🔵 DEBUG - Detalhes

Use quando:
- Quer registrar tentativas individuais
- Detalhes de regex/parsing
- Fluxo interno do algoritmo

```python
# ✅ CERTO
logger.debug(f"Tentando extrair com padrão: {pattern}")
logger.debug(f"can_handle {extrator.__name__}: retornando {resultado}")
```

---

## 2. Mensagens de Log Claras

### ❌ Mensagens Confusas (ANTES)

```python
# Parece erro grave, mas é só fallback
logger.warning(f"Erro ao abrir PDF {pdf} (pdfplumber):")
logger.warning(f"Erro ao abrir PDF {pdf} (pypdfium2):")
logger.info(f"PDF aberto com OCR com sucesso")  # Última linha separada
```

**Resultado no log:**
```
WARNING - Erro ao abrir PDF fatura.pdf (pdfplumber):
WARNING - Erro ao abrir PDF fatura.pdf (pypdfium2):
INFO - PDF aberto com OCR com sucesso
```

**Interpretação:** "O PDF deu erro em tudo!" ❌ (falso positivo)

---

### ✅ Mensagens Claras (DEPOIS)

```python
# Uma única linha informando a estratégia usada
logger.info(f"PDF {pdf}: extraído com OCR (pdfplumber falhou)")
# Ou apenas no debug:
logger.debug(f"PDF {pdf}: pdfplumber falhou, OCR funcionou")
```

**Resultado no log:**
```
INFO - PDF fatura.pdf: extraído com OCR
```

**Ou se quiser detalhes:**
```
DEBUG - PDF fatura.pdf: pdfplumber falhou
DEBUG - PDF fatura.pdf: OCR funcionou
INFO  - PDF fatura.pdf: extração concluída com OCR
```

---

## 3. Estrutura de Log por Componente

### 3.1 Estratégias de Extração (strategies/)

```python
# strategies/pdf_utils.py - ao abrir PDF

# ❌ Antes (confuso)
logger.warning(f"Erro ao abrir PDF {filename} (pdfplumber): {e}")
logger.warning(f"Tentando pypdfium2...")
logger.warning(f"Erro ao abrir PDF {filename} (pypdfium2): {e}")
logger.info(f"PDF {filename} aberto com OCR")

# ✅ Depois (claro)
def extract_text_with_fallback(pdf_path):
    strategies_tried = []
    
    # Tenta pdfplumber
    try:
        text = extract_with_pdfplumber(pdf_path)
        logger.debug(f"PDF {pdf_path}: pdfplumber OK")
        return text
    except Exception as e:
        strategies_tried.append("pdfplumber")
        logger.debug(f"PDF {pdf_path}: pdfplumber falhou")
    
    # Tenta pypdfium2
    try:
        text = extract_with_pypdfium2(pdf_path)
        logger.info(f"PDF {pdf_path}: extraído com pypdfium2 (pdfplumber falhou)")
        return text
    except Exception as e:
        strategies_tried.append("pypdfium2")
        logger.debug(f"PDF {pdf_path}: pypdfium2 falhou")
    
    # Tenta OCR
    try:
        text = extract_with_ocr(pdf_path)
        logger.info(f"PDF {pdf_path}: extraído com OCR (outras falharam)")
        return text
    except Exception as e:
        logger.error(f"PDF {pdf_path}: TODAS as estratégias falharam: {strategies_tried}")
        raise
```

### 3.2 Roteador de Extratores (core/processor.py)

```python
# ❌ Antes
logger.info(f"Testando extrator: {extrator.__name__}")
logger.info(f"Resultado do can_handle: {resultado}")

# ✅ Depois
logger.debug(f"Router: {extrator.__name__}.can_handle = {resultado}")
if resultado:
    logger.info(f"Router: {extrator.__name__} selecionado")
else:
    logger.debug(f"Router: {extrator.__name__} recusou")
```

### 3.3 Extratores (extractors/*.py)

```python
# ❌ Antes
logger.info(f"{cls.__name__}.can_handle chamado")
logger.info(f"Resultado: {resultado}")

# ✅ Depois
logger.debug(f"{cls.__name__}.can_handle: {resultado}")
```

---

## 4. Categorias de Log

### 4.1 Log de Sucesso (INFO)

```
INFO - Router: BoletoExtractor selecionado
INFO - BoletoExtractor: processado - R$ 1.234,56 - Venc: 2026-01-20
INFO - CSV: relatorio_lotes.csv atualizado (150 linhas)
```

### 4.2 Log de Fallback (INFO/DEBUG)

```
# Quando fallback é normal/transparente
DEBUG - PDF fatura.pdf: pdfplumber falhou, OCR funcionou

# Quando fallback é importante notar
INFO - PDF fatura.pdf: extraído com OCR (apenas imagem disponível)
```

### 4.3 Log de Aviso (WARNING)

```
# Apenas quando há impacto real
WARNING - PDF fatura.pdf: texto parcial extraído (página 3/5 corrompida)
WARNING - BoletoExtractor: valor não encontrado, usando 0.0
WARNING - CSV: 3 linhas com vencimento vazio
```

### 4.4 Log de Erro (ERROR)

```
# Apenas quando falha completamente
ERROR - PDF fatura.pdf: todas as estratégias de extração falharam
ERROR - Extractor: erro inesperado em extract(), documento ignorado
```

---

## 5. Checklist de Revisão de Logs

Antes de commitar, verifique:

- [ ] Mensagens de "erro" são realmente erros (não fallbacks)
- [ ] Fallbacks bem-sucedidos são INFO ou DEBUG (não WARNING/ERROR)
- [ ] Logs de sucesso são informativos (tipo, fornecedor, valor)
- [ ] Não há logs duplicados (mesma info em 2 linhas)
- [ ] Logs de debug têm contexto suficiente para diagnóstico

---

## 6. Exemplo de Arquivo Revisado

### Antes (confuso)

```python
# strategies/pdf_utils.py
logger.info(f"Abrindo PDF: {pdf_path}")
try:
    text = pdfplumber.open(pdf_path).extract_text()
except Exception as e:
    logger.warning(f"Erro ao abrir PDF {pdf_path} (pdfplumber): {e}")
    try:
        text = pypdfium2.open(pdf_path).get_text()
    except Exception as e2:
        logger.warning(f"Erro ao abrir PDF {pdf_path} (pypdfium2): {e2}")
        text = ocr.extract(pdf_path)
        logger.info(f"PDF {pdf_path} aberto com OCR")
```

**Log resultante:**
```
INFO - Abrindo PDF: fatura.pdf
WARNING - Erro ao abrir PDF fatura.pdf (pdfplumber): ...
WARNING - Erro ao abrir PDF fatura.pdf (pypdfium2): ...
INFO - PDF fatura.pdf aberto com OCR
```

**Interpretação:** "O PDF deu 2 erros graves mas funcionou no final?" 🤔

---

### Depois (claro)

```python
# strategies/pdf_utils.py
logger.debug(f"PDF {pdf_path}: tentando pdfplumber")
try:
    text = pdfplumber.open(pdf_path).extract_text()
    logger.debug(f"PDF {pdf_path}: pdfplumber OK")
    return text
except Exception as e:
    logger.debug(f"PDF {pdf_path}: pdfplumber indisponível, tentando pypdfium2")

try:
    text = pypdfium2.open(pdf_path).get_text()
    logger.info(f"PDF {pdf_path}: extraído com pypdfium2")
    return text
except Exception as e:
    logger.debug(f"PDF {pdf_path}: pypdfium2 indisponível, usando OCR")

text = ocr.extract(pdf_path)
logger.info(f"PDF {pdf_path}: extraído com OCR")
return text
```

**Log resultante:**
```
INFO - PDF fatura.pdf: extraído com OCR
```

**Ou com debug ativado:**
```
DEBUG - PDF fatura.pdf: tentando pdfplumber
DEBUG - PDF fatura.pdf: pdfplumber indisponível, tentando pypdfium2
DEBUG - PDF fatura.pdf: pypdfium2 indisponível, usando OCR
INFO  - PDF fatura.pdf: extraído com OCR
```

**Interpretação:** "O PDF foi extraído com OCR (outras opções não funcionaram)" ✅

---

## 7. Implementação Gradual

### Prioridade 1 (Erros Críticos)
- [ ] `strategies/pdf_utils.py` - Remover warnings de fallback
- [ ] `strategies/ocr.py` - Logs apenas quando OCR é usado

### Prioridade 2 (Roteador)
- [ ] `core/processor.py` - Simplificar logs de seleção
- [ ] `core/batch_processor.py` - Resumo ao invés de detalhes

### Prioridade 3 (Extratores)
- [ ] Extratores com logs excessivos
- [ ] Extratores com logs confusos

---

## 8. Verificação de Logs

Após implementar, verifique:

```bash
# Deve retornar 0 (ou apenas erros reais)
grep -c "ERROR" logs/scrapper.log

# Deve ser baixo (apenas avisos importantes)
grep -c "WARNING" logs/scrapper.log

# Deve ser alto (processos bem-sucedidos)
grep -c "INFO" logs/scrapper.log

# Deve mostrar distribuição saudável
grep "extraído com" logs/scrapper.log | cut -d: -f3 | sort | uniq -c
```

---

**Quer que eu revise algum arquivo específico agora?**