"""
Extrator especializado para comprovantes bancários.

Este módulo trata comprovantes de transferência que estavam sendo
classificados incorretamente como NFSe:
    - Comprovantes de TED
    - Comprovantes de PIX
    - Comprovantes de transferência entre contas
    - Comprovantes de DOC

Motivação:
    Documentos como "COMP PAGTO OP11 92.000.pdf" com valores muito altos
    (R$ 1.6M+ em total) estavam sendo classificados como NFSe sem número,
    gerando alertas de NFSE_SEM_NUMERO no relatório de saúde.

Campos extraídos:
    - tipo_documento: Sempre "OUTRO"
    - subtipo: "COMPROVANTE_BANCARIO"
    - banco: Nome do banco (quando identificável)
    - tipo_transferencia: TED, PIX, DOC, TRANSFERENCIA
    - valor_total: Valor da transferência
    - data_emissao: Data/hora da operação
    - pagador_nome: Nome de quem pagou
    - pagador_documento: CPF/CNPJ de quem pagou
    - recebedor_nome: Nome de quem recebeu
    - recebedor_documento: CPF/CNPJ de quem recebeu
    - recebedor_agencia_conta: Agência e conta de destino

Example:
    >>> from extractors.comprovante_bancario import ComprovanteBancarioExtractor
    >>> extractor = ComprovanteBancarioExtractor()
    >>> if extractor.can_handle(texto):
    ...     dados = extractor.extract(texto)
    ...     print(f"Transferência de R$ {dados['valor_total']:.2f}")
"""

import logging
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import (
    BR_MONEY_RE,
    extract_cnpj,
    extract_cpf,
    parse_br_money,
    parse_date_br,
)


