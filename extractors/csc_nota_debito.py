"""
Extrator especializado para documentos CSC GESTAO INTEGRADA S/A.

Este módulo processa documentos do tipo "NOTA DÉBITO / RECIBO FATURA" emitidos
pela CSC GESTAO INTEGRADA S/A (CNPJ: 38.323.227/0001-40).

Estes documentos são usados para cobrança de tarifas bancárias (Bradesco, Itaú, Sicoob)
e são enviados por Linnia Barreto (linnia.barreto@soumaster.com.br) como "Reembolso de Tarifas CSC".

Formato típico do documento:
- Cabeçalho: "NOTA DÉBITO / RECIBO FATURA (AR)"
- Numero: 347, 348, etc.
- CNPJ emissor: 38.323.227/0001-40
- Dados do emissor: CSC GESTAO INTEGRADA S/A
- Data de Emissão e Competência
- Tomador com CNPJ
- Itens com descrição, quantidade, preço unitário e total
- VALOR TOTAL em destaque

Campos extraídos:
- tipo_documento: "OUTRO" (não é NFSe nem boleto)
- subtipo: "NOTA_DEBITO"
- numero_documento: Número da nota (ex: 347)
- fornecedor_nome: CSC GESTAO INTEGRADA S/A
- cnpj_fornecedor: 38.323.227/0001-40
- data_emissao: Data de emissão (formato ISO)
- competencia: Mês/ano de competência
- tomador_nome: Nome do tomador/cliente
- cnpj_tomador: CNPJ do tomador/cliente
- valor_total: Valor total da nota
- observacoes: Descrição dos itens

Example:
    >>> from extractors.csc_nota_debito import CscNotaDebitoExtractor
    >>> if CscNotaDebitoExtractor.can_handle(texto):
    ...     dados = CscNotaDebitoExtractor().extract(texto)
    ...     print(f"Nota: {dados['numero_documento']} - R$ {dados['valor_total']:.2f}")
"""

import logging
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import normalize_entity_name, parse_date_br

logger = logging.getLogger(__name__)


def _compact(text: str) -> str:
    """Compacta texto removendo caracteres não alfanuméricos e acentos."""
    import unicodedata

    text_normalized = unicodedata.normalize("NFKD", text or "")
    text_ascii = text_normalized.encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"[^A-Z0-9]+", "", text_ascii.upper())


