"""
Extrator para NFCom (Nota Fiscal de Comunicação Eletrônica).

Este módulo implementa a extração de dados de NFCom, que é um documento
fiscal eletrônico específico para serviços de comunicação (telecomunicações,
internet, TV por assinatura, etc.).

A NFCom é diferente de:
- NFSe (serviços genéricos municipais)
- NFe/DANFE (produtos)
- Boletos (mesmo tendo linha digitável para pagamento)

Campos extraídos:
    - numero_nota: Número da NFCom
    - serie_nf: Série do documento
    - valor_total: Valor total do serviço
    - data_emissao: Data de emissão
    - vencimento: Data de vencimento
    - cnpj_prestador: CNPJ do emitente (prestador)
    - fornecedor_nome: Razão social do emitente
    - chave_acesso: Chave de acesso de 44 dígitos

Critérios de classificação:
    - "NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO"
    - "NFCOM" ou "NF-COM"
    - "SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA"
    - Presença de chave de acesso + contexto de comunicação

Example:
    >>> from extractors.nfcom import NFComExtractor
    >>> if NFComExtractor.can_handle(texto):
    ...     dados = NFComExtractor().extract(texto)
    ...     print(f"Valor: R$ {dados['valor_total']:.2f}")
"""

import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import (
    normalize_entity_name,
    parse_br_money,
    parse_date_br,
    strip_accents,
)


def _compact(text: str) -> str:
    """Remove espaços e caracteres especiais, mantém apenas A-Z e 0-9."""
    return re.sub(r"[^A-Z0-9]+", "", strip_accents((text or "").upper()))


