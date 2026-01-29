# Template: Project Status Snapshot

> **Uso:** Copie este template para o `project_overview.md` na seção `## 📊 Status Atual do Projeto` a cada pausa/parada de correção.
> 
> **Quando registrar:** Sempre que pausar uma orquestração, completar uma correção, ou fazer alterações significativas no sistema.

---

## Formato do Snapshot

```markdown
### Snapshot: [DATA] - [HH:MM] - [TIPO_DE_PARADA]

**Tipo:** PAUSA_CORRECAO | CORRECAO_CONCLUIDA | ORQUESTRACAO_PAUSADA | MANUTENCAO

**Contexto da Sessão:**
- Orquestração iniciada em: [data_hora_inicio]
- Correção em andamento: #[número] - [nome_curto]
- Tempo decorrido: [X minutos/horas]

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | CSV Atualizado | Validado |
|---|------|--------|---------------------|----------------|----------|
| 1 | Nome da Correção | ✅ CONCLUÍDA | extractor_x.py, __init__.py | Sim (DD/MM) | 3 batches |
| 2 | Próxima Correção | ⏸️ PAUSADA | - | - | - |
| 3 | Outra Correção | ⏳ PENDENTE | - | - | - |

**Estado do Sistema:**
- **Último commit (se aplicável):** [hash ou descrição]
- **Extractors no Registry:** [número] total ([lista dos novos/modificados])
- **Ordem do Registry:** [alterada? Descreva]
- **Validate Script:** [versão/data da última modificação]

**Estado dos Dados:**
- **relatorio_lotes.csv:** [última linha/modificação relevante]
- **relatorio_consolidado.csv:** [último fornecedor adicionado/atualizado]
- **⚠️ Batches processados:** [lista dos batches - APENAS referência temporal!]
  > NOTA: Batch IDs são voláteis (mudam a cada clean_dev + run_ingestion).
  > Para reencontrar, use: fornecedor, tipo, número do documento
- **Failed cases:** [há novos casos? Quantos?]

**Pendências Identificadas:**
1. [Descreva o que falta fazer na correção atual]
2. [Próximos passos claros]
3. [Bloqueios ou dependências]

**Decisões Tomadas (para memória):**
- [Registre decisões arquiteturais importantes]
- [Ex: "Decidimos usar OUTRO ao invés de FATURA porque..."]
- [Ex: "Mudamos a ordem do registry porque..."]

**Comandos Úteis para Retomada:**
```bash
# Verificar estado dos batches
python scripts/validate_extraction_rules.py --batch-mode --temp-email --batches [batch1,batch2]

# Ver últimas entradas do CSV
Get-Content data/output/relatorio_lotes.csv | Select-Object -Last 10

# Verificar logs recentes
Select-String "[PALAVRA_CHAVE]" logs/scrapper.log | Select-Object -Last 20
```

**Arquivos em Modificação (não commitados):**
- [ ] arquivo.py (contém: descrição rápida)
- [ ] outro_arquivo.json (contém: descrição rápida)

**Anotações Rápidas:**
- [Qualquer informação relevante para a próxima sessão]
- [Erros que apareceram e foram resolvidos]
- [Insights ou descobertas]
```

---

## Exemplo Real (Preenchido)

```markdown
### Snapshot: 29/01/2026 - 09:30 - PAUSA_CORRECAO

**Tipo:** PAUSA_CORRECAO

**Contexto da Sessão:**
- Orquestração iniciada em: 29/01/2026 08:44
- Correção em andamento: #1 - TunnaFaturaExtractor
- Tempo decorrido: ~46 minutos

**Estado das Correções:**
| # | Nome | Status | Arquivos Modificados | CSV Atualizado | Validado |
|---|------|--------|---------------------|----------------|----------|
| 1 | TunnaFaturaExtractor | ✅ CONCLUÍDA | tunna_fatura.py, __init__.py | Sim (29/01) | 3 batches FishTV |
| 2 | Vencimento em Boletos | ⏳ PENDENTE | - | - | Quick Win |
| 3 | (próximas do JSON) | ⏳ PENDENTE | - | - | Aguardando |

**Estado do Sistema:**
- **Último commit:** Não commitado (arquivos modificados localmente)
- **Extractors no Registry:** 15 total (1 novo: TunnaFaturaExtractor)
- **Ordem do Registry:** ✅ ATUALIZADA - DanfeExtractor movido antes de NfseGenericExtractor
- **Validate Script:** ✅ ATUALIZADO - Adicionado --temp-email e --batches

**Estado dos Dados:**
- **relatorio_lotes.csv:** Últimas entradas FishTV: 000.010.731, 000.010.732, 000.010.733
- **relatorio_consolidado.csv:** Novo fornecedor: TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA
- **⚠️ Batches processados:** email_20260129_084433_c5c04540, email_20260129_084433_ecf8dd6f, email_20260129_084433_2b2e3712
  > NOTA: Estes IDs são obsoletos após clean_dev. Use fornecedor "TUNNA" para reencontrar.
- **Failed cases:** 0 novos (zero regressões confirmado)

**Pendências Identificadas:**
1. Aguardar comando "CONTINUAR correção #2" para iniciar Vencimento em Boletos
2. Verificar se há mais batches FishTV pendentes (caso apareçam)
3. Commitar mudanças quando solicitado pelo usuário

**Decisões Tomadas:**
- FishTV são FATURAS COMERCIAIS (não fiscais) → usar tipo="OUTRO", subtipo="FATURA"
- OCR corrompe "Nº" para "N�" → usar regex tolerante `N[�º]?`
- Reordenar registry é preferível a regex complexo para DANFE vs NFSe

**Comandos Úteis para Retomada:**
```bash
# Validar FishTV específicos
python scripts/validate_extraction_rules.py --batch-mode --temp-email --batches email_20260129_084433_c5c04540,email_20260129_084433_ecf8dd6f,email_20260129_084433_2b2e3712

# Ver últimos FishTV no CSV
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA" | Select-Object -Last 5

# Verificar se há novos batches FishTV
Get-ChildItem temp_email/ | Select-String "email_"
```

**Arquivos em Modificação:**
- [x] extractors/tunna_fatura.py (novo extrator)
- [x] extractors/__init__.py (ordem do registry)
- [x] scripts/validate_extraction_rules.py (novas flags)
- [x] docs/context/* (documentação atualizada)

**Anotações Rápidas:**
- Documentação Windows criada (commands_reference.md, troubleshooting.md)
- Próxima sessão: usar "CONTINUAR correção #2" ou "RETOMAR orquestração"
- Nenhum erro crítico pendente
```

---

## Checklist de Preenchimento

Antes de fechar uma sessão, verifique:

- [ ] Data e hora preenchidas
- [ ] Tipo de parada identificado
- [ ] Correção em andamento claramente indicada
- [ ] Arquivos modificados listados
- [ ] Estado dos CSVs documentado
- [ ] Pendências descritas
- [ ] Decisões importantes registradas
- [ ] Comandos úteis para retomada incluídos

---

## Onde Inserir no project_overview.md

Inserir na seção `## 📊 Status Atual do Projeto`, mantendo apenas os **últimos 3 snapshots** para não poluir:

```markdown
## 📊 Status Atual do Projeto

> Snapshots das últimas sessões (máx 3). Ver histórico completo no git log.

### Snapshot: [MAIS RECENTE] - [DATA] - [TIPO]
...

### Snapshot: [ANTERIOR] - [DATA] - [TIPO]
...

### Snapshot: [MAIS ANTIGO] - [DATA] - [TIPO]
...

---
[Histórico antigo removido - ver versões anteriores do arquivo no git]
```
