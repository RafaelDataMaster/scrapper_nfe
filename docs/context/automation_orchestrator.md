# Orquestrador de Correções Automatizadas

> **Uso:** Executar correções em lote baseado na lista de priorização  
> **Modo:** Semi-automático (você aprova, eu executo e reporto)  
> **Status:** Mantém tracking de progresso em tempo real

---

## 🎯 Como Funciona

```
┌─────────────────────────────────────────────────────────────────┐
│  1. VOCÊ aprova a lista de correções prioritárias              │
│     (baseado em prioritization.md)                              │
├─────────────────────────────────────────────────────────────────┤
│  2. EU executo automaticamente para cada item:                 │
│     ┌───────────────────────────────────────────────────────┐  │
│     │ diagnosis.md → review.md → [creation/adjust] → validation│ │
│     └───────────────────────────────────────────────────────┘  │
│     A cada passo eu reporto: ✅ Sucesso / ⚠️ Bloqueio / ❌ Erro  │
├─────────────────────────────────────────────────────────────────┤
│  3. EU notifico quando cada caso termina:                      │
│     - Resultado da correção                                    │
│     - Casos afetados (reprocessados)                           │
│     - Validação de não-regressão                               │
│     - Próximo item na fila                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Iniciar Orquestração

### Input de Aprovação

```yaml
MODO_EXECUCAO: #[AUTOMATICO/SEMI_AUTOMATICO]
# AUTOMATICO: Eu executo tudo e reporto no final de cada caso
# SEMI_AUTOMATICO: Eu pauso para sua aprovação em decisões críticas

CORRECOES_APROVADAS:
  - id: 1
    tipo: QUICK_WIN
    descricao: "Ajustar can_handle NfseGeneric para não capturar DANFEs"
    arquivo: extractors/nfse_generic.py
    casos_afetados: 
      - email_20260129_084433_c5c04540  # FishTV
      - email_20260129_084433_ecf8dd6f  # FishTV
      - email_20260129_084433_eb070afb  # FishTV
    aprovado: true
    
  - id: 2
    tipo: QUICK_WIN
    descricao: "Melhorar extração de vencimento em boletos"
    arquivo: extractors/boleto.py
    casos_afetados: #[lista de batches com boleto]
    aprovado: true
    
  - id: 3
    tipo: NOVO_EXTRATOR
    descricao: "Criar UfinetExtractor"
    fornecedor: "Ufinet Brasil SA"
    cnpj: "XX.XXX.XXX/XXXX-XX"  # se conhecido
    casos_afetados:
      - email_20260129_084433_6f365b3e
      - email_20260129_084433_9f11fc01
      - email_20260129_084435_cd4ee4c7
    aprovado: true
    
  - id: 4
    tipo: AJUSTE
    descricao: "Verificar EnergyBillExtractor para CEMIG"
    arquivo: extractors/energy_bill.py
    casos_afetados:
      - email_20260129_084432_faddc3ac
      - email_20260129_084432_31552e05
      - email_20260129_084432_2ad483d5
      - email_20260129_084432_ec8f4ea2
    aprovado: true

CONFIGURACOES:
  backup_automatico: true
  validar_regressao: true
  reprocessar_batches: true
  notificar_a_cada: #[CADA_CORRECAO/CADA_PASSO/APENAS_ERROS]
  max_tentativas_por_caso: 3
  stop_on_error: false  # Se true, para tudo se um caso falhar
```

---

## 🔄 Fluxo de Trabalho da Orquestração

### Passo 0: Verificar Status Anterior ⭐ OBRIGATÓRIO

```markdown
ANTES de iniciar qualquer orquestração:

1. Leia o `project_overview.md` na seção "## 📊 Status Atual do Projeto"
2. Verifique se há snapshots de sessões anteriores
3. IMPORTANTE: Entenda que batch IDs são voláteis!
   - IDs como "email_20260129_084433_c5c04540" mudam a cada clean_dev + run_ingestion
   - NUNCA use batch IDs de sessões anteriores para validação
   - Use fornecedor, tipo, padrões de detecção (estáveis)
   - Veja: correction_tracking.md para detalhes

4. Identifique:
   - Correção que estava em andamento
   - Pendências registradas
   - Estado dos dados (CSVs, batches)
   - Decisões tomadas anteriormente

5. Apresente ao usuário:
   "Encontrei snapshot da sessão anterior (29/01 09:30):
    - Correção #1 CONCLUÍDA (TunnaFatura)
    - Correção #2 PENDENTE (Vencimento Boletos)
    
    ⚠️ Batch IDs da sessão anterior são obsoletos (clean_dev foi rodado).
    Para validar correção #1, buscarei por:
    - Fornecedor: TUNNA ENTRETENIMENTO
    - Tipo: FATURA COMERCIAL
    
    Deseja continuar de onde parou ou reiniciar?"

