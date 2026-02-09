#!/usr/bin/env python
"""
Script de teste para o sistema de quebra de senhas de PDFs.

Permite testar o desbloqueio de PDFs protegidos por senha usando os CNPJs
cadastrados no sistema como candidatos de senha.

Uso:
    python scripts/test_password_cracker.py <caminho_pdf>
    python scripts/test_password_cracker.py <caminho_pdf> --verbose
    python scripts/test_password_cracker.py --list-candidates
    python scripts/test_password_cracker.py --test-password <caminho_pdf> <senha>

Exemplos:
    # Testar desbloqueio de um PDF específico
    python scripts/test_password_cracker.py temp_email/batch123/fatura.pdf

    # Listar todos os candidatos de senha disponíveis
    python scripts/test_password_cracker.py --list-candidates

    # Testar uma senha específica em um PDF
    python scripts/test_password_cracker.py --test-password fatura.pdf 1234

    # Modo verbose (mostra cada tentativa)
    python scripts/test_password_cracker.py fatura.pdf --verbose
"""

import argparse
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pdfplumber
import pypdfium2 as pdfium

from config.empresas import EMPRESAS_CADASTRO


def gerar_candidatos_senha() -> list[str]:
    """
    Gera uma lista de candidatos a senha baseada nos CNPJs configurados.

    Replica a lógica de strategies/pdf_utils.py para testes independentes.
    """
    candidatos = set()

    for cnpj in EMPRESAS_CADASTRO.keys():
        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        candidatos.add(cnpj_limpo)

        # 4 primeiros dígitos
        if len(cnpj_limpo) >= 4:
            candidatos.add(cnpj_limpo[:4])

        # 5 primeiros dígitos
        if len(cnpj_limpo) >= 5:
            candidatos.add(cnpj_limpo[:5])

        # 8 primeiros dígitos (raiz do CNPJ)
        if len(cnpj_limpo) >= 8:
            candidatos.add(cnpj_limpo[:8])

    return sorted(list(candidatos))


def testar_senha_pdfplumber(
    file_path: str, senha: str | None = None
) -> tuple[bool, str | None]:
    """
    Tenta abrir um PDF com pdfplumber, opcionalmente com uma senha.

    Returns:
        Tupla (sucesso, mensagem_erro)
    """
    try:
        if senha:
            pdf = pdfplumber.open(file_path, password=senha)
        else:
            pdf = pdfplumber.open(file_path)

        # Tenta acessar páginas para verificar se realmente abriu
        _ = pdf.pages
        pdf.close()
        return True, None
    except Exception as e:
        return False, str(e)


def testar_senha_pypdfium(
    file_path: str, senha: str | None = None
) -> tuple[bool, str | None]:
    """
    Tenta abrir um PDF com pypdfium2, opcionalmente com uma senha.

    Returns:
        Tupla (sucesso, mensagem_erro)
    """
    try:
        if senha:
            pdf = pdfium.PdfDocument(file_path, password=senha)
        else:
            pdf = pdfium.PdfDocument(file_path)

        pdf.close()
        return True, None
    except Exception as e:
        return False, str(e)


def verificar_se_protegido(file_path: str) -> tuple[bool, str]:
    """
    Verifica se o PDF é protegido por senha.

    Returns:
        Tupla (protegido, biblioteca_usada)
    """
    # Tentar pdfplumber primeiro
    sucesso, erro = testar_senha_pdfplumber(file_path)
    if sucesso:
        return False, "pdfplumber"

    if "password" in erro.lower() or "encrypted" in erro.lower():
        return True, "pdfplumber"

    # Tentar pypdfium2
    sucesso, erro = testar_senha_pypdfium(file_path)
    if sucesso:
        return False, "pypdfium2"

    if "password" in erro.lower():
        return True, "pypdfium2"

    # Erro diferente de senha
    return False, f"erro: {erro}"


def tentar_quebrar_senha(file_path: str, verbose: bool = False) -> str | None:
    """
    Tenta quebrar a senha do PDF usando os candidatos gerados.

    Returns:
        Senha encontrada ou None se não conseguiu desbloquear
    """
    candidatos = gerar_candidatos_senha()
    total = len(candidatos)

    print(f"\n🔑 Tentando {total} candidatos de senha...")

    for i, senha in enumerate(candidatos, 1):
        if verbose:
            print(f"  [{i}/{total}] Testando: {senha}...", end=" ")

        # Tentar pdfplumber
        sucesso, _ = testar_senha_pdfplumber(file_path, senha)
        if sucesso:
            if verbose:
                print("✅ SUCESSO!")
            return senha

        # Tentar pypdfium2
        sucesso, _ = testar_senha_pypdfium(file_path, senha)
        if sucesso:
            if verbose:
                print("✅ SUCESSO!")
            return senha

        if verbose:
            print("❌")

    return None


