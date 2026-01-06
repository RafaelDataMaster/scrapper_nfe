# Guia de Migração: Processamento em Lote (Batch Processing)

Este documento descreve as mudanças introduzidas na refatoração do sistema de extração de documentos fiscais, migrando de um modelo de processamento por arquivo para processamento em lote (batch).

## Resumo das Mudanças

### Antes (v0.1.x)

- Processamento arquivo por arquivo
- Sem contexto do e-mail (assunto, remetente)
- Sem correlação entre documentos
- Arquivos soltos na pasta temporária

### Depois (v0.2.x)

- Processamento por lote (pasta de e-mail)
- Contexto completo do e-mail via `metadata.json`
- Correlação entre DANFE e Boleto
- Estrutura organizada em pastas por lote

---

## Nova Estrutura de Pastas

### Pasta Temporária (temp_email)

```
temp_email/
└── email_20251231_abc123/          <-- ID único por e-mail
    ├── metadata.json               <-- Contexto do e-mail
    ├── 01_danfe.pdf                <-- Numeração para ordenação
    ├── 02_boleto.pdf
    └── ignored/                    <-- (Opcional) Arquivos ignorados
        └── image001.png            <-- Assinaturas de e-mail
```

### Arquivo metadata.json

```json
{
    "batch_id": "email_20251231_abc123",
    "email_subject": "[NF] Nota Fiscal #12345 - Fornecedor LTDA",
    "email_sender_name": "Fornecedor LTDA",
    "email_sender_address": "nf@fornecedor.com.br",
    "email_body_text": "Segue em anexo a NF 12345. CNPJ: 12.345.678/0001-90",
    "received_date": "2025-01-15T10:30:00",
    "attachments": ["01_danfe.pdf", "02_boleto.pdf"],
    "created_at": "2025-01-15T10:35:22"
}
```

---

## Novos Módulos

### 1. `core/metadata.py` - EmailMetadata

Classe para gerenciar metadados do e-mail.

```python
from core.metadata import EmailMetadata

# Carregar de pasta existente
metadata = EmailMetadata.load(Path("temp_email/email_123"))

# Criar novo
metadata = EmailMetadata.create_for_batch(
    batch_id="email_123",
    subject="Nota Fiscal #123",
    sender_name="Fornecedor LTDA"
)

# Extrair dados do contexto
cnpj = metadata.extract_cnpj_from_body()
pedido = metadata.extract_numero_pedido_from_context()
fornecedor = metadata.get_fallback_fornecedor()
```

### 2. `core/batch_processor.py` - BatchProcessor

Processador de lotes que substitui o loop de arquivos.

```python
from core.batch_processor import BatchProcessor, process_email_batch

# Processar um lote
result = process_email_batch("temp_email/email_123")

# Processar múltiplos lotes
processor = BatchProcessor()
results = processor.process_multiple_batches("temp_email/")

# Processar arquivos legados (sem metadata)
result = processor.process_legacy_files("failed_cases_pdf/")
```

### 3. `core/batch_result.py` - BatchResult

Estrutura de resultado do processamento em lote.

```python
from core.batch_result import BatchResult

# Propriedades disponíveis
result.danfes          # Lista de DanfeData
result.boletos         # Lista de BoletoData
result.nfses           # Lista de InvoiceData
result.outros          # Lista de OtherDocumentData

result.has_danfe       # True se tem DANFE
result.has_boleto      # True se tem Boleto

result.get_valor_total_lote()      # Soma de todos os valores
result.get_valor_total_danfes()    # Soma só das DANFEs
result.get_valor_total_boletos()   # Soma só dos Boletos

result.to_summary()    # Dicionário com resumo do lote
```

### 4. `core/correlation_service.py` - CorrelationService

Serviço de correlação entre documentos do mesmo lote.

```python
from core.correlation_service import CorrelationService, correlate_batch

# Correlacionar um lote
correlation = correlate_batch(batch_result, metadata)

# Resultado
correlation.status           # "OK", "DIVERGENTE", "ORFAO"
correlation.divergencia      # Descrição do problema
correlation.vencimento_herdado    # Vencimento do boleto -> DANFE
correlation.numero_nota_herdado   # NF da DANFE -> Boleto
```

### 5. `services/ingestion_service.py` - IngestionService

Serviço de ingestão que organiza e-mails em lotes.

```python
from services.ingestion_service import IngestionService

service = IngestionService(ingestor, temp_dir=Path("temp_email"))

# Ingerir e-mails
batch_folders = service.ingest_emails(subject_filter="Nota Fiscal")

# Limpar lotes antigos (> 48h)
removed = service.cleanup_old_batches(max_age_hours=48)
```

---

## Campos Novos nos Models

### DocumentData (classe base)

