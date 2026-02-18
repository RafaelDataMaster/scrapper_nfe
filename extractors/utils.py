"""
Módulo de utilidades compartilhadas para extratores.

Contém funções de parsing e normalização usadas por múltiplos extratores:
- Parsing de valores monetários brasileiros (R$ 1.234,56)
- Parsing de datas brasileiras (dd/mm/yyyy, dd-mm-yyyy)
- Extração e formatação de CNPJ/CPF
- Normalização de texto (acentos, espaços, entidades, caracteres OCR)

Princípio DRY: Estas funções eram duplicadas em boleto.py, danfe.py,
nfse_generic.py e outros.py. Centralizá-las aqui evita inconsistências
e facilita manutenção.
"""

import re
import unicodedata
from datetime import datetime
from typing import List, Optional

# =============================================================================
# REGEX COMPILADOS (evita recompilação a cada chamada)
# =============================================================================

# Valor monetário brasileiro: 1.234,56 ou 1234,56
BR_MONEY_RE = re.compile(r"\b(\d{1,3}(?:\.\d{3})*,\d{2})\b")

# CNPJ formatado: 00.000.000/0000-00
CNPJ_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")

# CNPJ sem formatação (14 dígitos)
CNPJ_DIGITS_RE = re.compile(
    r"(?<!\d)(\d{2})\D?(\d{3})\D?(\d{3})\D?(\d{4})\D?(\d{2})(?!\d)"
)

# CPF formatado: 000.000.000-00
CPF_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")

# Data brasileira: dd/mm/yyyy ou dd-mm-yyyy ou dd/mm/yy
BR_DATE_RE = re.compile(r"\b(\d{2})[/\-](\d{2})[/\-](\d{2,4})\b")


# =============================================================================
# PARSING DE VALORES MONETÁRIOS
# =============================================================================


def normalize_ocr_money_string(text: str) -> str:
    """
    Normaliza string monetária removendo espaços inseridos pelo OCR dentro de números.

    OCR problemático frequentemente insere espaços dentro de valores numéricos:
    - "R$ 2 2.396,17" -> "R$ 22.396,17"
    - "1 2 3 4,56" -> "1234,56"
    - "R$ 1 . 2 3 4 , 5 6" -> "R$ 1.234,56"

    A função preserva espaços legítimos:
    - Entre "R$" e o valor
    - Entre valores monetários completos (ex: "0,00 0,00" permanece inalterado)

    Args:
        text: String com possíveis espaços incorretos em valores monetários

    Returns:
        String com espaços normalizados dentro de números

    Examples:
        >>> normalize_ocr_money_string("R$ 2 2.396,17")
        'R$ 22.396,17'
        >>> normalize_ocr_money_string("Total: 1 2 3 4,56")
        'Total: 1234,56'
        >>> normalize_ocr_money_string("R$ 1 . 2 3 4 , 5 6")
        'R$ 1.234,56'
        >>> normalize_ocr_money_string("0,00 0,00 22,16")
        '0,00 0,00 22,16'
    """
    if not text:
        return ""

    # Passo 1: Remove espaços ao redor de pontos e vírgulas dentro de contexto numérico
    # Ex: "1 . 2 3 4 , 5 6" -> "1.234,56"
    text = re.sub(r"(\d)\s*\.\s*(\d)", r"\1.\2", text)
    text = re.sub(r"(\d)\s*,\s*(\d)", r"\1,\2", text)

    # Passo 2: Remove espaços entre dígitos APENAS na parte inteira (antes da vírgula).
    # Valores monetários brasileiros têm formato: XXX.XXX,YY
    # Após ,YY (vírgula + 2 dígitos) o valor está completo e o espaço é legítimo.
    #
    # Estratégia: processar segmentos entre valores completos (,\d\d) individualmente.
    # Isso preserva "0,00 0,00" mas corrige "2 2.396,17".

    def fix_segment(segment: str) -> str:
        """Remove espaços entre dígitos em um segmento."""
        prev = ""
        result = segment
        while prev != result:
            prev = result
            result = re.sub(r"(\d)\s+(\d)", r"\1\2", result)
        return result

    # Divide o texto em partes: valores completos (,\d\d) e o resto
    # Padrão: captura grupos de (parte_antes_da_virgula + ,XX)
    # Usamos split com grupo de captura para manter os delimitadores
    parts = re.split(r"(,\d{2})(?=\s|$|[^\d])", text)

    result_parts = []
    i = 0
    while i < len(parts):
        part = parts[i]
        # Aplica fix apenas em partes que NÃO são o final de valor (,XX)
        if not re.match(r"^,\d{2}$", part):
            part = fix_segment(part)
        result_parts.append(part)
        i += 1

    return "".join(result_parts)


