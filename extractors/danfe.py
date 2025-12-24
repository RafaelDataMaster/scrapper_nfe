import re
from datetime import datetime
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor


def _normalize_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _parse_br_money(value: str) -> float:
    if not value:
        return 0.0
    try:
        return float(value.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def _parse_date_br(value: str) -> Optional[str]:
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


_MONEY_BR_RE = re.compile(r"\b(\d{1,3}(?:\.\d{3})*,\d{2})\b")


def _extract_best_money_from_segment(segment: str) -> float:
    values = []
    for raw in _MONEY_BR_RE.findall(segment or ""):
        v = _parse_br_money(raw.replace(" ", ""))
        if v > 0:
            values.append(v)
    return max(values) if values else 0.0


def _extract_danfe_valor_total(text: str) -> float:
    if not text:
        return 0.0

    # Em muitos DANFEs os campos vêm em uma "tabela" linearizada no texto,
    # onde a linha contém vários números (ex.: 0,00 0,00 ... 4.800,00).
    # Nesses casos, pegar o primeiro match falha; precisamos pegar o melhor (geralmente o último/maior).
    label_patterns = [
        r"(?i)\bVALOR\s+TOTAL\s+DA\s+NOTA\b",
        r"(?i)\bVALOR\s+TOTAL\s+(?:DOS\s+)?PRODUTOS\b",
        r"(?i)\bVALOR\s+TOTAL\s+PRODUTOS\b",
        r"(?i)\bV\.?\s*TOTAL\s+DA\s+NOTA\b",
        r"(?i)\bTOTAL\s+DA\s+NOTA\b",
    ]

    for lp in label_patterns:
        for m in re.finditer(lp, text):
            start = m.end()
            line_end = text.find("\n", start)
            if line_end == -1:
                line_end = min(len(text), start + 350)
            segment = text[start:line_end]
            best = _extract_best_money_from_segment(segment)
            if best > 0:
                return best

            # Em alguns PDFs o valor pode cair na linha seguinte
            next_end = text.find("\n", line_end + 1)
            if next_end == -1:
                next_end = min(len(text), line_end + 350)
            segment2 = text[start:next_end]
            best2 = _extract_best_money_from_segment(segment2)
            if best2 > 0:
                return best2

    # Fallback conservador: escolhe o maior valor monetário no documento.
    # Em DANFE, o maior valor quase sempre corresponde ao total da nota.
    best_overall = _extract_best_money_from_segment(text)
    return best_overall


@register_extractor
class DanfeExtractor(BaseExtractor):
    """Extrator para DANFE (NF-e modelo 55)."""

    @classmethod
    def can_handle(cls, text: str) -> bool:
        if not text:
            return False

        t = text.upper()

        # Identificadores fortes
        if "DANFE" in t:
            return True

        if "DOCUMENTO AUXILIAR" in t and "NOTA FISCAL" in t and "ELETR" in t:
            return True

        # Chave de acesso (44 dígitos), muitas vezes espaçada
        digits = _normalize_digits(text)
        if re.search(r"\b\d{44}\b", digits):
            return True

        # Algumas DANFEs vêm com 'NF-E' / 'NFE' + 'CHAVE DE ACESSO'
        if ("CHAVE DE ACESSO" in t) and ("NF-E" in t or "NFE" in t):
            return True

        return False

    def extract(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {"tipo_documento": "DANFE"}

        # Chave de acesso (44 dígitos)
        digits = _normalize_digits(text)
        m_key = re.search(r"\b(\d{44})\b", digits)
        if m_key:
            data["chave_acesso"] = m_key.group(1)

        # Número da NF (várias formas). Importante: em DANFE o número pode vir como
        # 'NF-E Nº000.084.653' (com pontos). Por isso capturamos também '.' e limpamos.
        patterns_num = [
            r"(?i)\bNF-?E\b[^\n]{0,120}?\bN[º°o]?\s*[:\-]?\s*([0-9\.]{1,20})",
            r"(?i)\bN[º°o]?\s*[:\-]?\s*([0-9\.]{1,20})\b\s*(?:S[ÉE]RIE|SERIE)\b",
            r"(?i)\bN[º°o]?\s*[:\-]?\s*([0-9\.]{1,20})\b",
        ]
        for pat in patterns_num:
            m = re.search(pat, text)
            if not m:
                continue
            numero = re.sub(r"\D", "", m.group(1))
            if numero:
                # Normaliza removendo zeros à esquerda só se ficar algo; mantém '0' se tudo zero
                data["numero_nota"] = numero.lstrip('0') or '0'
                break

        # Série
        m_serie = re.search(r"(?i)\bS[ÉE]RIE\s*[:\-]?\s*(\d{1,4})\b", text)
        if m_serie:
            data["serie_nf"] = m_serie.group(1)

        # Data de emissão
        # Em DANFE frequentemente aparece como 'Emissão 07/11/2025' ou 'DATA DE EMISSÃO'
        date_patterns = [
            r"(?i)\bEMISS[ÃA]O\b\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
            r"(?i)\bDATA\s+DE\s+EMISS[ÃA]O\b\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        ]
        for pat in date_patterns:
            m = re.search(pat, text)
            if m:
                data["data_emissao"] = _parse_date_br(m.group(1))
                break

        # Valor total
        data["valor_total"] = _extract_danfe_valor_total(text)

        # CNPJ emitente (formato com pontuação)
        m_cnpj = re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", text)
        if m_cnpj:
            data["cnpj_emitente"] = m_cnpj.group(0)

        # Fornecedor/emitente (razão social)
        # 1) 'Recebemos de X os produtos...'
        m_recv = re.search(r"(?is)\bRECEBEMOS\s+DE\s+(.+?)\s+OS\s+PRODUTOS", text)
        if m_recv:
            name = re.sub(r"\s+", " ", m_recv.group(1)).strip()
            data["fornecedor_nome"] = name

        # 2) 'DANFE X DOCUMENTO AUXILIAR...'
        if not data.get("fornecedor_nome"):
            m_danfe = re.search(r"(?is)\bDANFE\b\s+(.+?)\s+DOCUMENTO\s+AUXILIAR", text)
            if m_danfe:
                name = re.sub(r"\s+", " ", m_danfe.group(1)).strip()
                # Evita capturar lixo muito longo
                if 4 <= len(name) <= 120:
                    data["fornecedor_nome"] = name

        return data
