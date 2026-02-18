"""
Interface de busca semântica para documentos de contexto.

COMO FUNCIONA A BUSCA:
======================
1. Usuário faz pergunta: "como resolver PDF protegido?"
2. Pergunta é transformada em embedding (vetor de 384 números)
3. ChromaDB calcula distância entre esse vetor e todos os chunks
4. Retorna os N chunks mais "próximos" (semanticamente similares)

MÉTRICAS DE DISTÂNCIA:
======================
ChromaDB usa L2 (Euclidean) por padrão.
- Distância 0 = idêntico
- Distância pequena = muito similar
- Distância grande = pouco relacionado
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import chromadb
from chromadb.config import Settings
from typing import List, Optional
from dataclasses import dataclass

from scripts.context_db.embeddings import EmbeddingManager


@dataclass
class SearchResult:
    """
    Resultado de uma busca semântica.

    Attributes:
        content: Texto do chunk encontrado
        source: Arquivo de origem
        title: Título do documento
        distance: Distância do embedding (menor = mais relevante)
        chunk_index: Índice do chunk no documento original
    """

    content: str
    source: str
    title: str
    distance: float
    chunk_index: int

    def __str__(self) -> str:
        """Formatação amigável do resultado."""
        # Converte distância em % de relevância (menor distância = maior relevância)
        # Usamos uma fórmula simples: relevância = 1 / (1 + distance)
        relevance = 1 / (1 + self.distance)
        return (
            f"📄 {self.title}\n"
            f"   Fonte: {self.source}\n"
            f"   Relevância: {relevance:.2%}\n"
            f"   Chunk: {self.chunk_index}\n"
            f"   ─────────────────────────────────────\n"
            f"   {self.content[:500]}{'...' if len(self.content) > 500 else ''}\n"
        )


class ContextQuery:
    """
    Interface de busca semântica para o contexto do projeto.

    Example:
        >>> cq = ContextQuery()
        >>> resultados = cq.search("como resolver PDF protegido?", top_k=3)
        >>> for r in resultados:
        ...     print(r)
    """

    COLLECTION_NAME = "context_docs"

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa a interface de busca.

        Args:
            db_path: Caminho do banco vetorial. Default: data/vector_db/
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            db_path = project_root / "data" / "vector_db"

        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Banco vetorial não encontrado em {self.db_path}. "
                "Execute primeiro: python scripts/context_db/indexer.py"
            )

        # Conecta ao ChromaDB existente
        self.client = chromadb.PersistentClient(
            path=str(self.db_path), settings=Settings(anonymized_telemetry=False)
        )

        # Obtém a collection
        self.collection = self.client.get_collection(name=self.COLLECTION_NAME)

        # Inicializa embeddings (mesmo modelo usado na indexação!)
        self.embedding_manager = EmbeddingManager()

        print(f"✅ Conectado ao banco. {self.collection.count()} chunks disponíveis.")

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Busca semântica nos documentos de contexto.

        Args:
            query: Pergunta ou termo de busca
            top_k: Número de resultados a retornar

        Returns:
            Lista de SearchResult ordenados por relevância

        Example:
            >>> results = cq.search("timeout em PDF")
            >>> print(results[0].source)  # Arquivo mais relevante
        """
        print(f"🔍 Buscando: '{query}'")

        # 1. Transforma a query em embedding
        query_embedding = self.embedding_manager.embed(query).tolist()

        # 2. Busca no ChromaDB
        # query() retorna os N chunks mais próximos do embedding da query
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # 3. Formata resultados
        search_results = []

        # Os resultados vêm em listas (pois query pode ter múltiplas queries)
        # Pegamos o primeiro (índice 0) pois fizemos apenas 1 query
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            search_results.append(
                SearchResult(
                    content=doc,
                    source=meta.get("filename", "desconhecido"),
                    title=meta.get("title", "Sem título"),
                    distance=dist,
                    chunk_index=meta.get("chunk_index", 0),
                )
            )

        return search_results

    def search_formatted(self, query: str, top_k: int = 5) -> str:
        """
        Busca e retorna resultado formatado para exibição.

        Args:
            query: Pergunta ou termo de busca
            top_k: Número de resultados

        Returns:
            String formatada com todos os resultados
        """
        results = self.search(query, top_k)

        output = [f"\n🎯 {len(results)} resultados para: '{query}'\n"]
        output.append("=" * 50)

        for i, r in enumerate(results, 1):
            output.append(f"\n#{i} {r}")

        return "\n".join(output)

    def get_full_document(self, filename: str) -> str:
        """
        Recupera todos os chunks de um documento específico.

        Args:
            filename: Nome do arquivo (ex: "troubleshooting.md")

        Returns:
            Conteúdo completo do documento reconstruído
        """
        # Busca todos os chunks desse arquivo
        results = self.collection.get(
            where={"filename": filename},
            include=["documents", "metadatas"],
        )

        if not results["documents"]:
            return f"Documento '{filename}' não encontrado."

        # Ordena por chunk_index
        chunks_with_index = list(zip(results["documents"], results["metadatas"]))
        chunks_with_index.sort(key=lambda x: x[1].get("chunk_index", 0))

        # Reconstrói o documento
        # Note: devido ao overlap, pode haver repetição, mas é aceitável
        return "\n\n".join([chunk for chunk, _ in chunks_with_index])


# Script executável diretamente
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Busca semântica nos documentos de contexto"
    )
    parser.add_argument("query", nargs="*", help="Termo de busca")
    parser.add_argument(
        "-n", "--top-k", type=int, default=5, help="Número de resultados (default: 5)"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Modo interativo"
    )

    args = parser.parse_args()

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
        print("   - 'sair' ou 'q' - Encerra o programa\n")

        while True:
            try:
                user_input = input("🔍 > ").strip()

                if user_input.lower() in ("sair", "exit", "quit", "q"):
                    print("👋 Até mais!")
                    break

                if user_input.lower().startswith("doc "):
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
