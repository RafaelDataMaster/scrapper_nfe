# Guia de Logging e Debug

> **Uso:** Como adicionar logs durante criação de extratores ou modificações no projeto  
> **Ferramentas:** Módulo `logging` do Python, logs em `logs/scrapper.log`

---

## 1. Configuração do Logger no Projeto

### Como Obter o Logger

```python
import logging

# Use __name__ para hierarquia correta de loggers
logger = logging.getLogger(__name__)
```

### Logger em Extratores

```python
"""
Extrator de Faturas XPTO.

Este módulo implementa...
"""
import logging
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor

# Obter logger para este módulo
logger = logging.getLogger(__name__)


@register_extractor
class XptoExtractor(BaseExtractor):
    """Extrator para faturas XPTO."""
    
    @classmethod
    def can_handle(cls, text: str) -> bool:
        """Identifica documentos XPTO."""
        # Log de debug para rastrear decisões
        logger.debug("XptoExtractor.can_handle chamado")
        
        text_upper = text.upper()
        has_xpto = "XPTO" in text_upper
        
        logger.debug(f"Indicador XPTO encontrado: {has_xpto}")
        return has_xpto
    
    def extract(self, text: str) -> Dict[str, Any]:
        """Extrai dados da fatura XPTO."""
        logger.info("Iniciando extração XPTO")
        
        data = {"tipo_documento": "OUTRO"}
        
        # Extrair campos com logs de progresso
        numero = self._extract_numero(text)
        if numero:
            data["numero_documento"] = numero
            logger.info(f"Número extraído: {numero}")
        else:
            logger.warning("Número do documento não encontrado")
        
        return data
```

---

## 2. Níveis de Log e Quando Usar

### Hierarquia de Níveis

```
DEBUG < INFO < WARNING < ERROR < CRITICAL
```

### Quando Usar Cada Nível

| Nível | Quando Usar | Exemplo |
|-------|-------------|---------|
| **DEBUG** | Informações detalhadas para diagnóstico | Regex aplicada, match encontrado/não |
| **INFO** | Eventos normais do sistema | Extração iniciada/concluída, valor encontrado |
| **WARNING** | Situações anormais mas recuperáveis | Campo não encontrado (fallback usado), OCR corrompeu char |
| **ERROR** | Falhas que impedem operação | Erro de parsing, arquivo não encontrado |
| **CRITICAL** | Erros graves que impedem execução | - (raro em extratores) |

### Exemplos por Contexto

#### Em `can_handle()` - Use DEBUG

```python
@classmethod
def can_handle(cls, text: str) -> bool:
    """Identifica se é documento do tipo."""
    logger.debug(f"{cls.__name__}.can_handle - texto length: {len(text)}")
    
    has_term = "TERM" in text.upper()
    logger.debug(f"Indicador TERM: {has_term}")
    
    # Se recusar, explique por que (útil para debug)
    if not has_term:
        logger.debug(f"{cls.__name__} recusou: TERM não encontrado")
        return False
    
    return True
```

#### Em `extract()` - Use INFO para milestones

```python
def extract(self, text: str) -> Dict[str, Any]:
    """Extrai dados do documento."""
    logger.info(f"{self.__class__.__name__}.extract iniciado")
    
    data: Dict[str, Any] = {"tipo_documento": "OUTRO"}
    
    # Campos principais
    numero = self._extract_numero(text)
    if numero:
        data["numero_documento"] = numero
        logger.info(f"Número extraído: {numero}")
    else:
        logger.warning("Número não extraído - campo ficará vazio")
    
    valor = self._extract_valor(text)
    if valor > 0:
        data["valor_total"] = valor
        logger.info(f"Valor extraído: R$ {valor:.2f}")
    else:
        logger.warning("Valor zero ou não encontrado")
    
    logger.info(f"Extração concluída - campos: {list(data.keys())}")
    return data
```

#### Em Métodos Privados - Use DEBUG/INFO

```python
def _extract_valor(self, text: str) -> float:
    """Extrai valor total."""
    logger.debug("Buscando valor com padrões específicos")
    
    # Tentar padrões específicos
    for i, pattern in enumerate(self.VALOR_PATTERNS):
        logger.debug(f"Tentando padrão {i+1}: {pattern[:30]}...")
        match = re.search(pattern, text)
        if match:
            valor_str = match.group(1)
            logger.info(f"Valor encontrado com padrão {i+1}: {valor_str}")
            return parse_br_money(valor_str)
    
    logger.warning("Nenhum padrão de valor encontrado")
    return 0.0
```

