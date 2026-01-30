"""
Extrator para contas de utilidade pública (energia, água, gás, telecom).

Unifica faturas de:
- Energia elétrica (CEMIG, EDP, NEOENERGIA, etc.)
- Saneamento/Água (COPASA, SABESP, SANEPAR, etc.)
- Telecom (GOX, etc.) - via detecção específica

Retorna tipo_documento="UTILITY_BILL" para mapeamento correto no processador.
"""

import logging
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import parse_date_br


@register_extractor
class UtilityBillExtractor(BaseExtractor):
    """
    Extrator unificado para contas de utilidade pública.
    
    Subtipos:
    - ENERGY: Faturas de energia elétrica
    - WATER: Faturas de água/esgoto
    - TELECOM: Faturas de internet/telefonia (quando não há NF)
    
    Campos retornados:
    - tipo_documento: "UTILITY_BILL"
    - subtipo: "ENERGY", "WATER", "TELECOM"
    - numero_documento: Número da fatura/conta (não é nota fiscal!)
    - instalacao/matricula: Código do cliente
    """

    # Fornecedores conhecidos por categoria
    ENERGY_SUPPLIERS = {
        "CEMIG": "CEMIG DISTRIBUIÇÃO S.A.",
        "EDP": "EDP São Paulo Distribuição de Energia S.A.",
        "NEOENERGIA": "NEOENERGIA",
        "ELEKTRO": "NEOENERGIA Elektro",
        "COPEL": "COPEL",
        "CPFL": "CPFL",
        "ENERGISA": "ENERGISA",
        "ENEL": "ENEL",
        "LIGHT": "LIGHT",
        "COSERN": "COSERN",
        "CELESC": "CELESC",
        "CELPE": "CELPE",
        "COELBA": "COELBA",
        "COELCE": "COELCE",
    }
    
    WATER_SUPPLIERS = {
        "COPASA": "COPASA",
        "COMPANHIA DE SANEAMENTO DE MINAS GERAIS": "COPASA",
        "SABESP": "SABESP",
        "SANEPAR": "SANEPAR",
        "CASAN": "CASAN",
        "CORSAN": "CORSAN",
        "DESO": "DESO",
        "EMAE": "EMAE",
    }

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """Retorna True se é uma conta de utilidade (energia, água, etc.)."""
        if not text:
            return False

        text_upper = text.upper()
        score = {"energy": 0, "water": 0}

        # Indicadores de energia
        energy_indicators = [
            "DISTRIB DE ENERGIA", "DISTRIBUIDORA DE ENERGIA",
            "ENERGIA ELETRICA", "CONSUMO", "KWH",
            "INSTALACAO", "BANDEIRA TARIFARIA",
            "FATURA DE ENERGIA", "CONTA DE LUZ",
        ]
        
        # Indicadores de água/saneamento
        water_indicators = [
            "COMPANHIA DE SANEAMENTO", "COPASA", "SABESP", "SANEPAR",
            "FATURA DE SERVICOS", "CONTA DE AGUA",
            "ESGOTO", "MATRICULA", "CONTA-COPASA",
        ]

        score["energy"] = sum(1 for ind in energy_indicators if ind in text_upper)
        score["water"] = sum(1 for ind in water_indicators if ind in text_upper)

        if score["energy"] >= 2:
            return True
            
        if score["water"] >= 1 and ("NOTA FISCAL" in text_upper or "FATURA" in text_upper):
            return True
            
        # Verifica fornecedores conhecidos
        for supplier in list(cls.ENERGY_SUPPLIERS.keys()) + list(cls.WATER_SUPPLIERS.keys()):
            if supplier in text_upper:
                if "NOTA FISCAL" in text_upper or "FATURA" in text_upper or score["energy"] >= 1:
                    return True
                    
        return False

    def _detect_subtype(self, text: str) -> str:
        """Detecta o subtipo (ENERGY, WATER)."""
        text_upper = text.upper()
        
        # Verifica água primeiro (mais específico)
        water_score = sum(1 for key in self.WATER_SUPPLIERS.keys() if key in text_upper)
        for indicator in ["COPASA", "SABESP", "SANEPAR"]:
            if indicator in text_upper:
                water_score += 1
                
        if water_score > 0:
            return "WATER"
            
        return "ENERGY"

    def _extract_supplier(self, text: str, subtype: str) -> str:
        """Extrai nome do fornecedor baseado no subtipo."""
        text_upper = text.upper()
        
        # Verifica fornecedores de água
        if subtype == "WATER":
            for key, name in self.WATER_SUPPLIERS.items():
                if key in text_upper:
                    return name
                    
        # Verifica fornecedores de energia
        for key, name in self.ENERGY_SUPPLIERS.items():
            if key in text_upper:
                return name
        
        return "UTILIDADE"

    def _extract_document_number(self, text: str, subtype: str) -> Optional[str]:
        """Extrai número da fatura/conta (não nota fiscal!)."""
        patterns = [
            r"NOTA\s+FISCAL\s*No?\.?\s*([0-9\.\-]+)",
            r"NOTA\s+FISCAL\s*N[°º]?\s*[:\-]?\s*([0-9\.\-]+)",
            r"FATURA\s*N[°º]?\s*[:\-]?\s*([0-9\.\-]+)",
            r"([0-9]{3}\.[0-9]{3})\s+[0-9]{4,8}(?=\s+\d{5}-\d{3})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                numero = match.group(1).strip().strip('.-')
                if numero:
                    return numero
        
        # Fallback para saneamento: IDENTIFICADOR
        if subtype == "WATER":
            ident_patterns = [
                r"IDENTIFICADOR\s*[:\-]?\s*(\d[\d\s\.]+)",
            ]
            for pattern in ident_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    ident = re.sub(r'[\s\.]', '', match.group(1))
                    if len(ident) >= 8:
                        return ident

        return None

    def _extract_installation(self, text: str) -> Optional[str]:
        """Extrai número de instalação/matricula."""
        patterns = [
            r"INSTALACAO\s*[:\-]?\s*(\d+)",
            r"MATRICULA\s*[:\-]?\s*(\d[\d\s\.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().replace(" ", "").replace(".", "")

        return None

    def _extract_cnpj(self, text: str) -> Optional[str]:
        """Extrai CNPJ do fornecedor."""
        cnpj_patterns = [
            r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
            r"CNPJ\s*[:\-]?\s*(\d{14})",
        ]

        for pattern in cnpj_patterns:
            match = re.search(pattern, text)
            if match:
                cnpj = match.group(1)
                if re.match(r"^\d{14}$", cnpj):
                    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
                return cnpj

        return None

    def _extract_value(self, text: str) -> float:
        """Extrai valor total."""
        patterns = [
            r"TOTAL\s+A\s+PAGAR\s*[:\-]?\s*R?\$?\s*([\d.]+,\d{2})",
            r"VALOR\s+TOTAL\s*[:\-]?\s*R?\$?\s*([\d.]+,\d{2})",
            r"R\$\s*([\d.]+,\d{2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    valor_str = match.group(1).replace(".", "").replace(",", ".")
                    return float(valor_str)
                except (ValueError, IndexError):
                    continue

        return 0.0

    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extrai data de vencimento."""
        patterns = [
            r"VENCIMENTO\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return parse_date_br(match.group(1))

        return None

    def _extract_issue_date(self, text: str) -> Optional[str]:
        """Extrai data de emissão."""
        patterns = [
            r"EMISSAO\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return parse_date_br(match.group(1))

        return None

    def extract(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Extrai dados da conta de utilidade."""
        logger = logging.getLogger(__name__)
        logger.info("UtilityBillExtractor: iniciando extração")

        subtype = self._detect_subtype(text)

        data: Dict[str, Any] = {
            "tipo_documento": "UTILITY_BILL",
            "subtipo": subtype,
        }

        supplier = self._extract_supplier(text, subtype)
        if supplier:
            data["fornecedor_nome"] = supplier

        cnpj = self._extract_cnpj(text)
        if cnpj:
            data["cnpj_fornecedor"] = cnpj

        doc_number = self._extract_document_number(text, subtype)
        if doc_number:
            data["numero_documento"] = doc_number

        install = self._extract_installation(text)
        if install:
            data["instalacao"] = install

        value = self._extract_value(text)
        if value > 0:
            data["valor_total"] = value

        due_date = self._extract_due_date(text)
        if due_date:
            data["vencimento"] = due_date
            
        issue_date = self._extract_issue_date(text)
        if issue_date:
            data["data_emissao"] = issue_date

        logger.info(
            f"UtilityBillExtractor: extração concluída "
            f"(subtipo={subtype}, fornecedor={supplier}, doc={doc_number})"
        )
        return data
