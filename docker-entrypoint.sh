#!/bin/bash
# Script de inicialização do container

set -e

echo "🐳 Iniciando container do NFSe Scrapper..."

# Verifica se o Tesseract está instalado
if ! command -v tesseract &> /dev/null; then
    echo "❌ ERRO: Tesseract não encontrado!"
    exit 1
fi

echo "✅ Tesseract versão: $(tesseract --version | head -1)"

# Verifica se o Poppler está instalado
if ! command -v pdfinfo &> /dev/null; then
    echo "❌ ERRO: Poppler não encontrado!"
    exit 1
fi

echo "✅ Poppler versão: $(pdfinfo -v 2>&1 | head -1)"

# Verifica se as credenciais de email estão configuradas
if [ -z "$EMAIL_HOST" ] || [ -z "$EMAIL_USER" ] || [ -z "$EMAIL_PASS" ]; then
    echo "⚠️  AVISO: Credenciais de email não configuradas!"
    echo "    Configure as variáveis: EMAIL_HOST, EMAIL_USER, EMAIL_PASS"
fi

# Cria diretórios necessários se não existirem
mkdir -p data/output data/debug_output temp_email failed_cases_pdf

echo "📂 Estrutura de diretórios verificada"

# Executa o comando passado ao container (ou o CMD padrão)
echo "🚀 Executando: $@"
exec "$@"