@register_extractor
class CscNotaDebitoExtractor(BaseExtractor):
    """
    Extrator especializado em documentos NOTA DÉBITO / RECIBO FATURA da CSC.

    Identifica e extrai campos específicos de notas de débito/recibo fatura
    emitidas pela CSC GESTAO INTEGRADA S/A para cobrança de tarifas bancárias.
    """

    # CNPJ fixo da CSC GESTAO INTEGRADA S/A
    CSC_CNPJ = "38.323.227/0001-40"
    CSC_CNPJ_LIMPO = "38323227000140"
    CSC_NOME = "CSC GESTAO INTEGRADA S/A"

    # Padrões de identificação do documento
    # Nota: alguns PDFs têm OCR com espaços entre letras: "N O T A D É B I T O"
    IDENTIFICADORES = [
        r"NOTA\s+D[ÉE]BITO\s*/\s*RECIBO\s+FATURA",
        r"NOTA\s+D[ÉE]BITO",
        r"RECIBO\s+FATURA\s*\(AR\)",
        # Padrões com espaços entre letras (OCR variável)
        r"N\s*O\s*T\s*A\s+D\s*[ÉE]\s*B\s*I\s*T\s*O",
    ]

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Verifica se o documento é uma Nota Débito/Recibo Fatura da CSC.

        Critérios:
        - Contém "NOTA DÉBITO / RECIBO FATURA" ou variantes
        - Contém CNPJ da CSC (38.323.227/0001-40)
        - Contém "CSC GESTAO" no texto
        - Não é NFSe, DANFE ou boleto bancário

        Args:
            text: Texto completo do documento

        Returns:
            True se for Nota Débito/Recibo Fatura da CSC, False caso contrário
        """
        if not text:
            return False

        text_upper = text.upper()
        text_compact = _compact(text)

        # Verificar identificadores principais
        has_nota_debito = False
        for pattern in cls.IDENTIFICADORES:
            if re.search(pattern, text_upper, re.IGNORECASE):
                has_nota_debito = True
                break

        if not has_nota_debito:
            return False

        # Verificar presença do CNPJ ou nome da CSC
        has_csc = (
            cls.CSC_CNPJ in text
            or cls.CSC_CNPJ_LIMPO in text_compact
            or "CSCGESTAO" in text_compact
            or "CSC GESTAO" in text_upper
        )

        if not has_csc:
            return False

        # EXCLUSÕES: Não deve ser documento fiscal padrão ou boleto
        exclusion_patterns = [
            r"DANFE",
            r"DOCUMENTO\s+AUXILIAR\s+DA\s+NF",
            r"NFS-?E\s+(?:N[ºO°]|NÚMERO)",
            r"NOTA\s+FISCAL\s+(?:ELETR[ÔO]NICA|DE\s+SERVI[ÇC]O)",
            r"CHAVE\s+DE\s+ACESSO",
            r"LINHA\s+DIGIT[ÁA]VEL",
            r"C[ÓO]DIGO\s+DE\s+BARRAS",
            r"RECIBO\s+DO\s+SACADO",
            r"FICHA\s+DE\s+COMPENSA[ÇC][ÃA]O",
        ]

        for pattern in exclusion_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                logger.debug(
                    f"CscNotaDebitoExtractor: rejeitado - padrão de exclusão: {pattern}"
                )
                return False

        logger.debug("CscNotaDebitoExtractor: documento aceito para processamento")
        return True

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extrai dados estruturados da Nota Débito/Recibo Fatura.

        Args:
            text: Texto completo do documento

        Returns:
            Dicionário com campos extraídos
        """
        data: Dict[str, Any] = {
            "tipo_documento": "OUTRO",
            "doc_type": "OUTRO",
            "subtipo": "NOTA_DEBITO",
        }

        # Fornecedor (CSC) - dados fixos
        data["fornecedor_nome"] = self.CSC_NOME
        data["cnpj_fornecedor"] = self.CSC_CNPJ

        # Extrair número do documento
        numero = self._extract_numero(text)
        if numero:
            data["numero_documento"] = numero
            data["numero_nota"] = numero

        # Extrair data de emissão
        data_emissao = self._extract_data_emissao(text)
        if data_emissao:
            data["data_emissao"] = data_emissao

        # Extrair competência
        competencia = self._extract_competencia(text)
        if competencia:
            data["competencia"] = competencia

        # Extrair dados do tomador
        tomador_nome, cnpj_tomador = self._extract_tomador(text)
        if tomador_nome:
            data["tomador_nome"] = tomador_nome
        if cnpj_tomador:
            data["cnpj_tomador"] = cnpj_tomador

        # Extrair valor total
        valor = self._extract_valor_total(text)
        if valor:
            data["valor_total"] = valor
            data["valor_documento"] = valor

        # Extrair itens/descrição como observações
        observacoes = self._extract_itens(text)
        if observacoes:
            data["observacoes"] = observacoes

        logger.info(
            f"CscNotaDebitoExtractor: documento processado - "
            f"numero: {data.get('numero_documento')}, "
            f"valor: R$ {data.get('valor_total', 0):.2f}, "
            f"tomador: {data.get('tomador_nome', 'N/A')}"
        )

        return data

    def _extract_numero(self, text: str) -> Optional[str]:
        """
        Extrai número do documento.

        Padrões:
        - "Numero: 347"
        - "Número: 347"
        - "N°: 347"

        Args:
            text: Texto do documento

        Returns:
            Número do documento ou None
        """
        patterns = [
            r"N[úu]mero\s*:\s*(\d+)",
            r"N[ºo°]\s*:\s*(\d+)",
            r"NOTA\s+D[ÉE]BITO.*?N[ºo°]\s*:?\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_data_emissao(self, text: str) -> Optional[str]:
        """
        Extrai data de emissão e converte para formato ISO.

        Padrões:
        - "Emissão: 07/01/2026"
        - "Data Emissão: 07/01/2026"

        Args:
            text: Texto do documento

        Returns:
            Data no formato YYYY-MM-DD ou None
        """
        patterns = [
            r"Emiss[ãa]o\s*:\s*(\d{2}/\d{2}/\d{4})",
            r"Data\s+(?:de\s+)?Emiss[ãa]o\s*:\s*(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Converte DD/MM/YYYY para YYYY-MM-DD
                parts = date_str.split("/")
                if len(parts) == 3:
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"

        # Fallback: usar parse_date_br
        lines = text.split("\n")
        for line in lines:
            if "emiss" in line.lower():
                date_obj = parse_date_br(line)
                if date_obj:
                    return date_obj

        return None

    def _extract_competencia(self, text: str) -> Optional[str]:
        """
        Extrai competência (mês/ano de referência).

        Padrões:
        - "Competência: dezembro-25"
        - "Competência: 12/2025"
        - "Competência: dez/2025"

        Args:
            text: Texto do documento

        Returns:
            Competência no formato original ou None
        """
        patterns = [
            r"Compet[êe]ncia\s*:\s*([a-zA-Zç]+[-/]?\d{2,4})",
            r"Compet[êe]ncia\s*:\s*(\d{2}/\d{4})",
            r"Compet[êe]ncia\s*:\s*(\d{2}/\d{2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_tomador(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extrai dados do tomador (cliente).

        O formato típico é:
        Tomador:
        ATIVE TELECOMUNICAÇÕES S.A.
        33.960.847/0001-77

        Args:
            text: Texto do documento

        Returns:
            Tupla (nome_tomador, cnpj_tomador)
        """
        tomador_nome = None
        cnpj_tomador = None

        lines = text.split("\n")

        # Procurar seção do tomador
        tomador_index = None
        for i, line in enumerate(lines):
            if "Tomador:" in line or "TOMADOR:" in line.upper():
                tomador_index = i
                break

        if tomador_index is not None:
            # Procurar nome nas próximas linhas (ignorar linhas vazias)
            for offset in range(1, 5):
                if tomador_index + offset >= len(lines):
                    break

                check_line = lines[tomador_index + offset].strip()
                if not check_line:
                    continue

                # Se for CNPJ, extrair
                cnpj_match = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", check_line)
                if cnpj_match:
                    cnpj_tomador = cnpj_match.group(1)
                    continue

                # Se não for CNPJ e não tiver nome ainda, é o nome
                if not tomador_nome and len(check_line) > 5:
                    # Ignorar linhas que parecem ser campos do formulário
                    if not any(
                        x in check_line.upper()
                        for x in [
                            "PREÇO",
                            "ITEM",
                            "DESCRIÇÃO",
                            "QUANT",
                            "UNIT",
                            "TOTAL",
                        ]
                    ):
                        tomador_nome = normalize_entity_name(check_line)

        return tomador_nome, cnpj_tomador

    def _extract_valor_total(self, text: str) -> Optional[float]:
        """
        Extrai valor total do documento.

        Padrões:
        - "VALOR TOTAL R$ 2.163,60"
        - "VALOR TOTAL: R$ 2.163,60"
        - "Total: R$ 2.163,60"

        Args:
            text: Texto do documento

        Returns:
            Valor como float ou None
        """
        patterns = [
            r"VALOR\s+TOTAL\s*:?\s*R\$\s*([\d.]+,\d{2})",
            r"TOTAL\s*:?\s*R\$\s*([\d.]+,\d{2})",
            r"VALOR\s+TOTAL\s+([\d.]+,\d{2})",
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

        # Fallback: procurar último valor monetário significativo
        all_values = re.findall(r"R\$\s*([\d.]+,\d{2})", text)
        non_zero_values = []
        for val_str in all_values:
            try:
                val = float(val_str.replace(".", "").replace(",", "."))
                if val > 0:
                    non_zero_values.append(val)
            except ValueError:
                continue

        # Retornar o maior valor (geralmente é o total)
        if non_zero_values:
            return max(non_zero_values)

        return None

    def _extract_itens(self, text: str) -> Optional[str]:
        """
        Extrai descrição dos itens como observações.

        Formato típico:
        Item Descrição Quant. Unit. Total
        1 Boletos Impressos 384 3,00 1.152,00
        3 Boletos online 1600 0,60 960,00

        Args:
            text: Texto do documento

        Returns:
            Descrição consolidada dos itens ou None
        """
        itens = []

        # Padrão para linha de item: número + descrição + valores
        pattern = r"^\s*\d+\s+([A-Za-zÀ-ÿ\s/]+?)\s+(\d+)\s+([\d.,]+)\s+([\d.,]+)\s*$"

        lines = text.split("\n")
        for line in lines:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                descricao = match.group(1).strip()
                qtd = match.group(2)
                total = match.group(4)

                # Ignorar valores zero
                try:
                    total_float = float(total.replace(".", "").replace(",", "."))
                    if total_float > 0:
                        itens.append(f"{descricao} (Qtd: {qtd}, Total: R$ {total})")
                except ValueError:
                    itens.append(f"{descricao} (Qtd: {qtd})")

        if itens:
            return "; ".join(itens)

        return None
