"""
Extrator específico para documentos da Carrier Telecom/TELCABLES BRASIL LTDA.

Este extrator trata documentos de NFCom (Nota Fiscal de Comunicação) da
Carrier Telecom que possuem características específicas:
- Contêm "DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA"
- Incluem linha digitável para débito automático (que confunde o sistema geral)
- São NFSEs legítimas mas não eram classificadas corretamente

Problema original: O NfseGenericExtractor não reconhecia estes documentos porque
a função find_linha_digitavel() retornava True devido à presença do código de
débito automático (47-48 dígitos), e o texto contém "CHAVE DE ACESSO" que fazia
o DanfeExtractor capturar incorretamente.

Solução: Extrator específico com alta prioridade que reconhece padrões únicos
da Carrier Telecom e extrai valores corretamente.
"""

import logging
import re
from typing import Any, Dict

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import (
    BR_MONEY_RE,
    parse_br_money,
    parse_date_br,
)


@register_extractor
class CarrierTelecomExtractor(BaseExtractor):
    """Extrator específico para documentos da Carrier Telecom/TELCABLES BRASIL LTDA."""

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """Retorna True se o documento é da Carrier Telecom/TELCABLES BRASIL LTDA."""
        if not text:
            return False

        # Normalizar caracteres que o OCR pode usar como espaços
        text = text.replace("Ê", " ").replace("ê", " ")

        text_upper = text.upper()

        # Padrões específicos da Carrier Telecom
        carrier_patterns = [
            "TELCABLES BRASIL LTDA",
            "CARRIER TELECOM",
            "DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA",
            "DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVICOS DE COMUNICACAO ELETRONICA",
        ]

        # Verifica se algum padrão está presente
        for pattern in carrier_patterns:
            if pattern in text_upper:
                logging.getLogger(__name__).debug(
                    f"CarrierTelecomExtractor: can_handle detectou padrão '{pattern}'"
                )
                return True

        # Fallback: Verificar CNPJ específico da Carrier Telecom
        cnpj_patterns = [
            "20.609.743/0004-13",
            "20609743000413",
        ]
        for cnpj in cnpj_patterns:
            if cnpj in text or cnpj in text_upper:
                logging.getLogger(__name__).debug(
                    f"CarrierTelecomExtractor: can_handle detectou CNPJ da Carrier Telecom"
                )
                return True

        return False

    def _normalize_ocr_text(self, text: str) -> str:
        """Normaliza texto extraído por OCR para lidar com caracteres especiais."""
        if not text:
            return text

        logger = logging.getLogger(__name__)
        logger.debug(
            f"Texto OCR recebido para normalização ({len(text)} chars): {text[:200]}"
        )

        # Primeiro: substituir caracteres problemáticos comuns do OCR
        # Caracteres de placeholder (quadrados, retângulos, etc.)
        ocr_problem_chars = [
            "□",  # WHITE SQUARE U+25A1
            "▢",  # WHITE SQUARE WITH ROUNDED CORNERS U+25A2
            "■",  # BLACK SQUARE U+25A0
            "▭",  # WHITE RECTANGLE U+25AD
            "▯",  # WHITE VERTICAL RECTANGLE U+25AF
            "�",  # REPLACEMENT CHARACTER U+FFFD
            "Ê",  # E WITH CIRCUMFLEX, usado como espaço pelo OCR
            "ê",  # e with circumflex, minúsculo
        ]

        for char in ocr_problem_chars:
            text = text.replace(char, " ")

        # Substituir múltiplos caracteres de espaço por um único espaço
        text = re.sub(r"[ \t\r\n\f\v]+", " ", text)

        # Normalizar caracteres acentuados mal interpretados
        # Padrões comuns em OCR de PDFs (agora sem os caracteres quadrados)
        replacements = {
            # Padrões com caracteres especiais removidos
            "SERVI OS": "SERVIÇOS",
            "SERVICOS": "SERVIÇOS",
            "COMUNICA O": "COMUNICAÇÃO",
            "COMUNICACAO": "COMUNICAÇÃO",
            "ELETR NICA": "ELETRÔNICA",
            "ELETRONICA": "ELETRÔNICA",
            "ENDERE O": "ENDEREÇO",
            "ENDERECO": "ENDEREÇO",
            "INSCRI O": "INSCRIÇÃO",
            "INSCRICAO": "INSCRIÇÃO",
            "REFER NCIA": "REFERÊNCIA",
            "REFERENCIA": "REFERÊNCIA",
            "S RIE": "SÉRIE",
            "SERIE": "SÉRIE",
            "EMISS O": "EMISSÃO",
            "EMISSAO": "EMISSÃO",
            "C DIGO": "CÓDIGO",
            "CODIGO": "CÓDIGO",
            "PER ODO": "PERÍODO",
            "PERIODO": "PERÍODO",
            "AUTORIZA O": "AUTORIZAÇÃO",
            "AUTORIZACAO": "AUTORIZAÇÃO",
            "D BITO": "DÉBITO",
            "DEBITO": "DÉBITO",
            "AUTOM TICO": "AUTOMÁTICO",
            "AUTOMATICO": "AUTOMÁTICO",
            "PRIORIT RIAS": "PRIORITÁRIAS",
            "PRIORITARIAS": "PRIORITÁRIAS",
            "PRE O": "PREÇO",
            "PRECO": "PREÇO",
            " REA": "ÁREA",
            "AREA": "ÁREA",
            # Adicionar padrões específicos do documento Carrier Telecom
            "TOTAL A PAGAR": "TOTAL A PAGAR",  # Manter igual, mas garantir espaços
            "NOTA FISCAL FATURA": "NOTA FISCAL FATURA",
            "CHAVE DE ACESSO": "CHAVE DE ACESSO",
            "CPF/CNPJ": "CPF/CNPJ",
        }

        # Aplicar substituições (case-insensitive)
        for wrong, correct in replacements.items():
            # Usar boundary para evitar substituições parciais indesejadas
            pattern = r"\b" + re.escape(wrong) + r"\b"
            text = re.sub(pattern, correct, text, flags=re.IGNORECASE)

        # Corrigir padrões específicos que podem ter múltiplos espaços
        # "TOTAL  A  PAGAR" -> "TOTAL A PAGAR"
        text = re.sub(r"TOTAL\s+A\s+PAGAR", "TOTAL A PAGAR", text, flags=re.IGNORECASE)

        # "NOTA FISCAL  FATURA" -> "NOTA FISCAL FATURA"
        text = re.sub(
            r"NOTA FISCAL\s+FATURA", "NOTA FISCAL FATURA", text, flags=re.IGNORECASE
        )

        # Remover múltiplos espaços novamente após substituições
        text = re.sub(r"\s+", " ", text)

        # Garantir que valores monetários tenham formatação correta
        # "R$  29.250,00" -> "R$ 29.250,00"
        text = re.sub(r"R[$]\s+(\d)", r"R$ \1", text)

        logger.debug(
            f"Texto OCR normalizado ({len(text.strip())} chars): {text.strip()[:200]}"
        )
        return text.strip()

    def extract(self, text: str) -> Dict[str, Any]:
        """Extrai dados de documentos da Carrier Telecom."""
        logger = logging.getLogger(__name__)
        logger.info("CarrierTelecomExtractor: iniciando extração")

        print("DEBUG: CarrierTelecomExtractor.extract chamado")
        logger.debug(
            f"Texto recebido (primeiros 1000 chars): {text[:1000] if text else 'N/A'}"
        )
        # Normalizar texto OCR antes do processamento
        original_text = text
        text = self._normalize_ocr_text(text)
        if original_text != text:
            logger.debug("Texto OCR normalizado (diferenças encontradas)")

        data: Dict[str, Any] = {"tipo_documento": "NFSE"}
        text_upper = text.upper()

        # 1. CNPJ do prestador
        cnpj_match = re.search(
            r"(?:CPF/)?CNPJ\s*[:\-]?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", text
        )
        if cnpj_match:
            data["cnpj_prestador"] = cnpj_match.group(1)
            logger.debug(f"CNPJ extraído: {data['cnpj_prestador']}")
        else:
            # Fallback: procurar qualquer CNPJ formatado
            cnpj_fallback = re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", text)
            if cnpj_fallback:
                data["cnpj_prestador"] = cnpj_fallback.group(0)

        # 2. Nome do fornecedor
        # Padrão: "NOME: TELCABLES BRASIL LTDA FILIAL SAO PAULO"
        nome_match = re.search(
            r"(?i)NOME\s*[:\-]?\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9\s\.\-]{5,80})(?:\n|$)", text
        )
        if nome_match:
            fornecedor = nome_match.group(1).strip()
            # Limpar possíveis quebras de linha e parar no próximo campo
            fornecedor = re.sub(r"\s+", " ", fornecedor)
            # Remover possíveis campos seguintes (ex: "ENDEREÇO")
            fornecedor = re.split(
                r"\s*(?:ENDEREÇO|ENDERECO|CEP|CPF/CNPJ)", fornecedor, flags=re.I
            )[0].strip()
            data["fornecedor_nome"] = fornecedor
            logger.debug(f"Fornecedor extraído: {data['fornecedor_nome']}")
        else:
            # Fallback: usar o nome conhecido
            data["fornecedor_nome"] = "TELCABLES BRASIL LTDA"

        # 3. Número da nota
        # Padrão: "NOTA FISCAL FATURA: 114" ou "NOTA FISCAL: 114"
        nota_patterns = [
            r"(?i)NOTA\s+FISCAL\s+FATURA\s*[:\-]?\s*(\d+)",
            r"(?i)NOTA\s+FISCAL\s*[:\-]?\s*(\d+)",
            r"(?i)FATURA\s*[:\-]?\s*(\d+)",
            r"(?i)N[º°]\s*(?:DA\s+)?NOTA\s*[:\-]?\s*(\d+)",
        ]
        for i, pattern in enumerate(nota_patterns):
            match = re.search(pattern, text)
            if match:
                data["numero_nota"] = match.group(1)
                logger.debug(
                    f"Padrão {i}: número da nota extraído: {data['numero_nota']}"
                )
                break
            else:
                logger.debug(
                    f"Padrão {i} não encontrado para número da nota: '{pattern}'"
                )

        # 4. Valor total - padrão específico: "TOTAL A PAGAR: R$ 29.250,00"
        # NOTA: Após normalização, "TOTAL□A□PAGAR" se torna "TOTAL A PAGAR"
        valor_patterns = [
            r"(?i)TOTAL\s+A\s+PAGAR\s*[:\-]?\s*R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            r"(?i)TOTAL\s+A\s+PAGAR\s*[:\-]?\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            r"(?i)TOTAL\s*[:\-]?\s*R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            r"(?i)VALOR\s+TOTAL\s*[:\-]?\s*R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            r"R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            r"\b(\d{1,3}(?:\.\d{3})*,\d{2})\s*REAIS\b",
        ]
        for i, pattern in enumerate(valor_patterns):
            match = re.search(pattern, text)
            if match:
                logger.debug(
                    f"Padrão {i} encontrado: '{pattern}' -> '{match.group(1)}'"
                )
                valor = parse_br_money(match.group(1))
                if valor > 0:
                    data["valor_total"] = valor
                    logger.debug(f"Valor total extraído: R$ {data['valor_total']:.2f}")
                    break
            else:
                logger.debug(f"Padrão {i} não encontrado: '{pattern}'")

        # 5. Data de emissão
        # Padrão: data após "TOTAL A PAGAR" ou "DATA DE EMISSÃO"
        # No documento: "TOTAL A PAGAR: R$ 29.250,00\n10/11/2025"
        total_match = re.search(r"(?i)TOTAL\s+A\s+PAGAR", text)
        if total_match:
            # Procurar data nos próximos 100 caracteres
            start_pos = total_match.end()
            text_after_total = text[start_pos : start_pos + 100]
            date_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text_after_total)
            if date_match:
                data["data_emissao"] = parse_date_br(date_match.group(1))
                logger.debug(f"Data de emissão extraída: {data['data_emissao']}")

        # Se não encontrou, procurar padrão geral
        if not data.get("data_emissao"):
            date_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
            if date_match:
                data["data_emissao"] = parse_date_br(date_match.group(1))

        # 6. Vencimento
        # Padrão: "VENCIMENTO: 23/12/2025"
        vencimento_match = re.search(
            r"(?i)VENCIMENTO\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", text
        )
        if vencimento_match:
            data["vencimento"] = parse_date_br(vencimento_match.group(1))
            logger.debug(f"Vencimento extraído: {data['vencimento']}")

        # 7. Série
        serie_match = re.search(r"(?i)S[ÉE]RIE\s*[:\-]?\s*(\d+)", text)
        if serie_match:
            data["serie_nf"] = serie_match.group(1)

        # 8. Referência (período)
        ref_match = re.search(r"(?i)REFER[ÊE]NCIA\s*[:\-]?\s*(\d{2}/\d{4})", text)
        if ref_match:
            data["referencia"] = ref_match.group(1)
            # Extrair mês e ano para possível uso como período
            mes, ano = ref_match.group(1).split("/")
            data["periodo_referencia"] = f"{mes}/{ano}"

        # 9. Chave de acesso (opcional)
        chave_match = re.search(
            r"(?i)CHAVE\s+DE\s+ACESSO\s*[:\-]?\s*((?:\d{4}\s*){11})", text
        )
        if chave_match:
            chave = re.sub(r"\s+", "", chave_match.group(1))
            if len(chave) == 44:
                data["chave_acesso"] = chave

        # 10. Código do cliente (opcional)
        codigo_match = re.search(r"(?i)C[ÓO]DIGO\s+DO\s+CLIENTE\s*[:\-]?\s*(\d+)", text)
        if codigo_match:
            data["codigo_cliente"] = codigo_match.group(1)

        # Log do resultado
        if data.get("valor_total"):
            logger.info(
                f"CarrierTelecomExtractor: documento processado - "
                f"Nota: {data.get('numero_nota', 'N/A')}, "
                f"Valor: R$ {data['valor_total']:.2f}, "
                f"Fornecedor: {data.get('fornecedor_nome', 'N/A')}"
            )
        else:
            # Log do texto original não normalizado para debug
            logger.warning(
                f"CarrierTelecomExtractor: documento processado mas valor_total não encontrado. "
                f"Texto normalizado (primeiros 500 chars): {text[:500]}"
            )
            logger.debug(
                f"Texto original (primeiros 500 chars): {original_text[:500] if 'original_text' in locals() else text[:500]}"
            )

        return data
