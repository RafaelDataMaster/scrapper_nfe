"""
Camada de Serviços.

Este módulo agrupa serviços de alto nível que orquestram
funcionalidades do sistema.

Serviços disponíveis:
- IngestionService: Organização de e-mails em lotes
"""

from services.ingestion_service import IngestionService

__all__ = ['IngestionService']
