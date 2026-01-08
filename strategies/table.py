"""
Estratégia de extração para PDFs com estrutura tabular.

Este módulo detecta e extrai tabelas de PDFs, convertendo para formato
texto estruturado "chave: valor" que facilita a extração por regex.

Motivação:
    Boletos e notas fiscais frequentemente têm layouts onde rótulos
    (cabeçalhos) estão em uma linha e valores em linhas separadas.
    A extração nativa não preserva essa relação, dificultando o parse.

Formato de saída:
    ```
    === DADOS ESTRUTURADOS ===
    Beneficiário: EMPRESA LTDA
    CNPJ: 12.345.678/0001-90
    Valor: 1.234,56
    ```

Quando usar:
    - PDFs com tabelas visíveis (bordas)
    - Documentos onde a extração nativa retorna valores desalinhados
    - Boletos com campos em formato tabular

Example:
    >>> from strategies.table import TablePdfStrategy
    >>> strategy = TablePdfStrategy()
    >>> texto = strategy.extract("boleto.pdf")
    >>> if "=== DADOS ESTRUTURADOS ===" in texto:
    ...     print("Tabelas detectadas e convertidas")
"""
import pdfplumber
from core.interfaces import TextExtractionStrategy

class TablePdfStrategy(TextExtractionStrategy):
    """
    Estratégia para PDFs com estrutura tabular.
    
    Detecta tabelas via pdfplumber e converte para texto estruturado "chave: valor",
    facilitando a extração por regex em documentos com layouts complexos.
    
    Útil para boletos onde rótulos (cabeçalhos) estão em uma linha e
    valores estão em linhas separadas (formato tabular).
    """
    
    def extract(self, file_path: str) -> str:
        """
        Extrai texto + tabelas estruturadas de um PDF.
        
        Args:
            file_path (str): Caminho do arquivo PDF.
            
        Returns:
            str: Texto com tabelas convertidas para formato "chave: valor".
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                if not pdf.pages:
                    return ""
                
                full_text = ""
                has_tables = False
                
                for page in pdf.pages:
                    # Extrai texto normal primeiro (com layout preservado)
                    page_text = page.extract_text(layout=True) or ""
                    full_text += page_text + "\n"
                    
                    # Tenta detectar e extrair tabelas
                    tables = page.extract_tables()
                    
                    if tables:
                        has_tables = True
                        full_text += "\n=== DADOS ESTRUTURADOS ===\n"
                        
                        for table in tables:
                            if not table or len(table) < 2:
                                continue
                            
                            # Assume primeira linha como cabeçalho
                            headers = table[0]
                            
                            # Processa linhas de dados
                            for row in table[1:]:
                                if not row:
                                    continue
                                    
                                # Converte para formato "Chave: Valor"
                                for header, value in zip(headers, row):
                                    if header and value:
                                        # Remove espaços extras
                                        header_clean = str(header).strip()
                                        value_clean = str(value).strip()
                                        
                                        if header_clean and value_clean:
                                            full_text += f"{header_clean}: {value_clean}\n"
                                
                                full_text += "\n"  # Separa registros
                
                # Validação: só retorna se encontrou tabelas e tem conteúdo suficiente
                if not has_tables or len(full_text.strip()) < 50:
                    return ""
                
                return full_text
                
        except Exception as e:
            return ""