6. Use os comandos úteis listados no snapshot para validar estado atual
   - SEMPRE priorize busca por fornecedor/tipo em vez de batch ID
```

---

## 📋 Template de Execução

### Correção #{ID}: {Descrição}

#### ▶️ INÍCIO - {Timestamp}

**Status:** 🟡 EM ANDAMENTO

```
Correção: {descricao}
Tipo: {QUICK_WIN/NOVO_EXTRATOR/AJUSTE}
Arquivo: {caminho}
Casos afetados: {N} batches
```

---

#### PASSO 1: Diagnóstico

```bash
# Executando análise dos casos...
python scripts/inspect_pdf.py --batch {batch_id}
```

**Resultado:**
- ✅ Diagnóstico concluído
- Problema identificado: {causa_raiz}
- Solução recomendada: {solucao}

---

#### PASSO 2: Backup

```bash
# Criando backup...
cp {arquivo} {arquivo}.bak.{timestamp}
cp data/output/relatorio_lotes.csv data/output/relatorio_lotes.csv.bak.{timestamp}
```

**Resultado:** ✅ Backup criado em {caminho}

---

#### PASSO 3: Implementação

**Tipo:** {QUICK_WIN/NOVO_EXTRATOR/AJUSTE}

```python
# Código modificado/criado:
{snippet_do_codigo}
```

**Arquivos modificados:**
- ✅ {arquivo1}
- ✅ {arquivo2} (se aplicável)

---

#### PASSO 4: Validação Unitária

```bash
# Testando caso específico...
python scripts/inspect_pdf.py {pdf_de_teste}
```

**Resultados:**

| Campo | Antes | Depois | Status |
|-------|-------|--------|--------|
| Tipo | {NFSE} | {DANFE} | ✅ |
| Valor | {R$ 0,00} | {R$ 700,00} | ✅ |
| Número | {vazio} | {521912} | ✅ |

---

#### PASSO 5: Teste de Regressão

```bash
# Validando que não quebrou outros casos...
python scripts/validate_extraction_rules.py --batch-mode
```

**Resultado:** ✅ {N} casos testados, {0} regressões

---

#### PASSO 6: Reprocessamento

```bash
# Reprocessando batches afetados...
python run_ingestion.py --batch-folder {batch_id}
```

**Lotes reprocessados:**
- ✅ {batch_id_1}
- ✅ {batch_id_2}
- ✅ {batch_id_3}

---

#### PASSO 7: Validação Final CSV

```bash
# Verificando CSV de saída...
Select-String {batch_id} data/output/relatorio_lotes.csv
```

**Comparação:**

| Batch | Status Antes | Status Depois | Melhoria |
|-------|--------------|---------------|----------|
| {id1} | {CONFERIR} | {CONCILIADO} | ✅ |
| {id2} | {CONFERIR} | {CONCILIADO} | ✅ |

---

#### PASSO 8: Verificação de Código ⭐ OBRIGATÓRIO

```bash
# Verificar padrões de código
basedpyright extractors/[arquivo_modificado].py
```

**Checklist:**
- [ ] Type hints em todos os métodos públicos
- [ ] Sem imports não usados (`reportUnusedImport`)
- [ ] Sem variáveis não usadas (`reportUnusedVariable`)
- [ ] Docstrings completas
- [ ] Segue princípios SOLID (veja [`coding_standards.md`](./coding_standards.md))
- [ ] DRY aplicado corretamente (regras de negócio em `utils.py`)

Se houver erros, corrija antes de prosseguir.

---

#### PASSO 9: Snapshot de Status ⭐ OBRIGATÓRIO

```markdown
# Registrar snapshot no project_overview.md
```

**Ações:**
- [ ] Atualizar seção `## 📊 Status Atual do Projeto` em `project_overview.md`
- [ ] Adicionar novo snapshot (remover o mais antigo se houver 3+)
- [ ] Incluir: data/hora, tipo de parada, estado das correções, pendências
- [ ] Atualizar lista de arquivos modificados
- [ ] Registrar decisões importantes para memória futura
- [ ] Incluir aviso sobre batch IDs voláteis (use fornecedor/tipo)

**Template usado:** `project_status_template.md`

---

#### ✅ FIM - {Timestamp}

**Status:** ✅ CONCLUÍDO COM SUCESSO

```
Resumo da Correção #{ID}:
- Tempo total: {X minutos}
- Casos corrigidos: {N}
- Valor recuperado: {R$ X.XXX,XX}
- Regressões: {0}
- Próximo: Correção #{ID+1}
```

---

## 📊 Dashboard de Progresso

### Correções em Andamento

