"""
Extractor para Aditivos de Contrato.

Extrai informacoes de aditivos contratuais, que sao documentos
que alteram ou adicionam clausulas a contratos existentes.
"""
import re
from typing import Any, Dict, Optional
from core.extractors import BaseExtractor, register_extractor


@register_extractor
class AditivoContratoExtractor(BaseExtractor):
    """
    Extrator para aditivos de contrato.
    
    Padroes identificados:
    - "ADITIVO AO CONTRATO"
    - "ADITIVO DE CONTRATO"
    - CNPJ do fornecedor/contratado
    - Valores e descricao das alteracoes
    """

    # Indicadores de aditivo de contrato
    ADITIVO_INDICATORS = [
        r'ADITIVO\s+(?:AO|DE)\s+CONTRATO',
        r'CONTRATO\s+DE\s+PRESTA[ÇC]AO\s+DE\s+SERVI[ÇC]OS',
        r'TERMO\s+ADITIVO',
    ]

    # CNPJs conhecidos de empresas que frequentemente tem aditivos
    KNOWN_CNPJS = {
        '02.952.192/0001-61': 'ALARES INTERNET S/A',
        '02.952.192/0029-62': 'ALARES INTERNET S/A',  # Filial
        '13.003.072/0001-34': 'ITACOLOMI COMUNICACAO LTDA',
    }
    
    # CNPJs das empresas que sao destinatarias (nao fornecedores) em aditivos
    EMPRESAS_DESTINATARIAS = [
        '27.103.413/0001-57',  # CARRIER TELECOM S/A
    ]

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """Verifica se o texto eh um aditivo de contrato."""
        text_upper = text.upper()
        
        # Verificar indicadores de aditivo
        aditivo_matches = 0
        for pattern in cls.ADITIVO_INDICATORS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                aditivo_matches += 1
        
        # Se tem pelo menos um indicador forte de aditivo
        if aditivo_matches >= 1:
            # Verificar se tem CNPJ de fornecedor conhecido ou estrutura contratual
            if cls._extract_cnpj(text):
                return True
            
            # Verificar se tem estrutura de contrato (partes, clausulas, etc.)
            if re.search(r'(CONTRATANTE|CONTRATADA|PARTES|CLAUSULA)', text_upper):
                return True
        
        return False

    @classmethod
    def extract(cls, text: str, context: Optional[dict] = None) -> Dict[str, Any]:
        """Extrai dados do aditivo de contrato."""
        data: Dict[str, Any] = {
            'tipo_documento': 'OUTRO',
            'subtipo': 'ADITIVO_CONTRATO',
        }
        
        # Extrair CNPJs presentes no texto
        cnpjs_encontrados = cls._extract_all_cnpjs(text)
        
        # Identificar fornecedor pelo CNPJ conhecido
        # Priorizar CNPJs que estao em KNOWN_CNPJS
        fornecedor_cnpj = None
        for cnpj in cnpjs_encontrados:
            if cnpj in cls.KNOWN_CNPJS:
                # Se ainda nao temos fornecedor, usar este
                if fornecedor_cnpj is None:
                    fornecedor_cnpj = cnpj
                    data['cnpj_fornecedor'] = cnpj
                    data['fornecedor_nome'] = cls.KNOWN_CNPJS[cnpj]
                # Se ja temos ITACOLOMI mas achamos ALARES (qualquer filial), substituir
                elif fornecedor_cnpj == '13.003.072/0001-34' and cnpj.startswith('02.952.192'):
                    fornecedor_cnpj = cnpj
                    data['cnpj_fornecedor'] = cnpj
                    data['fornecedor_nome'] = cls.KNOWN_CNPJS[cnpj]
        
        # Se nao achou CNPJ conhecido, tentar extrair fornecedor pelo texto
        if 'fornecedor_nome' not in data:
            fornecedor = cls._extract_fornecedor(text)
            if fornecedor:
                data['fornecedor_nome'] = fornecedor
        
        # Extrair numero do contrato original
        contrato_num = cls._extract_contrato_numero(text)
        if contrato_num:
            data['numero_contrato_original'] = contrato_num
        
        # Extrair numero do aditivo
        aditivo_num = cls._extract_aditivo_numero(text)
        if aditivo_num:
            data['numero_aditivo'] = aditivo_num
        
        # Extrair valor (usar valor_total para compatibilidade com processor)
        valor = cls._extract_valor(text)
        if valor:
            data['valor_total'] = valor
        
        # Extrair descricao/objeto
        descricao = cls._extract_descricao(text)
        if descricao:
            data['descricao'] = descricao
        
        # Data do aditivo
        data_aditivo = cls._extract_data_aditivo(text)
        if data_aditivo:
            data['data_documento'] = data_aditivo
        
        return data

    @classmethod
    def _extract_fornecedor(cls, text: str) -> Optional[str]:
        """Extrai o nome do fornecedor/contratado/locador."""
        _text_upper = text.upper()
        
        # Caso 1: Aditivo de locacao - fornecedor eh o LOCADOR (pessoa fisica ou juridica)
        # Padrao: "LOCADOR, NOME, inscrito no CPF/CNPJ"
        match = re.search(
            r'LOCADOR[,\s]+([A-Z][A-Z\s]+?),\s*inscrito',
            text, re.IGNORECASE
        )
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r'[\x00-\x1F]', '', nome)
            nome = ' '.join(nome.split())
            if len(nome) > 3:
                return nome
        
        # Caso alternativo: procurar por nome antes de ", inscrito no CPF"
        match = re.search(
            r'([A-Z][A-Z\s]{5,50}[A-Z]),\s*inscrito\s+no\s+CPF',
            text, re.IGNORECASE
        )
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r'[\x00-\x1F]', '', nome)
            nome = ' '.join(nome.split())
            if len(nome) > 3:
                return nome
        
        # Caso 2: Aditivo de contrato de prestacao de servicos - fornecedor eh a CONTRATADA
        # Procurar por padroes de identificacao do contratado
        
        # Padrao especifico: apos "CONTRATANTE. " vem o nome da contratada
        match = re.search(
            r'CONTRATANTE\.\s*([A-Z][A-Z\s/]+S/A|[A-Z][A-Z\s]+LTDA\.?)[,\s]+inscrita',
            text, re.IGNORECASE
        )
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r'[\x00-\x1F]', '', nome)
            nome = ' '.join(nome.split())
            if len(nome) > 3:
                return nome
        
        # Padrao alternativo: CONTRATADA seguido do nome
        match = re.search(
            r'CONTRATADA[,\s]+([A-Z][A-Z\s/]+S/A|[A-Z][A-Z\s]+LTDA\.?)[,\s]+inscrita',
            text, re.IGNORECASE
        )
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r'[\x00-\x1F]', '', nome)
            nome = ' '.join(nome.split())
            if len(nome) > 3:
                return nome
        
        # Padrao generico: CNPJ X, doravante denominada 'NOME'
        match = re.search(
            r'doravante\s+denominada\s+[\'\"]?([^\'\"\n]{3,60}?)[\'\"]?\s*(?:,|ou|CONTRAT)',
            text, re.IGNORECASE
        )
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r'[\x00-\x1F]', '', nome)
            nome = ' '.join(nome.split())
            if len(nome) > 3 and len(nome) < 60:
                return nome
        
        return None

    @classmethod
    def _extract_cnpj(cls, text: str) -> Optional[str]:
        """Extrai o CNPJ do fornecedor/contratado."""
        # Procurar por CNPJ mencionado no contexto de contratada
        patterns = [
            # CNPJ apos "inscrita no CNPJ/MF sob o n"
            r'inscrita\s+no\s+CNPJ/MF\s+sob\s+o\s+n[\x00-\x1F]?[\s]*([\d]{2}[\.,][\d]{3}[\.,][\d]{3}[\.,/\s]*[\d]{4}[-\s]*[\d]{2})',
            # CNPJ apos "inscrita no CNPJ"
            r'inscrita\s+no\s+CNPJ.*?([\d]{2}[\.,][\d]{3}[\.,][\d]{3}[\.,/\s]*[\d]{4}[-\s]*[\d]{2})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cnpj = cls._normalize_cnpj(match)
                # Validar se eh CNPJ conhecido
                if cnpj in cls.KNOWN_CNPJS:
                    return cnpj
        
        # Se nao achou CNPJ conhecido, procurar qualquer CNPJ formatado
        cnpj_pattern = r'\b(\d{2}[\.,]\d{3}[\.,]\d{3}[\.,/]?\d{4}[-\s]?\d{2})\b'
        matches = re.findall(cnpj_pattern, text)
        for match in matches:
            cnpj = cls._normalize_cnpj(match)
            if cnpj in cls.KNOWN_CNPJS:
                return cnpj
        
        return None

    @classmethod
    def _extract_all_cnpjs(cls, text: str) -> list:
        """Extrai todos os CNPJs do texto."""
        cnpjs = []
        # Padrao CNPJ formatado
        pattern = r'\b(\d{2}[\.,]\d{3}[\.,]\d{3}[\.,/]?\d{4}[-\s]?\d{2})\b'
        matches = re.findall(pattern, text)
        for match in matches:
            cnpj = cls._normalize_cnpj(match)
            if cnpj not in cnpjs:
                cnpjs.append(cnpj)
        return cnpjs

    @classmethod
    def _normalize_cnpj(cls, cnpj: str) -> str:
        """Normaliza o CNPJ para formato padrao."""
        digits = re.sub(r'\D', '', cnpj)
        if len(digits) == 14:
            return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        return cnpj

    @classmethod
    def _extract_contrato_numero(cls, text: str) -> Optional[str]:
        """Extrai o numero do contrato original."""
        patterns = [
            r'CONTRATO\s+N[\x00-\x1F]?[\s]*[\xBA]?[\s]*(\d{2,10}(?:\.\d+)?)',
            r'CONTRATO\s+N[\x00-\x1F]?[\s]*(?:\xBA|N?\xBA)?[\s]*([A-Z]?\d{2,8})',
            r'CONTRATO\s+DE\s+PRESTA[ÇC][ÃA]O\s+DE\s+SERVI[ÇC]OS\s+N[\x00-\x1F]?[\s]*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    @classmethod
    def _extract_aditivo_numero(cls, text: str) -> Optional[str]:
        """Extrai o numero do aditivo."""
        patterns = [
            r'ADITIVO\s+(?:AO|DE)\s+CONTRATO\s+([\d\.]+)',
            r'ADITIVO\s+N[\x00-\x1F]?[\s]*(\d+)',
            r'(\d+)[\x00-\x1F]?[\s]*_?[\s]*ADITIVO',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    @classmethod
    def _extract_valor(cls, text: str) -> Optional[float]:
        """Extrai o valor do aditivo."""
        # Procurar por valores monetarios
        patterns = [
            r'VALOR[^\n]{0,50}(\d{1,3}(?:\.\d{3})*,\d{2})',
            r'R\$[^\n]{0,20}(\d{1,3}(?:\.\d{3})*,\d{2})',
            r'(\d{1,3}(?:\.\d{3})*,\d{2})\s*(?:REAIS?|R\$)',
        ]
        
        valores = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    valor_str = match.replace('.', '').replace(',', '.')
                    valor = float(valor_str)
                    if 10.0 < valor < 1000000.0:  # Valores razoaveis
                        valores.append(valor)
                except ValueError:
                    continue
        
        # Retornar o maior valor encontrado (geralmente o principal)
        return max(valores) if valores else None

    @classmethod
    def _extract_descricao(cls, text: str) -> Optional[str]:
        """Extrai a descricao/objeto do aditivo."""
        # Procurar por clausulas que descrevem o objeto
        patterns = [
            r'(?:CL[ÁA]USULA|OBJETO)[\s\w]*[:\-]?\s*([^\n]{20,200})',
            r'ADITIVO[^\n]{0,100}(CONEX[ÃA]O[^\n]{10,100})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                # Limpar caracteres de controle
                desc = re.sub(r'[\x00-\x1F]', ' ', desc)
                # Limitar tamanho
                if len(desc) > 200:
                    desc = desc[:200] + '...'
                return desc
        
        return None

    @classmethod
    def _extract_data_aditivo(cls, text: str) -> Optional[str]:
        """Extrai a data do aditivo."""
        # Procurar por datas no formato DD/MM/YYYY ou similar
        patterns = [
            r'(\d{2})[/-](\d{2})[/-](\d{4})',
            r'(\d{2})\s+de\s+(\w+)\s+de\s+(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 3:
                    dia, mes, ano = match.groups()
                    # Se mes eh texto, converter
                    if not mes.isdigit():
                        meses = {
                            'janeiro': '01', 'fevereiro': '02', 'marco': '03',
                            'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07',
                            'agosto': '08', 'setembro': '09', 'outubro': '10',
                            'novembro': '11', 'dezembro': '12'
                        }
                        mes = meses.get(mes.lower(), '01')
                    return f"{ano}-{mes}-{dia}"
        
        return None
