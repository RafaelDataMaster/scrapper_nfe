import os
import re
import pdfplumber
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from datetime import datetime

# --- CONFIGURAÇÕES ---
PASTA_ORIGEM = r'nfs/' # Ajuste aqui
ARQUIVO_SAIDA = 'carga_notas_fiscais.csv'
# Caminho para o executável (precisa terminar em .exe)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
custom_config = r'--psm 6'
# Caminho para a PASTA bin (não selecione um arquivo, selecione a pasta)
PATH_POPPLER = r'C:\Poppler\Release-25.12.0-0\poppler-25.12.0\Library\bin'

def extrair_texto_ocr(caminho_pdf):
    """
    Converte PDF em imagem e usa Tesseract para ler o texto.
    Use como último recurso (é mais lento).
    """
    print(f"⚠️ Ativando OCR para: {caminho_pdf}")
    try:
        # 1. Converte a primeira página do PDF em imagem
        imagens = convert_from_path(caminho_pdf, poppler_path=PATH_POPPLER, first_page=1, last_page=1)
        
        # 2. Extrai texto da imagem
        texto_ocr = ""
        for img in imagens:
            # lang='por' ajuda a identificar acentos
            texto_ocr += pytesseract.image_to_string(img, lang='por', config=custom_config)
            
        return texto_ocr
    except Exception as e:
        print(f"Erro no OCR: {e}")
        return ""
    
def limpar_valor_monetario(valor_str):
    """
    Converte '1.250,50' (BR) para 1250.50 (FLOAT PURO)
    Isso é vital para o PostgreSQL aceitar como NUMERIC/DECIMAL.
    """
    if not valor_str:
        return 0.0
    limpo = valor_str.replace('.', '').replace(',', '.')
    try:
        return float(limpo)
    except ValueError:
        return 0.0

def converter_data_iso(data_str):
    """
    Converte '25/12/2023' para '2023-12-25'
    O PostgreSQL prefere formato ISO (YYYY-MM-DD).
    """
    if not data_str:
        return None
    try:
        # Tenta parsear dia/mes/ano
        obj_data = datetime.strptime(data_str, '%d/%m/%Y')
        return obj_data.strftime('%Y-%m-%d')
    except ValueError:
        return None # Ou retorne a string original se preferir
    

def extrair_numero_nota_flexivel(texto):
    if not texto: return None

    # --- 1. LIMPEZA CIRÚRGICA (A Grande Mudança) ---
    # Em vez de apagar a linha inteira (que pode ter o número da nota),
    # vamos apagar apenas os padrões "RPS + Número", "Lote + Número", etc.
    
    texto_limpo = texto
    
    # Remove Datas (DD/MM/AAAA) para evitar confundir ano com número da nota
    texto_limpo = re.sub(r'\d{2}/\d{2}/\d{4}', ' ', texto_limpo)
    
    # Remove "RPS 1234", "Lote 1234", "Série 1", "Recibo 123"
    # O regex procura a palavra chave seguida opcionalmente de simbolos e depois digitos
    # Substitui por vazio '' para sumir com esses números do mapa.
    padroes_lixo = r'(?i)\b(RPS|Lote|Protocolo|Recibo|S[eé]rie)\b\D{0,10}?\d+'
    texto_limpo = re.sub(padroes_lixo, ' ', texto_limpo)

    # --- 2. DICIONÁRIO DE REGEX OTIMIZADO ---
    padroes = [
        # 1. CASO SALVADOR / MISTURADO (PRIORIDADE MÁXIMA)
        # Como já limpamos o RPS na etapa 1, agora podemos ser mais diretos.
        # Procura "Número da Nota", ignora lixo (.*?) e pega o número.
        # O (?:...)* permite pular palavras soltas como "Prefeitura", "Municipal", etc.
        r'(?i)Número\s+da\s+Nota.*?(?<!\d)(\d{1,15})(?!\d)',

        # 2. CASO NFS-e ESPECÍFICO
        r'(?i)(?:(?:Número|Numero|N[º°o])\s*da\s*)?NFS-e\s*(?:N[º°o]|Num)?\.?\s*[:.-]?\s*\b(\d{1,15})\b',

        # 3. CASO VERTICAL (MARÍLIA/OUTROS)
        # O [\s\S]*? permite pular quebra de linha se o OCR quebrou
        r'(?i)Número\s+da\s+Nota[\s\S]*?\b(\d{1,15})\b',

        # 4. CASO NOTA FISCAL (Genérico)
        r'(?i)Nota\s*Fiscal\s*(?:N[º°o]|Num)?\.?\s*[:.-]?\s*(\d{1,15})',
        
        # 5. CASO BLINDADO FINAL
        # Só pega se tiver certeza que não tem palavras chave antes (redundância de segurança)
        r'(?i)(?<!RPS\s)(?<!Lote\s)(?<!S[eé]rie\s)(?:Número|N[º°o])\s*[:.-]?\s*(\d{1,15})',
    ]

    for regex in padroes:
        match = re.search(regex, texto_limpo, re.IGNORECASE)
        if match:
            resultado = match.group(1)
            
            # --- 3. VALIDAÇÃO PÓS-MATCH (Pente Fino) ---
            
            # Remove pontos ou espaços que possam ter vindo junto (ex: "1.998" -> "1998")
            resultado = resultado.replace('.', '').replace(' ', '')

            # Validação de Ano (Evita pegar "2023" solto no texto)
            if resultado in ['2022', '2023', '2024', '2025', '2026']:
                continue
            
            # Validação de Tamanho
            # Notas costumam ter mais de 1 dígito, a menos que seja a nota nº 1 a 9.
            # Se for regex genérico (item 4 ou 5), exigimos pelo menos 3 digitos para segurança
            if len(resultado) < 2 and "NFS-e" not in regex:
                # Se for muito pequeno (1 dígito), assume que é lixo ou nº de página
                continue

            return resultado

    return None