@register_extractor
class NFComExtractor(BaseExtractor):
    """
    Extrator especializado em NFCom (Nota Fiscal de Comunicação Eletrônica).

    Identifica e extrai campos específicos de notas fiscais de telecomunicações:
    - Número e série da nota
    - CNPJ e razão social do prestador
    - Valor total do serviço
    - Data de emissão e vencimento
    - Chave de acesso
    """

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Verifica se o documento é uma NFCom (Nota Fiscal de Comunicação).

        NFCom é identificada pelo início do documento - se começa com
        "DOC. AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO",
        é uma NFCom mesmo que contenha linha digitável para pagamento.

        A ordem de verificação é importante:
        1. Primeiro verifica se o INÍCIO do documento indica NFCom
        2. Se sim, retorna True (ignora indicadores de boleto)
        3. Se não, verifica exclusões e outras heurísticas
        """
        text_upper = (text or "").upper()
        text_compact = _compact(text)

        # ========== VERIFICAÇÃO PRIORITÁRIA: Início do documento ==========
        # Se o documento COMEÇA com indicadores de NFCom, é NFCom
        # (mesmo que tenha linha digitável para pagamento)

        first_500 = text_upper[:500] if len(text_upper) > 500 else text_upper
        first_500_compact = _compact(first_500)

        # NFCom geralmente começa com "DOC. AUXILIAR DA NOTA FISCAL FATURA"
        is_nfcom_by_header = (
            "DOCAUXILIARDANOTAFISCALFATURA" in first_500_compact
            or "DOCUMENTOAUXILIARDANOTAFISCALFATURA" in first_500_compact
            or "NOTAFISCALFATURADESERVICOSDE" in first_500_compact
        )

        if is_nfcom_by_header:
            # Confirma que tem contexto de comunicação
            has_comunicacao = (
                "COMUNICACAO" in text_compact or "COMUNICACAOELETRONICA" in text_compact
            )
            if has_comunicacao:
                return True

        # ========== EXCLUSÕES: Documentos que NÃO são NFCom ==========

        # Boletos puros (sem header de NFCom no início)
        # Se começa com indicadores de boleto, não é NFCom
        first_200_compact = _compact(
            text_upper[:200] if len(text_upper) > 200 else text_upper
        )
        boleto_start_indicators = [
            "RECIBODOPAGADOR",
            "RECIBODOSACADO",
            "BENEFICIARIO",
            "CEDENTE",
        ]
        for indicator in boleto_start_indicators:
            if indicator in first_200_compact:
                return False

        # NFSe tradicional (começa com NFS-E ou prefeitura)
        nfse_start_indicators = [
            "NFSE",
            "NOTAFISCALDESERVICO",
            "PREFEITURA",
            "CODIGODEVERIFICACAO",
        ]
        for indicator in nfse_start_indicators:
            if indicator in first_200_compact:
                return False

        # ========== HEURÍSTICAS SECUNDÁRIAS ==========

        # Documento que menciona NFCom mas não é o documento principal
        # (ex: fatura consolidada que lista NFCom em resumo)
        if "LINHADIGITAVEL" in first_200_compact:
            # Se linha digitável está no início, é boleto, não NFCom
            return False

        # Verificação para NFCom com estrutura diferente
        has_razao_social = "RAZAOSOCIAL" in first_500_compact
        has_comunicacao_eletronica = "COMUNICACAOELETRONICA" in text_compact
        has_chave_44 = bool(re.search(r"\d{44}", re.sub(r"\D", "", text)))

        if has_razao_social and has_comunicacao_eletronica and has_chave_44:
            return True

        return False

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extrai dados estruturados da NFCom.

        Campos extraídos:
        - numero_nota: Número da nota fiscal
        - serie_nf: Série do documento
        - valor_total: Valor total do serviço
        - data_emissao: Data de emissão
        - vencimento: Data de vencimento
        - cnpj_prestador: CNPJ do emitente
        - fornecedor_nome: Razão social do emitente
        - chave_acesso: Chave de acesso de 44 dígitos
        """
        data: Dict[str, Any] = {}
        data["tipo_documento"] = (
            "DANFE"  # NFCom é tratada como DANFE para fins de classificação
        )
        data["doc_type"] = "DANFE"

        # Extrai campos
        data["numero_nota"] = self._extract_numero_nota(text)
        data["serie_nf"] = self._extract_serie(text)
        data["valor_total"] = self._extract_valor_total(text)
        data["data_emissao"] = self._extract_data_emissao(text)
        data["vencimento"] = self._extract_vencimento(text)
        data["cnpj_prestador"] = self._extract_cnpj_prestador(text)
        data["cnpj_emitente"] = data["cnpj_prestador"]  # Alias
        data["fornecedor_nome"] = self._extract_fornecedor_nome(text)
        data["chave_acesso"] = self._extract_chave_acesso(text)

        return data

    def _extract_numero_nota(self, text: str) -> Optional[str]:
        """Extrai número da nota fiscal."""
        patterns = [
            # NOTA FISCAL FATURA Nº: 000053011
            r"(?i)NOTA\s+FISCAL\s+FATURA\s+N[ºO°]?\s*[:\s]*(\d+)",
            # Número/Série: 53011 / 1
            r"(?i)N[úu]mero/S[ée]rie\s*[:\s]*(\d+)\s*/",
            # Número da NFS-e: 53011
            r"(?i)N[úu]mero\s+da\s+NF[S-]*[Ee]?\s*[:\s]*(\d+)",
            # NFCOM Nº 53011
            r"(?i)NFCOM\s+N[ºO°]?\s*[:\s]*(\d+)",
            # Número: 53011
            r"(?i)N[úu]mero\s*[:\s]+(\d{3,})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                numero = match.group(1).lstrip("0") or "0"
                return numero

        return None

    def _extract_serie(self, text: str) -> Optional[str]:
        """Extrai série do documento."""
        patterns = [
            # SÉRIE: 001
            r"(?i)S[ÉE]RIE\s*[:\s]*(\d+)",
            # Número/Série: 53011 / 1
            r"(?i)N[úu]mero/S[ée]rie\s*[:\s]*\d+\s*/\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_valor_total(self, text: str) -> Optional[float]:
        """Extrai valor total do serviço."""
        # Padrões prioritários para valor total
        patterns = [
            # VALOR TOTAL NFCOM R$ 360,00
            r"(?i)VALOR\s+TOTAL\s+NFCOM\s*[:\s]*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            # Total: R$ 360,00
            r"(?i)Total\s*[:\s]*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            # Valor Total R$ 360,00
            r"(?i)Valor\s+Total\s*[:\s]*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            # Vencimento: 20/01/2026 Total: R$ 360,00
            r"(?i)Vencimento.*?Total\s*[:\s]*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                valor = parse_br_money(match.group(1))
                if valor > 0:
                    return valor

        # Fallback: procura valores R$ e retorna o maior
        valores = re.findall(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})", text)
        if valores:
            valores_float = [parse_br_money(v) for v in valores]
            valores_validos = [v for v in valores_float if v > 0]
            if valores_validos:
                return max(valores_validos)

        return None

    def _extract_data_emissao(self, text: str) -> Optional[str]:
        """Extrai data de emissão."""
        patterns = [
            # DATA DE EMISSÃO: 02/01/2026
            r"(?i)DATA\s+DE\s+EMISS[ÃA]O\s*[:\s]*(\d{2}/\d{2}/\d{4})",
            # Emissão: 02/01/2026
            r"(?i)Emiss[ãa]o\s*[:\s]*(\d{2}/\d{2}/\d{4})",
            # Emitida em: 02/01/2026
            r"(?i)Emitida\s+em\s*[:\s]*(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return parse_date_br(match.group(1))

        return None

    def _extract_vencimento(self, text: str) -> Optional[str]:
        """Extrai data de vencimento."""
        patterns = [
            # Vencimento: 20/01/2026
            r"(?i)Vencimento\s*[:\s]*(\d{2}/\d{2}/\d{4})",
            # Data de Vencimento: 20/01/2026
            r"(?i)Data\s+de\s+Vencimento\s*[:\s]*(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return parse_date_br(match.group(1))

        return None

    def _extract_cnpj_prestador(self, text: str) -> Optional[str]:
        """Extrai CNPJ do emitente/prestador."""
        # Procura CNPJ próximo a "RAZÃO SOCIAL" ou no início do documento
        patterns = [
            # CNPJ: 14.481.936/0001-96
            r"(?i)CNPJ\s*[:\s]*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
            # Formato compacto
            r"(?i)CNPJ\s*[:\s]*(\d{14})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                cnpj = match.group(1)
                # Formata se necessário
                if len(cnpj) == 14 and "/" not in cnpj:
                    cnpj = (
                        f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
                    )
                return cnpj

        return None

    def _extract_fornecedor_nome(self, text: str) -> Optional[str]:
        """Extrai razão social do emitente/fornecedor."""
        patterns = [
            # RAZÃO SOCIAL: WN TELECOM LTDA (para antes de ENDEREÇO ou quebra de linha)
            r"(?i)RAZ[ÃA]O\s+SOCIAL\s*[:\s]*([A-ZÀ-Ú][A-ZÀ-Ú0-9\s\-\.]+?(?:LTDA|S\.?A\.?|ME|EPP|EIRELI))",
            # Empresa: WN TELECOM LTDA
            r"(?i)Empresa\s*[:\s]*([A-ZÀ-Ú][A-ZÀ-Ú0-9\s\-\.]+?(?:LTDA|S\.?A\.?|ME|EPP|EIRELI))",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                nome = match.group(1).strip()
                # Limpa e normaliza
                nome = re.sub(r"\s+", " ", nome)

                # Remove palavras que não fazem parte do nome
                stop_words = [
                    "ENDEREÇO",
                    "ENDERECO",
                    "CNPJ",
                    "CPF",
                    "IE",
                    "IM",
                    "TELEFONE",
                ]
                for stop in stop_words:
                    if stop in nome.upper():
                        idx = nome.upper().find(stop)
                        nome = nome[:idx].strip()

                if len(nome) > 3:
                    return normalize_entity_name(nome)

        return None

    def _extract_chave_acesso(self, text: str) -> Optional[str]:
        """Extrai chave de acesso de 44 dígitos."""
        # Remove espaços e caracteres não numéricos, depois procura 44 dígitos
        text_only_digits = re.sub(r"\D", "", text)

        # Procura sequência de 44 dígitos
        match = re.search(r"(\d{44})", text_only_digits)
        if match:
            return match.group(1)

        return None
