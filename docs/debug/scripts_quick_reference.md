# Scripts de Debug - Referência Rápida

Este documento fornece uma referência rápida aos scripts disponíveis na pasta `scripts/` para debugging e análise do sistema de extração.

## Script Principal

### `run_ingestion.py` - Orquestração Completa

Script principal que substitui a maioria das operações manuais:

```bash
# Ingestão completa (recomendado)
python run_ingestion.py

# Modos específicos
python run_ingestion.py --only-attachments      # Apenas com anexos
python run_ingestion.py --only-links             # Apenas sem anexos (links/códigos)

# Reprocessamento
python run_ingestion.py --reprocess              # Reprocessar todos os lotes
python run_ingestion.py --reprocess-timeouts     # Apenas lotes com timeout
python run_ingestion.py --batch-folder temp_email/email_xxx  # Pasta específica

# Gestão de estado
python run_ingestion.py --status                 # Ver status do checkpoint
python run_ingestion.py --export-partial         # Exportar dados parciais
python run_ingestion.py --fresh                  # Ignorar checkpoint (do zero)

# Manutenção
python run_ingestion.py --cleanup                # Limpar lotes antigos (>48h)
python run_ingestion.py --timeout 600            # Timeout customizado (10 min)
```

## Estrutura de Scripts

Os scripts estão organizados em quatro categorias principais:

| Categoria                 | Scripts Principais                                                                                                                              | Propósito                                                            |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 📊 **Análise de Dados**   | `list_problematic.py`, `simple_list.py`, `check_problematic_pdfs.py`, `generate_report.py`, `analyze_batch_health.py`, `analyze_report.py`      | Análise de lotes problemáticos, relatórios, identificação de padrões |
| 🔍 **Debug Específico**   | `inspect_pdf.py`, `diagnose_inbox_patterns.py`, `analyze_logs.py`                                                                               | Diagnóstico de problemas individuais, análise de texto e logs        |
| 🧪 **Testes e Validação** | `test_extractor_routing.py`, `validate_extraction_rules.py`, `test_admin_detection.py`                                                          | Teste de extratores, validação de regras, detecção administrativa    |
| 🔧 **Utilitários**        | `export_to_sheets.py`, `ingest_emails_no_attachment.py`, `consolidate_batches.py`, `clean_dev.py`, `extract_cases.py`, `extract_case_simple.py` | Exportação, ingestão, consolidação, limpeza, extração de casos       |

## Comandos Essenciais

### 1. **Debug Rápido de um PDF**

```bash
# Inspeção rápida de qualquer PDF (busca automaticamente em failed_cases_pdf/ e temp_email/)
python scripts/inspect_pdf.py arquivo.pdf

# Ver texto bruto para criar/ajustar regex
python scripts/inspect_pdf.py arquivo.pdf --raw

# Testar qual extrator seria usado
python scripts/test_extractor_routing.py caminho/completo/arquivo.pdf

# Analisar logs do dia
python scripts/analyze_logs.py --today
```

### 2. **Identificar Lotes Problemáticos**

```bash
# Lista simples de lotes com "outros > 0 e valor = 0"
python scripts/simple_list.py

# Análise detalhada com classificação de problemas
python scripts/list_problematic.py

# Análise dos PDFs problemáticos
python scripts/check_problematic_pdfs.py

# Analisar saúde dos batches
python scripts/analyze_batch_health.py
```

### 3. **Reprocessar Lotes**

```bash
# Reprocessar todos os lotes existentes
python run_ingestion.py --reprocess

# Reprocessar apenas lotes que deram timeout
python run_ingestion.py --reprocess-timeouts

# Processar pasta específica
python run_ingestion.py --batch-folder temp_email/email_20260125_xxx

# Com timeout maior (10 minutos)
python run_ingestion.py --reprocess --timeout 600
```

### 4. **Validação após Modificações**

```bash
# Validação completa das regras de extração
python scripts/validate_extraction_rules.py --batch-mode

# Teste de detecção de documentos administrativos
python scripts/test_admin_detection.py

# Teste de roteamento de extrator
python scripts/test_extractor_routing.py arquivo.pdf
```

### 5. **Análise de E-mails e Padrões**