def extrair_info_nfe(caminho_arquivo):
    dados = {
        'arquivo_origem': os.path.basename(caminho_arquivo),
        'cnpj_prestador': None,
        'numero_nota': None,
        'data_emissao': None,
        'valor_total': 0.0,
        'texto_bruto': '' 
    }
    
    try:
        texto = ""
        
        # 1. TENTATIVA RÁPIDA (PDFPLUMBER)
        with pdfplumber.open(caminho_arquivo) as pdf:
            if len(pdf.pages) > 0:
                texto = pdf.pages[0].extract_text() or "" 

            # 2. TENTATIVA LENTA (OCR)
            if not texto or len(texto.strip()) < 50:
                print(f"⚠️ Texto nativo não encontrado. Ativando OCR para: {dados['arquivo_origem']}")
                texto = extrair_texto_ocr(caminho_arquivo)

            if not texto:
                dados['texto_bruto'] = "Falha: Arquivo ilegível ou vazio"
                return dados
        
            dados['texto_bruto'] = texto[:100].replace('\n', ' ') 

            # 1. CNPJ
            match_cnpj = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto)
            if match_cnpj:
                dados['cnpj_prestador'] = match_cnpj.group(0)

            # 2. Número da Nota
            dados['numero_nota'] = extrair_numero_nota_flexivel(texto)

            # 3. Valor Total
            match_valor = re.search(r'R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2})', texto)
            if match_valor:
                dados['valor_total'] = limpar_valor_monetario(match_valor.group(1))
            
            # 4. Data de Emissão
            match_data = re.search(r'\d{2}/\d{2}/\d{4}', texto)
            if match_data:
                dados['data_emissao'] = converter_data_iso(match_data.group(0))

    except Exception as e:
        print(f"Erro ao ler {caminho_arquivo}: {e}")
    
    return dados

def main():
    lista_dados = []
    
    # 1. Varredura
    for root, dirs, files in os.walk(PASTA_ORIGEM):
        for file in files:
            if file.lower().endswith('.pdf'):
                caminho = os.path.join(root, file)
                print(f"Processando: {file}")
                lista_dados.append(extrair_info_nfe(caminho))

    # 2. Geração do CSV
    if lista_dados:
        df = pd.DataFrame(lista_dados)
        
        # Salvando CSV padrão internacional (separador virgula, aspas duplas)
        # Isso facilita muito o COPY do Postgres
        df.to_csv(ARQUIVO_SAIDA, index=False, sep=',', encoding='utf-8')
        
        print(f"\nConcluído! {len(df)} notas processadas.")
        print(f"Arquivo gerado: {os.path.abspath(ARQUIVO_SAIDA)}")
    else:
        print("Nenhum PDF encontrado.")

if __name__ == "__main__":
    main()