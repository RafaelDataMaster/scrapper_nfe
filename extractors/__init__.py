# IMPORT ORDER MATTERS: o registro (EXTRACTOR_REGISTRY) é uma lista e a prioridade
# é definida pela ordem em que os módulos são importados.
# REGRA: Extractors ESPECÍFICOS devem vir ANTES dos GENÉRICOS
from .boleto_repromaq import BoletoRepromaqExtractor
from .emc_fatura import EmcFaturaExtractor
from .net_center import NetCenterExtractor
from .nfse_custom_montes_claros import NfseCustomMontesClarosExtractor
from .nfse_custom_vila_velha import NfseCustomVilaVelhaExtractor
from .energy_bill import EnergyBillExtractor
from .nfcom_telcables_extractor import NfcomTelcablesExtractor

# Extrator especializado para boletos ACIMOC
from .acimoc_extractor import AcimocExtractor

# Extrator especializado para faturas MUGO TELECOM
from .mugo_extractor import MugoExtractor

# Extrator especializado para PRÓ - PAINEL LTDA
from .pro_painel_extractor import ProPainelExtractor

# Extrator especializado para faturas da Tunna (FishTV)
from .tunna_fatura import TunnaFaturaExtractor

# Extrator especializado para faturas Ufinet
from .ufinet import UfinetExtractor

# Extrator especializado para documentos administrativos (deve vir antes dos genéricos)
from .admin_document import AdminDocumentExtractor

# Extrator de corpo de e-mail (não usa EXTRACTOR_REGISTRY, é chamado diretamente)
from .email_body_extractor import (
    EmailBodyExtractionResult,
    EmailBodyExtractor,
    extract_from_email_body,
)


# Extractores de documentos fiscais (prioridade antes dos genéricos)
from .danfe import DanfeExtractor  # Danfe antes de genéricos para evitar captura incorreta

# Extractores de boletos (antes de OutrosExtractor para evitar classificação incorreta)
from .boleto import BoletoExtractor
from .sicoob import SicoobExtractor

# Extractores genéricos (vêm depois dos específicos)
from .outros import OutrosExtractor
from .nfse_generic import NfseGenericExtractor
from .xml_extractor import XmlExtractionResult, XmlExtractor, extract_xml

__all__ = [
    "BoletoRepromaqExtractor",
    "AcimocExtractor",
    "MugoExtractor",
    "BoletoExtractor",
    "DanfeExtractor",
    "EmcFaturaExtractor",
    "NetCenterExtractor",
    "NfcomTelcablesExtractor",
    "OutrosExtractor",
    "SicoobExtractor",
    "EnergyBillExtractor",
    "NfseCustomMontesClarosExtractor",
    "NfseCustomVilaVelhaExtractor",
    "NfseGenericExtractor",
    "XmlExtractor",
    "XmlExtractionResult",
    "extract_xml",
    # Extrator de corpo de e-mail
    "EmailBodyExtractor",
    "EmailBodyExtractionResult",
    "extract_from_email_body",
    # Extrator especializado para documentos administrativos
    "AdminDocumentExtractor",
    "ProPainelExtractor",
    # Extrator especializado para faturas da Tunna (FishTV)
    "TunnaFaturaExtractor",
    # Extrator especializado para faturas Ufinet
    "UfinetExtractor",
]