def parse_br_money(value: str) -> float:
    """
    Converte valor monetário brasileiro para float.

    Formatos suportados:
    - "1.234,56" -> 1234.56
    - "1234,56" -> 1234.56
    - "1.234.567,89" -> 1234567.89

    Args:
        value: String com valor monetário no formato brasileiro

    Returns:
        float: Valor numérico ou 0.0 se inválido

    Examples:
        >>> parse_br_money("1.234,56")
        1234.56
        >>> parse_br_money("352,08")
        352.08
        >>> parse_br_money("")
        0.0
    """
    if not value:
        return 0.0
    try:
        # Remove pontos de milhar e troca vírgula decimal por ponto
        cleaned = value.replace(".", "").replace(",", ".")
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0


def extract_br_money_values(text: str) -> List[float]:
    """
    Extrai todos os valores monetários de um texto.

    Aplica normalização OCR para corrigir espaços inseridos dentro de números.

    Args:
        text: Texto contendo valores monetários

    Returns:
        Lista de floats com valores encontrados (> 0)

    Example:
        >>> extract_br_money_values("Total: R$ 1.234,56 + R$ 100,00")
        [1234.56, 100.0]
        >>> extract_br_money_values("R$ 2 2.396,17")  # OCR com espaços
        [22396.17]
    """
    if not text:
        return []

    # Normaliza texto para corrigir espaços OCR dentro de números
    normalized_text = normalize_ocr_money_string(text)

    values = []
    for match in BR_MONEY_RE.findall(normalized_text):
        val = parse_br_money(match.replace(" ", ""))
        if val > 0:
            values.append(val)
    return values


def extract_best_money_from_segment(segment: str) -> float:
    """
    Extrai o maior valor monetário de um segmento de texto.

    Útil quando uma linha contém múltiplos valores e queremos o principal
    (geralmente o maior, que representa o total).

    Args:
        segment: Trecho de texto a analisar

    Returns:
        Maior valor encontrado ou 0.0

    Example:
        >>> extract_best_money_from_segment("0,00 0,00 4.800,00")
        4800.0
    """
    values = extract_br_money_values(segment)
    return max(values) if values else 0.0


# =============================================================================
# PARSING DE DATAS
# =============================================================================


def parse_date_br(value: str) -> Optional[str]:
    """
    Converte data brasileira para formato ISO (YYYY-MM-DD).

    Formatos suportados:
    - dd/mm/yyyy (ex: 24/03/2025)
    - dd-mm-yyyy (ex: 24-03-2025)
    - dd/mm/yy (ex: 24/03/25 -> 2025-03-24)

    Args:
        value: String com data no formato brasileiro

    Returns:
        Data no formato ISO ou None se inválida

    Examples:
        >>> parse_date_br("24/03/2025")
        '2025-03-24'
        >>> parse_date_br("24-03-25")
        '2025-03-24'
        >>> parse_date_br("invalid")
        None
    """
    if not value:
        return None

    # Remove espaços extras que podem aparecer em PDFs mal extraídos
    value = re.sub(r"\s+", "", value.strip())

    # Normaliza separadores: hífen e ponto -> barra para parsing uniforme
    # Suporta formatos: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    normalized = value.replace("-", "/").replace(".", "/")

    # Tenta diferentes formatos
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            dt = datetime.strptime(normalized, fmt)
            # Para anos de 2 dígitos, ajusta século se necessário
            if dt.year < 100:
                dt = dt.replace(year=dt.year + 2000)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def extract_first_date_br(text: str) -> Optional[str]:
    """
    Extrai a primeira data brasileira encontrada no texto.

    Args:
        text: Texto a ser analisado

    Returns:
        Data no formato ISO ou None

    Example:
        >>> extract_first_date_br("Emitido em 24/03/2025 com vencimento 24/04/2025")
        '2025-03-24'
    """
    if not text:
        return None

    match = BR_DATE_RE.search(text)
    if match:
        return parse_date_br(match.group(0))
    return None


# =============================================================================
# EXTRAÇÃO DE CNPJ/CPF
# =============================================================================


def extract_cnpj(text: str) -> Optional[str]:
    """
    Extrai o primeiro CNPJ formatado do texto.

    Args:
        text: Texto contendo CNPJ

    Returns:
        CNPJ formatado (00.000.000/0000-00) ou None

    Example:
        >>> extract_cnpj("Empresa XYZ - CNPJ: 12.345.678/0001-90")
        '12.345.678/0001-90'
    """
    if not text:
        return None

    match = CNPJ_RE.search(text)
    return match.group(0) if match else None


