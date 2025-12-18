#!/bin/bash
# Script de setup inicial para Docker
# Usage: ./setup-docker.sh

set -e

echo "🐳 NFSe Scrapper - Setup Docker"
echo "================================"
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Verifica se Docker está instalado
echo "1️⃣  Verificando Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não encontrado!${NC}"
    echo "   Instale o Docker em: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✅ Docker $(docker --version)${NC}"

# 2. Verifica se Docker Compose está instalado
echo "2️⃣  Verificando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose não encontrado!${NC}"
    echo "   Instale o Docker Compose em: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose $(docker-compose --version)${NC}"

# 3. Verifica se o arquivo .env existe
echo "3️⃣  Verificando arquivo .env..."
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Arquivo .env não encontrado!${NC}"
    
    if [ -f .env.example ]; then
        echo "   Copiando .env.example para .env..."
        cp .env.example .env
        echo -e "${GREEN}✅ .env criado${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  IMPORTANTE: Edite o arquivo .env com suas credenciais de email!${NC}"
        echo "   Variáveis obrigatórias:"
        echo "   - EMAIL_HOST (ex: imap.gmail.com)"
        echo "   - EMAIL_USER (seu email completo)"
        echo "   - EMAIL_PASS (senha de aplicativo, não sua senha normal!)"
        echo ""
        read -p "Pressione ENTER depois de configurar o .env..." 
    else
        echo -e "${RED}❌ .env.example não encontrado!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env encontrado${NC}"
fi

# 4. Valida conteúdo do .env
echo "4️⃣  Validando credenciais..."
if ! grep -q "EMAIL_HOST=" .env || ! grep -q "EMAIL_USER=" .env || ! grep -q "EMAIL_PASS=" .env; then
    echo -e "${RED}❌ Variáveis de email não configuradas no .env${NC}"
    echo "   Edite o arquivo .env e configure:"
    echo "   - EMAIL_HOST"
    echo "   - EMAIL_USER"
    echo "   - EMAIL_PASS"
    exit 1
fi

# Verifica se não estão vazias
if grep -q "EMAIL_PASS=$" .env || grep -q "EMAIL_PASS=sua_senha" .env; then
    echo -e "${YELLOW}⚠️  EMAIL_PASS parece não estar configurado!${NC}"
    read -p "Continuar mesmo assim? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ Credenciais configuradas${NC}"

# 5. Cria estrutura de diretórios
echo "5️⃣  Criando estrutura de diretórios..."
mkdir -p data/output data/debug_output temp_email failed_cases_pdf
echo -e "${GREEN}✅ Diretórios criados${NC}"

# 6. Build da imagem
echo "6️⃣  Fazendo build da imagem Docker..."
echo "   (Isso pode demorar alguns minutos na primeira vez)"
docker-compose build
echo -e "${GREEN}✅ Build concluído${NC}"

# 7. Teste rápido
echo "7️⃣  Executando teste de configuração..."
docker-compose run --rm scrapper python scripts/test_docker_setup.py
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ SETUP CONCLUÍDO COM SUCESSO!${NC}"
    echo ""
    echo "📚 Próximos passos:"
    echo ""
    echo "  1. Executar uma vez:"
    echo "     docker-compose run --rm scrapper"
    echo ""
    echo "  2. Executar continuamente (a cada 30 min):"
    echo "     docker-compose up -d scrapper-cron"
    echo ""
    echo "  3. Ver logs:"
    echo "     docker-compose logs -f scrapper-cron"
    echo ""
    echo "  4. Parar:"
    echo "     docker-compose down"
    echo ""
    echo "📖 Documentação completa: README-DOCKER.md"
    echo ""
else
    echo ""
    echo -e "${YELLOW}⚠️  SETUP CONCLUÍDO MAS COM AVISOS${NC}"
    echo ""
    echo "   Alguns testes falharam, mas você pode tentar executar mesmo assim:"
    echo "   docker-compose run --rm scrapper"
    echo ""
fi
