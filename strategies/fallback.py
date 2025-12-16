from core.interfaces import TextExtractionStrategy
from .native import NativePdfStrategy
from .ocr import TesseractOcrStrategy  

class SmartExtractionStrategy(TextExtractionStrategy):
    """
    Estratégia composta (Composite) que gerencia tentativas de leitura.

    Implementa um padrão de **Fallback**:
    1.  Tenta a estratégia nativa (rápida).
    2.  Se falhar, aciona a estratégia de OCR (lenta e robusta).
    """
    def __init__(self):
        # Define a ordem de prioridade
        self.strategies = [
            NativePdfStrategy(),      # 1. Tenta ser rápido
            TesseractOcrStrategy()    # 2. Se falhar, usa força bruta
        ]

    def extract(self, file_path: str) -> str:
        """
        Tenta extrair texto usando as estratégias em ordem de prioridade.

        Args:
            file_path (str): Caminho do arquivo PDF.

        Returns:
            str: Texto extraído pela primeira estratégia bem-sucedida.

        Raises:
            Exception: Se todas as estratégias falharem.
        """
        for strategy in self.strategies:
            texto = strategy.extract(file_path)
            if texto: # Se retornou algo válido
                return texto
        
        raise Exception("Falha: Nenhum método conseguiu ler o arquivo.")