```python
batch_id: Optional[str] = None              # ID do lote
source_email_subject: Optional[str] = None  # Assunto do e-mail
source_email_sender: Optional[str] = None   # Remetente do e-mail
valor_total_lote: Optional[float] = None    # Soma do lote
status_conciliacao: Optional[str] = None    # OK, DIVERGENTE, ORFAO
```

---

## Regras de Correlação Implementadas

### Regra 1: Herança de Dados

| Se o lote tem  | Campo faltando         | Herda de |
| -------------- | ---------------------- | -------- |
| DANFE + Boleto | Boleto sem numero_nota | DANFE    |
| DANFE + Boleto | DANFE sem vencimento   | Boleto   |
| NFSe + Boleto  | Boleto sem numero_nota | NFSe     |
| NFSe + Boleto  | NFSe sem vencimento    | Boleto   |

### Regra 2: Fallback de Identificação

| Campo faltando  | Fallback                         |
| --------------- | -------------------------------- |
| fornecedor_nome | email_sender_name do metadata    |
| cnpj            | CNPJ extraído do email_body_text |
| numero_pedido   | Pedido extraído do assunto/corpo |

### Regra 3: Validação Cruzada

| Situação                    | Status     |
| --------------------------- | ---------- |
| Valor DANFE = Valor Boletos | OK         |
| Valor DANFE ≠ Valor Boletos | DIVERGENTE |
| Só Boleto (sem nota)        | ORFAO      |

---

## Migração do Script de Validação

### Antes (v0.1.x)

```bash
python scripts/validate_extraction_rules.py
python scripts/validate_extraction_rules.py --validar-prazo --exigir-nf
```

### Depois (v0.2.x)

```bash
# Modo legado (compatível com v0.1.x)
python scripts/validate_extraction_rules.py

# Modo lote (nova estrutura)
python scripts/validate_extraction_rules.py --batch-mode

# Com correlação entre documentos
python scripts/validate_extraction_rules.py --batch-mode --apply-correlation

# Diretório customizado
python scripts/validate_extraction_rules.py --input-dir minha_pasta
```

---

## Migração do run_ingestion.py

### Antes (v0.1.x)

```bash
python run_ingestion.py
```

### Depois (v0.2.x)

```bash
# Ingestão padrão (usa nova estrutura de lotes)
python run_ingestion.py

# Reprocessar lotes existentes
python run_ingestion.py --reprocess

# Processar pasta específica
python run_ingestion.py --batch-folder temp_email/email_123

# Filtro de assunto customizado
python run_ingestion.py --subject "Nota Fiscal"

# Sem correlação
python run_ingestion.py --no-correlation

# Com limpeza automática
python run_ingestion.py --cleanup
```

---

## Docker: Serviço de Limpeza

Foi adicionado um serviço sidecar para limpeza automática:

```yaml
# docker-compose.yml
cleaner:
    image: alpine:latest
    container_name: scrapper_nfe_cleaner
    volumes:
        - temp_email:/app/temp_email
    command: >
        sh -c "while true; do
          find /app/temp_email -type f -mtime +2 -delete &&
          find /app/temp_email -type d -empty -delete &&
          sleep 86400;
        done"
```

**Política de retenção:** Arquivos com mais de 48 horas são automaticamente removidos.

---

## Remoção do NF_CANDIDATE

A lógica de `NF_CANDIDATE` foi removida do pipeline principal porque:

1. **Redundante:** O número da NF agora vem do contexto do e-mail (assunto/corpo)
2. **Correlação:** O `CorrelationService` herda o número entre documentos do mesmo lote
3. **Extratores:** Os extratores específicos já extraem o número da NF

O módulo `core/nf_candidate.py` foi mantido apenas para scripts de debug.

---

## Checklist de Migração

- [ ] Atualizar imports nos scripts customizados
- [ ] Usar `BatchProcessor` ao invés de loop manual de arquivos
- [ ] Usar `EmailMetadata` para contexto do e-mail
- [ ] Verificar campos novos nos models (`batch_id`, `source_email_*`, etc.)
- [ ] Atualizar Docker com serviço `cleaner` (se usar Docker)
- [ ] Testar com `--batch-mode` no script de validação

---

## Compatibilidade

| Feature                      | v0.1.x | v0.2.x     |
| ---------------------------- | ------ | ---------- |
| Processar arquivo individual | ✅     | ✅         |
| Processar pasta de arquivos  | ✅     | ✅         |
| Processar lote com metadata  | ❌     | ✅         |
| Correlação DANFE/Boleto      | ❌     | ✅         |
| Contexto do e-mail           | ❌     | ✅         |
| Limpeza automática           | Manual | Automática |

---

## Suporte

Em caso de dúvidas sobre a migração, consulte:

- `scripts/example_batch_processing.py` - Exemplos de uso
- `core/__init__.py` - Lista de exports disponíveis
- `docs/` - Documentação adicional