def extract_cnpj_flexible(text: str) -> Optional[str]:
    """
    Extrai CNPJ mesmo sem formatação padrão e retorna formatado.

    Útil para PDFs onde a formatação foi perdida na extração.

    Args:
        text: Texto contendo CNPJ (formatado ou não)

    Returns:
        CNPJ formatado (00.000.000/0000-00) ou None

    Example:
        >>> extract_cnpj_flexible("CNPJ 12345678000190")
        '12.345.678/0001-90'
    """
    if not text:
        return None

    match = CNPJ_DIGITS_RE.search(text)
    if match:
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}/{match.group(4)}-{match.group(5)}"
    return None


def extract_cpf(text: str) -> Optional[str]:
    """
    Extrai o primeiro CPF formatado do texto.

    Args:
        text: Texto contendo CPF

    Returns:
        CPF formatado (000.000.000-00) ou None
    """
    if not text:
        return None

    match = CPF_RE.search(text)
    return match.group(0) if match else None


def format_cnpj(digits: str) -> str:
    """
    Formata 14 dígitos como CNPJ.

    Args:
        digits: String com 14 dígitos

    Returns:
        CNPJ formatado ou string original se inválido

    Example:
        >>> format_cnpj("12345678000190")
        '12.345.678/0001-90'
    """
    digits = re.sub(r"\D", "", digits or "")
    if len(digits) != 14:
        return digits
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


# =============================================================================
# NORMALIZAÇÃO DE TEXTO
# =============================================================================


def strip_accents(value: str) -> str:
    """
    Remove acentos de uma string.

    Útil para comparações case-insensitive e matching de palavras-chave.

    Args:
        value: String com possíveis acentos

    Returns:
        String sem acentos

    Example:
        >>> strip_accents("Código Eletrônico")
        'Codigo Eletronico'
    """
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_whitespace(text: str) -> str:
    """
    Normaliza espaços em branco (tabs, múltiplos espaços, nbsp).

    Args:
        text: Texto a normalizar

    Returns:
        Texto com espaços normalizados

    Example:
        >>> normalize_whitespace("Nome    da   Empresa")
        'Nome da Empresa'
    """
    if not text:
        return ""
    # Substitui caracteres especiais de espaço
    text = text.replace("\u00a0", " ")  # nbsp
    text = text.replace("\t", " ")
    # Colapsa múltiplos espaços
    return re.sub(r" +", " ", text).strip()


def normalize_text_for_extraction(text: str) -> str:
    """
    Normaliza texto para extração de dados.

    Trata problemas comuns em PDFs:
    - Hífens especiais (soft hyphen, en-dash, em-dash)
    - Espaços não-breaking
    - Múltiplos espaços/tabs
    - Caracteres OCR problemáticos (Ê, □, etc.)

    Args:
        text: Texto bruto extraído de PDF

    Returns:
        Texto normalizado
    """
    if not text:
        return ""

    # Normaliza hífens especiais
    text = text.replace("\u00ad", "-")  # soft hyphen
    text = text.replace("\u2013", "-")  # en-dash
    text = text.replace("\u2014", "-")  # em-dash

    # Normaliza caracteres OCR problemáticos
    # Caractere 'Ê' (circumflex accent) que aparece no lugar de espaços em alguns PDFs
    text = text.replace("Ê", " ")
    text = text.replace("ê", " ")

    # Outros caracteres problemáticos que podem aparecer em OCR
    problematic_chars = ["□", "▢", "■", "▭", "▯", "�"]
    for char in problematic_chars:
        text = text.replace(char, " ")

    # Normaliza espaços
    text = text.replace("\u00a0", " ")  # nbsp
    text = re.sub(r"[ \t]+", " ", text)

    return text


def _fix_ocr_duplicated_chars(text: str) -> str:
    """
    Corrige caracteres duplicados causados por OCR ruim.

    Alguns PDFs (como boletos da Localiza) têm caracteres duplicados
    devido a proteção anti-cópia ou problemas de renderização.
    Ex: "LLOOCCAALLIIZZAA" -> "LOCALIZA"

    Args:
        text: Texto possivelmente corrompido

    Returns:
        Texto corrigido
    """
    if not text or len(text) < 2:
        return text

    # Verifica se parece ter caracteres duplicados (padrão: AABBCC)
    # Heurística: tamanho par E todos os pares consecutivos são iguais
    if len(text) % 2 != 0:
        return text

    pairs = [(text[i], text[i + 1]) for i in range(0, len(text), 2)]
    duplicated_pairs = sum(1 for a, b in pairs if a == b)

    # Para palavras curtas (2-4 chars), exige 100% duplicação
    # Para palavras longas (6+ chars), exige 70% duplicação
    if len(text) <= 4:
        # Palavras curtas: só corrige se todos pares são duplicados (ex: "AA" -> "A")
        if duplicated_pairs == len(pairs):
            return "".join(text[i] for i in range(0, len(text), 2))
    elif len(pairs) >= 3 and duplicated_pairs / len(pairs) >= 0.7:
        # Palavras longas: corrige se maioria é duplicada
        return "".join(text[i] for i in range(0, len(text), 2))

    return text


