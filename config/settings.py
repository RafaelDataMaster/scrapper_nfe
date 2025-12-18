import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# Caminhos Base
BASE_DIR = Path(__file__).resolve().parent.parent
DIR_SAIDA = BASE_DIR / "data" / "output"
DIR_TEMP = BASE_DIR / "temp_email"  # Nova pasta temporária para o gap de ingestão

# --- Caminhos de Debug (Test Rules) ---
DIR_DEBUG_INPUT = BASE_DIR / "failed_cases_pdf"  # Pasta de input para testes de regras
DIR_DEBUG_OUTPUT = BASE_DIR / "data" / "debug_output"
DEBUG_CSV_NFSE_SUCESSO = DIR_DEBUG_OUTPUT / "nfse_sucesso.csv"
DEBUG_CSV_NFSE_FALHA = DIR_DEBUG_OUTPUT / "nfse_falha.csv"
DEBUG_CSV_BOLETO_SUCESSO = DIR_DEBUG_OUTPUT / "boletos_sucesso.csv"
DEBUG_CSV_BOLETO_FALHA = DIR_DEBUG_OUTPUT / "boletos_falha.csv"
DEBUG_RELATORIO_QUALIDADE = DIR_DEBUG_OUTPUT / "relatorio_qualidade.txt"

# --- Caminhos de Binários Externos ---
# Centralizamos aqui para não espalhar caminhos pelo código
# Detecta automaticamente se está no Docker (Linux) ou Windows
import platform
is_linux = platform.system() == 'Linux'

# Defaults diferentes para Linux (Docker) e Windows (desenvolvimento)
if is_linux:
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', '/usr/bin/tesseract')
    POPPLER_PATH = os.getenv('POPPLER_PATH', '/usr/bin')
else:
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    POPPLER_PATH = os.getenv('POPPLER_PATH', r'C:\Poppler\Release-25.12.0-0\poppler-25.12.0\Library\bin')

# --- Parâmetros do OCR ---
# --psm 6: Assume um bloco único de texto uniforme (vital para notas fiscais)
OCR_CONFIG = r'--psm 6'
OCR_LANG = 'por'

# --- Parâmetros de Diretórios (Legado/Compatibilidade) ---
ARQUIVO_SAIDA = 'carga_notas_fiscais.csv'

# --- Configurações de E-mail (Lendo do ambiente com valores default seguros) ---
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_USER = os.getenv('EMAIL_USER', '')
EMAIL_PASS = os.getenv('EMAIL_PASS', '')
EMAIL_FOLDER = os.getenv('EMAIL_FOLDER', 'INBOX')

# Validação básica para não rodar sem config
if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASS]):
    print("⚠️ AVISO: Credenciais de e-mail não configuradas totalmente no .env")
