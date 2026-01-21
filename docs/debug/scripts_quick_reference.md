# Scripts de Debug - Referência Rápida

Este documento fornece uma referência rápida aos scripts disponíveis na pasta `scripts/` para debugging e análise do sistema de extração.

## Estrutura de Scripts

Os scripts estão organizados em quatro categorias principais:

| Categoria | Scripts Principais | Propósito |
|-----------|-------------------|-----------|
| 📊 **Análise de Dados** | `analyze_admin_nfse.py`, `analyze_all_batches.py`, `list_problematic.py`, `simple_list.py` | Análise de lotes problemáticos, relatórios, identificação de padrões |
| 🔍 **Debug Específico** | `inspect_pdf.py`, `debug_pdf_text.py`, `check_problematic_pdfs.py`, `diagnose_ocr_issue.py` | Diagnóstico de problemas individuais, análise de texto, problemas OCR |
| 🧪 **Testes e Validação** | `test_extractor_routing.py`, `validate_extraction_rules.py`, `test_admin_detection.py` | Teste de extratores, validação de regras, detecção administrativa |
| 🔧 **Utilitários** | `export_to_sheets.py`, `ingest_emails_no_attachment.py`, `consolidate_batches.py` | Exportação, ingestão, consolidação, limpeza |

## Comandos Essenciais

### 1. **Debug Rápido de um PDF**
```bash
# Inspeção rápida de qualquer PDF (busca automaticamente em failed_cases_pdf/ e temp_email/)
python scripts/inspect_pdf.py arquivo.pdf

# Ver texto bruto para criar/ajustar regex
python scripts/inspect_pdf.py arquivo.pdf --raw

# Testar qual extrator seria usado
python scripts/test_extractor_routing.py caminho/completo/arquivo.pdf
```

### 2. **Identificar Lotes Problemáticos**
```bash
# Lista simples de lotes com "outros > 0 e valor = 0"
python scripts/simple_list.py

# Análise detalhada com classificação de problemas
python scripts/list_problematic.py

# Foco em NFSEs mal classificadas como administrativas
python scripts/analyze_admin_nfse.py
```

### 3. **Problemas de Qualidade de Texto/OCR**
```bash
# Diagnóstico específico do problema do caractere 'Ê'
python scripts/diagnose_ocr_issue.py

# Análise detalhada de texto extraído de PDF
python scripts/debug_pdf_text.py
```

### 4. **Validação após Modificações**
```bash
# Validação completa das regras de extração
python scripts/validate_extraction_rules.py --batch-mode

# Teste de detecção de documentos administrativos
python scripts/test_admin_detection.py
```

### 5. **Análise de E-mails e Padrões**
```bash
# Analisar e-mails sem anexo (identificar padrões úteis)
python scripts/analyze_emails_no_attachment.py --limit 100

# Diagnóstico de padrões na caixa de entrada
python scripts/diagnose_inbox_patterns.py --limit 200
```

## Referência por Tipo de Problema

| Problema | Script Primário | Scripts Adicionais | Observação |
|----------|-----------------|--------------------|------------|
| **Campo não extraído de PDF** | `inspect_pdf.py` | `debug_pdf_text.py` | Use `--raw` para ver texto completo |
| **NFSE classificada como "outros"** | `analyze_admin_nfse.py` | `check_problematic_pdfs.py` | Analisa casos específicos de valor zero |
| **Lote com status DIVERGENTE** | `list_problematic.py` | `simple_list.py` | Lista completa com comandos de reprocessamento |
| **Texto com caracteres estranhos (OCR)** | `diagnose_ocr_issue.py` | `debug_pdf_text.py` | Problema comum: 'Ê' substituindo espaços |
| **Erro de importação** | `diagnose_import_issues.py` | `test_docker_setup.py` | Diagnóstico de módulos e paths |
| **Extrator não selecionado** | `test_extractor_routing.py` | `inspect_pdf.py` | Testa roteamento de extratores |
| **Exportação para Google Sheets** | `export_to_sheets.py` | - | Exporta relatórios para planilha |
| **Limpeza de desenvolvimento** | `clean_dev.py` | - | Remove arquivos temporários |

## Fluxo de Trabalho Recomendado

### Caso 1: Um PDF não extrai campos corretamente
1. `python scripts/inspect_pdf.py arquivo.pdf --raw`
2. Analise o texto bruto, ajuste regex no extrator correspondente
3. `python scripts/test_extractor_routing.py arquivo.pdf` para verificar se o extrator correto é selecionado
4. `python scripts/validate_extraction_rules.py --batch-mode` para validar sem regressões

### Caso 2: Múltiplos lotes com problemas no CSV final
1. `python scripts/simple_list.py` para visão rápida
2. `python scripts/list_problematic.py` para análise detalhada
3. `python scripts/analyze_admin_nfse.py` para casos específicos de NFSE
4. `python scripts/check_problematic_pdfs.py` para análise dos PDFs problemáticos

### Caso 3: Qualidade de texto ruim (problemas OCR)
1. `python scripts/diagnose_ocr_issue.py` para diagnóstico específico
2. `python scripts/debug_pdf_text.py` para análise detalhada
3. Considere normalizar texto nos extratores (ex: `text.replace('Ê', ' ')`)

## Dicas Rápidas

### 1. **Sempre comece com `inspect_pdf.py`**
- Busca automaticamente em `failed_cases_pdf/` e `temp_email/`
- Mostra tipo, extrator e campos extraídos
- Flag `--raw` mostra texto completo para ajuste de regex

### 2. **Use `simple_list.py` para visão geral**
- Rápido e direto: mostra apenas batch IDs problemáticos
- Inclui comandos prontos para reprocessamento

### 3. **Valide após cada modificação**
- Sempre execute `validate_extraction_rules.py` após modificar extratores
- Use `--batch-mode` para validação completa

### 4. **Analise padrões recorrentes**
- Use `analyze_emails_no_attachment.py` para identificar e-mails úteis sem anexos
- `diagnose_inbox_patterns.py` ajuda a ajustar filtros de ingestão

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
# Análise periódica de todos os batches
python scripts/analyze_all_batches.py

# Validação completa das regras
python scripts/validate_extraction_rules.py --full-scan

# Análise de padrões de inbox (ajustar filtros)
python scripts/diagnose_inbox_patterns.py --all --resume
```

## Scripts Especiais para Casos Específicos

| Script | Caso de Uso Específico |
|--------|------------------------|
| `demo_pairing.py` | Demonstração do sistema de pareamento NF↔Boleto |
| `example_batch_processing.py` | Exemplo de processamento de lote completo |
| `repro_extraction_failure.py` | Reproduz falhas específicas de extração para debugging |
| `consolidate_batches.py` | Consolida resultados de múltiplos batches em um único relatório |

**Nota**: A maioria dos scripts aceita argumentos `--help` para ver opções específicas.

**Última atualização**: 2025-01-21  
**Localização**: `scrapper/scripts/`
