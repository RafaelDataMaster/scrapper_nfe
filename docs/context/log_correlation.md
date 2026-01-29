# Prompt: Análise de Logs Correlacionados com CSV

> **Uso:** Execute este prompt quando precisar investigar erros de processamento que aparecem nos logs e seus impactos nos CSVs de saída
>
> **Ferramentas:** `scripts/analyze_logs.py`, `grep`, análise de `logs/scrapper.log`

---

## Input para Análise

```yaml
# Período de análise
DATA_INICIO: #[YYYY-MM-DD]
DATA_FIM: #[YYYY-MM-DD ou "hoje"]

# Foco da análise (escolha um ou mais)
FOCO:
  - [ ] Erros críticos que impediram processamento
  - [ ] Warnings de qualidade de extração
  - [ ] Lotes lentos (>20s)
  - [ ] PDFs protegidos por senha
  - [ ] Falhas de correlação NF↔Boleto
  - [ ] Erros de exportação para Sheets
  - [ ] Documentos sem extrator compatível

# Filtros opcionais
BATCH_ID_ESPECIFICO: #[ex: email_20260129_084433_5fafb989 ou "" para todos]
FORNECEDOR_ESPECIFICO: #[ex: "TCF Telecom" ou ""]
EMPRESA_ESPECIFICA: #[ex: "CARRIER" ou ""]
```

---

## Scripts de Coleta (execute antes)

```bash
# 1. Análise completa de logs
python scripts/analyze_logs.py --output docs/context/temp_log_analysis.md

# 2. Apenas erros do período
python scripts/analyze_logs.py --errors-only > docs/context/temp_errors.txt

# 3. Resumo estatístico
python scripts/analyze_logs.py --summary

# 4. Lote específico (se aplicável)
python scripts/analyze_logs.py --batch <BATCH_ID_ESPECIFICO>

# 5. Logs de hoje apenas
python scripts/analyze_logs.py --today

# 6. Buscar no arquivo de log diretamente
grep -i "<termo>" logs/scrapper.log | tail -n 50
```

---

## Template de Resposta Esperada

### 1. RESUMO EXECUTIVO

```
Período Analisado: #[YYYY-MM-DD] até #[YYYY-MM-DD]
Total de Entradas de Log: #[N]
Erros: #[N] | Warnings: #[N] | Info: #[N]

Problemas Críticos Encontrados:
- PDFs protegidos por senha: #[N]
- PDFs com erro de abertura: #[N]  
- Lotes lentos (>20s): #[N]
- Documentos sem extrator: #[N]
- Falhas de correlação: #[N]
```

### 2. ERROS POR MÓDULO

| Módulo | Erros | Warnings | % do Total |
|--------|-------|----------|------------|
| #[core.processor] | #[N] | #[N] | #[X%] |
| #[extractors.nfse_generic] | #[N] | #[N] | #[X%] |
| #[strategies.native] | #[N] | #[N] | #[X%] |

### 3. ANÁLISE DE LOTES LENTOS

**Top 5 lotes mais lentos:**

| Batch ID | Duração | Extratores Testados | Erros | Ação Recomendada |
|----------|---------|---------------------|-------|------------------|
| #[id] | #[45.2s] | #[Lista] | #[N] | #[Otimizar/Investigar] |

**Padrões identificados em lotes lentos:**
- [ ] PDFs muito grandes (>100 páginas)
- [ ] OCR necessário (PDF em imagem)
- [ ] Múltiplos extratores testados antes de match
- [ ] Timeout em operações de I/O

### 4. CORRELAÇÃO LOGS ↔ CSV

#### Casos onde erro no log resultou em problema no CSV:

| Batch ID | Erro no Log | Impacto no CSV | Severidade |
|----------|-------------|----------------|------------|
| #[id] | #[Falha ao desbloquear PDF] | #[Valor zero, sem dados] | #[ALTA] |
| #[id] | #[Nenhum extrator compatível] | #[Classificado como OUTRO] | #[MÉDIA] |
| #[id] | #[Timeout na extração] | #[Dados parciais] | #[ALTA] |

#### Falsos positivos (erro no log mas CSV correto):

