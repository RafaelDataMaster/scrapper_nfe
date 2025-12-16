import re
import os
from abc import ABC, abstractmethod
from datetime import datetime
from core.models import InvoiceData
from strategies.fallback import SmartExtractionStrategy
from core.extractors import EXTRACTOR_REGISTRY
import extractors.generic

class BaseInvoiceProcessor(ABC):
    """
    Classe orquestradora principal do processo de extração.

    Responsável por coordenar o fluxo completo:
    1.  **Leitura**: Converte PDF em texto (via `SmartExtractionStrategy`).
    2.  **Seleção**: Escolhe o extrator adequado para o texto (via `EXTRACTOR_REGISTRY`).
    3.  **Extração**: Executa a mineração de dados.
    4.  **Normalização**: Retorna um objeto `InvoiceData`.
    """
    def __init__(self):
        # Instancia a estratégia de leitura que você já criou
        self.reader = SmartExtractionStrategy()

    def _get_extractor(self, text: str):
        """Factory Method: Escolhe o extrator certo para o texto."""
        for extractor_cls in EXTRACTOR_REGISTRY:
            if extractor_cls.can_handle(text):
                return extractor_cls()
        raise ValueError("Nenhum extrator compatível encontrado para este documento.")

    def process(self, file_path: str) -> InvoiceData:
        """
        Executa o pipeline de processamento para um único arquivo.

        Args:
            file_path (str): Caminho absoluto ou relativo do arquivo PDF.

        Returns:
            InvoiceData: Objeto contendo os dados extraídos e metadados.
        """
        # 1. Leitura (Já implementado nas suas strategies)
        raw_text = self.reader.extract(file_path)
        
        # 2. Inicializa o modelo
        data = InvoiceData(
            arquivo_origem=os.path.basename(file_path),
            texto_bruto=raw_text[:100].replace('\n', ' ') # Guardando snippet como no seu teste
        )

        if not raw_text or "Falha" in raw_text:
            return data

        # 3. Seleção do Extrator (Factory)
        try:
            extractor = self._get_extractor(raw_text)
            extracted_data = extractor.extract(raw_text)
            
            # 4. Preenchimento do Modelo
            data.cnpj_prestador = extracted_data.get('cnpj_prestador')
            data.numero_nota = extracted_data.get('numero_nota')
            data.valor_total = extracted_data.get('valor_total')
            data.data_emissao = extracted_data.get('data_emissao')
            
        except ValueError as e:
            print(f"Erro ao processar {file_path}: {e}")

        return data



