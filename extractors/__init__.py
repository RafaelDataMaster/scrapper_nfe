# IMPORT ORDER MATTERS: o registro (EXTRACTOR_REGISTRY) é uma lista e a prioridade
# é definida pela ordem em que os módulos são importados.
# REGRA: Extractors ESPECÍFICOS devem vir ANTES dos GENÉRICOS
from .boleto_repromaq import BoletoRepromaqExtractor
from .boleto_gox import BoletoGoxExtractor  # Boleto GOX específico (antes do genérico)
from .emc_fatura import EmcFaturaExtractor
from .net_center import NetCenterExtractor
from .nfse_custom_montes_claros import NfseCustomMontesClarosExtractor
from .nfse_custom_vila_velha import NfseCustomVilaVelhaExtractor
from .utility_bill import (
    UtilityBillExtractor,
)  # Extrator unificado para utilidades (energia, água)
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

# Extrator especializado para faturas de água Sabesp (via email body)
from .sabesp import SabespWaterBillExtractor, extract_sabesp_from_email

# Extrator especializado para Nota Débito/Recibo Fatura da CSC GESTAO
from .csc_nota_debito import CscNotaDebitoExtractor

# Extrator especializado para documentos administrativos (deve vir antes dos genéricos)
from .admin_document import AdminDocumentExtractor

# Extrator especializado para comprovantes bancários (TED, PIX, DOC)
# CRÍTICO: deve vir antes dos genéricos para evitar que comprovantes de R$ 1.6M+
# sejam classificados como NFSe sem número
from .comprovante_bancario import ComprovanteBancarioExtractor

# Extrator de corpo de e-mail (não usa EXTRACTOR_REGISTRY, é chamado diretamente)
from .email_body_extractor import (
    EmailBodyExtractionResult,
    EmailBodyExtractor,
    extract_from_email_body,
)


# Extractores de documentos fiscais (prioridade antes dos genéricos)
from .ocr_danfe import (
    OcrDanfeExtractor,
)  # Antes do DanfeExtractor para casos corrompidos
from .danfe import (
    DanfeExtractor,
)  # Danfe antes de genéricos para evitar captura incorreta

# Extractores de boletos (antes de OutrosExtractor para evitar classificação incorreta)
from .boleto import BoletoExtractor
from .sicoob import SicoobExtractor

# Extrator especializado para aditivos de contrato
from .aditivo_contrato import AditivoContratoExtractor

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
    "BoletoGoxExtractor",
    "UtilityBillExtractor",
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
    # Extrator especializado para comprovantes bancários
    "ComprovanteBancarioExtractor",
    "ProPainelExtractor",
    # Extrator especializado para faturas da Tunna (FishTV)
    "TunnaFaturaExtractor",
    # Extrator especializado para faturas Ufinet
    "UfinetExtractor",
    # Extrator especializado para aditivos de contrato
    "AditivoContratoExtractor",
    # Extrator para DANFEs com OCR corrompido
    "OcrDanfeExtractor",
    # Extrator para faturas de água Sabesp (via email body)
    "SabespWaterBillExtractor",
    "extract_sabesp_from_email",
    # Extrator para Nota Débito/Recibo Fatura da CSC GESTAO
    "CscNotaDebitoExtractor",
]
