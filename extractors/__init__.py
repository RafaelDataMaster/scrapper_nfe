# IMPORT ORDER MATTERS: o registro (EXTRACTOR_REGISTRY) é uma lista e a prioridade
# é definida pela ordem em que os módulos são importados.
# REGRA: Extractors ESPECÍFICOS devem vir ANTES dos GENÉRICOS
from .boleto_repromaq import BoletoRepromaqExtractor  # Específico: antes do genérico
from .boleto import BoletoExtractor
from .danfe import DanfeExtractor

# Extrator de corpo de e-mail (não usa EXTRACTOR_REGISTRY, é chamado diretamente)
from .email_body_extractor import (
    EmailBodyExtractionResult,
    EmailBodyExtractor,
    extract_from_email_body,
)

# Extractores específicos (vêm antes dos genéricos)
from .emc_fatura import EmcFaturaExtractor
from .net_center import NetCenterExtractor
from .nfse_custom_montes_claros import NfseCustomMontesClarosExtractor
from .nfse_custom_vila_velha import NfseCustomVilaVelhaExtractor
from .sicoob import SicoobExtractor


# Extractores genéricos (vêm depois dos específicos)
from .outros import OutrosExtractor
from .nfse_generic import NfseGenericExtractor
from .xml_extractor import XmlExtractionResult, XmlExtractor, extract_xml

__all__ = [
    "BoletoRepromaqExtractor",
    "BoletoExtractor",
    "DanfeExtractor",
    "EmcFaturaExtractor",
    "NetCenterExtractor",
    "OutrosExtractor",
    "SicoobExtractor",
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
]
