"""
Módulo auxiliar para inicialização de ambiente nos scripts.

Centraliza a lógica de path resolution para evitar duplicação
em todos os scripts do projeto.

Usage:
    from _init_env import setup_project_path
    setup_project_path()
    
    # Agora pode importar módulos do projeto
    from config import settings
    from core.processor import BaseInvoiceProcessor
"""
import sys
from pathlib import Path


def setup_project_path() -> Path:
    """
    Adiciona a raiz do projeto ao sys.path.
    
    Returns:
        Path: Caminho absoluto da raiz do projeto
        
    Examples:
        >>> project_root = setup_project_path()
        >>> assert project_root.exists()
        >>> assert (project_root / "config").exists()
    """
    # Resolve o caminho da raiz do projeto (parent do diretório scripts)
    project_root = Path(__file__).resolve().parent.parent
    
    # Adiciona ao sys.path se ainda não estiver lá
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root
