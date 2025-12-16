import re
from datetime import datetime
from typing import Dict, Any
from core.extractors import BaseExtractor, register_extractor

@register_extractor
class GenericExtractor(BaseExtractor):
    """
    Extrator generalista baseado em Expressões Regulares (Regex).

    Tenta identificar padrões comuns de NFS-e (CNPJ, Datas, Valores) sem depender
    de um layout visual específico. Serve como "rede de segurança" para prefeituras desconhecidas.
    """
    
    @classmethod
    def can_handle(cls, text: str) -> bool:
        # Se nenhum outro pegar, este pega (ou defina uma regra específica)
        # Como é um extrator genérico, ele deve ser o último recurso ou sempre retornar True se for o único
        # Por enquanto, vamos assumir que ele sempre tenta se for chamado
        return True 

    def extract(self, text: str) -> Dict[str, Any]:
        data = {}
        data['cnpj_prestador'] = self._extract_cnpj(text)
        data['numero_nota'] = self._extract_numero_nota(text)
        data['valor_total'] = self._extract_valor(text)
        data['data_emissao'] = self._extract_data_emissao(text)
        return data

    def _extract_cnpj(self, text: str):
        match = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text)
        return match.group(0) if match else None

    def _extract_valor(self, text: str):
        # Migrando sua função limpar_valor_monetario
        match = re.search(r'R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2})', text)
        if match:
            valor_str = match.group(1)
            return float(valor_str.replace('.', '').replace(',', '.'))
        return 0.0

    def _extract_data_emissao(self, text: str):
        # Migrando converter_data_iso
        match = re.search(r'\d{2}/\d{2}/\d{4}', text)
        if match:
            try:
                dt = datetime.strptime(match.group(0), '%d/%m/%Y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        return None

    def _extract_numero_nota(self, text: str):
        if not text:
            return None

        # --- 1. LIMPEZA CIRÚRGICA (Trazida do seu teste original) ---
        texto_limpo = text
        
        # Remove Datas (DD/MM/AAAA) para evitar confundir ano com número da nota
        texto_limpo = re.sub(r'\d{2}/\d{2}/\d{4}', ' ', texto_limpo)
        
        # Remove "RPS 1234", "Lote 1234", "Série 1", etc.
        padroes_lixo = r'(?i)\b(RPS|Lote|Protocolo|Recibo|S[eé]rie)\b\D{0,10}?\d+'
        texto_limpo = re.sub(padroes_lixo, ' ', texto_limpo)

        # --- 2. LISTA DE PADRÕES (Sua lógica de ouro) ---
        padroes = [
            # 1. CASO SALVADOR / MISTURADO (PRIORIDADE MÁXIMA)
            r'(?i)Número\s+da\s+Nota.*?(?<!\d)(\d{1,15})(?!\d)',

            # 2. CASO NFS-e ESPECÍFICO
            r'(?i)(?:(?:Número|Numero|N[º°o])\s*da\s*)?NFS-e\s*(?:N[º°o]|Num)?\.?\s*[:.-]?\s*\b(\d{1,15})\b',

            # 3. CASO VERTICAL (MARÍLIA/OUTROS)
            r'(?i)Número\s+da\s+Nota[\s\S]*?\b(\d{1,15})\b',

            # 4. CASO NOTA FISCAL (Genérico)
            r'(?i)Nota\s*Fiscal\s*(?:N[º°o]|Num)?\.?\s*[:.-]?\s*(\d{1,15})',
            
            # 5. CASO BLINDADO FINAL
            r'(?i)(?<!RPS\s)(?<!Lote\s)(?<!S[eé]rie\s)(?:Número|N[º°o])\s*[:.-]?\s*(\d{1,15})',
        ]

        # --- 3. LOOP DE TENTATIVAS ---
        for regex in padroes:
            match = re.search(regex, texto_limpo, re.IGNORECASE)
            if match:
                resultado = match.group(1)
                
                # Limpeza pós-match
                resultado = resultado.replace('.', '').replace(' ', '')
                return resultado
        
        return None
