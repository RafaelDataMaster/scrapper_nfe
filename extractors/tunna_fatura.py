"""
Extrator de Faturas da Tunna Entretenimento e Audiovisual LTDA (FishTV).

Este módulo implementa extração de dados de faturas/demonstrativos da Tunna,
que são documentos comerciais/fiscais com layout específico "FAT/XXXXX".

Campos extraídos:
    - numero_documento: Número da fatura (formato FAT/XXXXX)
    - valor_total: Valor total da fatura
    - data_emissao: Data de emissão
    - cnpj_emitente: CNPJ da Tunna
    - fornecedor_nome: Razão social

Identificação:
    - CNPJ: 13.XXX.XXX/XXXX-XX (verificar no texto)
    - Termos: "TUNNA ENTRETENIMENTO", "FAT/", "FATURA N�"
    - Layout específico com número de fatura no formato 000.XXX.XXX

Example:
    >>> from extractors.tunna_fatura import TunnaFaturaExtractor
    >>> extractor = TunnaFaturaExtractor()
    >>> dados = extractor.extract(texto_pdf)
    >>> print(f"Fatura: {dados['numero_documento']} - R$ {dados['valor_total']:.2f}")
"""
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import (
    normalize_text_for_extraction,
    parse_br_money,
    parse_date_br,
)


