"""
Extrator para boletos GOX S.A. (provedor de internet).

Características:
- Boleto de fatura de internet/telecom
- Número do documento vem no nome do arquivo (padrão: receber_XXXXXXX)
- Fornecedor: GOX S.A.
- CNPJ: 07.543.400/0001-92
- Cliente tem código identificador no boleto
"""

import logging
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import parse_date_br


@register_extractor
class BoletoGoxExtractor(BaseExtractor):
    """
    Extrator específico para boletos da GOX S.A.
    
    Resolve o problema de boletos GOX sem número de documento,
    extraindo o número do nome do arquivo (padrão: receber_XXXXXXX).
    """

    # CNPJ da GOX S.A.
    GOX_CNPJ = "07.543.400/0001-92"
    
    # Padrões no nome do arquivo
    PADRAO_NUMERO_RECEBER = r'receber_(\d+)'
    
    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Retorna True se o texto é um boleto da GOX.
        
        Indicadores:
        - Presença de "GOX" no texto
        - CNPJ da GOX (07.543.400/0001-92)
        - Termos como "goxinternet.com.br"
        """
        if not text:
            return False
            
        text_upper = text.upper()
        
        # Precisa ter GOX e o CNPJ ou email para confirmar
        tem_gox = "GOX" in text_upper
        tem_cnpj = cls.GOX_CNPJ in text
        tem_email = "GOXINTERNET.COM.BR" in text_upper or "GOXINTERNET.COM" in text_upper
        
        logger = logging.getLogger(__name__)
        
        if tem_gox and (tem_cnpj or tem_email):
            logger.info(f"[BoletoGoxExtractor] Detectado boleto GOX (CNPJ={tem_cnpj}, Email={tem_email})")
            return True
            
        return False

    def _extract_from_filename(self, text: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        Extrai número do documento do nome do arquivo.
        
        Padrão esperado: receber_XXXXXXX.pdf
        """
        # Tenta obter do contexto (arquivo_origem)
        if context and 'arquivo_origem' in context:
            filename = context['arquivo_origem']
        else:
            return None
            
        # Busca padrão receber_XXXXXXX
        match = re.search(self.PADRAO_NUMERO_RECEBER, filename, re.IGNORECASE)
        if match:
            return match.group(1)
            
        return None

    def _extract_cliente_id(self, text: str) -> Optional[str]:
        """Extrai código do cliente do boleto."""
        # Padrão: "35875 - ITACOLOMI COMUNICACAO LTDA"
        # ou apenas "35875" próximo a "Área do cliente"
        
        patterns = [
            r'(\d{4,6})\s*-\s*[A-Z]',  # Código seguido de traço e empresa
            r'cliente[:\s]+(\d{4,6})',  # "cliente: 35875"
            r'código[:\s]+(\d{4,6})',   # "código: 35875"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
                
        return None

    def _extract_fornecedor(self, text: str) -> str:
        """Extrai nome do fornecedor (sempre GOX S.A. para boletos GOX)."""
        return "GOX S.A."

    def _extract_cnpj(self, text: str) -> str:
        """Extrai CNPJ do fornecedor."""
        return self.GOX_CNPJ

    def _extract_valor(self, text: str) -> float:
        """Extrai valor do documento."""
        # Procurar "Total a pagar:" ou "R$ XXX,XX"
        patterns = [
            r'Total a pagar[:\s]+R?\$?\s*([\d.]+,\d{2})',
            r'R\$\s*([\d.]+,\d{2})',
            r'VALOR[:\s]+R?\$?\s*([\d.]+,\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    valor_str = match.group(1).replace('.', '').replace(',', '.')
                    return float(valor_str)
                except (ValueError, IndexError):
                    continue
                    
        return 0.0

    def _extract_vencimento(self, text: str) -> Optional[str]:
        """Extrai data de vencimento."""
        # Procurar "Vencimento:" ou data no formato DD/MM/AAAA
        patterns = [
            r'Vencimento[:\s]+(\d{2}/\d{2}/\d{4})',
            r'VENC[:\s]+(\d{2}/\d{2}/\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return parse_date_br(match.group(1))
                
        # Fallback: procura qualquer data no formato DD/MM/AAAA
        # que seja futura (provavelmente vencimento)
        date_matches = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        if date_matches:
            # Converte para ISO e retorna a última (geralmente vencimento)
            dates = []
            for d in date_matches:
                parsed = parse_date_br(d)
                if parsed:
                    dates.append(parsed)
            if dates:
                dates.sort()
                return dates[-1]  # Retorna a mais recente
                
        return None

    def _extract_emissao(self, text: str) -> Optional[str]:
        """Extrai data de emissão."""
        # Procurar data de emissão (geralmente a primeira data no documento)
        date_matches = re.findall(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        if date_matches:
            for d in date_matches:
                parsed = parse_date_br(d)
                if parsed:
                    return parsed
        return None

    def _extract_linha_digitavel(self, text: str) -> Optional[str]:
        """Extrai linha digitável do boleto."""
        # Padrão: 5 números separados por espaços ou pontos
        pattern = r'(\d{5}[\s.]\d{5}[\s.]\d{5}[\s.]\d{6}[\s.]\d{2,3}|\d{47,48})'
        match = re.search(pattern, text)
        if match:
            linha = match.group(1).replace(' ', '').replace('.', '')
            if len(linha) >= 47:
                return linha
        return None

    def extract(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Extrai dados do boleto GOX."""
        logger = logging.getLogger(__name__)
        logger.info("BoletoGoxExtractor: iniciando extração")

        # Guarda contexto para uso em _extract_from_filename
        self.last_context = context

        data: Dict[str, Any] = {"tipo_documento": "BOLETO"}

        # Extrai número do documento do nome do arquivo (prioridade)
        numero_doc = self._extract_from_filename(text, context)
        if numero_doc:
            data["numero_documento"] = numero_doc
            logger.debug(f"Número do documento extraído do filename: {numero_doc}")

        # Extrai código do cliente
        cliente_id = self._extract_cliente_id(text)
        if cliente_id:
            data["cliente_gox_id"] = cliente_id
            logger.debug(f"Código do cliente GOX: {cliente_id}")

        # Fornecedor (sempre GOX)
        data["fornecedor_nome"] = self._extract_fornecedor(text)
        data["cnpj_beneficiario"] = self._extract_cnpj(text)

        # Valor
        valor = self._extract_valor(text)
        if valor > 0:
            data["valor_documento"] = valor
            logger.debug(f"Valor extraído: R$ {valor:.2f}")

        # Datas
        vencimento = self._extract_vencimento(text)
        if vencimento:
            data["vencimento"] = vencimento
            
        emissao = self._extract_emissao(text)
        if emissao:
            data["data_emissao"] = emissao

        # Linha digitável
        linha = self._extract_linha_digitavel(text)
        if linha:
            data["linha_digitavel"] = linha

        # Referência NF (opcional - usar número do documento se disponível)
        if numero_doc:
            data["referencia_nfse"] = numero_doc

        logger.info(f"BoletoGoxExtractor: extração concluída (doc={numero_doc}, valor={valor})")
        return data
