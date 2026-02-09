"""
Extrator específico para faturas da TIM S.A.

Detecta e extrai dados de faturas de telecomunicações da TIM, incluindo:
- Faturas de telefonia móvel (pós-pago)
- Faturas empresariais (TIM Black Empresa)
- Notas Fiscais de Serviços de Telecomunicações

Identificadores:
- CNPJ: 02.421.421/0001-11 (matriz) e filiais
- Nome: TIM S.A.
"""

import logging
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import parse_date_br


@register_extractor
class TIMFaturaExtractor(BaseExtractor):
    """Extrator específico para faturas TIM S.A."""

    # CNPJs conhecidos da TIM (matriz e principais filiais)
    TIM_CNPJS = [
        "02.421.421/0001-11",  # Matriz
        "02.421.421/0020-84",  # Filial Belo Horizonte
        "02.421.421/0012-97",  # Filial São Paulo
        "02.421.421/0014-59",  # Filial Rio de Janeiro
    ]

    # Padrões de identificação TIM
    TIM_IDENTIFIERS = [
        r"TIM\s*S\.?\s*A\.?",
        r"FATURA\s+DE\s+PAGAMENTO[:\s]*\d+",
        r"CNPJ\s+da\s+Matriz[:\s]*02\.421\.421",
        r"contatim@faturadatim\.com\.br",
        r"Tim\s+Black\s+Empresa",
        r"\*144\s+do\s+seu\s+TIM",
        r"www\.tim\.com\.br",
        r"Meu\s+TIM",
    ]

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Verifica se o documento é uma fatura da TIM.

        Critérios:
        1. Contém CNPJ da TIM (02.421.421/XXXX-XX)
        2. Contém "TIM S.A." + indicadores de fatura
        3. Contém múltiplos padrões exclusivos TIM

        Args:
            text: Texto extraído do PDF

        Returns:
            True se for fatura TIM
        """
        if not text:
            return False

        text_upper = text.upper()

        # 1. Verifica CNPJ da TIM (padrão 02.421.421)
        if re.search(r"02\.?421\.?421[/\-]?\d{4}[\-]?\d{2}", text):
            logging.debug("TIMFaturaExtractor: CNPJ da TIM detectado")
            return True

        # 2. Verifica nome TIM S.A. + indicadores de fatura
        tim_name_patterns = [
            r"TIM\s*S\.?\s*A\.?",
            r"TIMS\.A\.",  # OCR às vezes junta
        ]

        has_tim_name = any(re.search(p, text_upper) for p in tim_name_patterns)

        if has_tim_name:
            fatura_indicators = [
                "FATURA DE PAGAMENTO",
                "FATURA:",
                "VENCIMENTO",
                "DÉBITO AUTOMÁTICO",
                "TIM BLACK",
            ]
            if any(ind in text_upper for ind in fatura_indicators):
                logging.debug("TIMFaturaExtractor: Nome TIM + indicadores de fatura")
                return True

        # 3. Score de padrões exclusivos
        score = 0
        for pattern in cls.TIM_IDENTIFIERS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 1

        if score >= 2:
            logging.debug(f"TIMFaturaExtractor: {score} padrões TIM detectados")
            return True

        return False

    def extract(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extrai dados da fatura TIM.

        Campos extraídos:
        - fornecedor_nome: "TIM S.A."
        - cnpj_fornecedor: CNPJ da TIM
        - numero_documento: Número da fatura de pagamento
        - valor_total: Valor total a pagar
        - vencimento: Data de vencimento
        - data_emissao: Data de emissão

        Args:
            text: Texto extraído do PDF
            context: Contexto adicional (opcional)

        Returns:
            Dicionário com campos extraídos
        """
        logger = logging.getLogger(__name__)
        logger.info("TIMFaturaExtractor: iniciando extração")

        data: Dict[str, Any] = {
            "tipo_documento": "UTILITY_BILL",
            "subtipo": "TELECOM",
            "fornecedor_nome": "TIM S.A.",
        }

        # Extrai CNPJ
        cnpj = self._extract_cnpj(text)
        if cnpj:
            data["cnpj_fornecedor"] = cnpj

        # Extrai número da fatura
        numero = self._extract_numero_fatura(text)
        if numero:
            data["numero_documento"] = numero

        # Extrai valor
        valor = self._extract_valor(text)
        if valor > 0:
            data["valor_total"] = valor

        # Extrai vencimento
        vencimento = self._extract_vencimento(text)
        if vencimento:
            data["vencimento"] = vencimento

        # Extrai data de emissão
        emissao = self._extract_data_emissao(text)
        if emissao:
            data["data_emissao"] = emissao

        # Extrai cliente (para referência)
        cliente = self._extract_cliente(text)
        if cliente:
            data["cliente"] = cliente

        logger.info(
            f"TIMFaturaExtractor: extração concluída "
            f"(valor={valor}, vencimento={vencimento}, fatura={numero})"
        )
        return data

    def _extract_cnpj(self, text: str) -> Optional[str]:
        """Extrai CNPJ da TIM."""
        # Padrão específico para CNPJ TIM
        patterns = [
            r"CNPJ[:\s]*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
            r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Verifica se é CNPJ da TIM (02.421.421)
                if match.startswith("02.421.421"):
                    return match

        return None

    def _extract_numero_fatura(self, text: str) -> Optional[str]:
        """Extrai número da fatura de pagamento."""
        patterns = [
            # Fatura de pagamento principal
            r"FATURA\s+DE\s+PAGAMENTO[:\s]*(\d+)",
            r"FATURA[:\s]*(\d{10,})",
            # Número do cliente
            r"CLIENTE[:\s]*([\d\.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                numero = match.group(1).replace(".", "")
                if len(numero) >= 7:  # Números de fatura TIM têm pelo menos 7 dígitos
                    return numero

        return None

    def _extract_valor(self, text: str) -> float:
        """Extrai valor total da fatura."""
        # Padrões específicos TIM - valor aparece logo no início
        patterns = [
            # Valor destacado no cabeçalho (ex: "R$ 221,62" logo após endereço)
            r"Floresta\s*-\s*Belo\s+Horizonte\s*-\s*MG\s*\n?\s*R?\$?\s*([\d.]+,\d{2})",
            # Valor após CNPJ no cabeçalho
            r"MG\s*\n?\s*R?\$?\s*([\d.]+,\d{2})",
            # Padrão genérico com R$
            r"R\$\s*([\d.]+,\d{2})",
            # Valor após "VALOR" em tabela
            r"VALOR\s*\n?\s*R?\$?\s*([\d.]+,\d{2})",
        ]

        valores_encontrados = []

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    valor_str = match.replace(".", "").replace(",", ".")
                    valor = float(valor_str)
                    if valor > 0:
                        valores_encontrados.append(valor)
                except (ValueError, AttributeError):
                    continue

        # Retorna o primeiro valor significativo encontrado (geralmente o total no cabeçalho)
        if valores_encontrados:
            # Filtra valores muito pequenos ou muito grandes
            valores_validos = [v for v in valores_encontrados if 1 < v < 100000]
            if valores_validos:
                return valores_validos[0]

        return 0.0

    def _extract_vencimento(self, text: str) -> Optional[str]:
        """Extrai data de vencimento."""
        # Padrões específicos TIM
        patterns = [
            # Label VENCIMENTO seguido de data (layout padrão TIM)
            r"VENCIMENTO\s*\n?\s*(\d{2}/\d{2}/\d{4})",
            # Vencimento com espaços (OCR mal formatado)
            r"V\s*E\s*N\s*C\s*I\s*M\s*E\s*N\s*T\s*[Oo]?\s*\n?\s*(\d{2}/\d{2}/\d{4})",
            # Data após "DATA DE VENCIMENTO"
            r"DATA\s+DE\s+VENCIMENTO\s*[:\s]*(\d{2}/\d{2}/\d{4})",
            # Tabela com vencimento na última coluna
            r"VENCIMENTO\s+VALOR\s*\n.*?(\d{2}/\d{2}/\d{4})",
            # Padrão genérico após label
            r"(?:Vencimento|VENCIMENTO)[:\s]+(\d{2}[/\.]\d{2}[/\.]\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                date_str = match.group(1)
                date = parse_date_br(date_str)
                if date:
                    return date

        # Fallback: procura padrão "MM/YYYY DD/MM/YYYY" em linha de totais
        # Ex: "OUT/2025 01/10/2025 15/10/2025 R$ 221,62"
        fallback_pattern = (
            r"[A-Z]{3}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+(\d{2}/\d{2}/\d{4})\s+R?\$"
        )
        match = re.search(fallback_pattern, text)
        if match:
            date = parse_date_br(match.group(1))
            if date:
                return date

        return None

    def _extract_data_emissao(self, text: str) -> Optional[str]:
        """Extrai data de emissão."""
        patterns = [
            r"EMISS[ÃA]O[:\s]*(\d{2}/\d{2}/\d{4})",
            r"DATA\s+DE\s+EMISS[ÃA]O[:\s]*(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date = parse_date_br(match.group(1))
                if date:
                    return date

        return None

    def _extract_cliente(self, text: str) -> Optional[str]:
        """Extrai nome do cliente."""
        # Padrão: nome em caixa alta após header TIM
        patterns = [
            r"FATURA[:\s]*\d+\s*\n?\s*([A-ZÀ-Ú\s]+(?:SA|LTDA|ME|EPP)?)\s*\n",
            r"(?:Olá,?\s*)?([A-ZÀ-Ú][A-ZÀ-Ú\s]+(?:SA|LTDA)?)\s*\n.*?CPF/CNPJ",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                # Limpa e valida
                if len(nome) > 5 and not any(
                    x in nome.upper() for x in ["VENCIMENTO", "EMISSÃO", "FATURA"]
                ):
                    return nome

        return None
