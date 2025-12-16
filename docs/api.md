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

## Strategies (Leitura)

Implementações responsáveis por transformar arquivos binários (PDF) em texto bruto.

::: strategies.fallback.SmartExtractionStrategy
::: strategies.native.NativePdfStrategy
::: strategies.ocr.TesseractOcrStrategy

## Extractors (Mineração)

Classes responsáveis por interpretar o texto bruto e extrair campos específicos.

::: core.extractors.BaseExtractor
::: extractors.generic.GenericExtractor
