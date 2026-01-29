# Padrões de Código e Boas Práticas

> **Ferramentas:** basedpyright (type checking), ruff (linting - via .ruff_cache)  
> **Python:** 3.8+ | **Plataforma:** Windows  
> **Arquitetura:** SOLID principles com adaptações práticas

---

## 1. Type Checking com basedpyright

### Configuração do Projeto (`pyrightconfig.json`)

```json
{
    "typeCheckingMode": "basic",
    "pythonVersion": "3.8",
    "pythonPlatform": "Windows",
    "reportMissingImports": true,
    "reportUnusedImport": "warning",
    "reportUnusedClass": "warning",
    "reportUnusedFunction": "warning",
    "reportUnusedVariable": "warning"
}
```

### Regras de Type Hints Obrigatórias

#### ✅ SEMPRE use type hints em:

1. **Parâmetros de métodos públicos:**
```python
# ✅ Correto
def extract(self, text: str) -> Dict[str, Any]:
    pass

# ❌ Incorreto
def extract(self, text):  # Sem type hints
    pass
```

2. **Retorno de métodos:**
```python
# ✅ Correto
@classmethod
def can_handle(cls, text: str) -> bool:
    return False

# ✅ Correto para Optional
def _extract_valor(self, text: str) -> Optional[float]:
    return None
```

3. **Variáveis em retorno complexo:**
```python
# ✅ Correto - tipagem explícita
data: Dict[str, Any] = {
    "tipo_documento": "OUTRO",
    "valor_total": 0.0
}

# ✅ Correto - type inference permitido
numero = self._extract_numero(text)  # Optional[str] inferido
```

#### ⚠️ Atenção aos Warnings do basedpyright

| Warning | Significado | Ação |
|---------|-------------|------|
| `reportUnusedImport` | Import não usado | Remova ou use |
| `reportUnusedFunction` | Função/método não chamado | Verifique se é realmente necessário |
| `reportOptionalSubscript` | Acesso a item de Optional | Use `if x is not None:` ou `x.get()` |
| `reportOptionalMemberAccess` | Acesso a método de Optional | Verifique None antes |

#### Exemplo de tratamento de Optional:

```python
# ❌ Incorreto - pode gerar warning
return parse_date_br(match.group(1))  # match pode ser None

# ✅ Correto - verificação explícita
if match:
    return parse_date_br(match.group(1))
return None
```

---

## 2. Princípios SOLID

### S - Single Responsibility Principle (SRP)

> **Cada extrator deve fazer UMA coisa bem: extrair dados de UM tipo específico de documento.**

#### ✅ Correto:
```python
class TunnaFaturaExtractor(BaseExtractor):
    """Extrai APENAS faturas da Tunna."""
    
    def can_handle(self, text: str) -> bool:
        # Apenas verifica se é Tunna
        return "TUNNA" in text.upper()
    
    def extract(self, text: str) -> Dict[str, Any]:
        # Apenas extrai dados de fatura Tunna
        return {...}
```

#### ❌ Incorreto (viola SRP):
```python
class ExtratorUniversal(BaseExtractor):
    """Tenta extrair qualquer coisa."""
    
    def extract(self, text: str) -> Dict[str, Any]:
        # Lógica gigante tentando detectar e extrair tudo
        if "TUNNA" in text:
            return self._extract_tunna(text)
        elif "EMC" in text:
            return self._extract_emc(text)
        # ... mais 20 elifs
```

### O - Open/Closed Principle (OCP)

> **Aberto para extensão (novos extratores), fechado para modificação (extratores existentes).**

#### ✅ Correto:
```python
# Para adicionar novo fornecedor, crie NOVO arquivo:
# extractors/novo_fornecedor.py

@register_extractor
class NovoFornecedorExtractor(BaseExtractor):
    # Novo extrator sem modificar existentes
    pass

# Atualize apenas __init__.py para importar (registry order)
```

