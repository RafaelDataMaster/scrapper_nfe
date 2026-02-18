# Guia do Banco de Dados Vetorial (Vector DB)

> **Objetivo:** Facilitar a busca semântica nos documentos de contexto do projeto.

---

## 📋 Visão Geral

O sistema utiliza **ChromaDB** + **sentence-transformers** para criar uma base de dados vetorizada dos documentos em `docs/context/`. Isso permite buscar informação por **significado semântico**, não apenas por palavras exatas.

### Como funciona?

```
DOCUMENTO DE TEXTO                    VETOR (EMBEDDING)
─────────────────                    ─────────────────
"Como resolver PDF protegido"   →    [0.12, -0.45, 0.78, ..., 0.33]  (384 dimensões)
"Extrator de boletos GOX"       →    [-0.21, 0.56, 0.11, ..., 0.89]

BUSCA SEMÂNTICA:
1. Usuário pergunta: "PDF com senha não abre"
2. Pergunta vira vetor: [0.15, -0.42, 0.80, ..., 0.31]
3. ChromaDB calcula distância entre vetores
4. Retorna os documentos mais "próximos" semanticamente
```

**Por que funciona?** O modelo `all-MiniLM-L6-v2` foi treinado em milhões de textos e aprendeu que "PDF protegido" e "PDF com senha" têm significados similares, mesmo sendo palavras diferentes.

---

## 🚀 Uso Rápido

### Buscar informação

```powershell
# Busca simples
python scripts/ctx.py "PDF protegido"

# Limitar número de resultados
python scripts/ctx.py "timeout" -n 3

# Modo interativo
python scripts/ctx.py -i

# Listar documentos indexados
python scripts/ctx.py --list
```

### Re-indexar documentos

Rode quando adicionar/modificar arquivos em `docs/context/`:

```powershell
# Re-indexar tudo
python scripts/ctx.py --reindex

# Ou diretamente
python scripts/context_db/indexer.py --clear
```

---

## 📁 Estrutura do Módulo

```
scrapper/
├── data/
│   └── vector_db/              # ChromaDB persiste aqui
│       ├── chroma.sqlite3      # Banco de dados
│       └── ...                 # Arquivos de índice
├── scripts/
│   ├── ctx.py                  # ⭐ Script de conveniência (atalho)
│   └── context_db/
│       ├── __init__.py         # Módulo Python
│       ├── embeddings.py       # Gerenciador de embeddings
│       ├── indexer.py          # Indexa docs/context/*.md
│       └── query.py            # Busca semântica
```

---

## 🔧 Componentes

### 1. EmbeddingManager (`embeddings.py`)

Transforma texto em vetores numéricos usando o modelo `all-MiniLM-L6-v2`.

| Propriedade | Valor |
|-------------|-------|
| Modelo | `all-MiniLM-L6-v2` |
| Tamanho | ~80MB (baixado na 1ª execução) |
| Dimensões | 384 números por texto |
| Cache | `~/.cache/huggingface/` |

```python
from scripts.context_db.embeddings import EmbeddingManager

em = EmbeddingManager()
vetor = em.embed("Como resolver PDF protegido?")
print(len(vetor))  # 384
```

### 2. ContextIndexer (`indexer.py`)

Lê arquivos `.md`, divide em **chunks** (pedaços de ~500 palavras) e armazena no ChromaDB.

**Por que dividir em chunks?**
- Documentos grandes são difíceis de buscar com precisão
- Chunks menores permitem encontrar trechos específicos
- Overlap de 50 palavras evita que informação seja cortada

```python
from scripts.context_db.indexer import ContextIndexer

indexer = ContextIndexer()
indexer.index_directory()  # Indexa docs/context/
```

### 3. ContextQuery (`query.py`)

Interface de busca semântica.

```python
from scripts.context_db.query import ContextQuery

cq = ContextQuery()

# Busca simples
results = cq.search("PDF protegido", top_k=5)
for r in results:
    print(f"{r.title} - {r.source}")

# Busca formatada
print(cq.search_formatted("timeout", top_k=3))

# Recuperar documento completo
doc = cq.get_full_document("troubleshooting.md")
```

---

## 📊 Interpretando Resultados

```
#1 📄 Tratamento de PDFs Protegidos por Senha
   Fonte: pdf_password_handling.md
   Relevância: 55.41%
   Chunk: 0
   ─────────────────────────────────────
   # Tratamento de PDFs Protegidos por Senha...
```

| Campo | Significado |
|-------|-------------|
| **Título** | Extraído do primeiro `# heading` do documento |
| **Fonte** | Nome do arquivo de origem |
| **Relevância** | `1 / (1 + distância)` — maior = mais relevante |
| **Chunk** | Índice do pedaço no documento (0 = início) |

---

## 🔄 Quando Re-indexar?

Execute `python scripts/ctx.py --reindex` quando:

- ✅ Adicionar novo arquivo em `docs/context/`
- ✅ Modificar conteúdo de arquivo existente
- ✅ Remover arquivos
- ❌ Não precisa re-indexar para buscas normais

---

## 🛠️ Troubleshooting

### Erro: "Banco vetorial não encontrado"

O banco ainda não foi criado. Execute:

```powershell
python scripts/context_db/indexer.py
```

### Modelo demora para carregar

Normal na primeira execução (~80MB download). Depois fica em cache.

### Warning sobre symlinks no Windows

Pode ignorar — é apenas um aviso sobre otimização de cache:

```
UserWarning: `huggingface_hub` cache-system uses symlinks...
```

### Resultados não parecem relevantes

1. Tente reformular a busca
2. Use termos mais específicos
3. Re-indexe se os docs foram modificados: `python scripts/ctx.py --reindex`

---

## 📦 Dependências

```txt
chromadb
sentence-transformers
```

Instaladas via:

```powershell
pip install chromadb sentence-transformers
```

> **Nota:** `sentence-transformers` instala PyTorch automaticamente (~2GB).

---

## 🔮 Uso com Claude/AI

Para carregar contexto relevante antes de uma tarefa:

```powershell
# Buscar contexto sobre um tema
python scripts/ctx.py "como criar novo extrator" -n 3

# Copiar saída e colar no prompt do Claude
```

Ou no modo interativo:

```
🔍 > como resolver timeout
🔍 > doc troubleshooting.md
🔍 > sair
```
