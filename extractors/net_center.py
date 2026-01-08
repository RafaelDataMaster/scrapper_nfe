"""
Extrator especializado para boletos da Net Center Unaí.

Este módulo foi criado para tratar boletos do provedor de internet
Net Center Unaí (CNPJ 05.382.200/0001-70), que possuem layout específico
onde o extrator genérico de boleto captura incorretamente o campo
"CPF/CNPJ" como nome do fornecedor.

Corrigidos:
    - fornecedor_nome: Fixado como "NET CENTER UNAI PROVEDOR DE INTERNET LTDA"
    - cnpj_beneficiario: Garantido mesmo quando OCR falha
    - valor_documento: Padrão "Valor total a pagar" específico do layout

Critérios de ativação:
    - CNPJ 05.382.200/0001-70 presente no documento
    - Nome "Net Center" ou "Unaí" no texto
    - Indicadores de boleto (linha digitável, beneficiário, etc.)

Example:
    >>> from extractors.net_center import NetCenterExtractor
    >>> if NetCenterExtractor.can_handle(texto):
    ...     dados = NetCenterExtractor().extract(texto)
    ...     print(dados['fornecedor_nome'])  # NET CENTER UNAI PROVEDOR...
"""
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import (
    format_cnpj,
    parse_br_money,
    parse_date_br,
    strip_accents,
)