#### ❌ Incorreto (viola OCP):
```python
# Modificando extrator existente para lidar com caso novo
class NfseGenericExtractor(BaseExtractor):
    def extract(self, text: str) -> Dict[str, Any]:
        # Adicionando código específico para fornecedor X
        if "FORNECEDOR_X" in text:
            return {...}  # Não! Crie extrator específico
```

### L - Liskov Substitution Principle (LSP)

> **Subclasses devem poder substituir a classe base sem quebrar o sistema.**

#### ✅ Correto:
```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        """Retorna dicionário com dados estruturados."""
        pass

@register_extractor
class MeuExtractor(BaseExtractor):
    def extract(self, text: str) -> Dict[str, Any]:
        # Retorna estrutura compatível
        return {
            "tipo_documento": "NFSE",
            "numero_nota": "123",
            "valor_total": 100.0
        }
```

#### ❌ Incorreto (viola LSP):
```python
@register_extractor
class MeuExtractor(BaseExtractor):
    def extract(self, text: str) -> str:  # ❌ Retorna str, não Dict!
        return "dados extraídos"
```

### I - Interface Segregation Principle (ISP)

> **Clientes não devem depender de interfaces que não usam.**

Cada extrator implementa apenas os métodos que precisa:

```python
class BaseExtractor(ABC):
    @abstractmethod
    def can_handle(cls, text: str) -> bool:
        pass
    
    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        pass
    # Apenas 2 métodos obrigatórios - extrator não precisa implementar mais nada
```

Métodos auxiliares são PRIVADOS e específicos:
```python
class TunnaFaturaExtractor(BaseExtractor):
    # Métodos públicos obrigatórios
    def can_handle(cls, text: str) -> bool: ...
    def extract(self, text: str) -> Dict[str, Any]: ...
    
    # Métodos privados específicos deste extrator
    def _extract_numero_fatura(self, text: str) -> Optional[str]: ...
    def _extract_valor(self, text: str) -> float: ...
    def _extract_data_emissao(self, text: str) -> Optional[str]: ...
```

### D - Dependency Inversion Principle (DIP)

> **Dependa de abstrações, não de implementações concretas.**

#### ✅ Correto:
```python
# core/extractors.py define a abstração
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        pass

# Extratores concretos dependem da abstração
class TunnaFaturaExtractor(BaseExtractor):
    def extract(self, text: str) -> Dict[str, Any]:
        ...

# Sistema usa a abstração
from core.extractors import BaseExtractor

def process_document(extractor: BaseExtractor, text: str):  # Tipo abstrato
    return extractor.extract(text)
```

---

## 3. DRY - Don't Repeat Yourself (COM CUIDADO!)

> ⚠️ **IMPORTANTE:** DRY se aplica a REGRAS DE NEGÓCIO, não a lógica pura.

### ✅ APLIQUE DRY para Regras de Negócio

**Regras de negócio** = Padrões de extração, validações, transformações específicas do domínio.

```python
# ✅ EXTRAIR para utils.py - é regra de negócio compartilhada
# extractors/utils.py

def parse_br_money(value: str) -> float:
    """Converte valor monetário brasileiro para float.
    
    Regra de negócio: Formato brasileiro (1.234,56)
    Usado por múltiplos extratores.
    """
    if not value:
        return 0.0
    try:
        return float(value.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0

def normalize_text_for_extraction(text: str) -> str:
    """Normaliza texto para extração.
    
    Regra de negócio: Como limpamos o texto antes de extrair.
    """
    return text.replace('\n', ' ').strip()
```

### ❌ NÃO APLIQUE DRY Cegamente em Lógica Pura

**Lógica pura** = Estruturas de controle, loops, transformações simples.

