# 🚀 START HERE - Guia para o Claude

> **Este arquivo é para o Claude (AI).** Leia-o no início de cada sessão.

---

## Inicialização Rápida

Execute este comando para iniciar a sessão:

```bash
python scripts/session_init.py
```

Isso mostra:
- Status do banco vetorial (contexto indexado)
- Resumo do projeto (extratores, batches, logs)
- Comandos disponíveis

---

## Busca de Contexto

Este projeto usa **ChromaDB + sentence-transformers** para busca semântica nos documentos de contexto. Em vez de ler todos os 30 arquivos de `docs/context/`, busque apenas o que precisa:

```bash
# Buscar informação específica
python scripts/ctx.py "termo de busca" -n 3

# Exemplos:
python scripts/ctx.py "PDF protegido"
python scripts/ctx.py "criar novo extrator"
python scripts/ctx.py "timeout"
python scripts/ctx.py "boleto GOX problema"
```

### Comandos úteis:

| Comando | Descrição |
|---------|-----------|
| `python scripts/ctx.py "termo"` | Busca semântica |
| `python scripts/ctx.py -i` | Modo interativo |
| `python scripts/ctx.py --list` | Lista docs indexados |
| `python scripts/ctx.py --reindex` | Re-indexa após modificar docs |

---

## Fluxo de Trabalho

1. **Usuário pede algo** → "corrige o extrator X"
2. **Você busca contexto** → `python scripts/ctx.py "extrator X problema"`
3. **Você lê os chunks relevantes** → resultado da busca
4. **Você executa a tarefa** → com conhecimento do histórico

---

## Sobre o Projeto

**scrapper** - Pipeline ETL para extração de documentos fiscais

- Ingere e-mails com PDFs anexos
- Extrai dados (NF, Boletos, DANFE) usando extratores especializados
- Exporta para CSV/Google Sheets

### Estrutura principal:

```
scrapper/
├── extractors/          # ~28 extratores especializados
├── core/                # Processador principal
├── strategies/          # Estratégias de extração (PDF, OCR)
├── scripts/             # Scripts utilitários
│   ├── session_init.py  # ⭐ Inicialização de sessão
│   ├── ctx.py           # ⭐ Busca no contexto
│   └── context_db/      # Módulo de vetorização
├── docs/context/        # 30 docs de contexto (indexados)
├── data/vector_db/      # Banco ChromaDB (persistente)
└── temp_email/          # Batches de e-mails para processar
```

---

## Quando Re-indexar

Execute `python scripts/ctx.py --reindex` se:

- Adicionar/modificar arquivo em `docs/context/`
- `session_init.py` indicar "Re-indexação recomendada"

---

## Documentação Detalhada

Se precisar de mais detalhes, consulte:

- `docs/context/vector_db_guide.md` — Guia técnico do banco vetorial
- `docs/context/SESSION_START.md` — Guia completo de sessão
- `docs/context/project_overview.md` — Overview completo do sistema
- `docs/context/commands_reference.md` — Referência de comandos

---

## TL;DR

```bash
# 1. Inicializa sessão
python scripts/session_init.py

# 2. Busca contexto quando precisar
python scripts/ctx.py "termo relevante"

# 3. Executa a tarefa do usuário
```
