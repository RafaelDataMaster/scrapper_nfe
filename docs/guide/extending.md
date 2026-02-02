# Guia de Extensão

O sistema foi projetado com uma arquitetura de plugins para facilitar a adição de novos layouts de documentos (prefeituras, bancos, etc.) sem a necessidade de modificar o núcleo do processador.

Este guia cobre:

1. Como adicionar novos extratores de NFS-e
2. Como trabalhar com boletos
3. Como integrar com o batch processing (v0.2.x)
4. Padrões de código SOLID e boas práticas
5. Logging adequado para debug
6. Tolerância a OCR corrompido

## Visão Geral

Cada prefeitura ou layout de nota fiscal é tratado por uma classe "Extratora" específica. O sistema utiliza um mecanismo de **Registro (Registry)** para descobrir automaticamente quais extratores estão disponíveis.

Para adicionar suporte a uma nova cidade, você precisa apenas criar um novo arquivo Python na pasta `extractors/` e implementar uma classe que herde de `BaseExtractor`.

## Passo a Passo

### 1. Crie o Arquivo do Extrator

Crie um novo arquivo em `extractors/`, por exemplo: `extractors/curitiba.py`.

### 2. Implemente a Classe

Use o modelo abaixo como base. É fundamental decorar a classe com `@register_extractor` para que ela seja reconhecida pelo sistema.

```python
"""
Extrator de NFSe da Prefeitura de Curitiba - PR.

Este módulo implementa a extração de dados específicos do layout de Curitiba.

Campos extraídos:
    - numero_nota: Número da NFS-e
    - valor_total: Valor total da nota
    - cnpj_prestador: CNPJ do prestador de serviços
    - data_emissao: Data de emissão

Identificação:
    - Termos: "PREFEITURA MUNICIPAL DE CURITIBA"
"""
import logging
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import normalize_text_for_extraction, parse_br_money, parse_date_br

# Obter logger para este módulo
logger = logging.getLogger(__name__)


@register_extractor
class CuritibaExtractor(BaseExtractor):
    """
    Extrator para Notas Fiscais de Serviço de Curitiba - PR.

    Identifica documentos pela presença de "PREFEITURA MUNICIPAL DE CURITIBA".
    Extrai número da nota, valor total, CNPJ e data de emissão.
    """

    # Padrões de regex (OCR-tolerantes)
    # Use [^\w\s]? para tolerar caracteres corrompidos pelo OCR
    PATTERN_NUMERO = r"N[^\w\s]?\s*(?:da\s+)?Nota[:\s]*(\d+)"
    PATTERN_VALOR = r"Valor\s+Total[:\s]*R?\$?\s*([\d\.,]+)"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Identifica se este é o extrator correto.

        Args:
            text: Texto extraído do PDF.

        Returns:
            True se o documento é de Curitiba.
        """
        if not text:
            logger.debug(f"{cls.__name__}: texto vazio, recusando")
            return False

        text_upper = text.upper()
        result = "PREFEITURA MUNICIPAL DE CURITIBA" in text_upper

        if result:
            logger.info(f"{cls.__name__} aceitou documento")
        else:
            logger.debug(f"{cls.__name__} recusou: padrão não encontrado")

        return result

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extrai os dados específicos do layout.

        Args:
            text: Texto extraído do PDF.

        Returns:
            Dicionário com dados extraídos.
        """
        logger.info(f"{self.__class__.__name__}.extract iniciado")

        text = normalize_text_for_extraction(text or "")

        data: Dict[str, Any] = {
            "tipo_documento": "NFSE",
        }

        # Extração de Número da Nota
        data["numero_nota"] = self._extract_numero(text)

        # Extração de Valor
        data["valor_total"] = self._extract_valor(text)

        # Extração de CNPJ
        data["cnpj_prestador"] = self._extract_cnpj(text)

        # Extração de Data
        data["data_emissao"] = self._extract_data(text)

        logger.info(f"Extração concluída com {len([v for v in data.values() if v])} campos preenchidos")
        return data

    def _extract_numero(self, text: str) -> Optional[str]:
        """Extrai número da nota com logging."""
        match = re.search(self.PATTERN_NUMERO, text, re.IGNORECASE)
        if match:
            numero = match.group(1)
            logger.info(f"Número extraído: {numero}")
            return numero
        logger.warning("Número da nota não encontrado")
        return None

    def _extract_valor(self, text: str) -> float:
        """Extrai valor total usando utils."""
        match = re.search(self.PATTERN_VALOR, text, re.IGNORECASE)
        if match:
            valor = parse_br_money(match.group(1))
            logger.info(f"Valor extraído: R$ {valor:.2f}")
            return valor
        logger.warning("Valor não encontrado")
        return 0.0

    def _extract_cnpj(self, text: str) -> Optional[str]:
        """Extrai CNPJ do prestador."""
        # Padrão: XX.XXX.XXX/XXXX-XX
        match = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", text)
        if match:
            cnpj = match.group(1)
            logger.info(f"CNPJ extraído: {cnpj}")
            return cnpj
        logger.debug("CNPJ não encontrado")
        return None

    def _extract_data(self, text: str) -> Optional[str]:
        """Extrai data de emissão."""
        match = re.search(r"Data\s+(?:de\s+)?Emiss[ãa]o[:\s]*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if match:
            data = parse_date_br(match.group(1))
            logger.info(f"Data extraída: {data}")
            return data
        logger.debug("Data de emissão não encontrada")
        return None
```