```python
# ✅ OK repetir lógica simples se mantém clareza
class ExtratorA(BaseExtractor):
    def _processar_valores(self, valores: List[str]) -> List[float]:
        result = []
        for v in valores:
            result.append(float(v.replace(",", ".")))
        return result

class ExtratorB(BaseExtractor):
    def _processar_itens(self, itens: List[str]) -> List[float]:
        # Lógica similar mas contexto diferente
        resultados = []
        for item in itens:
            resultados.append(float(item.replace(",", ".")))
        return resultados

# NÃO crie função genérica só para isso:
# ❌ def converter_lista_strings_para_float(lista): ...
# Isso cria acoplamento desnecessário
```

### 📋 Regras para Extrair para `utils.py`

| Critério | Extrair? | Exemplo |
|----------|----------|---------|
| Usado em 3+ extratores | ✅ Sim | `parse_br_money()` |
| É padrão do domínio (PDF brasileiro) | ✅ Sim | `parse_date_br()` |
| Regex compartilhada (CNPJ, CEP) | ✅ Sim | `pattern_cnpj` |
| Usado em apenas 1-2 extratores | ❌ Não | Mantenha no extrator |
| Lógica específica de contexto | ❌ Não | `_extract_valor_total_emc()` |
| Facilita testes unitários | ✅ Sim | Funções puras |

### Exemplo Real do Projeto

```python
# ✅ Em utils.py (compartilhado)
def parse_br_money(value: str) -> float:
    """Converte valor monetário brasileiro."""
    ...

def parse_date_br(value: str) -> Optional[str]:
    """Converte data brasileira para ISO."""
    ...

# ✅ No extrator específico (não compartilhado)
class EmcFaturaExtractor(BaseExtractor):
    def _extract_valor_total(self, text: str) -> float:
        # Lógica específica EMC - NÃO extrair para utils
        # Embora use parse_br_money, a estratégia de extração é única
        m = re.search(r'TOTAL\s+R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})', text)
        if m:
            return parse_br_money(m.group(1))  # Usa utils
        
        # Fallback específico EMC
        all_values = re.findall(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})', text)
        ...
```

---

## 4. Estrutura de Extratores

### Template Padrão

```python
"""
Extrator de [Tipo de Documento] da [Fornecedor].

Descrição do que este extrator faz e qual problema resolve.

Campos extraídos:
    - campo1: Descrição
    - campo2: Descrição

Identificação:
    - CNPJ: XX.XXX.XXX/XXXX-XX
    - Termos: "TERM1", "TERM2"
"""
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import (
    normalize_text_for_extraction,
    parse_br_money,
    parse_date_br,
)


@register_extractor
class MeuExtractor(BaseExtractor):
    """
    Extrator para [descrição curta].
    
    Identifica documentos por [critérios].
    Extrai [campos principais].
    """
    
    # Constantes de classe (opcional)
    CNPJ_FORNECEDOR = "XX.XXX.XXX/XXXX-XX"
    
    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Identifica se este é o extrator correto.
        
        Args:
            text: Texto extraído do PDF.
            
        Returns:
            True se o documento é do tipo esperado.
        """
        if not text:
            return False
        
        text_upper = text.upper()
        
        # Implemente critérios de identificação
        has_indicador1 = "PADRAO1" in text_upper
        has_indicador2 = "PADRAO2" in text_upper
        
        return has_indicador1 and has_indicador2
    
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extrai dados estruturados do documento.
        
        Args:
            text: Texto extraído do PDF.
            
        Returns:
            Dicionário com dados extraídos.
        """
        text = self._normalize_text(text or "")
        
        data: Dict[str, Any] = {
            "tipo_documento": "OUTRO",  # ou "NFSE", "BOLETO", etc
            "subtipo": "MEU_SUBTIPO"
        }
        
        # Campos principais
        data["numero_documento"] = self._extract_numero(text)
        data["valor_total"] = self._extract_valor(text)
        data["fornecedor_nome"] = self._extract_fornecedor(text)
        
        return data
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para extração."""
        return normalize_text_for_extraction(text)
    
    def _extract_numero(self, text: str) -> Optional[str]:
        """Extrai número do documento."""
        # Implemente extração específica
        pass
    
    def _extract_valor(self, text: str) -> float:
        """Extrai valor total."""
        # Implemente extração específica
        pass
    
    def _extract_fornecedor(self, text: str) -> str:
        """Extrai nome do fornecedor."""
        # Implemente extração específica
        pass
```

