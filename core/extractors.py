from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# 1. O Registro (Lista de plugins disponíveis)
EXTRACTOR_REGISTRY = []

def register_extractor(cls):
    """Decorador para registrar novas cidades automaticamente."""
    EXTRACTOR_REGISTRY.append(cls)
    return cls

# 2. A Interface Base
class BaseExtractor(ABC):
    """Contrato que toda cidade deve implementar."""
    
    @classmethod
    @abstractmethod
    def can_handle(cls, text: str) -> bool:
        """Retorna True se este extrator reconhece o texto da nota."""
        pass

    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        """Recebe o texto bruto e retorna o dicionário de dados."""
        pass