@register_extractor
class TunnaFaturaExtractor(BaseExtractor):
    """
    Extrator para faturas da Tunna Entretenimento e Audiovisual LTDA (FishTV).
    
    Identifica documentos pela razão social "TUNNA ENTRETENIMENTO" ou variações,
    e extrai informações do layout específico de faturas comerciais.
    """

    # CNPJ da Tunna (verificado em documentos reais)
    CNPJ_TUNNA = "13.399.99"  # Placeholder - atualizar com CNPJ real completo
    
    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Identifica se este é o extrator correto para faturas da Tunna.
        
        Critérios de identificação:
        - Razão social "TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA"
        - Termo "FAT/" no texto ou nome do arquivo
        - Padrão de fatura específico (FATURA N�: 000.XXX.XXX)
        
        Args:
            text: Texto extraído do PDF.
            
        Returns:
            True se o documento é uma fatura da Tunna.
        """
        if not text:
            return False
            
        text_upper = text.upper()
        
        # Indicadores FORTES da Tunna
        tunna_patterns = [
            "TUNNA ENTRETENIMENTO",
            "TUNNA ENTRETENIMENTO E AUDIOVISUAL",
            "FISHTV",
        ]
        
        has_tunna = any(pattern in text_upper for pattern in tunna_patterns)
        
        # Indicadores de ser uma fatura (não NFSe nem boleto)
        fatura_patterns = [
            "FAT/",
            "FATURA N�",
            "FATURA Nº",
            "FATURA N",
            "DEMONSTRATIVO",
            "FATURA RUA",  # Padrão específico visto no texto: "FATURA RUA MAJ..."
        ]
        
        has_fatura = any(pattern in text_upper for pattern in fatura_patterns)
        
        # Se tem TUNNA + FATURA, é este extrator
        if has_tunna and has_fatura:
            return True
            
        # Verificar se é fatura da Tunna mesmo sem "FATURA" explícito
        # (alguns documentos podem ter apenas "TUNNA" + padrão de número)
        if has_tunna:
            # Verificar padrão de número de fatura: 000.XXX.XXX
            if re.search(r"N[�º]?\s*[:\.]\s*\d{3}\.\d{3}\.\d{3}", text_upper):
                return True
                
        return False

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extrai dados da fatura da Tunna.
        
        Args:
            text: Texto extraído do PDF.
            
        Returns:
            Dicionário com dados extraídos.
        """
        text = self._normalize_text(text or "")
        
        # Usar tipo OUTRO com subtipo FATURA (documento administrativo)
        data: Dict[str, Any] = {
            "tipo_documento": "OUTRO",
            "subtipo": "FATURA",
            "descricao": "Fatura comercial Tunna"
        }
        
        # Campos principais
        numero_fatura = self._extract_numero_fatura(text)
        data["numero_documento"] = numero_fatura
        data["valor_total"] = self._extract_valor(text)
        data["data_emissao"] = self._extract_data_emissao(text)
        data["vencimento"] = self._extract_vencimento(text)
        data["cnpj_fornecedor"] = self._extract_cnpj(text)
        data["fornecedor_nome"] = "TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA"
        
        return data

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para extração."""
        return normalize_text_for_extraction(text)

    def _extract_numero_fatura(self, text: str) -> Optional[str]:
        """
        Extrai número da fatura.
        
        Padrões buscados:
        - "FAT/10731" (no assunto ou texto)
        - "FATURA Nº: 000.010.731" (com caractere corrompido pelo OCR)
        - "Nº.: 000.010.731" (com caractere corrompido pelo OCR)
        - "N.: 000.XXX.XXX"
        
        Args:
            text: Texto normalizado.
            
        Returns:
            Número da fatura (ex: "FAT/10731" ou "000.010.731") ou None.
        """
        # Padrão 1: FAT/XXXXX (no assunto ou texto)
        pattern_fat = re.search(r"FAT\/(\d+)", text, re.IGNORECASE)
        if pattern_fat:
            return f"FAT/{pattern_fat.group(1)}"
            
        # Padrão 2: N[qualquer coisa].: 000.XXX.XXX (tolerância a OCR)
        # Aceita: N., Nº., N:., N�., etc. - qualquer coisa entre N e :
        pattern_num = re.search(
            r"N\s*[^\w\s]?\s*[:\.]\s*(\d{3}\.\d{3}\.\d{3})", 
            text, 
            re.IGNORECASE
        )
        if pattern_num:
            return pattern_num.group(1)
            
        # Padrão 2b: Após RECEBEDOR (contexto específico visto no texto)
        # "RECEBEDOR N�.: 000.010.731"
        pattern_receb = re.search(
            r"RECEBEDOR\s*\S*\s*(\d{3}\.\d{3}\.\d{3})",
            text,
            re.IGNORECASE
        )
        if pattern_receb:
            return pattern_receb.group(1)
            
        # Padrão 3: Apenas números no formato 000.XXX.XXX após "FATURA"
        pattern_fatura = re.search(
            r"FATURA[^\n]{0,50}(\d{3}\.\d{3}\.\d{3})",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if pattern_fatura:
            return pattern_fatura.group(1)
            
        # Padrão 4: Qualquer sequência 000.XXX.XXX no texto (fallback)
        pattern_generic = re.search(r"(\d{3}\.\d{3}\.\d{3})", text)
        if pattern_generic:
            return pattern_generic.group(1)
            
        return None

    def _extract_valor(self, text: str) -> float:
        """
        Extrai valor total da fatura.
        
        Padrões buscados:
        - "VALOR TOTAL R$ X.XXX,XX"
        - "TOTAL R$ X.XXX,XX"
        - "VALOR R$ X.XXX,XX"
        - "METODO DE PAGAMENTO VALOR\n300,00" (padrão específico Tunna)
        - "R$: X.XXX,XX" (com dois pontos)
        - "R$ X.XXX,XX" (maior valor encontrado)
        
        Estratégia:
        1. Buscar padrões específicos de fatura
        2. Se não encontrar, usar heurística do maior valor monetário
        
        Args:
            text: Texto normalizado.
            
        Returns:
            Valor como float ou 0.0 se não encontrado.
        """
        # Padrão específico Tunna: "METODO DE PAGAMENTO VALOR" seguido de valor na próxima linha
        pattern_metodo = re.search(
            r"METODO\s+DE\s+PAGAMENTO\s+VALOR\s*\n\s*([\d\.]*,\d{2})",
            text,
            re.IGNORECASE
        )
        if pattern_metodo:
            return parse_br_money(pattern_metodo.group(1))
        
        # Padrão específico Tunna na tabela: "10731 / 1 15/02/26 R$: 300,00"
        # Note o R$: (com dois pontos)
        pattern_tabela = re.search(
            r"FATURA\s+VENCIMENTO\s+VALOR.*?\n\s*\d+\s*/\s*\d+\s+[\d/]+\s+R\$:\s*([\d\.]+,\d{2})",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if pattern_tabela:
            return parse_br_money(pattern_tabela.group(1))
        
        # Padrão: valor após "VALOR DEMONSTRATIVO"
        pattern_demonstrativo = re.search(
            r"VALOR\s+DEMONSTRATIVO\s*\n\s*([\d\.]*,\d{2})",
            text,
            re.IGNORECASE
        )
        if pattern_demonstrativo:
            return parse_br_money(pattern_demonstrativo.group(1))
        
        # Padrões genéricos de fatura
        specific_patterns = [
            r"(?i)VALOR\s+TOTAL\s*[:\s]+R\$\s*([\d\.]+,\d{2})",
            r"(?i)TOTAL\s*[:\s]+R\$\s*([\d\.]+,\d{2})",
            r"(?i)VALOR\s*[:\s]+R\$\s*([\d\.]+,\d{2})",
            r"(?i)TOTAL\s+A\s+PAGAR\s*[:\s]+R\$\s*([\d\.]+,\d{2})",
        ]
        
        for pattern in specific_patterns:
            match = re.search(pattern, text)
            if match:
                return parse_br_money(match.group(1))
                
        # Fallback: buscar todos os valores monetários e pegar o maior
        # (em faturas, o valor total geralmente é o maior valor listado)
        money_pattern = re.findall(r"R\$[:\s]\s*([\d\.]+,\d{2})", text)
        if money_pattern:
            valores = [parse_br_money(v) for v in money_pattern]
            if valores:
                return max(valores)  # Retorna o maior valor encontrado
        
        # Último fallback: qualquer número com formato de valor monetário
        all_values = re.findall(r"\b([\d\.]*,\d{2})\b", text)
        if all_values:
            valores = []
            for v in all_values:
                try:
                    # Ignorar valores muito pequenos (possivelmente quantidades)
                    val = parse_br_money(v)
                    if val >= 10.0:  # Filtro de valores relevantes
                        valores.append(val)
                except Exception:
                    continue
            if valores:
                return max(valores)
                
        return 0.0

    def _extract_data_emissao(self, text: str) -> Optional[str]:
        """
        Extrai data de emissão da fatura.
        
        Padrões buscados:
        - "DATA: DD/MM/AAAA"
        - "EMISS�O: DD/MM/AAAA"
        - "DATA DE EMISS�O: DD/MM/AAAA"
        
        Args:
            text: Texto normalizado.
            
        Returns:
            Data no formato ISO (YYYY-MM-DD) ou None.
        """
        patterns = [
            r"(?i)DATA\s*(?:DE)?\s*EMISS[ÃA�]O\s*[:\s]+(\d{2}/\d{2}/\d{4})",
            r"(?i)EMISS[ÃA�]O\s*[:\s]+(\d{2}/\d{2}/\d{4})",
            r"(?i)DATA\s*[:\s]+(\d{2}/\d{2}/\d{4})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return parse_date_br(match.group(1))
                
        return None
    
    def _extract_vencimento(self, text: str) -> Optional[str]:
        """
        Extrai data de vencimento da fatura.
        
        Padrões buscados:
        - "VENCIMENTO DD/MM/YY" (após NÚMERO DA ORDEM)
        - "10731 / 1 15/02/26" (padrão da tabela)
        
        Args:
            text: Texto normalizado.
            
        Returns:
            Data no formato ISO (YYYY-MM-DD) ou None.
        """
        # Padrão 1: Após "NÚMERO DA ORDEM VENCIMENTO"
        # 000.010.731 15/02/26
        pattern_ordem = re.search(
            r"N[�º]?MERO\s+DA\s+ORDEM\s+VENCIMENTO\s*\n\s*\d{3}\.\d{3}\.\d{3}\s+(\d{2}/\d{2}/\d{2,4})",
            text,
            re.IGNORECASE
        )
        if pattern_ordem:
            data_str = pattern_ordem.group(1)
            # Converter ano de 2 para 4 dígitos se necessário
            if len(data_str.split('/')[-1]) == 2:
                dia, mes, ano = data_str.split('/')
                ano_int = int(ano)
                # Assumir que anos 00-29 são 2000-2029, 30-99 são 1930-1999
                if ano_int < 30:
                    ano = '20' + ano
                else:
                    ano = '19' + ano
                data_str = f"{dia}/{mes}/{ano}"
            return parse_date_br(data_str)
        
        # Padrão 2: Na tabela FATURA VENCIMENTO VALOR
        # 10731 / 1 15/02/26 R$: 300,00
        pattern_tabela = re.search(
            r"FATURA\s+VENCIMENTO\s+VALOR.*?\n\s*\d+\s*/\s*\d+\s+(\d{2}/\d{2}/\d{2,4})",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if pattern_tabela:
            data_str = pattern_tabela.group(1)
            # Converter ano de 2 para 4 dígitos se necessário
            if len(data_str.split('/')[-1]) == 2:
                dia, mes, ano = data_str.split('/')
                ano_int = int(ano)
                if ano_int < 30:
                    ano = '20' + ano
                else:
                    ano = '19' + ano
                data_str = f"{dia}/{mes}/{ano}"
            return parse_date_br(data_str)
        
        # Padrão 3: Busca genérica por "VENCIMENTO" seguido de data
        pattern_generic = re.search(
            r"(?i)VENCIMENTO\s*[:\s]+(\d{2}/\d{2}/\d{4})",
            text
        )
        if pattern_generic:
            return parse_date_br(pattern_generic.group(1))
                
        return None

    def _extract_cnpj(self, text: str) -> Optional[str]:
        """
        Extrai CNPJ da Tunna.
        
        Busca por padrões de CNPJ no texto.
        
        Args:
            text: Texto normalizado.
            
        Returns:
            CNPJ formatado ou None.
        """
        # Padrão CNPJ: XX.XXX.XXX/XXXX-XX
        pattern = r"(\d{2})\D?(\d{3})\D?(\d{3})\D?(\d{4})\D?(\d{2})"
        match = re.search(pattern, text)
        
        if match:
            cnpj = f"{match.group(1)}.{match.group(2)}.{match.group(3)}/{match.group(4)}-{match.group(5)}"
            return cnpj
            
        return None


# =============================================================================
# TESTES (para validação do extrator)
# =============================================================================

TEST_CASES = [
    # Caso real FishTV #205
    {
        "input": "TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA. FATURA N�: 000.010.731",
        "expected_numero": "000.010.731",
        "expected_fornecedor": "TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA",
    },
    # Caso com FAT/ no texto
    {
        "input": "FAT/10731 - TUNNA ENTRETENIMENTO",
        "expected_numero": "FAT/10731",
        "expected_fornecedor": "TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA",
    },
]

EDGE_CASES = [
    # Não deve pegar documentos de outros fornecedores
    ("OUTRA EMPRESA LTDA FATURA 123", False),
    ("TUNNA SEM SER FATURA", False),  # Sem indicador de fatura
]
