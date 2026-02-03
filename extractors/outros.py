"""
Extrator para documentos recorrentes que não são NFSe/Boleto/DANFE.

Este módulo trata documentos auxiliares como:
    - Demonstrativos de locação
    - Faturas de serviços (ex: Locaweb, provedores)
    - Contratos de locação de equipamentos

Motivação:
    Evitar que o NfseGenericExtractor classifique incorretamente estes
    documentos como notas fiscais, extraindo ao menos fornecedor, valor
    e datas quando possível.

Campos extraídos:
    - tipo_documento: Sempre "OUTRO"
    - subtipo: "LOCACAO" ou "FATURA"
    - fornecedor_nome: Nome do fornecedor
    - cnpj_fornecedor: CNPJ quando presente
    - valor_total: Valor total a pagar
    - vencimento: Data de vencimento
    - data_emissao: Data de emissão

Example:
    >>> from extractors.outros import OutrosExtractor
    >>> extractor = OutrosExtractor()
    >>> if extractor.can_handle(texto):
    ...     dados = extractor.extract(texto)
    ...     print(f"Tipo: {dados['subtipo']} - R$ {dados['valor_total']:.2f}")
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
class OutrosExtractor(BaseExtractor):
    """Extrator para documentos recorrentes que não são NFSe/Boleto/DANFE.

    Exemplos no seu report:
    - Demonstrativo de locação
    - Faturas de serviços (ex: Locaweb)

    Objetivo: evitar que o NfseGenericExtractor classifique isso como NFSe e
    extrair pelo menos fornecedor + valor + datas quando possível.
    """

    @classmethod
    def can_handle(cls, text: str) -> bool:
        if not text:
            return False

        t = text.upper()

        # Exclusão de documentos fiscais (NFSE, DANFE, etc.)
        # 1. Indicadores fortes de NFSE
        nfse_indicators = [
            "NFS-E",
            "NFSE",
            "NOTA FISCAL DE SERVIÇO ELETRÔNICA",
            "NOTA FISCAL DE SERVICO ELETRONICA",
            "NOTA FISCAL ELETRÔNICA DE SERVIÇO",
            "NOTA FISCAL ELETRONICA DE SERVICO",
            "DOCUMENTO AUXILIAR DA NOTA FISCAL DE SERVIÇO",
            "DOCUMENTO AUXILIAR DA NFS-E",
            "CÓDIGO DE VERIFICAÇÃO",
            "CODIGO DE VERIFICACAO",
            "PREFEITURA MUNICIPAL",
        ]

        # 2. Indicadores fortes de DANFE/NF-e
        danfe_indicators = [
            "DANFE",
            "DOCUMENTO AUXILIAR",
            "CHAVE DE ACESSO",
            "NF-E",
            "NFE",
            "DANFSE",
            "DOCUMENTO AUXILIAR DA NFE",
        ]

        # Verificar indicadores fortes
        if any(ind in t for ind in nfse_indicators):
            logging.getLogger(__name__).debug(
                "OutrosExtractor: can_handle excluído - documento fiscal (NFSE)"
            )
            return False

        if any(ind in t for ind in danfe_indicators):
            logging.getLogger(__name__).debug(
                "OutrosExtractor: can_handle excluído - documento fiscal (DANFE/NF-e)"
            )
            return False

        # Verificar chave de acesso de 44 dígitos
        if re.search(r"(?<!\d)\d{44}(?!\d)", text or ""):
            logging.getLogger(__name__).debug(
                "OutrosExtractor: can_handle excluído - chave de acesso de 44 dígitos"
            )
            return False

        # Verificar padrões de impostos que indicam documento fiscal
        # EXCEÇÃO: Faturas de locação podem ter campos de impostos sem serem NF-e
        is_fatura_locacao = (
            "FATURA DE LOCAÇÃO" in t
            or "FATURA DE LOCACAO" in t
            or "EXTRATO DE LOCAÇÃO" in t
            or "EXTRATO DE LOCACAO" in t
        )
        tax_patterns = r"ISS|INSS|PIS|COFINS|ICMS|CSLL|IRRF|IRPJ"
        tax_matches = re.findall(tax_patterns, t)
        if len(tax_matches) >= 2 and not is_fatura_locacao:
            logging.getLogger(__name__).debug(
                f"OutrosExtractor: can_handle excluído - múltiplos impostos ({len(tax_matches)})"
            )
            return False

        # Locação / demonstrativos
        if "DEMONSTRATIVO" in t and ("LOCA" in t or "LOCAÇÃO" in t or "LOCACAO" in t):
            logging.getLogger(__name__).debug(
                "OutrosExtractor: can_handle detectou demonstrativo de locação"
            )
            return True

        # EXTRATO DE LOCAÇÃO (ex: REPROMAQ)
        if "EXTRATO DE LOCAÇÃO" in t or "EXTRATO DE LOCACAO" in t:
            logging.getLogger(__name__).debug(
                "OutrosExtractor: can_handle detectou extrato de locação"
            )
            return True

        if "VALOR DA LOCA" in t:
            logging.getLogger(__name__).debug(
                "OutrosExtractor: can_handle detectou 'VALOR DA LOCA'"
            )
            return True

        # Faturas/contas - excluir faturas fiscais (NFSE)
        if "FATURA" in t:
            # Se for "NOTA FATURA" ou contém indicadores de NFSE, excluir
            if "NOTA FATURA" in t or "NOTA-FATURA" in t:
                logging.getLogger(__name__).debug(
                    "OutrosExtractor: can_handle excluído - 'NOTA FATURA' (NFSE)"
                )
                return False
            # Verificar se há outros indicadores de documento fiscal
            fiscal_indicators = [
                "NOTA FISCAL",
                "NFS",
                "NFSE",
                "SERVIÇO",
                "SERVICO",
                "ELETRÔNICA",
                "ELETRONICA",
            ]
            fiscal_count = sum(1 for ind in fiscal_indicators if ind in t)
            if fiscal_count >= 2:
                logging.getLogger(__name__).debug(
                    f"OutrosExtractor: can_handle excluído - fatura com {fiscal_count} indicadores fiscais"
                )
                return False
            logging.getLogger(__name__).debug(
                "OutrosExtractor: can_handle detectou fatura administrativa"
            )
            return True

        # Heurística específica do caso citado
        if "LOCAWEB" in t:
            logging.getLogger(__name__).debug(
                "OutrosExtractor: can_handle detectou LOCAWEB"
            )
            return True

        return False

    def extract(self, text: str) -> Dict[str, Any]:
        logger = logging.getLogger(__name__)
        data: Dict[str, Any] = {"tipo_documento": "OUTRO"}
        logger.debug("OutrosExtractor: iniciando extração de documento")

        t = text.upper()
        if "LOCA" in t and "DEMONSTRATIVO" in t:
            data["subtipo"] = "LOCACAO"
        elif "EXTRATO DE LOCAÇÃO" in t or "EXTRATO DE LOCACAO" in t:
            data["subtipo"] = "LOCACAO"
        elif "FATURA DE LOCAÇÃO" in t or "FATURA DE LOCACAO" in t:
            data["subtipo"] = "LOCACAO"
        elif "FATURA" in t:
            data["subtipo"] = "FATURA"

        # Fornecedor (tentativas)
        # Mapeamento de fornecedores conhecidos por palavra-chave
        # NOTA: NÃO incluir empresas próprias do grupo (CSC, EXATA, RBC, etc.)
        # Fornecedores que precisam de match exato (word boundary) para evitar falsos positivos
        # Ex: "TIM" não deve fazer match em "MULTIMIDIA"
        KNOWN_SUPPLIERS_WORD_BOUNDARY = {
            "TIM": "TIM",
        }

        # Fornecedores que podem usar substring match (são suficientemente únicos)
        KNOWN_SUPPLIERS = {
            "LOCAWEB": "LOCAWEB",
            "CORREIOS": "CORREIOS",
            "EMPRESA BRASILEIRA DE CORREIOS": "CORREIOS",
            "EXTRATO SINTETICO": "CORREIOS",
            "EXTRATO SINTÉTICO": "CORREIOS",
            "FATURA TIM": "TIM",
            "CONTATIM": "TIM",
            "MITELECOM": "MI TELECOM",
            "LEVYCAM": "LEVYCAM CORRETORA DE CÂMBIO",
            "FILIBRAS": "FILIBRAS COMERCIAL IMPORTACAO E EXPORTACAO LTDA",
            "GLOBENET": "GLOBENET CABOS SUBMARINOS S.A.",
            "GLOBE NET": "GLOBENET CABOS SUBMARINOS S.A.",
            "AMERICAN TOWER": "AMERICAN TOWER DO BRASIL",
        }

        # Primeiro, verificar fornecedores que precisam de word boundary
        for keyword, supplier in KNOWN_SUPPLIERS_WORD_BOUNDARY.items():
            # Usar regex para garantir que é uma palavra isolada
            if re.search(rf"\b{re.escape(keyword)}\b", t):
                data["fornecedor_nome"] = supplier
                break

        # Se não encontrou, verificar fornecedores com substring match
        if not data.get("fornecedor_nome"):
            for keyword, supplier in KNOWN_SUPPLIERS.items():
                if keyword in t:
                    data["fornecedor_nome"] = supplier
                    break

        # Para documentos de locação, o fornecedor geralmente é a primeira empresa no documento
        # (antes da seção "DESTINATÁRIO DA LOCAÇÃO" ou "TOMADOR")
        if not data.get("fornecedor_nome") and data.get("subtipo") == "LOCACAO":
            # Pegar texto antes de "DESTINATÁRIO" ou "TOMADOR" para evitar pegar o cliente
            texto_cabecalho = text
            for delimitador in ["DESTINATÁRIO", "DESTINATARIO", "TOMADOR", "CLIENTE"]:
                if delimitador in text.upper():
                    idx = text.upper().find(delimitador)
                    texto_cabecalho = text[:idx]
                    break

            # Procurar primeira empresa LTDA no cabeçalho
            m = re.search(
                r"(?im)^\s*([A-ZÀ-ÿ][A-ZÀ-ÿ0-9\s\.&\-]+(?:LTDA|S/?A|EIRELI)\.?)\s*$",
                texto_cabecalho,
            )
            if m:
                data["fornecedor_nome"] = re.sub(r"\s+", " ", m.group(1)).strip()

        if not data.get("fornecedor_nome"):
            # Tentar padrão "Fornecedor: NOME LTDA"
            m = re.search(
                r"(?i)Fornecedor\s*:\s*([A-ZÀ-ÿ][A-ZÀ-ÿ0-9\s\.&\-]+LTDA)\b", text
            )
            if m:
                data["fornecedor_nome"] = re.sub(r"\s+", " ", m.group(1)).strip()

        if not data.get("fornecedor_nome"):
            m = re.search(
                r"(?im)^\s*(?!FATURA)([A-ZÀ-ÿ][A-ZÀ-ÿ0-9\s\.&\-]{5,80}LTDA)\b", text
            )
            if m:
                data["fornecedor_nome"] = re.sub(r"\s+", " ", m.group(1)).strip()

        # CNPJ (primeiro formatado)
        m_cnpj = re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", text)
        if m_cnpj:
            data["cnpj_fornecedor"] = m_cnpj.group(0)

        # Valor total (locação/fatura)
        # 1) Layout analítico (Repromaq): "Total a Pagar no Mês ... 2.855,00" (sem R$)
        if data.get("subtipo") == "LOCACAO":
            m_total_mes = re.search(r"(?i)\bTOTAL\s+A\s+PAGAR\s+NO\s+M[ÊE]S\b", text)
            if m_total_mes:
                window = text[m_total_mes.start() : m_total_mes.start() + 400]
                values = [parse_br_money(v) for v in BR_MONEY_RE.findall(window)]
                values = [v for v in values if v > 0]
                if values:
                    data["valor_total"] = max(values)
                    logger.debug(
                        f"OutrosExtractor: valor_total extraído (layout analítico): R$ {data['valor_total']:.2f}"
                    )

            # 1b) Layout EXTRATO DE LOCAÇÃO (Repromaq): "VALOR TOTAL : 267,81"
            if not data.get("valor_total"):
                m_valor_total = re.search(r"(?i)\bVALOR\s+TOTAL\s*:\s*([\d.,]+)", text)
                if m_valor_total:
                    val = parse_br_money(m_valor_total.group(1))
                    if val > 0:
                        data["valor_total"] = val
                        logger.debug(
                            f"OutrosExtractor: valor_total extraído (VALOR TOTAL): R$ {data['valor_total']:.2f}"
                        )

            # 1c) Layout EXTRATO DE LOCAÇÃO (Repromaq): "R$ TOTAL : 267,81"
            if not data.get("valor_total"):
                m_rs_total = re.search(r"(?i)R\$\s*TOTAL\s*:\s*([\d.,]+)", text)
                if m_rs_total:
                    val = parse_br_money(m_rs_total.group(1))
                    if val > 0:
                        data["valor_total"] = val
                        logger.debug(
                            f"OutrosExtractor: valor_total extraído (R$ TOTAL): R$ {data['valor_total']:.2f}"
                        )

        # 2) Padrões genéricos (inclui casos com R$)
        if not data.get("valor_total"):
            value_patterns = [
                r"(?i)\bTOTAL\s+A\s+PAGAR\b[\s\S]{0,40}?R\$\s*([\d\.,]+)",
                r"(?i)\bTOTAL\s+A\s+PAGAR\b[\s\S]{0,80}?(\d{1,3}(?:\.\d{3})*,\d{2})\b",
                r"(?i)\bVALOR\s+DA\s+LOCA[ÇC][ÃA]O\b[\s\S]{0,40}?([\d\.]+,\d{2})\b",
                r"(?i)\bVALOR\b[\s\S]{0,20}?R\$\s*([\d\.,]+)",
                r"\bR\$\s*([\d\.]+,\d{2})\b",
            ]
            for pat in value_patterns:
                m = re.search(pat, text)
                if m:
                    val = parse_br_money(m.group(1))
                    if val > 0:
                        data["valor_total"] = val
                        logger.debug(
                            f"OutrosExtractor: valor_total extraído (padrão genérico): R$ {data['valor_total']:.2f}"
                        )
                        break

        # Datas: emissão/vencimento (melhor esforço)
        m_venc = re.search(r"(?i)\bVENCIMENTO\b\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", text)
        if m_venc:
            data["vencimento"] = parse_date_br(m_venc.group(1))
            logger.debug(f"OutrosExtractor: vencimento extraído: {data['vencimento']}")
        else:
            # Layout analítico: "Data de Vencimento do Contrato: 31/07/2025"
            m_venc2 = re.search(
                r"(?i)Data\s+de\s+Vencimento\s+do\s+Contrato\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
                text,
            )
            if m_venc2:
                data["vencimento"] = parse_date_br(m_venc2.group(1))
                logger.debug(
                    f"OutrosExtractor: vencimento extraído (contrato): {data['vencimento']}"
                )

        # Algumas faturas têm uma data isolada perto do topo; pegamos a primeira como 'data_emissao'
        m_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
        if m_date:
            data["data_emissao"] = parse_date_br(m_date.group(1))
            logger.debug(
                f"OutrosExtractor: data_emissao extraída: {data['data_emissao']}"
            )

        # Número do documento (para extratos de locação)
        # Prioridade: NÚMERO DO RECIBO > Nº SXXXXX > NÚMERO DA FATURA > NÚMERO DO CONTRATO
        if data.get("subtipo") == "LOCACAO":
            # Padrão REPROMAQ extrato: "NÚMERO DO RECIBO:S09679"
            m_recibo = re.search(
                r"(?i)N[ÚU]MERO\s+DO\s+RECIBO\s*:\s*([A-Z0-9\-]+)", text
            )
            if m_recibo:
                data["numero_documento"] = m_recibo.group(1).strip()
                logger.debug(
                    f"OutrosExtractor: numero_documento extraído (recibo): {data['numero_documento']}"
                )

            # Padrão REPROMAQ fatura: "Nº S09679"
            if not data.get("numero_documento"):
                m_num = re.search(r"N[ºo°]\s+([A-Z]\d{4,}(?:-\d+)?)", text)
                if m_num:
                    data["numero_documento"] = m_num.group(1).strip()
                    logger.debug(
                        f"OutrosExtractor: numero_documento extraído (Nº): {data['numero_documento']}"
                    )

            # Padrão: "NÚMERO DA FATURA ... S09679"
            if not data.get("numero_documento"):
                m_fatura = re.search(
                    r"(?i)N[ÚU]MERO\s+DA\s+FATURA[\s\S]{0,30}?([A-Z]\d{4,}(?:-\d+)?)",
                    text,
                )
                if m_fatura:
                    data["numero_documento"] = m_fatura.group(1).strip()
                    logger.debug(
                        f"OutrosExtractor: numero_documento extraído (fatura): {data['numero_documento']}"
                    )

            # Fallback: "NÚMERO DO CONTRATO :4152"
            if not data.get("numero_documento"):
                m_contrato = re.search(
                    r"(?i)N[ÚU]MERO\s+DO\s+CONTRATO\s*:\s*(\d+)", text
                )
                if m_contrato:
                    data["numero_documento"] = f"CONTRATO-{m_contrato.group(1).strip()}"
                    logger.debug(
                        f"OutrosExtractor: numero_documento extraído (contrato): {data['numero_documento']}"
                    )

        # Log final do resultado
        if data.get("valor_total"):
            logger.info(
                f"OutrosExtractor: documento processado - subtipo: {data.get('subtipo', 'N/A')}, valor_total: R$ {data['valor_total']:.2f}, fornecedor: {data.get('fornecedor_nome', 'N/A')}"
            )
        else:
            logger.warning(
                "OutrosExtractor: documento processado mas valor_total não encontrado"
            )

        return data
