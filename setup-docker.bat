@echo off
REM Script de setup inicial para Docker no Windows
REM Usage: setup-docker.bat

echo =======================================
echo NFSe Scrapper - Setup Docker (Windows)
echo =======================================
echo.

REM 1. Verifica se Docker está instalado
echo 1. Verificando Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker nao encontrado!
    echo         Instale o Docker Desktop em: https://docs.docker.com/desktop/windows/install/
    pause
    exit /b 1
)
echo [OK] Docker instalado
echo.

REM 2. Verifica se Docker Compose está instalado
echo 2. Verificando Docker Compose...
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose nao encontrado!
    pause
    exit /b 1
)
echo [OK] Docker Compose instalado
echo.

REM 3. Verifica se o arquivo .env existe
echo 3. Verificando arquivo .env...
if not exist .env (
    echo [AVISO] Arquivo .env nao encontrado!
    if exist .env.example (
        echo         Copiando .env.example para .env...
        copy .env.example .env
        echo [OK] .env criado
        echo.
        echo [IMPORTANTE] Edite o arquivo .env com suas credenciais de email!
        echo              Variaveis obrigatorias:
        echo              - EMAIL_HOST (ex: imap.gmail.com^)
        echo              - EMAIL_USER (seu email completo^)
        echo              - EMAIL_PASS (senha de aplicativo^)
        echo.
        pause
    ) else (
        echo [ERROR] .env.example nao encontrado!
        pause
        exit /b 1
    )
) else (
    echo [OK] .env encontrado
)
echo.

REM 4. Cria estrutura de diretórios
echo 4. Criando estrutura de diretorios...
if not exist "data\output" mkdir "data\output"
if not exist "data\debug_output" mkdir "data\debug_output"
if not exist "temp_email" mkdir "temp_email"
if not exist "failed_cases_pdf" mkdir "failed_cases_pdf"
echo [OK] Diretorios criados
echo.

REM 5. Build da imagem
echo 5. Fazendo build da imagem Docker...
echo    (Isso pode demorar alguns minutos na primeira vez)
docker-compose build
if %errorlevel% neq 0 (
    echo [ERROR] Falha no build!
    pause
    exit /b 1
)
echo [OK] Build concluido
echo.

REM 6. Teste rápido
echo 6. Executando teste de configuracao...
docker-compose run --rm scrapper python scripts/test_docker_setup.py
set TEST_EXIT_CODE=%errorlevel%
echo.

if %TEST_EXIT_CODE% equ 0 (
    echo =======================================
    echo [OK] SETUP CONCLUIDO COM SUCESSO!
    echo =======================================
    echo.
    echo Proximos passos:
    echo.
    echo   1. Executar uma vez:
    echo      docker-compose run --rm scrapper
    echo.
    echo   2. Executar continuamente (a cada 30 min^):
    echo      docker-compose up -d scrapper-cron
    echo.
    echo   3. Ver logs:
    echo      docker-compose logs -f scrapper-cron
    echo.
    echo   4. Parar:
    echo      docker-compose down
    echo.
    echo Documentacao completa: README-DOCKER.md
    echo.
) else (
    echo =======================================
    echo [AVISO] SETUP CONCLUIDO MAS COM AVISOS
    echo =======================================
    echo.
    echo Alguns testes falharam, mas voce pode tentar executar mesmo assim:
    echo docker-compose run --rm scrapper
    echo.
)

pause
