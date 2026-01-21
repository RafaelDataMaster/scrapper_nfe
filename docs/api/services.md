# Services

## Visão Geral

O módulo `services` contém serviços de alto nível que coordenam a lógica de negócio do sistema de extração de documentos fiscais. Estes serviços fornecem interfaces simplificadas para operações complexas como ingestão de e-mails e processamento de lotes.

## Services Disponíveis

### `IngestionService`

O serviço principal de ingestão que coordena o processo completo de baixar e-mails, extrair anexos, e criar estrutura de lotes.

**Características:**

- Conexão IMAP com provedores de e-mail
- Download de anexos PDF/XML
- Criação de estrutura de pastas de lote
- Geração de `metadata.json` com contexto do e-mail
- Limpeza automática de lotes antigos

**Métodos principais:**

- `download_email_attachments()`: Baixa anexos de um e-mail específico
- `create_batch_folder()`: Cria estrutura de pasta para um lote
- `process_inbox()`: Processa a caixa de entrada completa
- `cleanup_old_batches()`: Remove lotes processados após período configurado

### `BatchProcessingService`

Serviço auxiliar para operações de processamento em lote.

**Características:**

- Processamento paralelo de múltiplos lotes
- Validação de integridade de dados
- Geração de relatórios de processamento
- Retry automático para falhas transitórias

## Integração com Outros Módulos

O `IngestionService` utiliza:

1. **`ingestors.imap.ImapIngestor`** - Para comunicação com servidores de e-mail
2. **`core.batch_processor.BatchProcessor`** - Para processamento individual de lotes
3. **`core.correlation_service.CorrelationService`** - Para correlação de documentos
4. **`core.exporters.GoogleSheetsExporter`** - Para exportação de resultados

## Configuração

```python
from services.ingestion_service import IngestionService
from config import settings

# Criar serviço com configuração padrão
service = IngestionService()

# Configurar manualmente
service = IngestionService(
    email_host=settings.EMAIL_HOST,
    email_user=settings.EMAIL_USER,
    email_pass=settings.EMAIL_PASS,
    download_dir=settings.DIR_TEMP
)
```

## Exemplos de Uso

### Processar caixa de entrada completa

```python
from services.ingestion_service import IngestionService

service = IngestionService()
processed_batches = service.process_inbox(
    subject_filter="NOTA FISCAL",
    limit=50,
    mark_as_read=True
)

print(f"Processados {len(processed_batches)} lotes")
```

### Criar lote manualmente

```python
from services.ingestion_service import IngestionService
from core.metadata import EmailMetadata

service = IngestionService()

# Criar metadados do e-mail
metadata = EmailMetadata(
    subject="NF 12345 - FORNECEDOR XYZ",
    sender="fornecedor@xyz.com",
    date="2025-01-15 10:30:00",
    body="Segue NF em anexo..."
)

# Criar pasta do lote
batch_folder = service.create_batch_folder(metadata)
print(f"Lote criado em: {batch_folder}")
```

### Limpar lotes antigos

```python
from services.ingestion_service import IngestionService

service = IngestionService()
deleted_count = service.cleanup_old_batches(max_age_days=2)
print(f"Removidos {deleted_count} lotes antigos")
```

## Tratamento de Erros

O serviço implementa estratégias robustas de tratamento de erros:

1. **Retry automático**: Para falhas de conexão IMAP (3 tentativas)
2. **Fallback graceful**: Se falhar o download de um anexo, continua com os outros
3. **Logging detalhado**: Registra todos os passos para diagnóstico
4. **Validação de dados**: Verifica integridade antes de processar

## Performance

- **Processamento paralelo**: Até 5 lotes simultaneamente
- **Cache de conexão**: Mantém conexão IMAP aberta entre operações
- **Streaming de dados**: Processa e-mails em streaming para evitar estouro de memória
- **Limpeza incremental**: Remove arquivos temporários durante o processamento

## Ver Também

- [Batch Processing](batch.md) - BatchProcessor, CorrelationService
- [Core](core.md) - Modelos de dados
- [Guia de Ingestão](../guide/ingestion.md) - Configuração e uso
- [Migração Batch](../development/MIGRATION_BATCH_PROCESSING.md) - Guia de migração
