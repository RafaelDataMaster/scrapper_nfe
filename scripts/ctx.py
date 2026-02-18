#!/usr/bin/env python
"""
Script de conveniência para busca rápida no contexto vetorizado.

ATALHO RÁPIDO para buscar informação nos docs de contexto sem digitar
o caminho completo do módulo.

USO:
====
    python scripts/ctx.py "PDF protegido"
    python scripts/ctx.py "como criar extrator" -n 5
    python scripts/ctx.py -i  # modo interativo

É equivalente a:
    python scripts/context_db/query.py "PDF protegido"

Mas mais curto de digitar!
"""

import sys
from pathlib import Path

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importa e executa o módulo de query
from scripts.context_db.query import ContextQuery
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="🔍 Busca rápida no contexto do projeto",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/ctx.py "PDF protegido"
  python scripts/ctx.py "timeout" -n 3
  python scripts/ctx.py -i
  python scripts/ctx.py --list
        """,
    )
    parser.add_argument("query", nargs="*", help="Termo de busca")
    parser.add_argument(
        "-n", "--top-k", type=int, default=5, help="Número de resultados (default: 5)"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Modo interativo"
    )
    parser.add_argument(
        "--list", action="store_true", help="Lista todos os documentos indexados"
    )
    parser.add_argument(
        "--reindex", action="store_true", help="Re-indexa todos os documentos"
    )

    args = parser.parse_args()

    # Re-indexar
    if args.reindex:
        from scripts.context_db.indexer import ContextIndexer

        indexer = ContextIndexer()
        indexer.clear()
        indexer.index_directory()
        return

    # Listar documentos
    if args.list:
        cq = ContextQuery()
        results = cq.collection.get(include=["metadatas"])

        # Extrai filenames únicos
        filenames = set()
        for meta in results["metadatas"]:
            filenames.add(meta.get("filename", "desconhecido"))

        print(f"\n📚 {len(filenames)} documentos indexados:\n")
        for f in sorted(filenames):
            print(f"   📄 {f}")
        print()
        return

    cq = ContextQuery()

    if args.query and not args.interactive:
        # Busca passada como argumento
        query = " ".join(args.query)
        print(cq.search_formatted(query, args.top_k))
    else:
        # Modo interativo
        print("\n💬 Modo interativo. Digite sua busca (ou 'sair' para encerrar):\n")
        print("   Comandos especiais:")
        print("   - 'doc <filename>' - Mostra documento completo")
        print("   - 'list' - Lista documentos indexados")
        print("   - 'sair' ou 'q' - Encerra o programa\n")

        while True:
            try:
                user_input = input("🔍 > ").strip()

                if user_input.lower() in ("sair", "exit", "quit", "q"):
                    print("👋 Até mais!")
                    break

                if user_input.lower() == "list":
                    results = cq.collection.get(include=["metadatas"])
                    filenames = set()
                    for meta in results["metadatas"]:
                        filenames.add(meta.get("filename", "desconhecido"))
                    print(f"\n📚 {len(filenames)} documentos:")
                    for f in sorted(filenames):
                        print(f"   📄 {f}")
                    print()
                elif user_input.lower().startswith("doc "):
                    # Comando para mostrar documento completo
                    filename = user_input[4:].strip()
                    print(f"\n📄 Documento: {filename}\n")
                    print(cq.get_full_document(filename))
                    print("\n" + "=" * 50)
                elif user_input:
                    print(cq.search_formatted(user_input, args.top_k))

            except KeyboardInterrupt:
                print("\n👋 Até mais!")
                break


if __name__ == "__main__":
    main()
