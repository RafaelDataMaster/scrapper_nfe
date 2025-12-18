# Extractors - Extratores de Dados

Os extratores são responsáveis por interpretar o texto bruto e extrair campos específicos de diferentes tipos de documentos.

## Visão Geral

Cada extrator implementa a interface `BaseExtractor` e é especializado em um tipo de documento:

- **GenericExtractor**: NFSe de qualquer prefeitura (baseado em regex)
- **BoletoExtractor**: Boletos bancários (linha digitável, vencimento, etc.)

**Padrão de Design:** Chain of Responsibility + Strategy

## GenericExtractor

Extrator genérico para Notas Fiscais de Serviço Eletrônica usando expressões regulares.

### Características

- **Prefeituras suportadas**: Todas (fallback genérico)
- **Método de extração**: Regex patterns
- **Campos extraídos**:
  - CNPJ do Prestador
  - Número da Nota Fiscal
  - Data de Emissão
  - Valor Total

### Lógica de Identificação

O `GenericExtractor` aceita qualquer documento que **não seja** um boleto bancário.

**Indicadores de rejeição:**
- Presença de "Linha Digitável"
- Palavras-chave de boleto: "Beneficiário", "Cedente", "Código de Barras"
- Padrão de linha digitável (5 blocos numéricos)

### Regex Patterns

O extrator usa uma hierarquia de padrões regex ordenados por especificidade:

1. **Número da Nota com contexto explícito**: `"Número da Nota: XXXXX"`
2. **NFS-e específico**: `"NFS-e Nº XXXXX"`
3. **Nota Fiscal genérico**: `"Nota Fiscal Nº XXXXX"`
4. **Número isolado** (com filtros para evitar RPS/Lote/Série)

### Limpeza de Texto

Antes da extração, o texto passa por limpeza:
- Remove datas (DD/MM/AAAA) para evitar confusão com números
- Remove identificadores auxiliares (RPS, Lote, Protocolo, Série)

::: extractors.generic.GenericExtractor
    options:
      show_root_heading: true
      show_source: false
      members:
        - can_handle
        - extract
        - _extract_cnpj
        - _extract_numero_nota
        - _extract_valor
        - _extract_data_emissao

---

## BoletoExtractor

Extrator especializado em boletos bancários brasileiros.

### Características

- **Tipo de documento**: Boletos bancários
- **Método de extração**: Regex + Heurísticas
- **Campos extraídos**:
  - CNPJ do Beneficiário
  - Valor do Documento
  - Data de Vencimento
  - Número do Documento
  - Linha Digitável (código de barras)
  - Nosso Número
  - Referência à NFSe (se presente)

### Lógica de Identificação

O `BoletoExtractor` identifica boletos através de:

**Indicadores positivos (score):**
- "Linha Digitável" / "Linha Digitavel"
- "Beneficiário" / "Beneficiario"
- "Vencimento"
- "Valor do Documento"
- "Nosso Número"
- "Código de Barras"
- "Agência/Código"
- "Cedente"

**Critério de aceitação:**
- Score ≥ 3 palavras-chave **OU** padrão de linha digitável detectado
- **E** ausência de palavras-chave de NFSe

### Campos Específicos

#### Linha Digitável

Formato padrão brasileiro:
```
XXXXX.XXXXX XXXXX.XXXXXX XXXXX.XXXXXX X XXXXXXXXXXXXXX
```

#### Vencimento

Convertido automaticamente para formato ISO (YYYY-MM-DD).

#### Referência à NFSe

Alguns boletos contêm referência à nota fiscal que os originou. O extrator tenta identificar:
- Padrão "NF 12345" ou "Nota 12345"
- Padrão "Referente à NFS-e XXXXX"

::: extractors.boleto.BoletoExtractor
    options:
      show_root_heading: true
      show_source: false
      members:
        - can_handle
        - extract
        - _extract_cnpj_beneficiario
        - _extract_valor
        - _extract_vencimento
        - _extract_linha_digitavel
        - _extract_numero_documento
        - _extract_nosso_numero
        - _extract_referencia_nfse

---

## Registro de Extratores

Os extratores são registrados automaticamente usando o decorator `@register_extractor`:

```python
from core.extractors import BaseExtractor, register_extractor

@register_extractor
class MeuExtrator(BaseExtractor):
    @classmethod
    def can_handle(cls, text: str) -> bool:
        # Lógica de identificação
        return "palavra-chave" in text.lower()
    
    def extract(self, text: str) -> Dict[str, Any]:
        # Lógica de extração
        return {"campo": "valor"}
```

O sistema automaticamente testa cada extrator registrado até encontrar um que aceite o documento.

---

## Fluxo de Roteamento

```mermaid
graph TB
    A[Texto Extraído] --> B{BoletoExtractor.can_handle?}
    B -->|Sim| C[BoletoExtractor.extract]
    B -->|Não| D{GenericExtractor.can_handle?}
    D -->|Sim| E[GenericExtractor.extract]
    D -->|Não| F[Erro: Nenhum extrator disponível]
    C --> G[BoletoData]
    E --> H[InvoiceData]
```

---

## Extensibilidade

Para adicionar suporte a um novo tipo de documento:

1. **Criar classe que herda de `BaseExtractor`**
2. **Implementar `can_handle()`** - Lógica de identificação
3. **Implementar `extract()`** - Lógica de extração
4. **Adicionar decorator `@register_extractor`**
5. **Criar modelo de dados** (se necessário)

### Exemplo: Extrator de Recibos

```python
from core.extractors import BaseExtractor, register_extractor
from dataclasses import dataclass

@dataclass
class ReciboData:
    arquivo_origem: str
    numero_recibo: str
    valor: float
    data: str

@register_extractor
class ReciboExtractor(BaseExtractor):
    @classmethod
    def can_handle(cls, text: str) -> bool:
        return "RECIBO" in text.upper() and "recebemos de" in text.lower()
    
    def extract(self, text: str) -> Dict[str, Any]:
        data = {}
        data['tipo_documento'] = 'RECIBO'
        data['numero_recibo'] = self._extract_numero(text)
        data['valor'] = self._extract_valor(text)
        return data
```

---

## Testes

Cada extrator possui testes unitários em [`tests/test_extractors.py`](../../tests/test_extractors.py):

```bash
python tests/test_extractors.py
```

**Cobertura de testes:**
- ✅ Identificação de tipo de documento (`can_handle`)
- ✅ Extração de campos individuais
- ✅ Integração com modelos de dados
- ✅ Edge cases (texto vazio, formatos inválidos)

---

## Ver Também

- [Core](core.md) - Classe base `BaseExtractor`
- [Strategies](strategies.md) - Extração de texto de PDFs
- [Diagnostics](diagnostics.md) - Validação de extrações
- [Guia de Testes](../guide/testing.md) - Como testar extratores
