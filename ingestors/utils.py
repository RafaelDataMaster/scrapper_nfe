"""
Utilitários para ingestão de dados.

Módulo com helpers e classes auxiliares para o processo de ingestão,
incluindo download e salvamento de anexos de email.
"""

from pathlib import Path
import uuid
from core.exporters import FileSystemManager


class AttachmentDownloader:
    """
    Responsável por baixar e salvar anexos de email.
    
    Separado da lógica de ingestão e processamento (SRP).
    Localizado em ingestors por ser parte do fluxo de entrada (Input).
    """
    
    def __init__(self, file_manager: FileSystemManager):
        """
        Inicializa o downloader.
        
        Args:
            file_manager: Gerenciador de sistema de arquivos
        """
        self.file_manager = file_manager
    
    def save_attachment(self, filename: str, content: bytes) -> Path:
        """
        Salva um anexo no diretório temporário.
        
        Args:
            filename: Nome original do arquivo
            content: Conteúdo binário do arquivo
            
        Returns:
            Path do arquivo salvo
            
        Raises:
            OSError: Se houver erro ao salvar o arquivo
        """
        # Gera nome único para evitar colisões
        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = self.file_manager.get_temp_file_path(unique_filename)
        
        # Salva o arquivo
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return file_path
