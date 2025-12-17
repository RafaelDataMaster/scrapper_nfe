# Referência da API

Esta seção documenta as classes e métodos internos do projeto, gerados automaticamente a partir do código fonte.

## Core (Núcleo)

Componentes fundamentais que definem as estruturas de dados e o fluxo de processamento.

::: core.processor.BaseInvoiceProcessor
    options:
      show_root_heading: true
      show_source: true

::: core.models.InvoiceData
    options:
      show_root_heading: true
      members_order: source

::: core.interfaces.TextExtractionStrategy
    options:
      show_root_heading: true

::: core.interfaces.EmailIngestorStrategy
    options:
      show_root_heading: true

::: core.exceptions
    options:
      show_root_heading: true

## Ingestors (Entrada de Dados)

Componentes responsáveis por conectar em fontes externas (e-mail, APIs) e trazer os dados para o sistema.

::: ingestors.imap.ImapIngestor
    options:
      show_root_heading: true
      show_source: true

## Strategies (Leitura)

Implementações responsáveis por transformar arquivos binários (PDF) em texto bruto.

::: strategies.fallback.SmartExtractionStrategy
::: strategies.native.NativePdfStrategy
::: strategies.ocr.TesseractOcrStrategy

## Extractors (Mineração)

Classes responsáveis por interpretar o texto bruto e extrair campos específicos.

::: core.extractors.BaseExtractor
::: extractors.generic.GenericExtractor

## Scripts Utilitários

Ferramentas de linha de comando para diagnóstico e manutenção do pipeline.

::: scripts.diagnose_failures
    options:
      show_root_heading: true

::: scripts.move_failed_files
    options:
      show_root_heading: true

::: scripts.test_rules_extractors
    options:
      show_root_heading: true