```bash
# Diagnóstico de padrões na caixa de entrada
python scripts/diagnose_inbox_patterns.py --limit 200

# Ingestão de e-mails sem anexo (cria avisos)
python scripts/ingest_emails_no_attachment.py --limit 50

# Extrair casos para análise
python scripts/extract_cases.py
python scripts/extract_case_simple.py
```

### 6. **Manutenção e Limpeza**

```bash
# Limpar arquivos temporários de desenvolvimento
python scripts/clean_dev.py

# Limpar lotes antigos após processamento
python run_ingestion.py --cleanup

# Ver status do sistema
python run_ingestion.py --status
```

## Referência por Tipo de Problema

| Problema                                 | Script Primário                | Scripts Adicionais                      | Observação                                     |
| ---------------------------------------- | ------------------------------ | --------------------------------------- | ---------------------------------------------- |
| **Campo não extraído de PDF**            | `inspect_pdf.py`               | `test_extractor_routing.py`             | Use `--raw` para ver texto completo            |
| **NFSE classificada como "outros"**      | `check_problematic_pdfs.py`    | `list_problematic.py`                   | Analisa casos específicos de valor zero        |
| **Lote com status DIVERGENTE**           | `list_problematic.py`          | `simple_list.py`                        | Lista completa com comandos de reprocessamento |
| **Texto com caracteres estranhos (OCR)** | `inspect_pdf.py --raw`         | `validate_extraction_rules.py`          | Use validação após ajustar regex               |
| **Extrator não selecionado**             | `test_extractor_routing.py`    | `inspect_pdf.py`                        | Testa roteamento de extratores                 |
| **Reprocessar após erro**                | `run_ingestion.py --reprocess` | `run_ingestion.py --reprocess-timeouts` | Resume automaticamente do checkpoint           |
| **Exportação para Google Sheets**        | `export_to_sheets.py`          | -                                       | Exporta relatórios para planilha               |
| **Limpeza de desenvolvimento**           | `clean_dev.py`                 | `run_ingestion.py --cleanup`            | Remove arquivos temporários                    |

## Fluxo de Trabalho Recomendado

### Caso 1: Um PDF não extrai campos corretamente

1. `python scripts/inspect_pdf.py arquivo.pdf --raw`
2. Analise o texto bruto, ajuste regex no extrator correspondente
3. `python scripts/test_extractor_routing.py arquivo.pdf` para verificar se o extrator correto é selecionado
4. `python scripts/validate_extraction_rules.py --batch-mode` para validar sem regressões

### Caso 2: Múltiplos lotes com problemas no CSV final

1. `python scripts/simple_list.py` para visão rápida
2. `python scripts/list_problematic.py` para análise detalhada
3. `python scripts/check_problematic_pdfs.py` para análise dos PDFs problemáticos
4. `python run_ingestion.py --reprocess` para reprocessar lotes corrigidos

### Caso 3: Ingestão interrompida ou com timeout

1. `python run_ingestion.py --status` - verificar estado atual
2. `python run_ingestion.py` - resume automaticamente do checkpoint
3. Ou `python run_ingestion.py --export-partial` - exportar dados já processados
4. `python run_ingestion.py --reprocess-timeouts` - tentar lotes com timeout novamente

### Caso 4: Qualidade de texto ruim (problemas OCR)

1. `python scripts/inspect_pdf.py arquivo.pdf --raw` para análise do texto extraído
2. Ajuste regex no extrator ou normalize texto (ex: `text.replace('Ê', ' ')`)
3. `python scripts/validate_extraction_rules.py` para validar correções

## Dicas Rápidas

### 1. **Sempre verifique o status primeiro**

```bash
python run_ingestion.py --status
```

Mostra se há dados parciais, lotes pendentes ou checkpoints para resumir.

### 2. **Use `inspect_pdf.py` para debug de PDFs**

- Busca automaticamente em `failed_cases_pdf/` e `temp_email/`
- Mostra tipo, extrator e campos extraídos
- Flag `--raw` mostra texto completo para ajuste de regex

### 3. **Use `simple_list.py` para visão geral**

- Rápido e direto: mostra apenas batch IDs problemáticos
- Inclui comandos prontos para reprocessamento

### 4. **Valide após cada modificação**

- Sempre execute `validate_extraction_rules.py` após modificar extratores
- Use `--batch-mode` para validação completa

### 5. **Use o `run_ingestion.py` como ferramenta principal**

- Substitui a maioria das operações manuais
- Possui checkpointing automático (resume após interrupção)
- Exporta dados parciais automaticamente