def _extract_cnpj_like(text: str) -> Optional[str]:
    if not text:
        return None

    # Prefer formatted CNPJ.
    m = re.search(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b", text)
    if m:
        return m.group(1)

    # Fallback: 14 digits.
    m = re.search(r"\b(\d{14})\b", re.sub(r"\D+", " ", text))
    if m:
        return m.group(1)

    return None


@register_extractor
class NetCenterExtractor(BaseExtractor):
    """Extrator cirúrgico para faturas/boletos da Net Center Unaí.

    Objetivo: evitar capturar rótulos (ex: CPF/CNPJ) como nome de fornecedor,
    garantindo um fornecedor_nome limpo e estável.
    """

    FORNECEDOR_FIXO = "NET CENTER UNAI PROVEDOR DE INTERNET LTDA"
    CNPJ_NETCENTER = "05.382.200/0001-70"
    CNPJ_NETCENTER_DIGITS = "05382200000170"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        text_up = (text or "").upper()
        text_norm = strip_accents(text_up)
        text_compact = re.sub(r"[^A-Z0-9]+", "", text_norm)

        digits_only = re.sub(r"\D+", "", text or "")

        # Assinatura forte: CNPJ do beneficiário.
        if cls.CNPJ_NETCENTER_DIGITS in digits_only:
            return True

        has_vendor = (
            "NETCENTER" in text_compact
            or "NET CENTER" in text_norm
            or "NETCENTERUNAI" in text_compact
            or "NETCENTERUNAI" in text_compact
            or "UNAI" in text_norm and "NET" in text_norm and "CENTER" in text_norm
        )

        # Evita falso-positivo em docs não-boleto: exige também sinais típicos de boleto.
        boleto_markers = [
            "LINHA DIGITAVEL",
            "LINHA DIGITÁVEL",
            "BENEFICI",
            "VENCIMENTO",
            "VALOR DO DOCUMENTO",
            "CODIGO DE BARRAS",
            "CÓDIGO DE BARRAS",
        ]
        markers_score = sum(1 for kw in boleto_markers if re.sub(r"[^A-Z0-9]+", "", strip_accents(kw.upper())) in text_compact)

        # Também aceita a presença de uma linha digitável (OCR às vezes perde labels).
        has_linha_digitavel = bool(
            re.search(
                r"\d{5}[\.\s]\d{5}\s+\d{5}[\.\s]\d{6}\s+\d{5}[\.\s]\d{6}",
                text or "",
            )
        )

        return bool(has_vendor and (markers_score >= 1 or has_linha_digitavel))

    def extract(self, text: str) -> Dict[str, Any]:
        # Lazy import para não antecipar o registro do BoletoExtractor (ordem do registry).
        from extractors.boleto import BoletoExtractor

        generic = BoletoExtractor()
        data = generic.extract(text)

        # Correção 1: fornecedor fixo (layout identificado)
        data["fornecedor_nome"] = self.FORNECEDOR_FIXO

        # Correção 2: garante CNPJ do beneficiário se o genérico falhar
        if not data.get("cnpj_beneficiario"):
            # Ex: "CPF/CNPJ: 05.382.200/0001-70" / "CNPJ: 05.382.200/0001-70"
            m = re.search(
                r"(?i)\b(?:CPF\s*/\s*CNPJ|CNPJ)\s*:?[\s\n\r]*"
                r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b",
                text or "",
            )
            if m:
                data["cnpj_beneficiario"] = m.group(1)
            else:
                cnpj_any = _extract_cnpj_like(text or "")
                if cnpj_any:
                    # Se vier só em dígitos, tenta formatar
                    if re.fullmatch(r"\d{14}", str(cnpj_any)):
                            data["cnpj_beneficiario"] = format_cnpj(str(cnpj_any))
                    else:
                        data["cnpj_beneficiario"] = cnpj_any

        # Correção 2.1: se o genérico capturou o label como nome (ex: "CPF/CNPJ"), força mesmo assim.
        # (Mantém o fornecedor fixo; aqui é só um reforço caso alguém altere acima.)
        if not data.get("fornecedor_nome") or re.search(r"(?i)\bCPF\b\s*/\s*\bCNPJ\b|\bCPF/CNPJ\b", data.get("fornecedor_nome") or ""):
            data["fornecedor_nome"] = self.FORNECEDOR_FIXO

        # Correção 3: valor total (layout Net Center costuma ter "Valor total a pagar")
        m_total = re.search(
            r"(?is)\bValor\s+total\s+a\s+pagar\b\s*:?\s*(?:R\$\s*)?([\d\.,]+)",
            text or "",
        )
        if m_total:
            v = parse_br_money(m_total.group(1))
            if v > 0:
                data["valor_documento"] = v

        # Correção 3: valor do documento (se existir em formato bem definido)
        m_val = re.search(
            r"(?i)\bValor\s+documento\b\s*[\n\r]*\s*R?\$?\s*([\d\.,]+)",
            text or "",
        )
        if m_val:
            v = parse_br_money(m_val.group(1))
            if v > 0:
                data["valor_documento"] = v

        # Fallback (bem específico/seguro para este layout): pega o maior valor monetário com vírgula.
        # Evita capturar "1" (quantidade) como valor do documento.
        money_vals = []
        for m in re.finditer(r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b", text or ""):
            fv = parse_br_money(m.group(0))
            if fv > 0:
                money_vals.append(fv)
        if money_vals:
            max_v = max(money_vals)
            cur = data.get("valor_documento")
            try:
                cur_f = float(cur) if cur is not None else None
            except Exception:
                cur_f = None
            if cur_f is None or cur_f < max_v:
                data["valor_documento"] = max_v

        # Correção 4: emissão e vencimento (muito estável no topo do layout)
        # Ex: "Emissão Vencimento" + linha com "26/12/2023 20/01/2024"
        m_dates = re.search(
            r"(?is)\bEmiss[aã]o\b\s+Vencim\s*ento\b.*?(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})",
            text or "",
        )
        if m_dates:
            emissao_iso = parse_date_br(m_dates.group(1))
            venc_iso = parse_date_br(m_dates.group(2))
            if emissao_iso:
                data["data_emissao"] = emissao_iso
            if venc_iso:
                data["vencimento"] = venc_iso

        # Fallback: vencimento também aparece como "Local de pagamento Vencimento".
        m_venc = re.search(
            r"(?is)\bLocal\s+de\s+pagamento\s+Vencimento\b.*?(\d{2}/\d{2}/\d{4})",
            text or "",
        )
        if m_venc:
            venc_iso = parse_date_br(m_venc.group(1))
            if venc_iso:
                data["vencimento"] = venc_iso

        return data
