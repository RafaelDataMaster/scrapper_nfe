#!/usr/bin/env python
"""
Script de inicialização de sessão para o Claude.

OBJETIVO:
=========
Preparar o contexto de forma rápida e leve no início de cada sessão,
sem precisar ler todos os 29 documentos manualmente.

USO:
====
    python scripts/session_init.py

O QUE FAZ:
==========
1. Verifica se o banco vetorial está atualizado
2. Mostra resumo do projeto (status, métricas)
3. Lista documentos disponíveis para busca
4. Fornece comandos úteis para a sessão

FLUXO RECOMENDADO:
==================
1. Usuário inicia sessão: "Nova sessão - carrega contexto"
2. Claude roda: python scripts/session_init.py
3. Claude está pronto para buscar contexto sob demanda com: python scripts/ctx.py "termo"
"""

import sys
from pathlib import Path
from datetime import datetime

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check_vector_db() -> dict:
    """
    Verifica status do banco vetorial.

    Returns:
        Dict com status do banco
    """
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "data" / "vector_db"

    status = {
        "exists": db_path.exists(),
        "path": str(db_path),
        "chunks": 0,
        "documents": 0,
        "needs_reindex": False,
    }

    if not db_path.exists():
        status["needs_reindex"] = True
        return status

    try:
        # Importa apenas se o banco existir
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=str(db_path), settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_collection(name="context_docs")
        results = collection.get(include=["metadatas"])

        status["chunks"] = len(results["ids"])

        # Conta documentos únicos
        filenames = set()
        for meta in results["metadatas"]:
            filenames.add(meta.get("filename", ""))
        status["documents"] = len(filenames)

        # Verifica se há docs novos não indexados
        docs_path = project_root / "docs" / "context"
        current_docs = set(f.name for f in docs_path.glob("*.md"))
        indexed_docs = filenames

        new_docs = current_docs - indexed_docs
        if new_docs:
            status["needs_reindex"] = True
            status["new_docs"] = list(new_docs)

    except Exception as e:
        status["error"] = str(e)
        status["needs_reindex"] = True

    return status


def get_project_summary() -> dict:
    """
    Obtém resumo rápido do projeto.

    Returns:
        Dict com informações do projeto
    """
    project_root = Path(__file__).resolve().parent.parent

    summary = {
        "name": "scrapper",
        "description": "Pipeline ETL para extração de documentos fiscais (NF, Boletos, DANFE)",
    }

    # Conta extratores
    extractors_path = project_root / "extractors"
    if extractors_path.exists():
        extractors = list(extractors_path.glob("*.py"))
        # Remove __init__.py e utils.py
        extractors = [
            e for e in extractors if e.name not in ("__init__.py", "utils.py")
        ]
        summary["extractors_count"] = len(extractors)

    # Verifica se há logs recentes
    logs_path = project_root / "logs"
    if logs_path.exists():
        log_files = list(logs_path.glob("*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
            summary["latest_log"] = latest_log.name

    # Verifica batches pendentes
    temp_email_path = project_root / "temp_email"
    if temp_email_path.exists():
        batches = [d for d in temp_email_path.iterdir() if d.is_dir()]
        summary["pending_batches"] = len(batches)

    return summary


def print_session_header():
    """Imprime cabeçalho da sessão."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 60)
    print("🚀 INICIALIZAÇÃO DE SESSÃO - SCRAPPER")
    print(f"📅 {now}")
    print("=" * 60)


def print_vector_db_status(status: dict):
    """Imprime status do banco vetorial."""
    print("\n📊 BANCO VETORIAL (ChromaDB)")
    print("-" * 40)

    if not status["exists"]:
        print("   ❌ Banco não encontrado!")
        print("   💡 Execute: python scripts/ctx.py --reindex")
        return

    if status.get("error"):
        print(f"   ⚠️ Erro ao acessar banco: {status['error']}")
        return

    print(f"   📁 Documentos indexados: {status['documents']}")
    print(f"   📄 Chunks totais: {status['chunks']}")

    if status["needs_reindex"]:
        print("   ⚠️ Re-indexação recomendada!")
        if status.get("new_docs"):
            print(f"   📝 Novos docs: {', '.join(status['new_docs'])}")
        print("   💡 Execute: python scripts/ctx.py --reindex")
    else:
        print("   ✅ Banco atualizado!")


def print_project_summary(summary: dict):
    """Imprime resumo do projeto."""
    print("\n📋 RESUMO DO PROJETO")
    print("-" * 40)
    print(f"   📦 {summary['name']}: {summary['description']}")

    if "extractors_count" in summary:
        print(f"   🔧 Extratores: {summary['extractors_count']}")

    if "pending_batches" in summary:
        print(f"   📨 Batches em temp_email: {summary['pending_batches']}")

    if "latest_log" in summary:
        print(f"   📝 Log mais recente: {summary['latest_log']}")


def print_quick_commands():
    """Imprime comandos úteis."""
    print("\n⚡ COMANDOS RÁPIDOS")
    print("-" * 40)
    print("   🔍 Buscar contexto:")
    print('      python scripts/ctx.py "termo de busca"')
    print()
    print("   📄 Ver documento completo:")
    print("      python scripts/ctx.py -i  →  doc troubleshooting.md")
    print()
    print("   🔄 Re-indexar docs:")
    print("      python scripts/ctx.py --reindex")
    print()
    print("   📋 Listar docs disponíveis:")
    print("      python scripts/ctx.py --list")


def print_context_topics():
    """Imprime tópicos principais disponíveis no contexto."""
    print("\n📚 TÓPICOS DISPONÍVEIS NO CONTEXTO")
    print("-" * 40)
    topics = [
        ("Criar extrator", "creation.md"),
        ("Validar correção", "validation.md"),
        ("Diagnosticar problema", "diagnosis.md"),
        ("Troubleshooting", "troubleshooting.md"),
        ("Padrões de código", "coding_standards.md"),
        ("Comandos úteis", "commands_reference.md"),
        ("Overview do projeto", "project_overview.md"),
        ("Padrões de logging", "logging_standards.md"),
        ("PDFs protegidos", "pdf_password_handling.md"),
    ]

    for topic, doc in topics:
        print(f"   • {topic:<25} → {doc}")


def print_footer():
    """Imprime rodapé."""
    print("\n" + "=" * 60)
    print("✅ Sessão inicializada! Pronto para receber comandos.")
    print("💡 Use 'python scripts/ctx.py \"termo\"' para buscar contexto.")
    print("=" * 60 + "\n")


def main():
    """Executa inicialização da sessão."""
    print_session_header()

    # Verifica banco vetorial (sem carregar modelo de embeddings)
    db_status = check_vector_db()
    print_vector_db_status(db_status)

    # Resumo do projeto
    project_summary = get_project_summary()
    print_project_summary(project_summary)

    # Tópicos disponíveis
    print_context_topics()

    # Comandos úteis
    print_quick_commands()

    # Rodapé
    print_footer()

    # Retorna código de saída baseado no status
    if db_status.get("needs_reindex"):
        return 1  # Indica que re-indexação é necessária
    return 0


if __name__ == "__main__":
    sys.exit(main())