---

## 3. Padrões de Logging no Projeto

### Formato Padrão

O projeto usa formato configurado em `core/logging_config.py` ou similar:

```
2026-01-29 08:44:30 - nome.do.modulo - NIVEL - Mensagem
```

Exemplo real:
```
2026-01-29 08:44:30 - extractors.tunna_fatura - INFO - Número extraído: 000.010.731
2026-01-29 08:44:30 - extractors.tunna_fatura - DEBUG - Regex aplicada: N[�º]?\s*[:\.]\s*(\d{3}\.\d{3}\.\d{3})
```

### O que Incluir nas Mensagens

#### ✅ Bom

```python
# Contexto claro
logger.info(f"TunnaFaturaExtractor: número extraído: {numero}")
logger.warning(f"Valor não encontrado em {len(text)} caracteres de texto")
logger.debug(f"Regex match: {match.group(0) if match else 'None'}")
```

#### ❌ Ruim

```python
# Sem contexto
logger.info("Encontrado")  # O que?
logger.debug("ok")  # O que está ok?
```

---

## 4. Logging para Debug de Regex

### Padrão Recomendado

```python
def _extract_campo(self, text: str) -> Optional[str]:
    """Extrai campo com logging detalhado."""
    logger.debug(f"Extraindo campo de {len(text)} caracteres")
    
    # Mostrar trecho relevante (primeiros 500 chars)
    trecho = text[:500].replace('\n', ' ')
    logger.debug(f"Trecho analisado: {trecho}...")
    
    for pattern_name, pattern in self.PATTERNS.items():
        logger.debug(f"Tentando {pattern_name}: {pattern}")
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            valor = match.group(1).strip()
            logger.info(f"{pattern_name} encontrou: {valor}")
            return valor
        else:
            logger.debug(f"{pattern_name} não encontrou match")
    
    logger.warning("Nenhum padrão encontrou o campo")
    return None
```

### Debug de OCR

```python
def _normalize_text(self, text: str) -> str:
    """Normaliza texto com log de caracteres problemáticos."""
    # Logar caracteres corrompidos comuns
    if '�' in text:
        count = text.count('�')
        logger.warning(f"Texto contém {count} caracteres corrompidos (�)")
        
        # Mostrar contexto
        idx = text.find('�')
        context = text[max(0, idx-20):min(len(text), idx+20)]
        logger.debug(f"Contexto do corrupção: ...{context}...")
    
    return normalize_text_for_extraction(text)
```

---

## 5. Logging em Casos de Erro

### Try/Except com Logging

```python
def _extract_valor(self, text: str) -> float:
    """Extrai valor com tratamento de erro."""
    try:
        match = re.search(self.PATTERN_VALOR, text)
        if not match:
            logger.warning("Padrão de valor não encontrado no texto")
            return 0.0
        
        valor_str = match.group(1)
        logger.debug(f"String de valor encontrada: {valor_str}")
        
        valor = parse_br_money(valor_str)
        logger.info(f"Valor parseado: R$ {valor:.2f}")
        return valor
        
    except re.error as e:
        logger.error(f"Erro na regex de valor: {e}")
        return 0.0
    except ValueError as e:
        logger.error(f"Erro ao converter valor '{valor_str}': {e}")
        return 0.0
    except Exception as e:
        logger.error(f"Erro inesperado em _extract_valor: {e}", exc_info=True)
        return 0.0
```

### exc_info para Stack Trace

Use `exc_info=True` quando precisar do stack trace completo:

```python
try:
    resultado = operacao_risco()
except Exception as e:
    # Loga mensagem + stack trace
    logger.error(f"Falha na operação: {e}", exc_info=True)
    return None
```

---

## 6. Verificando Logs durante Desenvolvimento

### Tail de Logs em Tempo Real

```powershell
# PowerShell - acompanhar logs em tempo real
Get-Content logs/scrapper.log -Wait -Tail 20

# Ou use o alias (se configurado)
tail -f logs/scrapper.log
```

### Buscar Logs Específicos

```powershell
# Buscar logs de um extrator específico
Select-String "tunna_fatura" logs/scrapper.log | Select-Object -Last 20

# Buscar apenas erros
Select-String "ERROR" logs/scrapper.log | Select-Object -Last 20

# Buscar em um período específico
Select-String "2026-01-29 09:" logs/scrapper.log | Select-String "tunna"
```