| ID | Correção | Status | Progresso | Tempo Est. | Tempo Real |
|----|----------|--------|-----------|------------|------------|
| 1 | Ajuste DANFE/NFSE | ✅ Concluído | 100% | 30 min | 25 min |
| 2 | Venc. Boleto | 🟡 Em andamento | 60% | 1 h | 45 min |
| 3 | UfinetExtractor | ⚪ Pendente | 0% | 4 h | - |
| 4 | EnergyBill CEMIG | ⚪ Pendente | 0% | 2 h | - |

### Métricas Acumuladas

```
Correções Concluídas: 1/4
Tempo Total Gasto: 25 minutos
Casos Corrigidos: 3
Valor Total Recuperado: R$ 2.100,00
Taxa de Sucesso: 100%
Regressões: 0
```

---

## 🔔 Notificações

### Modo: Notificar a Cada Correção

```
═══════════════════════════════════════════════════════
✅ CORREÇÃO #{ID} CONCLUÍDA
═══════════════════════════════════════════════════════

Correção: Ajustar can_handle NfseGeneric

Resultado:
  • 3 casos do FishTV corrigidos
  • Valor recuperado: R$ 2.100,00
  • Nenhuma regressão detectada

Próximo: Correção #2 - Vencimento em Boletos
         (Iniciando em 5 segundos...)

[Ctrl+C para pausar ou responder para interagir]
═══════════════════════════════════════════════════════
```

### Modo: Notificar Apenas Erros

```
═══════════════════════════════════════════════════════
❌ ERRO NA CORREÇÃO #{ID}
═══════════════════════════════════════════════════════

Correção: Criar UfinetExtractor

Erro: Regressão detectada em 2 casos do extrator genérico

Ação necessária:
  [1] Ver casos afetados e decidir
  [2] Ignorar e continuar
  [3] Parar orquestração

Detalhes:
  Casos com regressão:
    - batch_XXXXX: valor alterado de R$ 500 para R$ 0
    - batch_YYYYY: tipo alterado de NFSE para OUTRO
═══════════════════════════════════════════════════════
```

### Modo: Relatório Final

```
═══════════════════════════════════════════════════════
🎉 ORQUESTRAÇÃO CONCLUÍDA
═══════════════════════════════════════════════════════

Resumo Geral:
  Correções planejadas: 4
  Concluídas com sucesso: 3
  Falhas: 1 (UfinetExtractor - requer análise)
  Canceladas: 0

Impacto:
  Casos corrigidos: 15
  Valor recuperado: R$ 8.500,00
  Tempo economizado (vs manual): ~5 horas

Detalhes por Correção:
  ✅ #1 DANFE/NFSE: 3 casos, 25 min
  ✅ #2 Venc. Boleto: 8 casos, 45 min
  ❌ #3 UfinetExtractor: Falhou na validação
  ✅ #4 EnergyBill: 4 casos, 1h 30min

Próximos Passos:
  • Caso #3 requer análise manual
  • Revisar exportação para Sheets
  • Commit das alterações

Arquivos Modificados:
  - extractors/nfse_generic.py
  - extractors/boleto.py
  - extractors/energy_bill.py
  - extractors/ufinet.py (criado mas não validado)

Backups Disponíveis:
  - *.bak.20260129_104500
═══════════════════════════════════════════════════════
```

---

## 🛡️ Safeguards (Proteções)

### Checkpoints Automáticos

A orquestração para automaticamente se:

1. **Regressão crítica detectada**
   - >5 casos existentes quebrados
   - Alteração de tipo (NFSE→OUTRO) em casos que funcionavam
   - Valores zerados em casos que tinham valor

2. **Erro de sintaxe no código**
   - ImportError ao carregar extrator
   - SyntaxError no Python
   - Falha nos testes unitários

3. **Timeout**
   - Correção demora mais que 3x o tempo estimado
   - Possível loop infinito ou bloqueio

4. **Conflito de merge**
   - Arquivos modificados externamente durante execução
   - Hash dos arquivos mudou

### Ações em Caso de Problema

```yaml
Se_regressao_detectada:
  automatico: Restaurar backup imediato
  notificacao: "⚠️ Regressão detectada - Backup restaurado"
  proximo: "Aguardando decisão para continuar"
  
Se_erro_sintaxe:
  automatico: Restaurar backup + log do erro
  notificacao: "❌ Erro de sintaxe - Correção abortada"
  proximo: "Próxima correção na fila"
  
Se_timeout:
  automatico: Interromper processo + salvar estado
  notificacao: "⏱️ Timeout - Correção pausada"
  proximo: "Aguardando intervenção manual"
```

---

## 📝 Log de Execução

Arquivo gerado automaticamente: `docs/context/automation_log_{timestamp}.md`

