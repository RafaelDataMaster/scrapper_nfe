# 🚀 Guia de Início de Sessão

> **Para o usuário:** Este documento explica como iniciar uma sessão de trabalho com o Claude de forma otimizada.

---

## Fluxo Rápido

### Opção 1: Comando Simples (Recomendado)

Inicie a sessão com:

```
Nova sessão - inicializa contexto
```

O Claude irá executar `python scripts/session_init.py` e estará pronto para trabalhar.

### Opção 2: Comando Direto

```
Roda: python scripts/session_init.py
```

---

## O Que Mudou?

### ❌ Antes (pesado)
```
Você: "Leia todos os arquivos em docs/context/"
Claude: [lê 29 arquivos, ~106 chunks, demora, ocupa contexto]
Você: "Corrige o extrator X"
Claude: [90% do contexto carregado é irrelevante]
```

### ✅ Agora (leve e rápido)
```
Você: "Nova sessão - inicializa contexto"
Claude: [roda session_init.py em 1 segundo, sem carregar modelo]
Você: "Corrige o extrator X"
Claude: [busca só contexto relevante: "extrator X problema"]
        [carrega 3 chunks específicos]
        [executa a correção]
```

---

## Comandos Disponíveis

| Comando | Descrição |
|---------|-----------|
| `python scripts/session_init.py` | Inicializa sessão (status do projeto) |
| `python scripts/ctx.py "termo"` | Busca semântica no contexto |
| `python scripts/ctx.py -i` | Modo interativo de busca |
| `python scripts/ctx.py --list` | Lista documentos indexados |
| `python scripts/ctx.py --reindex` | Re-indexa após modificar docs |

---

## Quando Re-indexar?

O Claude deve rodar `python scripts/ctx.py --reindex` quando:

- ✅ Você adicionar novo arquivo em `docs/context/`
- ✅ Você modificar conteúdo de arquivo existente
- ✅ O `session_init.py` indicar "Re-indexação recomendada"
- ❌ Não precisa para buscas normais

---

## Exemplos de Uso

### Exemplo 1: Corrigir um extrator

```
Você: "O extrator de boletos GOX está com problema"

Claude pensa: "Preciso de contexto sobre boletos GOX"
Claude roda:  python scripts/ctx.py "boleto GOX problema" -n 3
Claude lê:    Chunks relevantes de troubleshooting
Claude:       "Encontrei histórico de correções para BoletoGoxExtractor..."
```

### Exemplo 2: Criar novo extrator

```
Você: "Preciso criar extrator para faturas da Empresa X"

Claude pensa: "Preciso do template de criação"
Claude roda:  python scripts/ctx.py "criar novo extrator" -n 3
Claude lê:    creation.md, coding_standards.md
Claude:       "Vou seguir o padrão documentado..."
```

### Exemplo 3: Investigar erro

```
Você: "Está dando timeout em alguns PDFs"

Claude pensa: "Preciso de contexto sobre timeout e PDF"
Claude roda:  python scripts/ctx.py "timeout PDF" -n 3
Claude lê:    sessao_2026_02_05_timeout_tim.md
Claude:       "Encontrei uma sessão anterior que resolveu isso..."
```

---

## Tópicos Pré-indexados

O contexto vetorizado inclui informações sobre:

| Tópico | Documento |
|--------|-----------|
| Criar extrator | `creation.md` |
| Validar correção | `validation.md` |
| Diagnosticar problema | `diagnosis.md` |
| Troubleshooting geral | `troubleshooting.md` |
| Padrões de código | `coding_standards.md` |
| Comandos úteis | `commands_reference.md` |
| Overview do projeto | `project_overview.md` |
| Padrões de logging | `logging_standards.md` |
| PDFs protegidos | `pdf_password_handling.md` |
| Sessões anteriores | `sessao_*.md` |
| Análises de erros | `analise_*.md` |

---

## Estrutura do Sistema

```
scrapper/
├── data/
│   └── vector_db/           # Banco ChromaDB (persistente)
├── scripts/
│   ├── session_init.py      # ⭐ Inicialização de sessão
│   ├── ctx.py               # ⭐ Busca rápida no contexto
│   └── context_db/
│       ├── embeddings.py    # Modelo de embeddings
│       ├── indexer.py       # Indexador de documentos
│       └── query.py         # Interface de busca
└── docs/
    └── context/             # Documentos fonte (29 arquivos)
```

---

## Troubleshooting

### "Banco vetorial não encontrado"

```powershell
python scripts/ctx.py --reindex
```

### "Resultados não parecem relevantes"

1. Reformule a busca com termos diferentes
2. Use mais palavras-chave específicas
3. Re-indexe se os docs foram modificados recentemente

### Modelo demora para carregar

Normal na primeira busca da sessão (~2-3 segundos para carregar o modelo).
O `session_init.py` não carrega o modelo, então é instantâneo.

---

## Benefícios

| Métrica | Antes | Agora |
|---------|-------|-------|
| Tempo de inicialização | ~30s (ler 29 docs) | ~1s |
| Contexto carregado | 100% (~50KB) | Só o necessário (~2KB) |
| Precisão | Genérico | Específico por busca |
| Manutenção | Manual | Auto-indexado |
