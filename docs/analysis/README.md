# Análise de Problemas

Esta seção contém documentação sobre análise de falhas de extração e diagnósticos do sistema.

---

## 📋 Visão Geral

O sistema de extração pode encontrar diversos tipos de problemas durante o processamento de documentos. Esta seção documenta:

1. **Análise de Falhas** - Padrões de falha identificados e suas causas
2. **Diagnósticos** - Ferramentas e técnicas para identificar problemas
3. **Soluções** - Correções aplicadas e lições aprendidas

---

## 🔍 Tipos de Problemas Comuns

| Categoria              | Descrição                                        | Documentação                                    |
| ---------------------- | ------------------------------------------------ | ----------------------------------------------- |
| **Extração**           | Campos não extraídos ou extraídos incorretamente | [Análise de Falhas](analise-falhas.md)          |
| **Classificação**      | Documento classificado como tipo errado          | [Troubleshooting](../guide/troubleshooting.md)  |
| **OCR**                | Caracteres corrompidos pelo OCR                  | [Troubleshooting](../guide/troubleshooting.md)  |
| **PDFs protegidos**    | Documentos com senha desconhecida                | [Troubleshooting](../guide/troubleshooting.md)  |
| **Registry/Prioridade**| Extrator errado selecionado                      | [API Extractors](../api/extractors.md)          |

---

## 🛠️ Scripts de Diagnóstico

Os seguintes scripts auxiliam na análise de problemas:

```bash
# Identificar lotes problemáticos
python scripts/simple_list.py
python scripts/list_problematic.py

# Analisar PDFs específicos
python scripts/inspect_pdf.py arquivo.pdf --raw
python scripts/check_problematic_pdfs.py

# Validar extratores
python scripts/validate_extraction_rules.py --batch-mode --temp-email
python scripts/test_extractor_routing.py arquivo.pdf

# Analisar logs
python scripts/analyze_logs.py --today
python scripts/analyze_logs.py --errors-only
```

---

## 📊 Métricas de Qualidade

| Métrica                    | Alvo    | Como Medir                                         |
| -------------------------- | ------- | -------------------------------------------------- |
| Taxa de extração completa  | > 95%   | `campos_preenchidos / campos_totais`               |
| Taxa de classificação      | > 98%   | Documentos no tipo correto / total                 |
| Tempo médio por documento  | < 5s    | Logs de processamento                              |
| Erros de OCR               | < 5%    | Verificação manual de amostra                      |

---

## 🔗 Ver Também

- [Guia de Debug](../development/debugging_guide.md) - Workflows detalhados
- [Referência de Scripts](../debug/scripts_quick_reference.md) - Comandos essenciais
- [Troubleshooting](../guide/troubleshooting.md) - Soluções rápidas

---

**Última atualização:** 2026-02-02
