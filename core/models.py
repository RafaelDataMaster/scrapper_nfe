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

@dataclass
class BoletoData:
    """
    Modelo de dados para Boletos Bancários.

    Attributes:
        arquivo_origem (str): Nome do arquivo PDF processado.
        texto_bruto (str): Snippet do texto extraído.
        cnpj_beneficiario (Optional[str]): CNPJ do beneficiário (quem recebe).
        valor_documento (float): Valor nominal do boleto.
        vencimento (Optional[str]): Data de vencimento no formato YYYY-MM-DD.
        numero_documento (Optional[str]): Número do documento/fatura.
        linha_digitavel (Optional[str]): Linha digitável do boleto.
        nosso_numero (Optional[str]): Nosso número (identificação do banco).
        referencia_nfse (Optional[str]): Número da NFSe vinculada (se encontrado).
    """
    arquivo_origem: str
    texto_bruto: str
    cnpj_beneficiario: Optional[str] = None
    valor_documento: float = 0.0
    vencimento: Optional[str] = None
    numero_documento: Optional[str] = None
    linha_digitavel: Optional[str] = None
    nosso_numero: Optional[str] = None
    referencia_nfse: Optional[str] = None