---

## 5. Documentação e Docstrings

### Formato Google Style (usado no projeto)

```python
def extract(self, text: str) -> Dict[str, Any]:
    """
    Extrai dados estruturados do documento.
    
    Args:
        text: Texto extraído do PDF.
        
    Returns:
        Dicionário com dados extraídos.
        
    Example:
        >>> extractor = MeuExtractor()
        >>> dados = extractor.extract("TUNNA FATURA Nº 123")
        >>> print(dados['numero_documento'])
        '123'
    """
```

### Seções Obrigatórias

1. **Módulo:** Descrição geral, campos extraídos, identificação
2. **Classe:** Propósito, critérios de identificação
3. **Métodos públicos:** Args, Returns, (opcional: Raises, Example)
4. **Métodos privados:** Breve descrição do que fazem

---

## 6. Padrões de Regex

### OCR-Tolerância

```python
# ❌ Regex rígido (falha com OCR)
pattern = r"Nº\s*:\s*(\d+)"

# ✅ Regex tolerante (funciona com OCR)
pattern = r"N[^\w\s]?\s*[:\.]\s*(\d+)"  # Aceita Nº, N., N�, etc.
```

### Constantes de Padrão

```python
# ✅ Defina padrões reutilizáveis como constantes
class MeuExtractor(BaseExtractor):
    # Padrões de identificação
    PATTERN_NUMERO = r"N[^\w\s]?\s*[:\.]\s*(\d{3}\.\d{3}\.\d{3})"
    PATTERN_VALOR = r"TOTAL\s+R\$\s*([\d\.]+,\d{2})"
    
    def _extract_numero(self, text: str) -> Optional[str]:
        match = re.search(self.PATTERN_NUMERO, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
```

---

## 7. Checklist antes de Commit

```markdown
- [ ] basedpyright sem erros (rode: `basedpyright` ou `pyright`)
- [ ] Type hints em todos os métodos públicos
- [ ] Docstrings em módulo, classe e métodos públicos
- [ ] Sem imports não usados
- [ ] Funções utilitárias compartilháveis em utils.py
- [ ] Regex OCR-tolerantes quando aplicável
- [ ] Extrator registrado em extractors/__init__.py (ordem correta)
- [ ] Testes validados com validate_extraction_rules.py
```

---

## 8. Anti-Padrões Comuns

### ❌ Extrator "Faz Tudo"

```python
class ExtratorUniversal(BaseExtractor):
    """Tenta extrair qualquer tipo de documento."""
    
    def extract(self, text: str) -> Dict[str, Any]:
        # 200 linhas de if/elif/else
        # Mistura lógica de NFSE, DANFE, Boleto, etc
```

### ❌ Duplicação de Regras de Negócio

```python
# ❌ Mesma lógica de parse de dinheiro em 5 extratores
# (deveria estar em utils.py)

def _extrair_valor(self, text: str) -> float:
    valor_str = re.search(r"R\$\s*([\d\.,]+)", text).group(1)
    return float(valor_str.replace(".", "").replace(",", "."))  # Copiado!
```

### ❌ Violation de LSP

```python
@register_extractor
class MeuExtractor(BaseExtractor):
    def extract(self, text: str) -> str:  # ❌ Retorna str, não Dict!
        return "resultado"
```

---

## 9. Exemplo Completo Aprovado

Veja `extractors/tunna_fatura.py` e `extractors/emc_fatura.py` como referências.

Pontos fortes desses arquivos:
- ✅ Docstrings completas
- ✅ Type hints em todos os métodos
- ✅ Separação clara de responsabilidades
- ✅ Uso de utils.py para regras de negócio compartilhadas
- ✅ Métodos privados para cada campo
- ✅ Constantes de padrões regex
- ✅ OCR-tolerância nos padrões
