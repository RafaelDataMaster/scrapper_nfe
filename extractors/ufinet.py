"""
Extractor para faturas da Ufinet Brasil.
Detecta faturas comerciais da Ufinet (não-fiscais).
"""

import re
from typing import Any, Dict, Optional
from core.extractors import BaseExtractor, register_extractor
from extractors.utils import parse_br_money, parse_date_br


@register_extractor
class UfinetExtractor(BaseExtractor):
    """Extractor para faturas da Ufinet Brasil S.A."""

    FORNECEDOR_CNPJ_MAP = {
        "UFINET BRASIL S.A": "06.288.154/0006-11",
        "UFINET BRASIL S.A - FILIAL MG": "06.288.154/0006-11",
        "UFINET BRASIL": "06.288.154/0006-11",
    }

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """Verifica se o texto é de uma fatura Ufinet."""
        text_upper = text.upper()
        
        # Deve conter UFINET
        if "UFINET" not in text_upper:
            return False
            
        # Deve ser uma fatura (não NFS-e)
        if "NOTA FISCAL" in text_upper or "NFS-E" in text_upper or "NFSE" in text_upper:
            return False
            
        # Padrões de fatura Ufinet
        fatura_patterns = [
            r"FATURA\s*(No\.?|N[º°]?|NUMERO)?\s*:?\s*\d+",
            r"UFINET\s*BRASIL",
        ]
        
        matches = sum(1 for p in fatura_patterns if re.search(p, text_upper))
        return matches >= 1

    def _extract_numero_fatura(self, text: str) -> Optional[str]:
        """Extrai o número da fatura."""
        # Padrão: "FATURA No: 000000145" ou "FATURA Nº: 000000145"
        patterns = [
            r"FATURA\s*(?:No\.?|N[º°]?|NUMERO)?\s*:?\s*(\d+)",
            r"FATURA\s*No\.?\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_vencimento(self, text: str) -> Optional[str]:
        """Extrai a data de vencimento."""
        # Padrão: "VENCIMENTO: 25/01/2026"
        patterns = [
            r"VENCIMENTO\s*:?\s*(\d{2}/\d{2}/\d{4})",
            r"VENC\.?\s*:?\s*(\d{2}/\d{2}/\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return parse_date_br(match.group(1))
        return None

    def _extract_valor(self, text: str) -> Optional[float]:
        """Extrai o valor total da fatura."""
        # Procura por "Total (BRL):" ou similar
        patterns = [
            r"Total\s*\(BRL\)\s*:?\s*([\d\.]+,?\d{2})",
            r"Total\s*:?\s*R\$\s*([\d\.]+,?\d{2})",
            r"TOTAL\s*:?\s*([\d\.]+,?\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = parse_br_money(match.group(1))
                return val if val > 0 else None
        return None

    def _extract_fornecedor_nome(self, text: str) -> str:
        """Extrai o nome do fornecedor."""
        # Padrão: "Ufinet Brasil S.A - Filial MG"
        match = re.search(r"(UFINET\s*BRASIL[^\n\r-]*)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "UFINET BRASIL S.A"

    def _extract_cnpj(self, text: str) -> Optional[str]:
        """Extrai o CNPJ do fornecedor."""
        # Padrão: "CNPJ (MF) 062881540006-11"
        patterns = [
            r"CNPJ\s*\(?MF\)?\s*:?\s*(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})",
            r"CNPJ\s*:?\s*(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cnpj = match.group(1).replace(".", "").replace("/", "").replace("-", "")
                return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return "06.288.154/0006-11"  # CNPJ padrão

    def extract(self, text: str) -> Dict[str, Any]:
        """Extrai dados da fatura Ufinet."""
        return {
            "tipo_documento": "OUTRO",
            "subtipo": "FATURA",
            "numero_documento": self._extract_numero_fatura(text),
            "fornecedor_nome": self._extract_fornecedor_nome(text),
            "fornecedor_cnpj": self._extract_cnpj(text),
            "valor": self._extract_valor(text),
            "vencimento": self._extract_vencimento(text),
        }
