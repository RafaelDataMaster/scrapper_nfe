# Padrões de Código e Boas Práticas

Este guia define os padrões de código para o projeto de extração de documentos fiscais.

---

## 🛠️ Ferramentas

| Ferramenta    | Uso                          |
| ------------- | ---------------------------- |
| basedpyright  | Type checking                |
| ruff          | Linting e formatação         |
| Python        | 3.8+ (compatibilidade)       |
| Plataforma    | Windows (PowerShell)         |

---

## 1. Type Checking com basedpyright

### Regras de Type Hints

#### ✅ SEMPRE use type hints em:

**Parâmetros de métodos públicos:**

```python
# ✅ Correto
def extract(self, text: str) -> Dict[str, Any]:
    pass

# ❌ Incorreto
def extract(self, text):
    pass
```

**Retorno de métodos:**

```python
# ✅ Correto
@classmethod
def can_handle(cls, text: str) -> bool:
    return False

# ✅ Correto para Optional
def _extract_valor(self, text: str) -> Optional[float]:
    return None
```

**Variáveis em retorno complexo:**

```python
# ✅ Correto - tipagem explícita
data: Dict[str, Any] = {
    "tipo_documento": "OUTRO",
    "valor_total": 0.0
}
```

### Tratamento de Optional

```python
# ❌ Incorreto - pode gerar warning
return parse_date_br(match.group(1))  # match pode ser None

# ✅ Correto
if match:
    return parse_date_br(match.group(1))
return None
```

---

## 2. Princípios SOLID

### S - Single Responsibility Principle

> Cada extrator deve fazer UMA coisa bem: extrair dados de UM tipo específico de documento.

```python
# ✅ Correto
class TunnaFaturaExtractor(BaseExtractor):
    """Extrai APENAS faturas da Tunna."""
    pass

# ❌ Incorreto
class ExtratorUniversal(BaseExtractor):
    """Tenta extrair qualquer coisa."""
    def extract(self, text):
        if "TUNNA" in text: ...
        elif "EMC" in text: ...
        # 20 elifs
```

### O - Open/Closed Principle

> Aberto para extensão (novos extratores), fechado para modificação.

```python
# ✅ Correto - Novo arquivo para novo fornecedor
# extractors/novo_fornecedor.py
@register_extractor
class NovoFornecedorExtractor(BaseExtractor):
    pass

# ❌ Incorreto - Modificando extrator existente
class NfseGenericExtractor:
    def extract(self, text):
        if "FORNECEDOR_X" in text:  # Não! Crie extrator específico
            return {...}
```

### L - Liskov Substitution Principle

> Subclasses devem substituir a classe base sem quebrar o sistema.

```python
# ✅ Correto - retorna Dict compatível
def extract(self, text: str) -> Dict[str, Any]:
    return {"tipo_documento": "NFSE", "numero_nota": "123"}

# ❌ Incorreto - retorna tipo diferente
def extract(self, text: str) -> str:  # Viola LSP!
    return "dados"
```

### I - Interface Segregation Principle

> Clientes não devem depender de interfaces que não usam.

```python
class BaseExtractor(ABC):
    # Apenas 2 métodos obrigatórios
    @abstractmethod
    def can_handle(cls, text: str) -> bool: pass
    
    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]: pass
```

### D - Dependency Inversion Principle

> Dependa de abstrações, não de implementações concretas.

```python
# ✅ Correto - usa tipo abstrato
def process_document(extractor: BaseExtractor, text: str):
    return extractor.extract(text)
```

---

## 3. DRY - Don't Repeat Yourself (Com Cuidado!)

> ⚠️ DRY se aplica a REGRAS DE NEGÓCIO, não a lógica pura.

### ✅ APLIQUE DRY para Regras de Negócio

```python
# Em extractors/utils.py - compartilhado
def parse_br_money(value: str) -> float:
    """Converte valor monetário brasileiro para float."""
    if not value:
        return 0.0
    return float(value.replace(".", "").replace(",", "."))

def parse_date_br(value: str) -> Optional[str]:
    """Converte data brasileira para ISO."""
    ...
```

### ❌ NÃO Extraia Lógica Simples

```python
# OK repetir lógica simples em diferentes contextos
# NÃO crie: def converter_lista_strings_para_float(lista): ...
```

### Quando Extrair para `utils.py`

