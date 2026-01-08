"""
Extrator otimizado para boletos SICOOB/BANCOOB (banco 756).

Este módulo trata boletos emitidos pelo sistema cooperativo SICOOB,
aplicando correções pontuais na identificação do beneficiário/fornecedor
que o extrator genérico de boleto não consegue tratar corretamente.

Problemas corrigidos:
    - fornecedor_nome: Captura incorreta de labels como "CPF/CNPJ"
    - banco_nome: Forçado como "SICOOB" quando OCR falha
    - Caso específico: Beneficiário "Camargo e Silva"

Critérios de ativação:
    - Texto contém "SICOOB", "BANCOOB" ou código 756
    - Indicadores de boleto presentes (linha digitável, etc.)

Example:
    >>> from extractors.sicoob import SicoobExtractor
    >>> if SicoobExtractor.can_handle(texto):
    ...     dados = SicoobExtractor().extract(texto)
    ...     print(f"Banco: {dados['banco_nome']}")  # SICOOB
"""
import re
from typing import Any, Dict

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import strip_accents


def _compact(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", strip_accents((text or "").upper()))


@register_extractor
class SicoobExtractor(BaseExtractor):
    """Extrator otimizado para boletos SICOOB/BANCOOB (banco 756).

    Mantém a extração genérica do boleto e aplica correções pontuais
    na identificação do beneficiário/fornecedor.
    """

    @classmethod
    def can_handle(cls, text: str) -> bool:
        text_compact = _compact(text)

        # Assinaturas fortes
        has_bank = (
            "SICOOB" in text_compact
            or "BANCOOB" in text_compact
            or "7560" in text_compact  # ex: "756-0" compactado
            or "756" in text_compact and "LINHADIGITAVEL" in text_compact
        )

        # Confirma sinais mínimos de boleto para evitar pegar docs aleatórios.
        boleto_markers = [
            "LINHADIGITAVEL",
            "BENEFICI",
            "VENCIMENTO",
            "VALORDODOCUMENTO",
            "CODIGODEBARRAS",
        ]
        markers_score = sum(1 for kw in boleto_markers if kw in text_compact)

        return bool(has_bank and markers_score >= 1)

    def extract(self, text: str) -> Dict[str, Any]:
        # Lazy import para preservar ordem de registro no EXTRACTOR_REGISTRY.
        from extractors.boleto import BoletoExtractor

        generic = BoletoExtractor()
        data = generic.extract(text)

        # === Correções específicas SICOOB ===
        raw_text = text or ""

        fornecedor = (data.get("fornecedor_nome") or "").strip()
        if (not fornecedor) or len(fornecedor) < 5 or re.search(r"(?i)\bCPF\b|\bCNPJ\b|\bBENEFICI", fornecedor):
            # Captura bloco entre "Beneficiário" e "Agência/CNPJ/CPF".
            # Usa DOTALL para tolerar OCR quebrando linhas.
            m = re.search(
                r"(?is)\bBenefici[aá]rio\b\s*[:\-]?\s*(.+?)\s*(?:\bAg[êe]ncia\b|\bCNPJ\b|\bCPF\b)",
                raw_text,
            )
            if m:
                cand = m.group(1)
                # Limpeza: remove CNPJ/CPF, números e excesso de whitespace.
                cand = re.sub(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", " ", cand)
                cand = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", " ", cand)
                cand = re.sub(r"[\d\./\-]+", " ", cand)
                cand = re.sub(r"\s+", " ", cand).strip(" -:;\n\r\t")
                if len(cand) >= 4:
                    data["fornecedor_nome"] = cand

        # Força banco_nome em casos onde OCR não bate com NOMES_BANCOS
        data["banco_nome"] = "SICOOB"

        # Caso específico: Camargo e Silva (heurística conservadora)
        if "CAMARGO" in (raw_text or "").upper() and "SILVA" in (raw_text or "").upper():
            m = re.search(r"(?i)\b(CAMARGO\s+E\s+SILVA\s+[^\n\r0-9]{3,80})\b", raw_text)
            if m:
                data["fornecedor_nome"] = m.group(1).strip()

        return data