### 3. Teste o Novo Extrator

Basta colocar um PDF correspondente na pasta `nfs/` e rodar o `main.py`. O sistema irá:

1. Ler o texto do PDF.
2. Percorrer todos os extratores registrados.
3. Chamar `CuritibaExtractor.can_handle(texto)`.
4. Se retornar `True`, usará sua classe para extrair os dados.

## Dicas para Expressões Regulares (Regex)

### Básico

- Use `(?i)` no início da regex para ignorar maiúsculas/minúsculas.
- Use `\s*` para lidar com espaços variáveis entre o rótulo e o valor.
- Teste suas regex em sites como [regex101.com](https://regex101.com/).

### Tolerância a OCR

PDFs processados com OCR podem ter caracteres corrompidos. Use padrões tolerantes:

```python
# ❌ Regex rígido (falha com OCR)
pattern = r"Nº\s*:\s*(\d+)"

# ✅ Regex tolerante (funciona com OCR)
pattern = r"N[^\w\s]?\s*[:\.]\s*(\d+)"  # Aceita Nº, N., N�, etc.
```

**Padrões comuns de corrupção OCR:**

| Original | OCR pode gerar     | Solução              |
| -------- | ------------------ | -------------------- | --------- |
| `Nº`     | `N�`, `N.`, `N `   | `N[^\w\s]?`          |
| `R$`     | `R5`, `RS`, `R `   | `R[\$5S]?`           |
| `1`      | `l`, `I`, `        | `                    | `[1lI\|]` |
| `0`      | `O`, `o`           | `[0Oo]`              |
| espaço   | `Ê`, caractere 160 | `.replace('Ê', ' ')` |

## Prioridade de Execução (Registry)

O sistema verifica os extratores na ordem em que são importados em `extractors/__init__.py`.

**Regra fundamental:** Extratores específicos devem vir ANTES dos genéricos.

```python
# Em extractors/__init__.py
# ✅ Correto - Específico antes
from .curitiba import CuritibaExtractor          # Específico
from .nfse_generic import NfseGenericExtractor   # Genérico (fallback)

# ❌ Incorreto - Genérico primeiro
from .nfse_generic import NfseGenericExtractor   # Pega tudo!
from .curitiba import CuritibaExtractor          # Nunca chega aqui
```

### Onde Inserir Novo Extrator

1. **Extrator de fornecedor específico** (CNPJ único): No início, junto com outros específicos
2. **Extrator de tipo de documento**: Antes dos genéricos do mesmo tipo
3. **Extrator genérico/fallback**: No final

Consulte a [lista completa de extratores](../api/extractors.md) para ver a ordem atual.

---

## Integração com Batch Processing (v0.2.x)

A partir da v0.2.x, os extratores são chamados pelo `BatchProcessor` que fornece contexto adicional do e-mail. Isso permite correlação automática entre DANFE e Boleto.

### Acessando Contexto do Lote

Quando seu extrator é chamado dentro de um lote, você pode acessar metadados do e-mail:

```python
from core.batch_processor import process_email_batch
from core.metadata import EmailMetadata

# Processar um lote
result = process_email_batch("temp_email/email_123")

# Cada documento tem contexto do lote
for doc in result.all_documents:
    print(f"Batch ID: {doc.batch_id}")
    print(f"Email Subject: {doc.source_email_subject}")
    print(f"Email Sender: {doc.source_email_sender}")
```

### Usando Fallbacks do Metadata

Se seu extrator não conseguir extrair certos campos, o `CorrelationService` pode preencher com dados do e-mail:

```python
from core.correlation_service import correlate_batch

# Após processar o lote
correlation = correlate_batch(batch_result, metadata)

# Campos preenchidos automaticamente:
# - fornecedor_nome <- email_sender_name (se vazio)
# - cnpj <- extraído do email_body_text (se vazio)
# - vencimento <- herdado do boleto (para DANFE)
# - numero_nota <- herdado da DANFE (para boleto)
```

### Campos Disponíveis no Metadata

O arquivo `metadata.json` de cada lote contém:

| Campo                  | Descrição           | Uso Típico                |
| :--------------------- | :------------------ | :------------------------ |
| `batch_id`             | ID único do lote    | Rastreabilidade           |
| `email_subject`        | Assunto do e-mail   | Extrair número de pedido  |
| `email_sender_name`    | Nome do remetente   | Fallback para fornecedor  |
| `email_sender_address` | E-mail do remetente | Identificação             |
| `email_body_text`      | Corpo do e-mail     | Extrair CNPJ, referências |
| `received_date`        | Data de recebimento | Auditoria                 |
| `attachments`          | Lista de anexos     | Debug                     |

---

## Trabalhando com Boletos

O sistema agora identifica e processa **boletos bancários** automaticamente, separando-os de notas fiscais. Para cada boleto, extraímos:

### Campos Extraídos de Boletos

- **CNPJ do Beneficiário**: Quem está recebendo o pagamento
- **Valor do Documento**: Valor nominal do boleto
- **Data de Vencimento**: Quando deve ser pago (formato YYYY-MM-DD)
- **Número do Documento**: ID da fatura/documento
- **Linha Digitável**: Código de barras do boleto
- **Nosso Número**: Identificação interna do banco
- **Referência NFSe**: Número da nota fiscal (se mencionado no boleto)

### Vinculando Boletos a NFSe

#### Modo Automático (v0.2.x - Batch Processing)

A partir da v0.2.x, a correlação é automática quando DANFE e Boleto estão no mesmo lote:

```python
from core.batch_processor import process_email_batch
from core.correlation_service import correlate_batch
from core.metadata import EmailMetadata

# Processar lote com correlação
result = process_email_batch("temp_email/email_123")
metadata = EmailMetadata.load(Path("temp_email/email_123"))
correlation = correlate_batch(result, metadata)

# Verificar status
print(f"Status: {correlation.status}")  # OK, DIVERGENTE, ORFAO
print(f"Vencimento herdado: {correlation.vencimento_herdado}")
print(f"Número NF herdado: {correlation.numero_nota_herdado}")
```

#### Modo Manual (v0.1.x - Legado)

Você pode cruzar os dados dos boletos com as notas fiscais usando:

1. **Campo `referencia_nfse`**: Alguns boletos incluem explicitamente "Ref. NF 12345"
2. **Campo `numero_documento`**: Muitos fornecedores usam o número da NF como número do documento
3. **Cruzamento por dados**: Compare CNPJ + Valor + Data aproximada entre os dois CSVs

### Arquivos de Saída

O sistema gera dois CSVs separados:

- `relatorio_nfse.csv`: Contém todas as notas fiscais processadas
- `relatorio_boletos.csv`: Contém todos os boletos identificados

### Exemplo de Cruzamento com Pandas

```python
import pandas as pd

# Carregar os dois relatórios
df_nfse = pd.read_csv('data/output/relatorio_nfse.csv')
df_boleto = pd.read_csv('data/output/relatorio_boletos.csv')

# Vincular por referência explícita
merged = pd.merge(
    df_boleto,
    df_nfse,
    left_on='referencia_nfse',
    right_on='numero_nota',
    how='left'
)

# Ou vincular por número do documento
merged2 = pd.merge(
    df_boleto,
    df_nfse,
    left_on='numero_documento',
    right_on='numero_nota',
    how='left'
)
```

---

## Testando Seus Extratores

### Com o Script de Inspeção

Use `inspect_pdf.py` para ver rapidamente os campos extraídos:

```bash
# Ver todos os campos extraídos
python scripts/inspect_pdf.py seu_pdf_de_teste.pdf

# Ver campos específicos
python scripts/inspect_pdf.py seu_pdf_de_teste.pdf --fields numero_nota valor_total cnpj

# Ver texto bruto (para criar regex)
python scripts/inspect_pdf.py seu_pdf_de_teste.pdf --raw
```

### Com Validação em Lote

Valide seu extrator com múltiplos PDFs:

```bash
# Modo legado (PDFs soltos)
python scripts/validate_extraction_rules.py

# Modo batch (com correlação)
python scripts/validate_extraction_rules.py --batch-mode --apply-correlation
```

---

---

## Checklist para Novo Extrator

Antes de finalizar, verifique:

### Funcional

- [ ] `can_handle()` identifica corretamente o documento
- [ ] `can_handle()` NÃO aceita documentos de outros tipos
- [ ] `extract()` retorna todos os campos esperados
- [ ] Campos obrigatórios preenchidos (`tipo_documento`, `valor_total`)
- [ ] Regex são OCR-tolerantes
- [ ] Testado com PDFs reais do fornecedor

### Código (basedpyright)

- [ ] Type hints em todos os métodos públicos
- [ ] Docstrings em módulo, classe e métodos públicos
- [ ] Sem imports não usados
- [ ] Sem erros do basedpyright

### Logging

- [ ] Logger obtido no topo: `logger = logging.getLogger(__name__)`
- [ ] `can_handle()` loga decisão (DEBUG quando recusa, INFO quando aceita)
- [ ] `extract()` loga início e fim (INFO)
- [ ] Campos extraídos logados (INFO)
- [ ] Campos ausentes logados (WARNING)

### Integração

- [ ] Extrator registrado em `extractors/__init__.py`
- [ ] Ordem correta no registry (específico antes de genérico)
- [ ] Adicionado ao `__all__` do módulo
- [ ] Validação executada: `python scripts/validate_extraction_rules.py --batch-mode --temp-email`

---

## Próximos Passos

- [Guia de Debug](../development/debugging_guide.md) - Técnicas avançadas de debug de PDFs
- [Migração Batch](../development/MIGRATION_BATCH_PROCESSING.md) - Detalhes da migração v0.1.x → v0.2.x
- [API Reference](../api/overview.md) - Documentação técnica completa
- [Lista de Extratores](../api/extractors.md) - Todos os extratores disponíveis
