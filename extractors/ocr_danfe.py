"""
Extractor para DANFEs com texto corrompido/OCR ruim.

Este extrator eh especializado em documentos onde o texto nativo do PDF
esta truncado ou corrompido, mas o OCR pode recuperar as informacoes.

Exemplos:
- Postos de gasolina com PDFs escaneados de baixa qualidade
- Documentos com fontes nao padrao
- PDFs com camadas de texto danificadas
"""

import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor


@register_extractor
class OcrDanfeExtractor(BaseExtractor):
    """
    Extrator para DANFEs que necessitam de OCR devido a corrupcao do texto nativo.

    Detecta padroes de corrupcao no texto e, quando aplicavel, utiliza OCR
    para extrair informacoes corretamente.
    """

    # Indicadores de texto corrompido (OCR necessario)
    CORRUPTION_INDICATORS = [
        r"RECEHEMOS",  # OCR errou "RECEBEMOS"
        r"HINAT",  # OCR errou "MINAS"
        r"CIVCRE",  # OCR errou "CIVIL"
        r"GETULIO\s+VANGAS",  # OCR errou "VARGAS"
        r"[A-Z]{20,}",  # Palavras muito longas (lixo OCR)
    ]

    # CNPJs de postos/empresas conhecidas com este problema
    KNOWN_CNPJS = {
        "07.355.400/0001-69": "AUTO POSTO PORTAL DE MINAS LTDA",
    }

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Verifica se o texto eh um DANFE corrompido que precisa de OCR.

        Critérios:
        1. Tem indicadores de DANFE (DANFE, RECEBEMOS/RECEHEMOS, etc.)
        2. Tem indicadores de corrupcao grave no texto
        3. Tem CNPJ de fornecedor conhecido com este problema
        """
        import logging

        logger = logging.getLogger(__name__)

        if not text:
            logger.debug("OcrDanfeExtractor.can_handle: texto vazio")
            return False

        text_upper = text.upper()

        # Verificar se eh DANFE (indicadores basicos)
        is_danfe = False
        if "DANFE" in text_upper:
            is_danfe = True
            logger.debug("OcrDanfeExtractor.can_handle: 'DANFE' encontrado")
        if "RECEBEMOS" in text_upper or "RECEHEMOS" in text_upper:
            is_danfe = True
            logger.debug(
                "OcrDanfeExtractor.can_handle: 'RECEBEMOS/RECEHEMOS' encontrado"
            )
        if "DOCUMENTO AUXILIAR" in text_upper:
            is_danfe = True
            logger.debug(
                "OcrDanfeExtractor.can_handle: 'DOCUMENTO AUXILIAR' encontrado"
            )

        if not is_danfe:
            logger.debug("OcrDanfeExtractor.can_handle: não é DANFE")
            return False

        # Verificar se tem indicadores de corrupcao
        corruption_score = 0
        corruption_details = []
        for pattern in cls.CORRUPTION_INDICATORS:
            if re.search(pattern, text_upper):
                corruption_score += 1
                corruption_details.append(pattern)

        # Se tem corrupcao significativa
        if corruption_score >= 2:
            logger.debug(
                f"OcrDanfeExtractor.can_handle: corrupção alta (score={corruption_score}): {corruption_details}"
            )
            return True

        # Ou se tem CNPJ conhecido com problema
        for cnpj in cls.KNOWN_CNPJS:
            if cnpj in text:
                logger.debug(
                    f"OcrDanfeExtractor.can_handle: CNPJ conhecido encontrado: {cnpj}"
                )
                return True

        logger.debug(
            f"OcrDanfeExtractor.can_handle: recusado (is_danfe={is_danfe}, corruption_score={corruption_score})"
        )
        return False

    def extract(self, text: str, context: Optional[dict] = None) -> Dict[str, Any]:
        """
        Extrai dados do DANFE usando padroes tolerantes a OCR ruim.

        Nota: Este extrator assume que o texto ja passou por OCR se necessario,
        ou trabalha com o texto corrompido usando padroes flexiveis.
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.info("OcrDanfeExtractor.extract iniciado")

        data: Dict[str, Any] = {"tipo_documento": "DANFE"}

        # Extrair CNPJ
        cnpj = self._extract_cnpj(text)
        if cnpj:
            data["cnpj_emitente"] = cnpj
            logger.info(f"OcrDanfeExtractor: CNPJ extraído: {cnpj}")
            # Se CNPJ eh conhecido, usar nome mapeado
            if cnpj in self.KNOWN_CNPJS:
                data["fornecedor_nome"] = self.KNOWN_CNPJS[cnpj]
                logger.info(
                    f"OcrDanfeExtractor: fornecedor conhecido: {self.KNOWN_CNPJS[cnpj]}"
                )
        else:
            logger.warning("OcrDanfeExtractor: CNPJ não extraído")

        # Extrair numero da nota
        numero = self._extract_numero_nota(text)
        if numero:
            data["numero_nota"] = numero
            logger.info(f"OcrDanfeExtractor: número da nota extraído: {numero}")
        else:
            logger.warning("OcrDanfeExtractor: número da nota não extraído")

        # Extrair serie
        serie = self._extract_serie(text)
        if serie:
            data["serie_nf"] = serie
            logger.info(f"OcrDanfeExtractor: série extraída: {serie}")
        else:
            logger.debug("OcrDanfeExtractor: série não extraída")

        # Extrair valor total
        valor = self._extract_valor(text)
        if valor:
            data["valor_total"] = valor
            logger.info(f"OcrDanfeExtractor: valor total extraído: R$ {valor:.2f}")
        else:
            logger.warning("OcrDanfeExtractor: valor total não extraído")

        # Extrair data de emissao
        data_emissao = self._extract_data_emissao(text)
        if data_emissao:
            data["data_emissao"] = data_emissao
            logger.info(f"OcrDanfeExtractor: data de emissão extraída: {data_emissao}")
        else:
            logger.debug("OcrDanfeExtractor: data de emissão não extraída")

        # Se nao achou fornecedor pelo CNPJ, tentar pelo texto
        if "fornecedor_nome" not in data:
            fornecedor = self._extract_fornecedor(text)
            if fornecedor:
                data["fornecedor_nome"] = fornecedor
                logger.info(
                    f"OcrDanfeExtractor: fornecedor extraído do texto: {fornecedor}"
                )
            else:
                logger.warning(
                    "OcrDanfeExtractor: fornecedor não encontrado nem pelo CNPJ nem pelo texto"
                )
        else:
            logger.debug(
                f"OcrDanfeExtractor: fornecedor já definido: {data['fornecedor_nome']}"
            )

        logger.info(
            f"OcrDanfeExtractor.extract concluído - campos: {list(data.keys())}"
        )

        return data

    def _extract_cnpj(self, text: str) -> Optional[str]:
        """Extrai CNPJ do emitente."""
        # Procura CNPJ formatado
        pattern = r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b"
        matches = re.findall(pattern, text)

        # Retorna o primeiro que nao for de empresa conhecida nossa
        # (assumindo que eh o do emitente)
        for cnpj in matches:
            if cnpj in self.KNOWN_CNPJS:
                return cnpj

        # Se nao achou CNPJ conhecido, retorna o primeiro encontrado
        if matches:
            return matches[0]

        return None

    def _extract_numero_nota(self, text: str) -> Optional[str]:
        """Extrai numero da nota fiscal."""
        # Padroes comuns em DANFEs corrompidos
        patterns = [
            r"N[�º\s]*([0-9]{4,10})",  # N 222405 ou N� 222405 ou Nº22404
            r"N[�º\s]*([0-9\.]+)",  # N� 000.123.456
            r"NF[\s]*([0-9]{4,10})",  # NF 222405
            r"N[�º\s]*:?\s*([0-9]{4,10})",  # N�: 22404
            r"N[�º\s]*[º°]?\s*([0-9]{4,10})",  # Nº22404 ou N°22404
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                numero = match.group(1).replace(".", "").strip()
                if numero.isdigit() and len(numero) >= 4:
                    return numero

        # Fallback: buscar qualquer sequência de 4+ dígitos após "N" ou "NF"
        # Útil para OCR muito corrompido
        fallback_patterns = [
            r"(?:N[�º\s]|NF[�º\s]|NOTA[�º\s]+FISCAL[�º\s]+)(\d{4,})",
            r"(?:NUMERO|NÚMERO|N�MERO)[�º\s:]*(\d{4,})",
        ]

        for pattern in fallback_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                numero = match.group(1).strip()
                if numero.isdigit() and len(numero) >= 4:
                    return numero

        return None

    def _extract_serie(self, text: str) -> Optional[str]:
        """Extrai serie da nota fiscal."""
        # Padrao: SERIE: 2 ou SRIE: 2 (OCR errou)
        patterns = [
            r"S[�E]R[IE][E\s]*[:\s]*([0-9]{1,3})",
            r"SERIE[\s]*[:\s]*([0-9]{1,3})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_valor(self, text: str) -> Optional[float]:
        """Extrai valor total da nota."""
        # Procura valores monetarios
        pattern = r"(\d{1,3}(?:\.\d{3})*,\d{2})"
        matches = re.findall(pattern, text)

        valores = []
        for match in matches:
            try:
                valor_str = match.replace(".", "").replace(",", ".")
                valor = float(valor_str)
                if 10.0 < valor < 50000.0:  # Faixa razoavel para DANFEs
                    valores.append(valor)
            except ValueError:
                continue

        # Retorna o maior valor (geralmente o total)
        if valores:
            # Tentar encontrar valor próximo a "VALOR TOTAL" ou similar
            total_patterns = [
                r"VALOR\s+TOTAL[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2})",
                r"TOTAL\s+DA\s+NOTA[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2})",
                r"TOTAL\s+R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            ]

            for total_pattern in total_patterns:
                total_match = re.search(total_pattern, text, re.IGNORECASE)
                if total_match:
                    try:
                        total_str = (
                            total_match.group(1).replace(".", "").replace(",", ".")
                        )
                        total_valor = float(total_str)
                        if 10.0 < total_valor < 50000.0:
                            return total_valor
                    except ValueError:
                        continue

            # Fallback: maior valor
            return max(valores)

        return None

    def _extract_data_emissao(self, text: str) -> Optional[str]:
        """Extrai data de emissao."""
        # Padroes comuns
        patterns = [
            r"(\d{2})/(\d{2})/(\d{4})",  # DD/MM/YYYY
            r"(\d{2})-(\d{2})-(\d{4})",  # DD-MM-YYYY
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                dia, mes, ano = match.groups()
                return f"{ano}-{mes}-{dia}"

        return None

    def _extract_fornecedor(self, text: str) -> Optional[str]:
        """Extrai nome do fornecedor/emitente."""
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"OcrDanfeExtractor._extract_fornecedor: iniciando com {len(text)} caracteres"
        )

        # Padrao DANFE X | DOCUMENTO
        # Padrao 1: DANFE X | DOCUMENTO (com variacoes de OCR)
        patterns = [
            # Padrao original com mais flexibilidade
            r"\bDANFE\b[^\w]*(.{3,60}?)\s*[|\-—–]\s*DOCUMENTO",
            # Alternativa: DANFE seguido de nome e qualquer coisa
            r"\bDANFE\b[^\w]*(.{3,60}?)(?:\s*(?:[|\-—–]|DOCUMENTO|$))",
            # Para OCR muito corrompido: D A N F E ou variacoes
            r"[D�][\s�]*[A�][\s�]*[N�][\s�]*[F�][\s�]*[E�][^\w]*(.{3,60}?)(?:\s*[|\-—–]|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nome = re.sub(r"\s+", " ", match.group(1)).strip()
                # Limpar caracteres corrompidos comuns
                nome = re.sub(r"[�\*\#\@\$\%\&\+\=]+", " ", nome)
                nome = re.sub(r"\s+", " ", nome).strip()
                if 4 <= len(nome) <= 120 and not re.search(r"^\d+$", nome):
                    logger.debug(
                        f"OcrDanfeExtractor._extract_fornecedor: padrão DANFE encontrado: '{nome}' com padrão: {pattern[:50]}..."
                    )
                    return nome
                else:
                    logger.debug(
                        f"OcrDanfeExtractor._extract_fornecedor: padrão DANFE encontrado mas nome inválido (len={len(nome)}, nome='{nome}')"
                    )
            else:
                logger.debug(
                    f"OcrDanfeExtractor._extract_fornecedor: padrão DANFE não match: {pattern[:50]}..."
                )

        # Padrao 2: RECEBEMOS/RECEHEMOS DE X (os produtos/a mercadoria)
        recebe_patterns = [
            # Original com mais flexibilidade
            r"\bRECE[BH�]EMOS\s+DE[^\w]*(.{3,60}?)\s+(?:OS\s+PRODUTOS|A\s+MERCADORIA|PRODUTOS|MERCADORIA)",
            # Variante mais simples: RECEBEMOS DE X
            r"\bRECE[BH�]EMOS\s+DE[^\w]*(.{3,60}?)(?:\s|,|\.|$)",
            # OCR muito corrompido: R E C E B E M O S
            r"[R�]\s*[E�]\s*[C�]\s*[E�]\s*[BH�]\s*[E�]\s*[M�]\s*[O�]\s*[S�]\s+DE[^\w]*(.{3,60}?)(?:\s|$)",
            # RECEBEMOS os produtos de X (ordem invertida)
            r"\bRECE[BH�]EMOS[^\w]+(?:OS\s+PRODUTOS|A\s+MERCADORIA)[^\w]+DE[^\w]*(.{3,60}?)(?:\s|,|\.|$)",
        ]

        for pattern in recebe_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nome = re.sub(r"\s+", " ", match.group(1)).strip()
                # Limpar lixo OCR comum
                nome = re.sub(r"[�\*\#\@\$\%\&\+\=]+", " ", nome)
                nome = re.sub(
                    r"\s+[A-Z]{10,}$", "", nome
                )  # Remove palavras longas no final
                nome = re.sub(r"^\s*[:\-–—]\s*", "", nome)  # Remove pontuacao no inicio
                nome = re.sub(r"\s+", " ", nome).strip()
                if 4 <= len(nome) <= 120 and not re.search(r"^\d+$", nome):
                    logger.debug(
                        f"OcrDanfeExtractor._extract_fornecedor: padrão RECEBEMOS encontrado: '{nome}' com padrão: {pattern[:50]}..."
                    )
                    return nome
                else:
                    logger.debug(
                        f"OcrDanfeExtractor._extract_fornecedor: padrão RECEBEMOS encontrado mas nome inválido (len={len(nome)}, nome='{nome}')"
                    )
            else:
                logger.debug(
                    f"OcrDanfeExtractor._extract_fornecedor: padrão RECEBEMOS não match: {pattern[:50]}..."
                )

        # Padrao 3: CNPJ/CPF seguido de nome (caso o nome venha depois)
        cnpj_pattern = r"(?:CPF/CNPJ|CNPJ/CPF|CNPJ|CPF)[\s:]*([\d\.\-/]+)[^\w]*(.{3,60}?)(?:\s|,|\.|$)"
        match = re.search(cnpj_pattern, text, re.IGNORECASE)
        if match:
            cnpj_part = match.group(1)
            nome = match.group(2).strip()
            # Verificar se o nome nao eh apenas o CNPJ repetido
            if cnpj_part not in nome:
                nome = re.sub(r"\s+", " ", nome).strip()
                nome = re.sub(r"[�\*\#\@\$\%\&\+\=]+", " ", nome)
                if 4 <= len(nome) <= 120 and not re.search(r"^[\d\.\-/]+$", nome):
                    logger.debug(
                        f"OcrDanfeExtractor._extract_fornecedor: padrão CNPJ encontrado: '{nome}' (CNPJ: {cnpj_part})"
                    )
                    return nome
                else:
                    logger.debug(
                        f"OcrDanfeExtractor._extract_fornecedor: padrão CNPJ encontrado mas nome inválido (len={len(nome)}, nome='{nome}', CNPJ={cnpj_part})"
                    )
            else:
                logger.debug(
                    f"OcrDanfeExtractor._extract_fornecedor: padrão CNPJ encontrado mas nome igual ao CNPJ: {cnpj_part}"
                )
        else:
            logger.debug(
                "OcrDanfeExtractor._extract_fornecedor: padrão CNPJ não encontrado"
            )

        # Padrao 4: Nome antes de "LTDA", "S/A", "S.A." etc (empresa)
        empresa_patterns = [
            r"([A-Z][A-Z\s�]{3,50}?)\s+(?:LTDA|LTDA\.|S/A|S\.A\.|S\.A|SA|EIRELI|ME|EPP)(?:\s|,|\.|$)",
            r"([A-Z][A-Z\s�]{3,50}?)\s+[A-Z]{2,}\s+(?:LTDA|S/A|S\.A\.)(?:\s|$)",
        ]

        for pattern in empresa_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nome = re.sub(r"\s+", " ", match.group(1)).strip()
                nome = re.sub(r"[�\*\#\@\$\%\&\+\=]+", " ", nome)
                nome = re.sub(r"\s+", " ", nome).strip()
                if 4 <= len(nome) <= 120:
                    logger.debug(
                        f"OcrDanfeExtractor._extract_fornecedor: padrão empresa encontrado: '{nome}' com padrão: {pattern[:50]}..."
                    )
                    return nome
                else:
                    logger.debug(
                        f"OcrDanfeExtractor._extract_fornecedor: padrão empresa encontrado mas nome inválido (len={len(nome)}, nome='{nome}')"
                    )
            else:
                logger.debug(
                    f"OcrDanfeExtractor._extract_fornecedor: padrão empresa não match: {pattern[:50]}..."
                )

        logger.debug(
            "OcrDanfeExtractor._extract_fornecedor: nenhum padrão encontrado, retornando None"
        )
        return None