def listar_candidatos():
    """Lista todos os candidatos de senha disponíveis."""
    candidatos = gerar_candidatos_senha()

    print("=" * 70)
    print("SISTEMA DE QUEBRA DE SENHAS - CANDIDATOS DISPONÍVEIS")
    print("=" * 70)
    print()
    print(f"Total de empresas cadastradas: {len(EMPRESAS_CADASTRO)}")
    print(f"Total de candidatos de senha: {len(candidatos)}")
    print()

    # Agrupar por tamanho
    por_tamanho = {}
    for c in candidatos:
        tamanho = len(c)
        if tamanho not in por_tamanho:
            por_tamanho[tamanho] = []
        por_tamanho[tamanho].append(c)

    print("Distribuição por tamanho:")
    for tamanho in sorted(por_tamanho.keys()):
        print(f"  - {tamanho} dígitos: {len(por_tamanho[tamanho])} candidatos")

    print()
    print("-" * 70)
    print("4 PRIMEIROS DÍGITOS (padrão TIM e alguns fornecedores):")
    print("-" * 70)
    for c in sorted(por_tamanho.get(4, [])):
        # Encontrar empresa correspondente
        empresa = None
        for cnpj, dados in EMPRESAS_CADASTRO.items():
            cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
            if cnpj_limpo.startswith(c):
                empresa = dados.get("razao_social", "")[:50]
                break
        print(f"  {c}  ->  {empresa or '?'}")

    print()
    print("-" * 70)
    print("8 PRIMEIROS DÍGITOS (raiz do CNPJ):")
    print("-" * 70)
    for c in sorted(por_tamanho.get(8, []))[:20]:  # Limitar a 20 para não poluir
        empresa = None
        for cnpj, dados in EMPRESAS_CADASTRO.items():
            cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
            if cnpj_limpo.startswith(c):
                empresa = dados.get("razao_social", "")[:40]
                break
        print(f"  {c}  ->  {empresa or '?'}")

    if len(por_tamanho.get(8, [])) > 20:
        print(f"  ... e mais {len(por_tamanho.get(8, [])) - 20} candidatos")


def testar_pdf(file_path: str, verbose: bool = False):
    """Testa um PDF específico."""
    path = Path(file_path)

    if not path.exists():
        # Tentar buscar em temp_email
        for pasta in Path("temp_email").rglob(path.name):
            path = pasta
            break

    if not path.exists():
        print(f"❌ Arquivo não encontrado: {file_path}")
        sys.exit(1)

    print("=" * 70)
    print("TESTE DE QUEBRA DE SENHA")
    print("=" * 70)
    print()
    print(f"📄 Arquivo: {path}")
    print(f"📏 Tamanho: {path.stat().st_size / 1024:.1f} KB")
    print()

    # Verificar se é protegido
    protegido, lib = verificar_se_protegido(str(path))

    if not protegido:
        print("✅ PDF NÃO é protegido por senha!")
        print(f"   (verificado com {lib})")
        return

    print("🔒 PDF PROTEGIDO por senha!")
    print(f"   (detectado via {lib})")

    # Tentar quebrar
    senha = tentar_quebrar_senha(str(path), verbose)

    if senha:
        print()
        print("=" * 70)
        print(f"🎉 SUCESSO! Senha encontrada: {senha}")
        print("=" * 70)

        # Identificar empresa
        for cnpj, dados in EMPRESAS_CADASTRO.items():
            cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
            if cnpj_limpo.startswith(senha) or cnpj_limpo == senha:
                print(f"   Empresa: {dados.get('razao_social', '?')}")
                print(f"   CNPJ: {cnpj}")
                break
    else:
        print()
        print("=" * 70)
        print("❌ FALHA! Senha não encontrada nos candidatos disponíveis.")
        print("=" * 70)
        print()
        print("Possíveis causas:")
        print("  1. A senha usa outro padrão (não baseado em CNPJ)")
        print("  2. O CNPJ do destinatário não está em EMPRESAS_CADASTRO")
        print("  3. Senha baseada em CPF (ex: Sabesp usa 3 primeiros dígitos do CPF)")
        print()
        print(
            "Para Sabesp: o sistema usa fallback para extrair dados do corpo do email"
        )


def testar_senha_especifica(file_path: str, senha: str):
    """Testa uma senha específica em um PDF."""
    path = Path(file_path)

    if not path.exists():
        print(f"❌ Arquivo não encontrado: {file_path}")
        sys.exit(1)

    print(f"📄 Testando senha '{senha}' em: {path}")
    print()

    # pdfplumber
    sucesso, erro = testar_senha_pdfplumber(str(path), senha)
    print(f"pdfplumber: {'✅ SUCESSO' if sucesso else f'❌ Falha ({erro})'}")

    # pypdfium2
    sucesso, erro = testar_senha_pypdfium(str(path), senha)
    print(f"pypdfium2:  {'✅ SUCESSO' if sucesso else f'❌ Falha ({erro})'}")


def main():
    parser = argparse.ArgumentParser(
        description="Testa o sistema de quebra de senhas de PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("pdf_path", nargs="?", help="Caminho do PDF a testar")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Mostra cada tentativa de senha"
    )

    parser.add_argument(
        "--list-candidates",
        "-l",
        action="store_true",
        help="Lista todos os candidatos de senha disponíveis",
    )

    parser.add_argument(
        "--test-password",
        "-t",
        nargs=2,
        metavar=("PDF", "SENHA"),
        help="Testa uma senha específica em um PDF",
    )

    args = parser.parse_args()

    if args.list_candidates:
        listar_candidatos()
    elif args.test_password:
        testar_senha_especifica(args.test_password[0], args.test_password[1])
    elif args.pdf_path:
        testar_pdf(args.pdf_path, args.verbose)
    else:
        parser.print_help()
        print()
        print("Dica: Use --list-candidates para ver os candidatos de senha disponíveis")


if __name__ == "__main__":
    main()