| Batch ID | Erro no Log | CSV Status | Observação |
|----------|-------------|------------|------------|
| #[id] | #[Warning de regex] | #[OK] | #[Erro tratado, fallback funcionou] |

### 5. PADRÕES DE ERRO FREQUENTES

**Top 5 erros mais comuns:**

```
1. (#[N] ocorrências) #[Descrição do erro]
   - Causa provável: #[análise]
   - Correção sugerida: #[ação]

2. (#[N] ocorrências) #[Descrição do erro]
   ...
```

**Top 5 warnings mais comuns:**

```
1. (#[N] ocorrências) #[Descrição do warning]
   - Impacto: #[análise]
   - Ação necessária: #[sim/não - justificativa]
```

### 6. IMPACTO NA EXPORTAÇÃO SHEETS

**Documentos que falharão na exportação:**

| Problema | Quantidade | Impacto na Planilha PAF |
|----------|------------|------------------------|
| Valor zero | #[N] | #[Coluna VALOR vazia] |
| Vencimento inválido | #[N] | #[Não calcula situação] |
| Fornecedor genérico | #[N] | #[Coluna FORNECEDOR incorreta] |

**Validação de exportação:**
```bash
# Verificar se há dados que não serão exportados
grep -E "(valor.*0\.0.*fornecedor.*$|vencimento.*$)" data/output/relatorio_lotes.csv | wc -l
```

### 7. RECOMENDAÇÕES DE AÇÃO

#### Ações Imediatas (Alta Prioridade)

1. **[Problema]:** #[Descrição]
   - **Ação:** #[O que fazer]
   - **Arquivos afetados:** #[lista]
   - **Estimativa de correção:** #[tempo]

2. **[Problema]:** #[Descrição]
   ...

#### Ações de Médio Prazo

1. **[Melhoria]:** #[Descrição]
   - **Benefício:** #[impacto esperado]
   - **Esforço:** #[alto/médio/baixo]

#### Monitoramento Contínuo

**Métricas a acompanhar:**
- Taxa de sucesso de extração: #[X%] (meta: >95%)
- Tempo médio por lote: #[Xs] (meta: <10s)
- Documentos sem extrator: #[N] (meta: <5%)

### 8. COMANDOS PARA VERIFICAÇÃO

```bash
# Verificar se problemas foram resolvidos após correções

# 1. Reprocessar e comparar
python run_ingestion.py --reprocess --batch-folder <pasta>

# 2. Comparar CSVs antes/depois
diff data/output/relatorio_lotes.csv.bak data/output/relatorio_lotes.csv

# 3. Validar exportação
python scripts/export_to_sheets.py --dry-run

# 4. Verificar logs de erro novamente
python scripts/analyze_logs.py --errors-only --today
```

---

## Guia de Interpretação de Logs

### Formatos de Log Comuns

```
# Sucesso
2026-01-29 08:44:30 - core.processor - INFO - [123/500] email_20260129_084430_xxx - Processado em 2.5s

# Lento
2026-01-29 08:44:30 - core.processor - WARNING - [123/500] email_20260129_084430_xxx - LENTO (45.2s)

# Erro
2026-01-29 08:44:30 - extractors.nfse_generic - ERROR - Falha ao extrair valor: ...

# Sem extrator
2026-01-29 08:44:30 - core.processor - WARNING - Nenhum extrator compatível encontrado

# PDF protegido
2026-01-29 08:44:30 - strategies.pdf_utils - WARNING - Falha ao desbloquear PDF arquivo.pdf
```

### Códigos de Erro Importantes

| Mensagem no Log | Significado | Ação Recomendada |
|-----------------|-------------|------------------|
| `Falha ao desbloquear PDF` | Senha desconhecida | Adicionar CNPJ a `config/empresas.py` |
| `Nenhum extrator compatível` | Layout não reconhecido | Criar extrator específico |
| `Timeout na extração` | PDF muito grande/complexo | Aumentar timeout ou otimizar OCR |
| `Linha digitável não encontrada` | Boleto com formato diferente | Verificar extrator de boleto |
| `can_handle.*False` | Extrator recusou documento | Revisar padrões de detecção |