@register_extractor
class ComprovanteBancarioExtractor(BaseExtractor):
    """Extrator especializado para comprovantes bancários (TED, PIX, DOC).

    Prioridade ALTA: deve ser registrado ANTES dos extratores genéricos
    para evitar que comprovantes sejam classificados como NFSe.
    """

    # Nomes inválidos para fornecedor (watermarks, labels do banco, etc.)
    # "Original" aparece como watermark/selo em comprovantes do Santander
    INVALID_SUPPLIER_NAMES = {
        "ORIGINAL",  # Watermark do Santander que OCR lê como nome
        "COPIA",
        "CÓPIA",
        "VIA",
        "2A VIA",
        "2ª VIA",
        "PAGADOR",
        "BENEFICIARIO",
        "BENEFICIÁRIO",
        "FAVORECIDO",
        "CLIENTE",
    }

    # Padrões fortes que indicam comprovante bancário
    STRONG_PATTERNS = [
        r"COMPROVANTE\s+DE\s+TRANSFER[EÊ]NCIA",
        r"COMPROVANTE\s+DE\s+PAGAMENTO",
        r"COMPROVANTE\s+(?:TED|PIX|DOC)\b",
        r"DADOS\s+DE\s+QUEM\s+EST[AÁ]\s+PAGANDO",
        r"DADOS\s+DE\s+QUEM\s+EST[AÁ]\s+RECEBENDO",
        r"TRANSFER[EÊ]NCIA\s+(?:ENTRE\s+CONTAS|REALIZADA)",
        r"(?:TED|PIX|DOC)\s+(?:REALIZADO|EFETUADO|AGENDADO)",
        r"TIPO\s+DE\s+CONTA\s+CONTA[_\s]?CORRENTE",
    ]

    # Padrões secundários (precisam de combinação)
    SECONDARY_PATTERNS = [
        r"AG[EÊ]NCIA\s+E\s+CONTA",
        r"IDENTIFICA[CÇ][AÃ]O\s+NO\s+EXTRATO",
        r"CONTA[_\s]?CORRENTE",
        r"CONTA[_\s]?POUPAN[CÇ]A",
        r"FAVORECIDO",
        r"ORDENANTE",
        r"BENEFICI[AÁ]RIO",
    ]

    # Bancos conhecidos
    KNOWN_BANKS = [
        "ITA[UÚ]",
        "BRADESCO",
        "BANCO DO BRASIL",
        "SANTANDER",
        "CAIXA",
        "CEF",
        "SICOOB",
        "SICREDI",
        "INTER",
        "NUBANK",
        "C6",
        "BTG",
        "SAFRA",
        "ORIGINAL",
        "BANRISUL",
        "BRB",
        "UNICRED",
    ]

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Verifica se o documento é um comprovante bancário.

        Critérios:
        1. Pelo menos 1 padrão forte OU
        2. Pelo menos 2 padrões secundários + indicador de banco

        Args:
            text: Texto completo do documento

        Returns:
            True se for comprovante bancário, False caso contrário
        """
        if not text:
            return False

        logger = logging.getLogger(__name__)
        t = text.upper()

        # Exclusões: documentos que definitivamente NÃO são comprovantes
        exclusion_patterns = [
            r"NOTA\s+FISCAL",
            r"NFS-?E",
            r"DANFE",
            r"BOLETO",
            r"FATURA\s+DE\s+SERVI[CÇ]O",
            r"PREFEITURA\s+MUNICIPAL",
            r"SECRETARIA\s+(?:MUNICIPAL\s+)?(?:DA\s+)?FAZENDA",
            r"NOTA\s+DE\s+D[EÉ]BITO",  # Nota de débito não é comprovante bancário
        ]

        for pattern in exclusion_patterns:
            if re.search(pattern, t):
                logger.debug(
                    f"ComprovanteBancarioExtractor: excluído por padrão '{pattern}'"
                )
                return False

        # Verificar padrões fortes
        strong_count = sum(1 for p in cls.STRONG_PATTERNS if re.search(p, t))
        if strong_count >= 1:
            logger.debug(
                f"ComprovanteBancarioExtractor: detectado {strong_count} padrão(ões) forte(s)"
            )
            return True

        # Verificar padrões secundários + banco
        secondary_count = sum(1 for p in cls.SECONDARY_PATTERNS if re.search(p, t))
        bank_found = any(re.search(bank, t) for bank in cls.KNOWN_BANKS)

        if secondary_count >= 2 and bank_found:
            logger.debug(
                f"ComprovanteBancarioExtractor: detectado {secondary_count} padrões secundários + banco"
            )
            return True

        return False

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extrai dados do comprovante bancário.

        Args:
            text: Texto completo do documento

        Returns:
            Dicionário com dados extraídos
        """
        logger = logging.getLogger(__name__)
        logger.debug("ComprovanteBancarioExtractor: iniciando extração")

        data: Dict[str, Any] = {
            "tipo_documento": "OUTRO",
            "subtipo": "COMPROVANTE_BANCARIO",
        }

        t_upper = text.upper()

        # Detectar tipo de transferência
        data["tipo_transferencia"] = self._detect_transfer_type(t_upper)

        # Detectar banco
        data["banco"] = self._detect_bank(t_upper)

        # Extrair valor
        data["valor_total"] = self._extract_value(text)

        # Extrair data
        data["data_emissao"] = self._extract_date(text)

        # Extrair dados do pagador
        pagador_data = self._extract_party_data(text, "PAGANDO")
        if pagador_data:
            data["pagador_nome"] = pagador_data.get("nome")
            data["pagador_documento"] = pagador_data.get("documento")
            data["pagador_agencia_conta"] = pagador_data.get("agencia_conta")

        # Extrair dados do recebedor
        recebedor_data = self._extract_party_data(text, "RECEBENDO")
        if recebedor_data:
            data["recebedor_nome"] = recebedor_data.get("nome")
            data["recebedor_documento"] = recebedor_data.get("documento")
            data["recebedor_agencia_conta"] = recebedor_data.get("agencia_conta")
            # Usar recebedor como fornecedor_nome para compatibilidade
            if recebedor_data.get("nome"):
                nome = recebedor_data["nome"]
                # Limpar termos inválidos que podem aparecer no nome (watermarks do banco)
                nome = re.sub(
                    r"\s+(?:Original|Copia|Cópia|Via|2[ªa]\s*Via)\s*(?:-\s*CNPJ.*)?$",
                    "",
                    nome,
                    flags=re.I,
                ).strip()
                # Validar se não é um nome inválido (watermark, label, etc.)
                if nome.upper().strip() not in self.INVALID_SUPPLIER_NAMES:
                    data["fornecedor_nome"] = nome
            if recebedor_data.get("documento"):
                # Tentar identificar se é CNPJ ou CPF
                doc = recebedor_data["documento"]
                if "/" in doc:
                    data["cnpj_fornecedor"] = doc

        # Fallback: extrair beneficiário/favorecido se recebedor não foi encontrado
        if not data.get("fornecedor_nome"):
            fornecedor_fallback = self._extract_beneficiario_fallback(text)
            if fornecedor_fallback:
                nome = fornecedor_fallback.get("nome")
                # Validar se não é um nome inválido (watermark, label, etc.)
                if nome and nome.upper().strip() not in self.INVALID_SUPPLIER_NAMES:
                    data["fornecedor_nome"] = nome
                    if fornecedor_fallback.get("documento"):
                        data["cnpj_fornecedor"] = fornecedor_fallback["documento"]
                    logger.debug(
                        f"ComprovanteBancarioExtractor: fornecedor extraído via fallback: {data.get('fornecedor_nome')}"
                    )

        # Fallback: extrair vencimento de boleto pago
        if not data.get("vencimento"):
            m_venc = re.search(
                r"(?:Data\s+de\s+vencimento|Vencimento)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
                text,
                re.I,
            )
            if m_venc:
                data["vencimento"] = parse_date_br(m_venc.group(1))

        # Extrair identificação no extrato
        m_id = re.search(
            r"IDENTIFICA[CÇ][AÃ]O\s+(?:NO\s+)?EXTRATO\s*[:\-]?\s*(\S+)", text, re.I
        )
        if m_id:
            data["identificacao_extrato"] = m_id.group(1).strip()

        # Log do resultado
        logger.info(
            f"ComprovanteBancarioExtractor: {data['tipo_transferencia']} de R$ {data.get('valor_total', 0):.2f} "
            f"via {data.get('banco', 'banco desconhecido')}"
        )

        return data

    def _detect_transfer_type(self, text_upper: str) -> str:
        """Detecta o tipo de transferência (TED, PIX, DOC, etc.)."""
        if re.search(r"\bPIX\b", text_upper):
            return "PIX"
        if re.search(r"\bTED\b", text_upper):
            return "TED"
        if re.search(r"\bDOC\b", text_upper):
            return "DOC"
        if re.search(r"TRANSFER[EÊ]NCIA", text_upper):
            return "TRANSFERENCIA"
        return "TRANSFERENCIA"

    def _detect_bank(self, text_upper: str) -> Optional[str]:
        """Detecta o banco emissor do comprovante."""
        bank_mapping = {
            r"\bITA[UÚ]\b": "ITAÚ",
            r"\bBANCO\s+ITA[UÚ]\b": "ITAÚ",
            r"\bBRADESCO\b": "BRADESCO",
            r"\bBANCO\s+DO\s+BRASIL\b": "BANCO DO BRASIL",
            r"\bSANTANDER\b": "SANTANDER",
            r"\bCAIXA\s+ECON[OÔ]MICA\b": "CAIXA",
            r"\bCEF\b": "CAIXA",
            r"\bSICOOB\b": "SICOOB",
            r"\bSICREDI\b": "SICREDI",
            r"\bBANCO\s+INTER\b": "INTER",
            r"\bNUBANK\b": "NUBANK",
            r"\bC6\s+BANK\b": "C6 BANK",
            r"\bBTG\b": "BTG",
            r"\bSAFRA\b": "SAFRA",
            r"\bORIGINAL\b": "ORIGINAL",
        }

        for pattern, bank_name in bank_mapping.items():
            if re.search(pattern, text_upper):
                return bank_name

        return None

    def _extract_value(self, text: str) -> float:
        """Extrai o valor da transferência."""
        # Padrões específicos de valor em comprovantes
        value_patterns = [
            r"VALOR\s*[:\-]?\s*R\$\s*([\d\.,]+)",
            r"VALOR\s+DA\s+TRANSFER[EÊ]NCIA\s*[:\-]?\s*R\$\s*([\d\.,]+)",
            r"VALOR\s+TRANSFERIDO\s*[:\-]?\s*R\$\s*([\d\.,]+)",
            r"QUANTIA\s*[:\-]?\s*R\$\s*([\d\.,]+)",
            r"MONTANTE\s*[:\-]?\s*R\$\s*([\d\.,]+)",
        ]

        for pattern in value_patterns:
            m = re.search(pattern, text, re.I)
            if m:
                val = parse_br_money(m.group(1))
                if val > 0:
                    return val

        # Fallback: procurar valores monetários gerais (pegar o maior)
        values = [parse_br_money(v) for v in BR_MONEY_RE.findall(text)]
        values = [v for v in values if v > 0]
        if values:
            return max(values)

        return 0.0

    def _extract_date(self, text: str) -> Optional[str]:
        """Extrai a data da transferência."""
        # Padrões específicos de data em comprovantes
        date_patterns = [
            r"DATA\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
            r"DATA\s+DA\s+TRANSFER[EÊ]NCIA\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
            r"REALIZADO\s+EM\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
            r"EFETUADO\s+EM\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        ]

        for pattern in date_patterns:
            m = re.search(pattern, text, re.I)
            if m:
                return parse_date_br(m.group(1))

        # Fallback: primeira data encontrada
        m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
        if m:
            return parse_date_br(m.group(1))

        return None

    def _extract_party_data(
        self, text: str, party_type: str
    ) -> Optional[Dict[str, str]]:
        """
        Extrai dados de uma parte (pagador ou recebedor).

        Args:
            text: Texto completo
            party_type: "PAGANDO" ou "RECEBENDO"

        Returns:
            Dicionário com nome, documento, agencia_conta ou None
        """
        # Encontrar a seção relevante
        pattern = rf"DADOS\s+DE\s+QUEM\s+EST[AÁ]\s+{party_type}"
        m = re.search(pattern, text, re.I)
        if not m:
            return None

        # Pegar um trecho após o match (próximos 500 caracteres)
        start = m.end()
        # Encontrar o próximo "Dados de quem" ou fim do documento
        next_section = re.search(r"DADOS\s+DE\s+QUEM", text[start:], re.I)
        end = start + (next_section.start() if next_section else 500)
        section = text[start:end]

        result: Dict[str, str] = {}

        # Extrair nome
        m_nome = re.search(
            r"NOME\s+([A-Z][A-Z\s\.]+(?:LTDA|S\.?A\.?|ME|EPP)?)", section, re.I
        )
        if m_nome:
            result["nome"] = re.sub(r"\s+", " ", m_nome.group(1)).strip()

        # Extrair CPF ou CNPJ
        cnpj = extract_cnpj(section)
        if cnpj:
            result["documento"] = cnpj
        else:
            cpf = extract_cpf(section)
            if cpf:
                result["documento"] = cpf
            else:
                # Tentar padrão "CPF ou CNPJ" seguido de valor
                m_doc = re.search(
                    r"(?:CPF|CNPJ)\s*(?:ou\s*(?:CPF|CNPJ))?\s*[:\-]?\s*([\d\.\-/]+)",
                    section,
                    re.I,
                )
                if m_doc:
                    result["documento"] = m_doc.group(1).strip()

        # Extrair agência e conta
        m_ag = re.search(r"AG[EÊ]NCIA\s+E\s+CONTA\s*[:\-]?\s*([\d/\-]+)", section, re.I)
        if m_ag:
            result["agencia_conta"] = m_ag.group(1).strip()
        else:
            # Padrão alternativo: "Agência: XXXX Conta: XXXXX"
            m_ag2 = re.search(
                r"AG[EÊ]NCIA\s*[:\-]?\s*(\d+)\s*CONTA\s*[:\-]?\s*([\d\-]+)",
                section,
                re.I,
            )
            if m_ag2:
                result["agencia_conta"] = f"{m_ag2.group(1)}/{m_ag2.group(2)}"

        return result if result else None

    def _extract_beneficiario_fallback(self, text: str) -> Optional[Dict[str, str]]:
        """
        Fallback para extrair beneficiário/favorecido de comprovantes com formatos alternativos.

        Formatos suportados:
        - "Favorecido\nNome do beneficiário: EMPRESA XYZ"
        - "Beneficiário: EMPRESA XYZ"
        - "Nome do beneficiário: EMPRESA XYZ"

        Args:
            text: Texto completo do comprovante

        Returns:
            Dicionário com nome e documento ou None
        """
        result: Dict[str, str] = {}

        # Padrões para nome do beneficiário/favorecido
        # NOTA: A ordem importa - padrões mais específicos primeiro
        nome_patterns = [
            # Padrão específico Santander: "Nome/Razão Social do Beneficiário Original CPF/CNPJ do Beneficiário EMPRESA Original - CNPJ"
            # O "Original" é um watermark que aparece entre os campos
            r"Nome/Raz[ãa]o\s+Social\s+do\s+Benefici[aá]rio\s+Original\s+CPF/CNPJ\s+do\s+Benefici[aá]rio\s+([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9\s\.\-&]+?)(?:\s+Original|\s+-\s*CNPJ)",
            # Padrões genéricos
            r"Nome\s+do\s+benefici[aá]rio\s*[:\-]?\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9\s\.\-&]+?)(?:\s*\n|Documento|CPF|CNPJ|$)",
            r"Favorecido\s*[:\-]?\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9\s\.\-&]+(?:LTDA|S/?A|ME|EPP)?)",
            r"Benefici[aá]rio\s*[:\-]?\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9\s\.\-&]+(?:LTDA|S/?A|ME|EPP)?)",
            r"Recebedor\s*[:\-]?\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ0-9\s\.\-&]+(?:LTDA|S/?A|ME|EPP)?)",
        ]

        for pattern in nome_patterns:
            m = re.search(pattern, text, re.I)
            if m:
                nome = re.sub(r"\s+", " ", m.group(1)).strip()
                # Limpar possíveis sufixos indesejados
                nome = re.sub(
                    r"\s*(Documento|CPF|CNPJ).*$", "", nome, flags=re.I
                ).strip()
                # Remover termos inválidos que podem aparecer como sufixo (watermarks do banco)
                nome = re.sub(
                    r"\s+(?:Original|Copia|Cópia|Via|2[ªa]\s*Via)\s*(?:-\s*CNPJ.*)?$",
                    "",
                    nome,
                    flags=re.I,
                ).strip()
                if len(nome) >= 5:
                    result["nome"] = nome
                    break

        # Padrões para documento do beneficiário (CNPJ mascarado ou completo)
        doc_patterns = [
            r"Documento\s+do\s+benefici[aá]rio\s*[:\-]?\s*([\d\.\-/\*]+)",
            r"CNPJ\s+(?:do\s+)?(?:benefici[aá]rio|favorecido)\s*[:\-]?\s*([\d\.\-/\*]+)",
            r"CPF\s+(?:do\s+)?(?:benefici[aá]rio|favorecido)\s*[:\-]?\s*([\d\.\-\*]+)",
        ]

        for pattern in doc_patterns:
            m = re.search(pattern, text, re.I)
            if m:
                doc = m.group(1).strip()
                if len(doc) >= 10:  # CNPJ ou CPF mínimo
                    result["documento"] = doc
                    break

        return result if result else None
