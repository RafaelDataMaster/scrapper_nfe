"""
Extrator especializado para faturas de água da Sabesp.

A Sabesp envia faturas por email onde:
- O PDF é protegido por senha (3 primeiros dígitos do CPF do titular)
- Todos os dados estão no corpo do email HTML

Este extrator processa o corpo do email para extrair:
- Valor da fatura
- Data de vencimento
- Número de fornecimento (instalação)
- Código de barras
- Unidade/localidade

Retorna tipo_documento="UTILITY_BILL" com subtipo="WATER".
"""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SabespWaterBillExtractor:
    """
    Extrator para faturas de água da Sabesp via corpo de email.

    Não é registrado no EXTRACTOR_REGISTRY pois não processa texto de PDF.
    É chamado diretamente pelo BatchProcessor quando detecta email da Sabesp.

    Características do email Sabesp:
    - Sender: fatura_sabesp@sabesp.com.br ou similar
    - Subject: "Sabesp - Fatura por e-mail"
    - Body HTML com dados estruturados em tags <b>
    """

    # Padrões para identificar email da Sabesp
    SABESP_SENDERS = [
        "sabesp.com.br",
        "fatura_sabesp",
        "fatura.sabesp",
        "noreply@sabesp",
    ]

    SABESP_SUBJECTS = [
        "sabesp",
        "fatura por e-mail",
        "sua fatura digital",
    ]

    @classmethod
    def can_handle_email(
        cls,
        email_subject: Optional[str] = None,
        email_sender: Optional[str] = None,
        email_body: Optional[str] = None,
    ) -> bool:
        """
        Verifica se o email é da Sabesp.

        Args:
            email_subject: Assunto do email
            email_sender: Endereço do remetente
            email_body: Corpo do email

        Returns:
            True se é um email da Sabesp
        """
        # Verifica sender
        if email_sender:
            sender_lower = email_sender.lower()
            for pattern in cls.SABESP_SENDERS:
                if pattern in sender_lower:
                    return True

        # Verifica subject
        if email_subject:
            subject_lower = email_subject.lower()
            for pattern in cls.SABESP_SUBJECTS:
                if pattern in subject_lower:
                    return True

        # Verifica corpo (fallback)
        if email_body:
            body_lower = email_body.lower()
            # Detecta "sabesp" explícito
            if "sabesp" in body_lower and "fornecimento" in body_lower:
                return True
            # Detecta padrão típico de fatura Sabesp (mesmo sem mencionar o nome)
            # O email Sabesp tem: Fornecimento + Unidade + Vencimento + Valor
            sabesp_indicators = [
                "fornecimento" in body_lower,
                "unidade" in body_lower,
                "vencimento" in body_lower,
                "valor" in body_lower,
            ]
            # Se tem 3+ indicadores, é provavelmente Sabesp
            if sum(sabesp_indicators) >= 3:
                return True

        return False

    def extract(
        self,
        email_body: str,
        email_subject: Optional[str] = None,
        email_sender: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extrai dados da fatura Sabesp do corpo do email.

        Args:
            email_body: Corpo do email (HTML ou texto)
            email_subject: Assunto do email (opcional)
            email_sender: Remetente (opcional)

        Returns:
            Dicionário com dados extraídos
        """
        logger.info("SabespWaterBillExtractor: iniciando extração do corpo do email")

        data: Dict[str, Any] = {
            "tipo_documento": "UTILITY_BILL",
            "subtipo": "WATER",
            "fornecedor_nome": "SABESP",
        }

        # Extrai valor
        valor = self._extract_valor(email_body)
        if valor:
            data["valor_total"] = valor

        # Extrai vencimento
        vencimento = self._extract_vencimento(email_body)
        if vencimento:
            data["vencimento"] = vencimento

        # Extrai número de fornecimento (como numero_documento)
        fornecimento = self._extract_fornecimento(email_body)
        if fornecimento:
            data["numero_documento"] = fornecimento
            data["instalacao"] = fornecimento

        # Extrai código de barras
        codigo_barras = self._extract_codigo_barras(email_body)
        if codigo_barras:
            data["linha_digitavel"] = codigo_barras

        # Extrai unidade/localidade
        unidade = self._extract_unidade(email_body)
        if unidade:
            data["observacoes"] = f"Unidade: {unidade}"

        # CNPJ da Sabesp (fixo)
        data["cnpj_fornecedor"] = "43.776.517/0001-80"

        logger.info(
            f"SabespWaterBillExtractor: extração concluída "
            f"(valor={data.get('valor_total')}, venc={data.get('vencimento')}, "
            f"fornec={data.get('numero_documento')})"
        )

        return data

    def _extract_valor(self, text: str) -> Optional[float]:
        """Extrai valor da fatura."""
        # Padrões específicos do email Sabesp
        patterns = [
            # <b>Valor:</b> R$ 138,56
            r"Valor[:\s]*</b>\s*R\$\s*([\d.]+,\d{2})",
            # Valor: R$ 138,56
            r"Valor[:\s]+R\$\s*([\d.]+,\d{2})",
            # R$ 138,56 (genérico)
            r"R\$\s*([\d.]+,\d{2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    valor_str = match.group(1).replace(".", "").replace(",", ".")
                    valor = float(valor_str)
                    if valor > 0:
                        return valor
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_vencimento(self, text: str) -> Optional[str]:
        """Extrai data de vencimento e converte para formato ISO."""
        patterns = [
            # <b>Vencimento:</b> 20/01/2026
            r"Vencimento[:\s]*</b>\s*(\d{2}/\d{2}/\d{4})",
            # Vencimento: 20/01/2026
            r"Vencimento[:\s]+(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Converte DD/MM/YYYY para YYYY-MM-DD
                    parts = date_str.split("/")
                    if len(parts) == 3:
                        return f"{parts[2]}-{parts[1]}-{parts[0]}"
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_fornecimento(self, text: str) -> Optional[str]:
        """Extrai número de fornecimento (instalação)."""
        patterns = [
            # <b>Fornecimento:</b> 86040721896813
            r"Fornecimento[:\s]*</b>\s*(\d{10,20})",
            # Fornecimento: 86040721896813
            r"Fornecimento[:\s]+(\d{10,20})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_codigo_barras(self, text: str) -> Optional[str]:
        """Extrai código de barras."""
        # Padrão: 82660000001 0  38560097091 2  10655945380 3  19573630603 4
        patterns = [
            r"[Cc][óo]digo\s+de\s+barras[:\s]*</b>?\s*<br>?\s*([\d\s]{40,60})",
            r"[Cc][óo]digo\s+de\s+barras[:\s]+([\d\s]{40,60})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Remove espaços extras e formata
                codigo = re.sub(r"\s+", " ", match.group(1)).strip()
                # Remove espaços para formato padrão de linha digitável
                codigo_limpo = codigo.replace(" ", "")
                if len(codigo_limpo) >= 44:
                    return codigo_limpo
                return codigo

        return None

    def _extract_unidade(self, text: str) -> Optional[str]:
        """Extrai unidade/localidade."""
        patterns = [
            # <b>Unidade:</b> TAUBATE
            r"Unidade[:\s]*</b>\s*([A-Z\s]+?)(?:<|$|\n)",
            # Unidade: TAUBATE
            r"Unidade[:\s]+([A-Z\s]+?)(?:<|$|\n)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                unidade = match.group(1).strip()
                if unidade and len(unidade) >= 3:
                    return unidade.upper()

        return None


def extract_sabesp_from_email(
    email_body: str,
    email_subject: Optional[str] = None,
    email_sender: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Função helper para extrair dados de email Sabesp.

    Args:
        email_body: Corpo do email
        email_subject: Assunto (opcional)
        email_sender: Remetente (opcional)

    Returns:
        Dicionário com dados ou None se não for Sabesp
    """
    if not SabespWaterBillExtractor.can_handle_email(
        email_subject=email_subject,
        email_sender=email_sender,
        email_body=email_body,
    ):
        return None

    extractor = SabespWaterBillExtractor()
    return extractor.extract(
        email_body=email_body,
        email_subject=email_subject,
        email_sender=email_sender,
    )
