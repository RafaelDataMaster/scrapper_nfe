import re
from typing import Any, Dict, Optional

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

        # Locação / demonstrativos
        if "DEMONSTRATIVO" in t and ("LOCA" in t or "LOCAÇÃO" in t or "LOCACAO" in t):
            return True

        if "VALOR DA LOCA" in t:
            return True

        # Faturas/contas
        if "FATURA" in t:
            return True

        # Heurística específica do caso citado
        if "LOCAWEB" in t:
            return True

        return False

    def extract(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {"tipo_documento": "OUTRO"}

        t = text.upper()
        if "LOCA" in t and "DEMONSTRATIVO" in t:
            data["subtipo"] = "LOCACAO"
        elif "FATURA" in t:
            data["subtipo"] = "FATURA"

        # Fornecedor (tentativas)
        if "LOCAWEB" in t:
            data["fornecedor_nome"] = "LOCAWEB"

        if not data.get("fornecedor_nome"):
            m = re.search(r"(?im)^\s*([A-ZÀ-ÿ][A-ZÀ-ÿ0-9\s\.&\-]{5,80}LTDA)\b", text)
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
                        break

        # Datas: emissão/vencimento (melhor esforço)
        m_venc = re.search(r"(?i)\bVENCIMENTO\b\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", text)
        if m_venc:
            data["vencimento"] = parse_date_br(m_venc.group(1))
        else:
            # Layout analítico: "Data de Vencimento do Contrato: 31/07/2025"
            m_venc2 = re.search(r"(?i)Data\s+de\s+Vencimento\s+do\s+Contrato\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", text)
            if m_venc2:
                data["vencimento"] = parse_date_br(m_venc2.group(1))

        # Algumas faturas têm uma data isolada perto do topo; pegamos a primeira como 'data_emissao'
        m_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
        if m_date:
            data["data_emissao"] = parse_date_br(m_date.group(1))

        return data
