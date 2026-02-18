"""
Indexador de documentos de contexto para ChromaDB.

CONCEITO:
=========
Este script lê todos os arquivos .md de docs/context/, divide cada um
em "chunks" (pedaços menores) e armazena no ChromaDB com seus embeddings.

POR QUE DIVIDIR EM CHUNKS?
==========================
1. Documentos grandes (ex: 5000 palavras) são difíceis de buscar com precisão
2. Se você pergunta "como resolver timeout?", o documento inteiro é muito genérico
3. Dividindo em chunks de ~500 palavras, a busca retorna o trecho específico
4. Cada chunk mantém metadados (arquivo de origem, posição) para referência

ESTRUTURA DO CHROMADB:
======================
Collection "context_docs":
├── ID: hash único do chunk
├── Document: texto do chunk
├── Embedding: vetor de 384 dimensões
└── Metadata:
    ├── source: "docs/context/troubleshooting.md"
    ├── chunk_index: 0, 1, 2...
    └── title: título extraído do documento
"""

import sys
from pathlib import Path

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import chromadb
from chromadb.config import Settings
import hashlib
import re
from typing import List, Dict, Optional

from scripts.context_db.embeddings import EmbeddingManager


# Configurações de chunking
CHUNK_SIZE = 500  # Palavras por chunk (aproximado)
CHUNK_OVERLAP = 50  # Palavras de sobreposição entre chunks


def extract_title(content: str) -> str:
    """
    Extrai o título do documento (primeiro # heading).

    Args:
        content: Conteúdo markdown do arquivo

    Returns:
        Título extraído ou "Sem título"
    """
    # Procura por # no início de linha (heading markdown)
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Sem título"


def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> List[str]:
    """
    Divide texto em chunks com sobreposição.

    COMO FUNCIONA:
    ==============
    Texto: "palavra1 palavra2 palavra3 palavra4 palavra5 palavra6"
    chunk_size=3, overlap=1

    Chunk 0: "palavra1 palavra2 palavra3"
    Chunk 1: "palavra3 palavra4 palavra5"  <- overlap: palavra3 repetida
    Chunk 2: "palavra5 palavra6"

    A sobreposição evita que informação seja "cortada" entre chunks.

    Args:
        text: Texto completo
        chunk_size: Número aproximado de palavras por chunk
        overlap: Palavras de sobreposição

    Returns:
        Lista de chunks de texto
    """
    # Divide por palavras (simplificado)
    words = text.split()

    if len(words) <= chunk_size:
        # Texto pequeno, retorna inteiro
        return [text]

    chunks = []
    start = 0

    while start < len(words):
        # Pega chunk_size palavras a partir de start
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))

        # Avança com sobreposição
        # Se chunk_size=500 e overlap=50, avança 450 palavras
        start += chunk_size - overlap

    return chunks


def generate_chunk_id(source: str, chunk_index: int) -> str:
    """
    Gera ID único para um chunk.

    Usa hash MD5 do path + índice para garantir unicidade
    e permitir atualizações incrementais.
    """
    content = f"{source}::{chunk_index}"
    return hashlib.md5(content.encode()).hexdigest()


class ContextIndexer:
    """
    Indexa documentos de contexto no ChromaDB.

    Attributes:
        db_path: Caminho onde o ChromaDB persiste os dados
        collection: Collection do ChromaDB com os documentos
        embedding_manager: Gerenciador de embeddings
    """

    COLLECTION_NAME = "context_docs"

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa o indexador.

        Args:
            db_path: Caminho para persistir o banco.
                    Default: data/vector_db/
        """
        # Define caminho do banco
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            db_path = project_root / "data" / "vector_db"

        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        print(f"📁 Banco vetorial em: {self.db_path}")

        # Inicializa ChromaDB com persistência em disco
        # PersistentClient = dados salvos em disco, sobrevivem entre execuções
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False),  # Desativa telemetria
        )

        # Inicializa gerenciador de embeddings
        self.embedding_manager = EmbeddingManager()

        # Cria ou obtém a collection
        # get_or_create = cria se não existe, obtém se já existe
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Documentos de contexto do projeto scrapper"},
        )

        print(
            f"📚 Collection '{self.COLLECTION_NAME}' pronta. "
            f"Documentos atuais: {self.collection.count()}"
        )

    def index_file(self, file_path: Path) -> int:
        """
        Indexa um único arquivo markdown.

        Args:
            file_path: Caminho do arquivo .md

        Returns:
            Número de chunks indexados
        """
        print(f"  📄 Indexando: {file_path.name}")

        # Lê conteúdo do arquivo
        content = file_path.read_text(encoding="utf-8")

        # Extrai título
        title = extract_title(content)

        # Divide em chunks
        chunks = chunk_text(content)
        print(f"     → {len(chunks)} chunks")

        # Prepara dados para inserção
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = generate_chunk_id(str(file_path), i)

            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append(
                {
                    "source": str(file_path),
                    "filename": file_path.name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "title": title,
                }
            )

        # Gera embeddings para todos os chunks de uma vez (mais eficiente)
        embeddings = self.embedding_manager.embed(documents).tolist()

        # Insere no ChromaDB (upsert = insert or update)
        self.collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

        return len(chunks)

    def index_directory(self, docs_path: Optional[Path] = None) -> Dict[str, int]:
        """
        Indexa todos os arquivos .md de um diretório.

        Args:
            docs_path: Caminho do diretório. Default: docs/context/

        Returns:
            Dict com estatísticas {arquivo: n_chunks}
        """
        if docs_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            docs_path = project_root / "docs" / "context"

        print(f"\n🔍 Indexando documentos de: {docs_path}\n")

        stats = {}
        total_chunks = 0

        # Lista todos os .md no diretório
        md_files = sorted(docs_path.glob("*.md"))

        for file_path in md_files:
            n_chunks = self.index_file(file_path)
            stats[file_path.name] = n_chunks
            total_chunks += n_chunks

        print(f"\n✅ Indexação completa!")
        print(f"   📁 Arquivos: {len(stats)}")
        print(f"   📄 Chunks totais: {total_chunks}")
        print(f"   💾 Banco em: {self.db_path}")

        return stats

    def clear(self) -> None:
        """
        Remove todos os documentos da collection.

        Útil para re-indexar do zero.
        """
        print("🗑️ Limpando collection...")
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Documentos de contexto do projeto scrapper"},
        )
        print("✅ Collection limpa!")


# Script executável diretamente
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Indexa documentos de contexto no ChromaDB"
    )
    parser.add_argument(
        "--clear", action="store_true", help="Limpa o banco antes de indexar"
    )
    parser.add_argument(
        "--path", type=str, help="Caminho alternativo para os documentos"
    )

    args = parser.parse_args()

    indexer = ContextIndexer()

    if args.clear:
        indexer.clear()

    docs_path = Path(args.path) if args.path else None
    indexer.index_directory(docs_path)