### Análise com Script

```bash
# Usar o script de análise
python scripts/analyze_logs.py --today
python scripts/analyze_logs.py --errors-only
python scripts/analyze_logs.py --batch email_20260129_084433_c5c04540
```

---

## 7. Boas Práticas

### ✅ Faça

1. **Use logger do módulo**: `logging.getLogger(__name__)`
2. **Logue decisões importantes**: "Extrator X aceitou/recusou documento"
3. **Inclua valores encontrados**: "Valor extraído: R$ 100,00"
4. **Logue fallbacks**: "Usando fallback para valor"
5. **Use níveis apropriados**: DEBUG para detalhes, INFO para milestones
6. **Logue erros com contexto**: "Erro ao extrair valor: {e}"

### ❌ Não Faça

1. **Não use print()**: Use sempre `logger`
2. **Não logue textos completos**: Limite a trechos (primeiros 500 chars)
3. **Não logue em loop sem limitação**: Pode gerar logs enormes
4. **Não use f-string em logs complexos** sem necessidade: Pode ser custoso
5. **Não ignore exceções**: Sempre logue erros

### Anti-Padrões

```python
# ❌ Ruim - print em vez de logger
print(f"Valor: {valor}")  # Não faça!

# ❌ Ruim - log de texto completo (muito grande)
logger.debug(f"Texto completo: {text}")  # Pode ser 100KB!

# ❌ Ruim - log em loop sem controle
for item in itens:
    logger.debug(f"Processando: {item}")  # Milhares de linhas!

# ✅ Bom - log resumido
logger.debug(f"Processando {len(itens)} itens")
```

---

## 8. Habilitando DEBUG em Produção

### Via Configuração

No `.env` ou configuração:

```bash
# Nível de log global
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# Ou por módulo
LOG_LEVEL_EXTRACTORS=DEBUG
LOG_LEVEL_CORE=INFO
```

### Via Código (para testes)

```python
# No início do script de teste
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Ou configurar apenas um módulo
logging.getLogger('extractors.tunna_fatura').setLevel(logging.DEBUG)
```

---

## 9. Checklist de Logging para Novo Extrator

```markdown
- [ ] Logger obtido no topo do arquivo: `logger = logging.getLogger(__name__)`
- [ ] `can_handle()` loga decisão (DEBUG quando recusa, INFO quando aceita)
- [ ] `extract()` loga início e fim (INFO)
- [ ] Campos principais logam quando encontrados (INFO)
- [ ] Campos ausentes logam warning (WARNING)
- [ ] Erros de parsing são logados com contexto (ERROR)
- [ ] Regex complexas logam tentativas (DEBUG)
- [ ] Não há prints (tudo usa logger)
- [ ] Logs testados e aparecem em `logs/scrapper.log`
```

---

## 10. Exemplo Completo

Veja `extractors/tunna_fatura.py` como referência de logging bem implementado:

```python
import logging
from core.extractors import BaseExtractor, register_extractor

logger = logging.getLogger(__name__)

@register_extractor
class TunnaFaturaExtractor(BaseExtractor):
    """Extrator com logging adequado."""
    
    @classmethod
    def can_handle(cls, text: str) -> bool:
        logger.debug(f"{cls.__name__}.can_handle chamado")
        
        text_upper = text.upper()
        has_tunna = "TUNNA" in text_upper
        has_fatura = "FATURA" in text_upper
        
        logger.debug(f"Indicadores: TUNNA={has_tunna}, FATURA={has_fatura}")
        
        result = has_tunna and has_fatura
        if result:
            logger.info(f"{cls.__name__} aceitou documento")
        else:
            logger.debug(f"{cls.__name__} recusou: TUNNA={has_tunna}, FATURA={has_fatura}")
        
        return result
    
    def extract(self, text: str) -> Dict[str, Any]:
        logger.info(f"{self.__class__.__name__}.extract iniciado")
        
        data: Dict[str, Any] = {
            "tipo_documento": "OUTRO",
            "subtipo": "FATURA",
            "fornecedor_nome": "TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA"
        }
        
        numero = self._extract_numero_fatura(text)
        if numero:
            data["numero_documento"] = numero
            logger.info(f"Número da fatura: {numero}")
        else:
            logger.warning("Número da fatura não encontrado")
        
        logger.info(f"Extração concluída com {len(data)} campos")
        return data
```
