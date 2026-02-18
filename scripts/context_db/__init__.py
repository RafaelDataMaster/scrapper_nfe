"""
Módulo de Vector Database para contexto do projeto.

Este módulo permite indexar e buscar semanticamente os documentos
de contexto em docs/context/, facilitando a consulta de informações
históricas, padrões e troubleshooting.

Componentes:
- embeddings.py: Gerencia embeddings via sentence-transformers
- indexer.py: Indexa documentos markdown no ChromaDB
- query.py: Interface de busca semântica

Uso básico:
    # Indexar documentos (rodar 1x ou quando atualizar docs)
    python scripts/context_db/indexer.py

    # Buscar informação
    python scripts/context_db/query.py "como resolver PDF protegido"
"""

from scripts.context_db.embeddings import EmbeddingManager
from scripts.context_db.indexer import ContextIndexer
from scripts.context_db.query import ContextQuery, SearchResult

__all__ = [
    "EmbeddingManager",
    "ContextIndexer",
    "ContextQuery",
    "SearchResult",
]