## Estrutura de Diretórios Relevante

```
scrapper/
├── scripts/                    # Todos os scripts de debug
├── data/
│   ├── output/                # Relatórios (relatorio_lotes.csv, etc.)
│   ├── debug_output/          # Outputs de scripts de debug
│   └── cache/                 # Cache de processamento
├── temp_email/                # Lotes de e-mail processados
├── failed_cases_pdf/          # PDFs de falha para análise
└── tests/                     # Testes unitários
```

## Monitoramento Contínuo

Para manter a saúde do sistema:

```bash
# Validação completa das regras
python scripts/validate_extraction_rules.py --batch-mode

# Análise de padrões de inbox (ajustar filtros)
python scripts/diagnose_inbox_patterns.py --all --resume

# Geração de relatórios
python scripts/generate_report.py

# Limpeza periódica
python scripts/clean_dev.py
```

## Scripts Disponíveis (Lista Completa)

Lista atualizada de todos os scripts na pasta `scripts/`:

| Script                           | Descrição                                                             |
| -------------------------------- | --------------------------------------------------------------------- |
| `_init_env.py`                   | Configuração de paths para importação de módulos                      |
| `analyze_batch_health.py`        | Análise de saúde dos batches processados                              |
| `analyze_logs.py`                | Análise de logs do sistema                                            |
| `analyze_report.py`              | Análise de relatórios gerados                                         |
| `check_problematic_pdfs.py`      | Análise de PDFs problemáticos                                         |
| `clean_dev.py`                   | Limpeza de arquivos temporários de desenvolvimento                    |
| `consolidate_batches.py`         | Consolidação de resultados de múltiplos batches                       |
| `diagnose_inbox_patterns.py`     | Análise de padrões de e-mail na caixa de entrada                      |
| `example_batch_processing.py`    | Exemplo de processamento de lote completo                             |
| `export_to_sheets.py`            | Exportação para Google Sheets                                         |
| `extract_case_simple.py`         | Extração simples de casos para análise                                |
| `extract_cases.py`               | Extração de casos para análise                                        |
| `generate_report.py`             | Geração de relatório pyright JSON→Markdown                            |
| `ingest_emails_no_attachment.py` | Ingestão de e-mails sem anexos                                        |
| `inspect_pdf.py`                 | Inspeção rápida de PDFs (campos, texto bruto)                         |
| `list_problematic.py`            | Lista detalhada de lotes problemáticos                                |
| `repro_extraction_failure.py`    | Reprodução de falhas de extração                                      |
| `simple_list.py`                 | Lista simples de lotes problemáticos                                  |
| `test_admin_detection.py`        | Teste de detecção de documentos administrativos                       |
| `test_docker_setup.py`           | Teste de configuração Docker                                          |
| `test_extractor_routing.py`      | Teste de roteamento de extratores                                     |
| `validate_extraction_rules.py`   | Validação de regras de extração (suporta `--temp-email`, `--batches`) |

## Referência de Comandos do `run_ingestion.py`

| Flag                   | Descrição                                 |
| ---------------------- | ----------------------------------------- |
| `--only-attachments`   | Apenas e-mails COM anexos                 |
| `--only-links`         | Apenas e-mails SEM anexos (links/códigos) |
| `--reprocess`          | Reprocessar lotes existentes              |
| `--reprocess-timeouts` | Reprocessar apenas lotes com timeout      |
| `--batch-folder PATH`  | Processar pasta específica                |
| `--subject FILTER`     | Filtro de assunto (default: \*)           |
| `--no-correlation`     | Desabilitar correlação entre documentos   |
| `--cleanup`            | Limpar lotes antigos (>48h)               |
| `--timeout SECONDS`    | Timeout por lote (default: 300)           |
| `--fresh`              | Ignorar checkpoint (do zero)              |
| `--status`             | Ver status do checkpoint                  |
| `--export-partial`     | Exportar dados parciais                   |
| `--max-emails N`       | Limite máximo de e-mails                  |
| `--links-first`        | Processar sem anexo antes                 |
| `--export-metrics`     | Exportar métricas de telemetria           |

**Nota**: A maioria dos scripts aceita argumentos `--help` para ver opções específicas.

**Última atualização**: 2026-02-02  
**Localização**: `scrapper/scripts/`