def normalize_entity_name(raw: str) -> str:
    """
    Normaliza nome de entidade (empresa/pessoa).

    Remove:
    - CNPJ/CPF embutidos
    - Números de documento
    - Espaços extras
    - Caracteres especiais de pontuação
    - Caracteres OCR problemáticos
    - Sufixos truncados como "..."
    - Caracteres duplicados de OCR
    - Artefatos de OCR corrompido (ex: "Aeee [dede", "[dede", etc.)

    Args:
        raw: Nome bruto extraído

    Returns:
        Nome limpo e normalizado

    Example:
        >>> normalize_entity_name("EMPRESA XYZ LTDA   12.345.678/0001-90  ")
        'EMPRESA XYZ LTDA'
        >>> normalize_entity_name("LLOOCCAALLIIZZAA RREENNTT AA CCAARR")
        'LOCALIZA RENT A CAR'
        >>> normalize_entity_name("CORREIOS E TELEGRAFOS Aeee [dede")
        'CORREIOS E TELEGRAFOS'
    """
    name = (raw or "").strip()

    # Remove prefixos genéricos que não são parte do nome da empresa
    prefixes_to_remove = [
        r"^E-mail\s+",
        r"^Beneficiario\s+",
        r"^Beneficiário\s+",
        r"^Nome/NomeEmpresarial\s+",
        r"^Nome\s+/\s*Nome\s+Empresarial\s+E-mail\s+",  # "Nome / Nome Empresarial E-mail"
        r"^Nome\s+Empresarial\s+",
        r"^Razão\s+Social\s+",
        r"^Razao\s+Social\s+",
        r"^CNPJ\s*[:\s]*",  # "CNPJ" ou "CNPJ:" sozinho no início
        r"^CPF\s*[:\s]*",  # "CPF" ou "CPF:" sozinho no início
    ]
    for prefix_pattern in prefixes_to_remove:
        name = re.sub(prefix_pattern, "", name, flags=re.IGNORECASE)

    # Remove sufixos genéricos que não são parte do nome da empresa
    suffixes_to_remove = [
        r"\s+CONTATO\s*$",
        r"\s+CONTATO@[^\s]+\s*$",
        r"\s+CPF\s+ou\s+CNPJ\s*$",
        r"\s+CPF/CNPJ\s*$",
        r"\s+-\s+CNPJ\s*$",  # "- CNPJ" no final
        r"\s+-\s+CNPJ\s+\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s*$",  # "- CNPJ XX.XXX.XXX/XXXX-XX"
        r"\s+\|\s*CNPJ\s+-\s+CNPJ\s*$",  # "| CNPJ - CNPJ"
        r"\s+\|\s*CNPJ\s*$",  # "| CNPJ" no final
        r"\s+\|\s+CNL\.\s*$",  # "| CNL." no final (ex: VERO S.A. CNL.)
        r"\s+CNL\.\s*$",  # "CNL." solto no final
        r"\s+\|\s*$",  # "|" solto no final
        r"\s+=\s+CNPJ\s*$",  # "= CNPJ" no final
        r"\s+-\s+Endereço.*$",
        r"\s+-\s+Município.*$",
        r"\s+-\s+CEP.*$",
        r"\s+Endereço\s+Município\s+CEP.*$",  # "Endereço Município CEP PARAIBA"
        r"\s+-\s+Endereço\s+Município\s+CEP.*$",  # "- Endereço Município CEP PARAIBA"
        r"\s+Endereço\s*$",
        r"\s+CNPJ:\s*Al\s+.*$",  # "CNPJ: Al Vicente" texto truncado
        r"\s+CNPJ:\s*$",  # "CNPJ:" solto no final
        r"\s+ao\s+assinar\s*$",  # "ao assinar" no final
        r"\s+Gerente\s+de\s+conta:.*$",  # "Gerente de conta:NOME"
        r"\s+\*{4,}/\*{4,}\s*$",  # "******/********" (CNPJ mascarado)
        r"\s+\d{3,4}[-/]?\d*\s*$",  # Códigos de agência soltos no final (ex: "393", "401-301")
        r"\s+CPF/CNPJ\s*$",  # "CPF/CNPJ" solto no final
        r"\s+CPF\s*$",  # "CPF" solto no final
        r"\s+CNPJ\s+\.\s*\.\d*\s*$",  # "CNPJ . .61" lixo OCR
        r"\s+CNPJ\s*\.\s*\.\s*\d*\s*$",  # variação do padrão anterior
        r"\s+Nome\s+Empresarial\s*$",  # "Nome Empresarial" no final
        r"\s+Nome\s+/\s*Nome\s+Empresarial.*$",  # "Nome / Nome Empresarial..."
        r"\s+Nome\s+Fantasia\s+.*$",  # "Nome Fantasia NEW CONT..."
        # Emails/usernames colados ao nome da empresa
        r"\s+[a-z]+\.[a-z]+@.*$",  # "janaina.campos@..."
        r"\s+[a-z]+@.*$",  # "financeiro@..."
        r"\s+joaopmsoares\s*$",  # username colado
        r"\s+janaina\.campos\s*$",
        r"\s+financeiro\s*$",  # departamento colado (minúsculo)
        r"\s+comercial\s*$",  # departamento colado (minúsculo)
        r"\s+COMERCIAL\s*$",  # departamento colado (maiúsculo)
        r"\s+JOAOPMSOARES\s*$",
        r"\s+CONEXAOIDEALMG\s*$",  # username colado
        r"\s+[A-Z]+MG\s*$",  # usernames tipo "EMPRESAMG"
        # Sites www colados
        r"\s+www\.[a-z0-9\-]+\.[a-z\.]+\s*$",  # "www.voicecorp.com.br"
        # Padrões "inscrita no CNPJ"
        r",?\s+inscrita?\s+no\s+CNPJ.*$",  # ", inscrita no CNPJ/MF sob o nº"
        r"\s+CNPJ/MF\s+sob.*$",
        r"\s+CNPJ/CPF\s*$",  # "LTDA CNPJ/CPF"
        r"\s+CNPJ\s*$",  # "LTDA CNPJ" no final
        # Padrões de endereços/lixo que aparecem colados ao nome da empresa
        r"\s+ENDEREÇO\s+AV\.?.*$",  # "ENDEREÇO AV. AMAZONAS"
        r"\s+ENDERECO\s+AV\.?.*$",  # sem acento
        r"\s+/\s*-?\d*\s*\d*\s*\(\s*\)\s*Mudou-se.*$",  # "/ -1 1 ( ) Mudou-se"
        r"\s+Mudou-se.*$",  # "Mudou-se" no final
        r"\s+TAXID\d*-?.*$",  # "TAXID95-" e variações
        r"\s+Inscrição\s+Municipal.*$",  # "Inscrição Municipal" no final
        r"\s+Inscricao\s+Municipal.*$",  # sem acento
        r"\s+[A-F0-9]{8,}\s+Inscrição\s+Municipal.*$",  # "F50C0E532 Inscrição Municipal"
        r"\s+[A-F0-9]{8,}\s+Inscricao\s+Municipal.*$",  # sem acento
        r"\s+Florida\d+USA.*$",  # "Florida33134USA"
        r"\s+FINANCEIRO\s*$",  # "FINANCEIRO" solto no final
        r"\s+R\s+vel\s+pela\s+Ret.*$",  # "R vel pela Retoncã" OCR corrompido
        r"\s+Cod\.\s+de\s+Autenticidade.*$",  # "Cod. de Autenticidade"
        r"\s+\d+\s+ANDAR.*$",  # "17 ANDAR" endereço
        r"\s+EDIF\s+.*$",  # "EDIF PALACIO DA AGRICULTURA"
        # Endereços com cidade/UF
        r"\s+-\s+[A-Z]{2}\s+-\s+[A-Z][a-zA-Z\s]+$",  # "- CE - FORTALEZA"
        r"\s+-\s+[A-Z][a-zA-Z\s]+/\s*[A-Z]{2}\s*$",  # "- CARMO/ RJ"
        r"\s+CENTRO\s+NOVO\s+.*$",  # "CENTRO NOVO HAMBURGO/ RS"
        r"\s+PC\s+PRESIDENTE\s+.*$",  # "PC PRESIDENTE GETULIO VARGAS..."
        # Frases genéricas que não são nomes
        r"^Valor\s+da\s+causa\s*$",  # "Valor da causa"
        r"^No\s+Internet\s+Banking.*$",  # "No Internet Banking ou DDA..."
        r"^para\s+pagamento:.*$",  # "para pagamento: FAVORECIDO:..."
        r"^FAVORECIDO:.*$",  # "FAVORECIDO: EMPRESA"
        # "NOTA DE DÉBITO" no meio do nome (lixo OCR)
        r"\s+NOTA\s+DE\s+D[ÉE]BITO\s+",  # remove do meio
        # Strings muito genéricas que não são nomes de empresa
        r"^SISTEMAS\s+LTDA\s*$",  # "SISTEMAS LTDA" sozinho
        r"^UTILIDADE\s*$",  # "UTILIDADE" sozinho
        # Domínios de email/web no início ou como nome completo
        r"^[a-z0-9\-]+\.[a-z]{2,3}\.br\s*.*$",  # "dcadvogados.com.br ..."
        r"^[a-z0-9\-]+\.net\.br\s*.*$",  # "comunix.net.br ..."
        # CEP solto como nome
        r"^CEP[:\s].*$",  # "CEP: -325 - PRAIA..."
    ]
    for suffix_pattern in suffixes_to_remove:
        name = re.sub(suffix_pattern, "", name, flags=re.IGNORECASE)

    # Remove domínios .com.br / .net.br que aparecem como "nome" da empresa
    # Esses são OCR de rodapés de documentos, não nomes de fornecedor
    if re.match(r"^[a-z0-9\-]+\.(com|net|org)\.br\b", name, re.IGNORECASE):
        # Se começa com domínio, provavelmente é lixo - limpa tudo
        name = ""

    # Se começa com "Florida" + dígitos (endereço americano), é lixo
    if re.match(r"^Florida\d+", name, re.IGNORECASE):
        name = ""

    # Se começa com "CEP" ou "CEP:", é endereço, não fornecedor
    if re.match(r"^CEP[:\s]", name, re.IGNORECASE):
        name = ""

    # Se é frase genérica (não nome de empresa)
    if re.match(r"^Valor\s+da\s+causa\s*$", name, re.IGNORECASE):
        name = ""
    if re.match(r"^No\s+Internet\s+Banking", name, re.IGNORECASE):
        name = ""
    if re.match(r"^para\s+pagamento:", name, re.IGNORECASE):
        name = ""
    if re.match(r"^FAVORECIDO:", name, re.IGNORECASE):
        name = ""

    # Se é "SISTEMAS LTDA" ou "UTILIDADE" sozinho (muito genérico)
    if re.match(r"^SISTEMAS\s+LTDA\s*$", name, re.IGNORECASE):
        name = ""
    if re.match(r"^UTILIDADE\s*$", name, re.IGNORECASE):
        name = ""

    # Se é "Contas a Receber" ou similar (departamento, não fornecedor)
    if re.match(r"^Contas\s+a\s+(Receber|Pagar)\s*$", name, re.IGNORECASE):
        name = ""

    # Se é apenas UF (MG, SP, RJ, etc.) ou "CNPJ" sozinho
    if re.match(
        r"^(MG|SP|RJ|PR|SC|RS|BA|GO|DF|ES|PE|CE|PA|MA|MT|MS|CNPJ|CPF|CEP)$",
        name.strip(),
        re.IGNORECASE,
    ):
        name = ""

    # Se começa com "CENTRO NOVO" (endereço)
    if re.match(r"^CENTRO\s+NOVO\s+", name, re.IGNORECASE):
        name = ""

    # Se começa com "PC PRESIDENTE" ou "PRAÇA" (endereço)
    if re.match(r"^(PC|PRAÇA|PRACA)\s+PRESIDENTE\s+", name, re.IGNORECASE):
        name = ""

    # Remove artefatos OCR com colchetes (ex: "[dede", "[abc123", "Aeee [dede")
    # Colchetes não são comuns em nomes de empresas
    name = re.sub(r"\s*\[[^\]]*$", "", name)  # Remove "[algo" no final (sem fechar)
    name = re.sub(r"\s*\[[^\]]*\]", " ", name)  # Remove "[algo]" completo

    # Remove palavras curtas suspeitas no final (artefatos OCR como "Aeee", "dede")
    # Padrão: palavras de 2-5 letras repetidas (ex: "Aeee", "eee", "dede")
    name = re.sub(
        r"\s+[A-Za-z]([a-z])\1{2,}\s*$", "", name
    )  # "Aeee" (vogal + 3+ repetidas)
    name = re.sub(r"\s+([a-z])\1([a-z])\2\s*$", "", name)  # "dede" (padrão abab)

    # Remove sufixos truncados como "..." ou ".." (em qualquer posição)
    name = re.sub(r"\.{2,}", " ", name)

    # Remove prefixo "Beneficiário" colado (ex: "BeneficiárioREPROMAQ" -> "REPROMAQ")
    name = re.sub(r"(?i)^benefici[aá]rio\s*", "", name)

    # Normaliza espaços
    name = re.sub(r"\s+", " ", name)

    # Corrige caracteres duplicados de OCR (ex: "LLOOCCAALLIIZZAA" -> "LOCALIZA")
    # Aplica por palavra para preservar espaços
    words = name.split()
    fixed_words = [_fix_ocr_duplicated_chars(word) for word in words]
    name = " ".join(fixed_words)

    # Remove CNPJ
    name = re.sub(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", " ", name)

    # Remove CPF
    name = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", " ", name)

    # Remove números de documento (ex: 2025.122, 1234/5678)
    name = re.sub(r"\b\d+[\./]\d+\b", " ", name)

    # Remove sequências numéricas longas (4+ dígitos)
    name = re.sub(r"\b\d{4,}\b", " ", name)

    # Remove caracteres OCR problemáticos (Ê, □, etc.)
    name = name.replace("Ê", " ")
    name = name.replace("ê", " ")
    problematic_chars = ["□", "▢", "■", "▭", "▯", "�"]
    for char in problematic_chars:
        name = name.replace(char, " ")

    # Remove sufixos residuais após limpeza (ex: "// -- // --77")
    name = re.sub(r"[\s/\-]+\d*\s*$", "", name)

    # Remove código de agência/conta no final (3-4 dígitos após nome)
    # Ex: "Skymail LTDA 393" -> "Skymail LTDA"
    name = re.sub(r"\s+\d{3,4}\s*$", "", name)

    # Remove CNPJ mascarado no final (ex: "******/********")
    name = re.sub(r"\s+\*+/\*+\s*$", "", name)

    # Remove padrão "| CNPJ - CNPJ XX.XXX..." no final
    name = re.sub(r"\s*\|\s*CNPJ.*$", "", name, flags=re.IGNORECASE)

    # Remove padrão "= CNPJ" no final
    name = re.sub(r"\s*=\s*CNPJ.*$", "", name, flags=re.IGNORECASE)

    # Remove "CNL." ou "| CNL." no final
    name = re.sub(r"\s*\|?\s*CNL\.\s*$", "", name, flags=re.IGNORECASE)

    # Remove padrões de endereço internacional (Florida, USA, TAXID)
    name = re.sub(r"\s+Florida\d+USA.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+TAXID\d*-?.*$", "", name, flags=re.IGNORECASE)

    # Remove "/ -1 1 ( ) Mudou-se" e variações
    name = re.sub(
        r"\s*/\s*-?\d*\s*\d*\s*\(\s*\)\s*Mudou-se.*$", "", name, flags=re.IGNORECASE
    )
    name = re.sub(r"\s+Mudou-se.*$", "", name, flags=re.IGNORECASE)

    # Remove "Inscrição Municipal" e variações com hash
    name = re.sub(
        r"\s+[A-Fa-f0-9]{6,}\s+Inscri[cç][aã]o\s+Municipal.*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    name = re.sub(r"\s+Inscri[cç][aã]o\s+Municipal.*$", "", name, flags=re.IGNORECASE)

    # Remove "- Endereço Município CEP" e variações
    name = re.sub(
        r"\s+-\s+Endereço\s+Município\s+CEP.*$", "", name, flags=re.IGNORECASE
    )
    name = re.sub(r"\s+Endereço\s+Município\s+CEP.*$", "", name, flags=re.IGNORECASE)

    # Remove "FINANCEIRO" solto no final
    name = re.sub(r"\s+FINANCEIRO\s*$", "", name, flags=re.IGNORECASE)

    # Remove OCR corrompido tipo "R vel pela Retoncã"
    name = re.sub(r"\s+R\s+vel\s+pela\s+Ret.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+Q?comunix\.net\.br.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+dcadvogados\.com\.br.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+repromaq\.com\.br.*$", "", name, flags=re.IGNORECASE)

    # Remove "ENDEREÇO AV." e variações
    name = re.sub(r"\s+ENDERE[CÇ]O\s+AV\.?.*$", "", name, flags=re.IGNORECASE)

    # Remove endereços com EDIF/ANDAR
    name = re.sub(r"\s+EDIF\s+.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+\d+\s+ANDAR.*$", "", name, flags=re.IGNORECASE)

    # Remove "Cod. de Autenticidade" e similares
    name = re.sub(r"\s+Cod\.?\s+de\s+Autenticidade.*$", "", name, flags=re.IGNORECASE)

    # Remove emails/usernames colados no final
    name = re.sub(r"\s+[a-z]+\.[a-z]+@[^\s]*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+[a-z]+@[^\s]*$", "", name, flags=re.IGNORECASE)
    name = re.sub(
        r"\s+(joaopmsoares|janaina\.campos|conexaoidealmg)\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    name = re.sub(r"\s+(financeiro|comercial)\s*$", "", name, flags=re.IGNORECASE)

    # Remove "Nome Fantasia ..." colado no final
    name = re.sub(r"\s+Nome\s+Fantasia\s+.*$", "", name, flags=re.IGNORECASE)

    # Remove "NOTA DE DÉBITO" do meio do nome (lixo OCR) - mantém espaço
    name = re.sub(r"\s+NOTA\s+DE\s+D[ÉE]BITO\s+", " DE ", name, flags=re.IGNORECASE)

    # Remove www. colado no final
    name = re.sub(r"\s+www\.[a-z0-9\-\.]+\s*$", "", name, flags=re.IGNORECASE)

    # Remove ", inscrita no CNPJ" e variações
    name = re.sub(r",?\s+inscrita?\s+no\s+CNPJ.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+CNPJ/MF\s+sob.*$", "", name, flags=re.IGNORECASE)

    # Remove "CNPJ/CPF" ou "CNPJ" solto no final (após nome da empresa)
    name = re.sub(r"\s+CNPJ/CPF\s*$", "", name, flags=re.IGNORECASE)
    # Já existe regex para CNPJ solto, mas reforçando:
    name = re.sub(r"\s+CNPJ\s*$", "", name, flags=re.IGNORECASE)

    # Remove padrões de cidade/UF no final
    name = re.sub(r"\s+-\s+[A-Z]{2}\s+-\s+[A-Z][a-zA-Z\s]+$", "", name)
    name = re.sub(r"\s+-\s+[A-Z][a-zA-Z]+/\s*[A-Z]{2}\s*$", "", name)

    # Remove "CPF/CNPJ" ou "CNPJ" solto no final
    name = re.sub(r"\s+CPF/CNPJ\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+CNPJ\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+CPF\s*$", "", name, flags=re.IGNORECASE)

    # Remove lixo OCR tipo "CNPJ . .61"
    name = re.sub(r"\s+CNPJ\s*\.\s*\.\s*\d*\s*$", "", name, flags=re.IGNORECASE)

    # Remove palavras soltas no final que parecem lixo OCR
    # (palavras muito curtas ou com padrões estranhos após empresa válida)
    # Ex: "EMPRESA LTDA ABC" onde "ABC" é lixo
    words = name.split()
    if len(words) >= 3:
        last_word = words[-1]
        # Se última palavra é curta (<=4 chars) e não é sufixo empresarial válido
        valid_suffixes = {
            "LTDA",
            "SA",
            "S/A",
            "S.A",
            "S.A.",
            "ME",
            "MEI",
            "EPP",
            "EIRELI",
            "SS",
            "SIMPLES",
            "CIA",
            "CIA.",
            "INC",
            "CORP",
            "BRASIL",
            "BR",
            "SP",
            "RJ",
            "MG",
            "PR",
            "SC",
            "RS",
            "BA",
            "GO",
            "DF",
            "ES",
            "PE",
            "CE",
            "PA",
            "MA",
            "MT",
            "MS",
        }
        if len(last_word) <= 4 and last_word.upper() not in valid_suffixes:
            # Verifica se parece lixo (padrão de caracteres repetidos ou estranhos)
            if re.match(r"^[A-Za-z]([a-z])\1+$", last_word):  # ex: "Aeee"
                words = words[:-1]
                name = " ".join(words)

    # Limpa espaços e pontuação residual
    name = re.sub(r"\s+", " ", name).strip(" -:;/")

    return name.strip()


def normalize_digits(value: str) -> str:
    """
    Remove todos os caracteres não-numéricos.

    Útil para comparar CNPJs, CPFs, chaves de acesso.

    Args:
        value: String com possíveis não-dígitos

    Returns:
        Apenas os dígitos

    Example:
        >>> normalize_digits("12.345.678/0001-90")
        '12345678000190'
    """
    return re.sub(r"\D", "", value or "")


# =============================================================================
# VALIDAÇÕES
# =============================================================================


def is_valid_cnpj_format(value: str) -> bool:
    """
    Verifica se string está no formato de CNPJ (não valida dígitos verificadores).

    Args:
        value: String a verificar

    Returns:
        True se formato válido
    """
    if not value:
        return False
    return bool(CNPJ_RE.fullmatch(value.strip()))


def is_valid_cpf_format(value: str) -> bool:
    """
    Verifica se string está no formato de CPF (não valida dígitos verificadores).

    Args:
        value: String a verificar

    Returns:
        True se formato válido
    """
    if not value:
        return False
    return bool(CPF_RE.fullmatch(value.strip()))
