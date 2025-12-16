from dataclasses import dataclass
from typing import Optional

@dataclass
class InvoiceData:
    """
    Modelo de dados padronizado para uma Nota Fiscal de Serviço.

    Attributes:
        arquivo_origem (str): Nome do arquivo PDF processado.
        texto_bruto (str): Snippet do texto extraído (para fins de debug).
        cnpj_prestador (Optional[str]): CNPJ formatado do prestador de serviço.
        numero_nota (Optional[str]): Número da nota fiscal limpo.
        data_emissao (Optional[str]): Data de emissão no formato YYYY-MM-DD.
        valor_total (float): Valor total líquido da nota.
    """
    arquivo_origem: str
    texto_bruto: str
    cnpj_prestador: Optional[str] = None
    numero_nota: Optional[str] = None
    data_emissao: Optional[str] = None
    valor_total: float = 0.0