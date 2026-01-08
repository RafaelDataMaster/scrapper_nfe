"""
Estratégia de extração via OCR (Reconhecimento Óptico de Caracteres).

Este módulo implementa a última camada de fallback para PDFs que não
possuem camada de texto (documentos escaneados, imagens).

Dependências:
    - Tesseract OCR: Engine de reconhecimento de texto
    - Poppler: Biblioteca para conversão PDF→imagem
    - pdf2image: Wrapper Python para Poppler

Configuração (via config/settings.py):
    - TESSERACT_CMD: Caminho do executável Tesseract
    - POPPLER_PATH: Caminho da pasta bin do Poppler
    - OCR_LANG: Idioma do OCR (padrão: "por" para português)
    - OCR_CONFIG: Parâmetros adicionais do Tesseract

Limitações:
    - Processo lento (rasterização + OCR)
    - Qualidade depende da resolução do documento original
    - Pode falhar em documentos muito degradados

Example:
    >>> from strategies.ocr import TesseractOcrStrategy
    >>> strategy = TesseractOcrStrategy()
    >>> texto = strategy.extract("documento_escaneado.pdf")
"""
import logging
import pytesseract
from pdf2image import convert_from_path
from core.interfaces import TextExtractionStrategy
from config import settings  # Importando suas configurações

logger = logging.getLogger(__name__)

class TesseractOcrStrategy(TextExtractionStrategy):
    """
    Estratégia de leitura baseada em OCR (Reconhecimento Óptico de Caracteres).

    Utiliza `pdf2image` para rasterizar o PDF e `pytesseract` para extrair texto da imagem.
    Acionada quando o PDF não possui camada de texto (ex: digitalizações).
    """
    def __init__(self):
        """
        Inicializa a estratégia configurando o caminho do executável Tesseract.
        """
        # 1. Configurar o caminho do Tesseract (VITAL NO WINDOWS)
        # Se não fizer isso, vai dar erro de "tesseract not found" depois
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    def extract(self, file_path: str) -> str:
        """
        Converte PDF em imagem e executa OCR.

        Args:
            file_path (str): Caminho do arquivo PDF.

        Returns:
            str: Texto extraído da imagem.

        Raises:
            Exception: Se houver erro na conversão ou no OCR.
        """
        custom_config = settings.OCR_CONFIG
        
        try:
            # 2. Passar o poppler_path explicitamente
            # Sem isso, ele grita "Unable to get page count"
            imagens = convert_from_path(
                file_path, 
                first_page=1, 
                last_page=1,
                poppler_path=settings.POPPLER_PATH ### AQUI ESTAVA FALTANDO!
            )
            
            texto_final = ""
            for img in imagens:
                texto_final += pytesseract.image_to_string(
                    img, 
                    lang=settings.OCR_LANG, 
                    config=custom_config
                )
            
            # Validação: Se OCR retornou texto muito curto, considere falha
            if len(texto_final.strip()) < 50:
                logger.warning(f"OCR extraiu texto insuficiente (<50 chars) de {file_path}")
                return ""  # Falha recuperável, força próxima estratégia
            
            return texto_final
            
        except Exception as e:
            # Log do erro para rastreabilidade, mas mantém fluxo (LSP)
            logger.warning(f"Falha na estratégia OCR para {file_path}: {e}")
            return ""