| Critério                       | Extrair? |
| ------------------------------ | -------- |
| Usado em 3+ extratores         | ✅ Sim   |
| É padrão do domínio (BR)       | ✅ Sim   |
| Regex compartilhada (CNPJ)     | ✅ Sim   |
| Usado em apenas 1-2 extratores | ❌ Não   |
| Lógica específica de contexto  | ❌ Não   |

---

## 4. Estrutura de Extratores

### Template Padrão

```python
"""
Extrator de [Tipo] da [Fornecedor].

Campos extraídos:
    - campo1: Descrição
    - campo2: Descrição

Identificação:
    - CNPJ: XX.XXX.XXX/XXXX-XX
    - Termos: "TERM1", "TERM2"
"""
import logging
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import parse_br_money, parse_date_br

logger = logging.getLogger(__name__)


@register_extractor
class MeuExtractor(BaseExtractor):
    """Extrator para [descrição curta]."""
    
    CNPJ_FORNECEDOR = "XX.XXX.XXX/XXXX-XX"
    
    @classmethod
    def can_handle(cls, text: str) -> bool:
        """Identifica se este é o extrator correto."""
        if not text:
            return False
        text_upper = text.upper()
        return "PADRAO" in text_upper
    
    def extract(self, text: str) -> Dict[str, Any]:
        """Extrai dados estruturados do documento."""
        logger.info(f"{self.__class__.__name__}.extract iniciado")
        
        data: Dict[str, Any] = {"tipo_documento": "OUTRO"}
        data["numero_documento"] = self._extract_numero(text)
        data["valor_total"] = self._extract_valor(text)
        
        return data
    
    def _extract_numero(self, text: str) -> Optional[str]:
        """Extrai número do documento."""
        ...
    
    def _extract_valor(self, text: str) -> float:
        """Extrai valor total."""
        ...
```

---

## 5. Padrões de Regex

### OCR-Tolerância

```python
# ❌ Regex rígido (falha com OCR)
pattern = r"Nº\s*:\s*(\d+)"

# ✅ Regex tolerante
pattern = r"N[^\w\s]?\s*[:\.]\s*(\d+)"  # Aceita Nº, N., N�, etc.
```

### Constantes de Padrão

```python
class MeuExtractor(BaseExtractor):
    PATTERN_NUMERO = r"N[^\w\s]?\s*[:\.]\s*(\d{3}\.\d{3}\.\d{3})"
    PATTERN_VALOR = r"TOTAL\s+R\$\s*([\d\.]+,\d{2})"
```

---

## 6. Documentação

### Formato Google Style

```python
def extract(self, text: str) -> Dict[str, Any]:
    """
    Extrai dados estruturados do documento.
    
    Args:
        text: Texto extraído do PDF.
        
    Returns:
        Dicionário com dados extraídos.
    """
```

### Seções Obrigatórias

1. **Módulo:** Descrição geral, campos, identificação
2. **Classe:** Propósito, critérios
3. **Métodos públicos:** Args, Returns
4. **Métodos privados:** Breve descrição

---

## 7. Checklist antes de Commit

```markdown
- [ ] basedpyright sem erros
- [ ] Type hints em todos os métodos públicos
- [ ] Docstrings em módulo, classe e métodos públicos
- [ ] Sem imports não usados
- [ ] Funções compartilhadas em utils.py
- [ ] Regex OCR-tolerantes
- [ ] Extrator registrado em __init__.py (ordem correta)
- [ ] Testes executados com validate_extraction_rules.py
```

---

## 8. Anti-Padrões Comuns

### ❌ Extrator "Faz Tudo"

```python
class ExtratorUniversal(BaseExtractor):
    def extract(self, text):
        # 200 linhas de if/elif/else
```

### ❌ Duplicação de Regras de Negócio

```python
# Mesma lógica de parse em 5 extratores
def _extrair_valor(self, text):
    return float(valor.replace(".", "").replace(",", "."))  # Deveria usar utils!
```

### ❌ Violação de LSP

```python
def extract(self, text: str) -> str:  # Deveria ser Dict!
    return "resultado"
```

---

## Ver Também

- [Como Estender](extending.md) - Template completo de extrator
- [Guia de Troubleshooting](troubleshooting.md) - Erros comuns
- [API Reference](../api/extractors.md) - Lista de extratores

---

**Última atualização:** 2026-02-02
