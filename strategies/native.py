"""
Estratégia de extração nativa para PDFs vetoriais.

Este módulo implementa a leitura direta da camada de texto de PDFs,
utilizando a biblioteca pdfplumber. É a estratégia preferencial por ser
mais rápida e precisa que o OCR.

Características:
    - Extração rápida: ~90% dos PDFs são resolvidos aqui
    - Layout preservado: Mantém estrutura tabular quando necessário
    - Fallback automático: Retorna string vazia para acionar próxima estratégia

Modos de operação:
    1. Extração simples (rápida): Texto linear, suficiente para maioria
    2. Layout preservado (lenta): Mantém posicionamento, útil para tabelas

Example:
    >>> from strategies.native import NativePdfStrategy
    >>> strategy = NativePdfStrategy()
    >>> texto = strategy.extract("documento.pdf")
    >>> if texto:
    ...     print("PDF vetorial extraído com sucesso")
"""
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
        Extrai texto de um PDF vetorial com múltiplas estratégias.
        
        Tenta primeiro com layout preservado (melhor para documentos tabulares),
        depois com extração simples como fallback.

        Args:
            file_path (str): Caminho absoluto ou relativo do arquivo PDF.

        Returns:
            str: Texto extraído ou string vazia se a extração falhar/for insuficiente.
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                if not pdf.pages:
                    return ""

                # Tentativa 1 (rápida): extração simples
                text_simple = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text_simple += page_text + "\n"

                # Regra de Ouro: se extraiu pouco texto, considere falha e deixe o fallback decidir.
                if len(text_simple.strip()) < 50:
                    return ""

                # Se a extração simples já é "boa o bastante", evita layout=True (pode ser bem lento).
                # Em muitos PDFs híbridos/gerados, o layout preservado degrada performance.
                if len(text_simple.strip()) >= 300:
                    return text_simple

                # Tentativa 2: layout preservado (melhor para documentos tabulares, porém mais lenta)
                text_layout = ""
                for page in pdf.pages:
                    page_text = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3) or ""
                    text_layout += page_text + "\n"

                # Usa o layout se ele trouxe significativamente mais conteúdo, senão fica no simples.
                if len(text_layout.strip()) > len(text_simple.strip()) + 100:
                    return text_layout

                return text_simple

        except Exception:
            return ""