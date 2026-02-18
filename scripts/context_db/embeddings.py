"""
Gerenciador de Embeddings usando sentence-transformers.

CONCEITO:
=========
Embedding = transformar texto em um vetor numérico de tamanho fixo.
Textos semanticamente similares terão vetores "próximos" no espaço.

MODELO USADO:
=============
all-MiniLM-L6-v2
- Tamanho: ~80MB (baixa na primeira execução)
- Dimensões: 384 (cada texto vira um vetor de 384 números)
- Velocidade: Muito rápido, funciona bem em CPU
- Qualidade: Boa para textos em inglês/português técnico

COMO FUNCIONA:
==============
1. O modelo foi pré-treinado em milhões de pares de texto
2. Ele aprendeu que "PDF protegido" e "arquivo com senha" são similares
3. Quando você passa um texto, ele retorna um vetor que "representa" o significado
"""

from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np


class EmbeddingManager:
    """
    Gerencia a criação de embeddings para textos.

    Attributes:
        model: Modelo sentence-transformers carregado
        model_name: Nome do modelo usado
        embedding_dim: Dimensão dos vetores gerados (384 para MiniLM)

    Example:
        >>> em = EmbeddingManager()
        >>> vetor = em.embed("Como resolver PDF protegido?")
        >>> print(len(vetor))  # 384
    """

    # Modelo leve e eficiente - bom equilíbrio qualidade/velocidade
    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        Inicializa o gerenciador de embeddings.

        Args:
            model_name: Nome do modelo do HuggingFace a usar.
                       Default: all-MiniLM-L6-v2 (recomendado)

        Note:
            Na primeira execução, o modelo será baixado (~80MB).
            Depois fica em cache local.
        """
        self.model_name = model_name
        print(f"🔄 Carregando modelo de embeddings: {model_name}...")

        # SentenceTransformer carrega o modelo do HuggingFace
        # O modelo fica em cache em ~/.cache/huggingface/
        self.model = SentenceTransformer(model_name)

        # Dimensão do vetor de saída (384 para MiniLM)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"✅ Modelo carregado! Dimensão dos embeddings: {self.embedding_dim}")

    def embed(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Gera embedding(s) para texto(s).

        Args:
            text: String única ou lista de strings

        Returns:
            np.ndarray: Vetor(es) de embedding
                - Para string única: shape (embedding_dim,)
                - Para lista: shape (n_textos, embedding_dim)

        Example:
            >>> em = EmbeddingManager()
            >>> v1 = em.embed("PDF protegido")
            >>> v2 = em.embed("arquivo com senha")
            >>> # v1 e v2 serão vetores "próximos" no espaço
        """
        # O modelo processa o texto e retorna o vetor
        # convert_to_numpy=True garante que retorna np.ndarray
        return self.model.encode(text, convert_to_numpy=True)
