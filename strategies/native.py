import pdfplumber
from core.interfaces import TextExtractionStrategy

class NativePdfStrategy(TextExtractionStrategy):
    """
    Estratégia de leitura rápida para PDFs vetoriais (baseados em texto).

    Utiliza a biblioteca `pdfplumber` para acessar a camada de texto do PDF diretamente.
    É a estratégia preferencial por ser mais rápida e precisa que o OCR.
    """
    def extract(self, file_path: str) -> str:
        """
        Extrai texto de um PDF vetorial.

        Args:
            file_path: Caminho do arquivo.

        Returns:
            str: Texto extraído ou string vazia se a extração falhar/for insuficiente.
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                if not pdf.pages:
                    return ""
                # Extrai texto da primeira página (ou loop por todas)
                text = pdf.pages[0].extract_text() or ""
                
                # Regra de Ouro: Se extraiu pouco texto, considere falha!
                if len(text.strip()) < 50: 
                    return "" # Força o fallback
                
                return text
        except Exception as e:
            # Logar o erro se necessário
            return ""