```markdown
# Log de Orquestração - 2026-01-29 10:45:00

## Correção #1: Ajuste DANFE/NFSE
- [10:45:00] Início
- [10:45:05] Diagnóstico concluído - Problema: regex can_handle
- [10:45:10] Backup criado
- [10:45:15] Código modificado
- [10:45:30] Validação unitária - 3 casos OK
- [10:45:45] Regressão testada - 0 problemas
- [10:46:00] Reprocessamento concluído
- [10:46:10] Validação CSV - OK
- [10:46:10] ✅ CONCLUÍDO (1m 10s)

## Correção #2: Vencimento em Boletos
- [10:46:15] Início
- [10:46:20] Diagnóstico concluído
- [10:46:25] Backup criado
- [10:46:30] ⚠️ PAUSA - Decisão necessária
  Usar decode_linha_digitavel OU parse do texto?
  Usuário escolheu: decode_linha_digitavel
- [10:47:00] Código modificado
...
```

---

## 💬 Interação Durante Execução

### Perguntas que posso fazer durante:

1. **Decisões de implementação:**
   ```
   Correção #3 requer decisão:
   
   Opção A: Criar extrator específico (4 horas, cobertura total)
   Opção B: Ajustar genérico (30 min, pode não cobrir todos os casos)
   
   Qual prefere? [A/B]
   ```

2. **Confirmação em caso de alerta:**
   ```
   ⚠️ Alerta: Correção vai afetar 15 casos do extrator genérico
   
   Deseja:
   [1] Ver lista dos 15 casos afetados
   [2] Prosseguir mesmo assim
   [3] Pular esta correção
   ```

3. **Solicitação de informação:**
   ```
   ❓ Informação necessária:
   
   Criar extrator para Ufinet - CNPJ não encontrado automaticamente.
   
   Por favor forneça o CNPJ (ou digite "pular" para ignorar)
   ```

---

## 🎬 Comandos de Controle

Durante a orquestração, você pode:

```bash
# Pausar
"Pausar" ou "Pause"

# Pular correção atual
"Pular #{id}" ou "Skip"

# Ver status
"Status" ou "Progresso"

# Cancelar tudo
"Parar" ou "Cancelar"

# Ver detalhes de uma correção
"Ver #{id}"

# Aprovar e continuar (em modo semi-automático)
"Continuar" ou "Aprovar"
```

---

## 📦 Entregáveis Finais

Ao final da orquestração, você recebe:

1. **Relatório completo** (`automation_log_{timestamp}.md`)
2. **Lista de arquivos modificados** com diff
3. **CSV comparativo** (antes/depois)
4. **Métricas de impacto** (casos corrigidos, valor recuperado)
5. **Recomendações** para próximas rodadas

---

## Exemplo de Uso

**Você diz:**
```
Execute as correções aprovadas:
1. Ajuste DANFE/NFSE
2. Vencimento boleto
3. UfinetExtractor

Modo: SEMI_AUTOMATICO
Notificar: A_CADA_CORRECAO
```

**Eu respondo:**
```
🚀 ORQUESTRAÇÃO INICIADA
═══════════════════════════════════════════════════════
Correções na fila: 3
Modo: SEMI_AUTOMATICO
Notificações: A cada correção
═══════════════════════════════════════════════════════

▶️ CORREÇÃO #1: Ajuste DANFE/NFSE
Status: 🟡 EM ANDAMENTO

[10:45:00] Passo 1/7: Diagnóstico... 
[10:45:05] ✅ Diagnóstico concluído
           Problema: can_handle aceitando DANFEs
           
[10:45:05] Passo 2/7: Backup...
[10:45:10] ✅ Backup criado

[10:45:10] Passo 3/7: Implementação...
⚠️ DECISÃO NECESSÁRIA:
   
   Opção A: Adicionar "DANFE" como padrão negativo no can_handle
   Opção B: Verificar se tem chave de acesso (44 dígitos) antes de aceitar
   
   Qual prefere? [A/B]
```

**Você responde:** "B"

**Eu continuo:**
```
[10:45:30] ✅ Implementado: Verificação de chave de acesso
[10:45:30] Passo 4/7: Validação unitária...
[10:45:45] ✅ 3 casos do FishTV validados

... (continua até o fim)

═══════════════════════════════════════════════════════
✅ CORREÇÃO #1 CONCLUÍDA
═══════════════════════════════════════════════════════
Tempo: 5 minutos
Casos corrigidos: 3
Valor recuperado: R$ 2.100,00

Próxima: Correção #2 - Vencimento em Boletos
Iniciando em 3 segundos...
═══════════════════════════════════════════════════════
```

---

**Quer que eu inicie uma orquestração com as correções identificadas no exemplo de priorização?**