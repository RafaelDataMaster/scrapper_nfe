# Prompt: Análise de Priorização de Erros por Recorrência

> **Uso:** Análise macro dos erros para decidir O QUE atacar primeiro baseado em impacto e recorrência
> 
> **Foco:** Agrupamento por fornecedor, cidade (NFSe), tipo de erro e viabilidade de correção

---

## Input para Análise

```yaml
# Período de análise
DATA_INICIO: #[YYYY-MM-DD]
DATA_FIM: #[YYYY-MM-DD ou "atual"]

# Fonte de dados
CSV_ANALISE: #[data/output/relatorio_lotes.csv]
CSV_DETALHADO: #[data/output/relatorio_consolidado.csv - opcional]
ARQUIVO_ANALISE_PDFS: #[data/output/analise_pdfs_detalhada.txt - opcional]

# Critérios de filtro (opcional)
FILTROS:
  valor_minimo: #[0.00 - considerar apenas casos acima deste valor]
  empresas: #[lista ou "todas"]
  status: #[CONFERIR/PAREADO_FORCADO - focar em status problemáticos]

# Objetivo da análise
OBJETIVO:
  - [ ] Identificar fornecedores recorrentes com problema
  - [ ] Identificar cidades (NFSe) com padrão problemático
  - [ ] Calcular impacto financeiro total por tipo de erro
  - [ ] Priorizar correções por esforço/benefício
  - [ ] Decidir: automatizar vs tratamento manual
```

---

## Scripts de Coleta (execute antes)

```bash
# 1. Estatísticas gerais do CSV
wc -l data/output/relatorio_lotes.csv
echo "Total de lotes processados"

# 2. Agrupar por status
echo "=== POR STATUS ==="
awk -F';' 'NR>1 {print $3}' data/output/relatorio_lotes.csv | sort | uniq -c | sort -rn

# 3. Casos com valor zero (problema crítico)
echo "=== VALOR ZERO ==="
awk -F';' 'NR>1 && ($9=="0,0" || $9=="0" || $9=="0,00") {print}' data/output/relatorio_lotes.csv | wc -l

# 4. Agrupar por fornecedor (top 20 com problema)
echo "=== TOP FORNECEDORES COM PROBLEMA ==="
awk -F';' 'NR>1 && ($3=="CONFERIR" || $9=="0,0") {print $6}' data/output/relatorio_lotes.csv | sort | uniq -c | sort -rn | head -20

# 5. Análise por cidade (extrair de fornecedor ou email)
echo "=== ANÁLISE POR DOMÍNIO/REMETENTE ==="
awk -F';' 'NR>1 && ($3=="CONFERIR" || $9=="0,0") {print $18}' data/output/relatorio_lotes.csv | sort | uniq -c | sort -rn | head -20

# 6. Casos por tipo de divergência
echo "=== TIPOS DE DIVERGÊNCIA ==="
awk -F';' 'NR>1 {print $4}' data/output/relatorio_lotes.csv | sort | uniq -c | sort -rn | head -15

# 7. Extrair CNPJs dos fornecedores problemáticos (se houver no texto)
grep -oE "[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}" data/output/relatorio_lotes.csv | sort | uniq -c | sort -rn | head -10

# 8. Análise de NFSes por cidade (padrão em fornecedor ou assunto)
echo "=== POSSÍVEIS CIDADES NFS-e ==="
awk -F';' 'NR>1 && $16>0 {print $6}' data/output/relatorio_lotes.csv | grep -iE "prefeitura|municipal|sao paulo|belo horizonte|rio de janeiro" | sort | uniq -c | sort -rn | head -15
```

---

## Template de Análise Estatística

### 1. RESUMO EXECUTIVO

```
Período Analisado: #[DATA_INICIO] a #[DATA_FIM]
Total de Lotes: #[N]
Total Documentos Fiscais: #[N NFSe + N DANFE + N Boletos]
Valor Total Processado: #[R$ X.XXX.XXX,XX]
```

**Distribuição por Status:**

| Status | Quantidade | % do Total | Valor Total | Severidade |
|--------|------------|------------|-------------|------------|
| CONCILIADO | #[N] | #[X%] | #[R$ X] | ✅ OK |
| CONFERIR | #[N] | #[X%] | #[R$ X] | 🔴 ALTA |
| PAREADO_FORCADO | #[N] | #[X%] | #[R$ X] | 🟡 MÉDIA |

**Problemas Críticos Identificados:**

| Problema | Quantidade | Valor Total | % do Valor Total |
|----------|------------|-------------|------------------|
| Valor Zero (CSV=0, PDF≠0) | #[N] | #[R$ X] | #[X%] |
| Vencimento Vazio | #[N] | #[R$ X] | #[X%] |
| Fornecedor Genérico | #[N] | #[R$ X] | #[X%] |
| Número Nota Vazio | #[N] | #[R$ X] | #[X%] |

### 2. ANÁLISE POR FORNECEDOR (Recorrência)

#### Top 10 Fornecedores com Problemas

| Rank | Fornecedor | CNPJ | Casos | Valor Total | Tipo Principal | Cidade/UF | Ação Recomendada |
|------|------------|------|-------|-------------|----------------|-----------|------------------|
| 1 | #[Nome] | #[CNPJ] | #[N] | #[R$ X] | #[Valor Zero] | #[Cidade] | #[Criar Extrator] |
| 2 | #[Nome] | #[CNPJ] | #[N] | #[R$ X] | #[Vencimento] | #[Cidade] | #[Ajustar Regex] |
| 3 | ... | ... | ... | ... | ... | ... | ... |

#### Classificação por Viabilidade

**🔴 ALTA PRIORIDADE (Criar Extrator):**
```yaml
Fornecedor: #[Nome]
CNPJ: #[XX.XXX.XXX/XXXX-XX]
Quantidade: #[N] casos
Valor Total: #[R$ X.XXX,XX]
Recorrência: #[Mensal/Semestral]
Layout: #[Estável/Variável]
Justificativa: "#[Por que vale a pena automatizar]"
Estimativa de Esforço: #[X horas]
ROI: #[Alto/Médio - justificar]
```

**🟡 MÉDIA PRIORIDADE (Ajustar Regex):**
```yaml
Fornecedor: #[Nome]
Padrão: #[Tipo de documento]
Problema: #[Qual campo falha]
Quantidade: #[N] casos
Solução: "#[Ajuste específico no extrator genérico]"
```

**🟢 BAIXA PRIORIDADE (Tratamento Manual):**
```yaml
Fornecedor: #[Nome]
Quantidade: #[N] casos (#[X%] do total)
Valor Médio: #[R$ XXX,XX]
Justificativa: "#[Por que não vale automatizar - ex: baixo volume, variável]"
Ação: #[Planilha de ajuste manual / ignorar]
```

### 3. ANÁLISE POR CIDADE (NFSe Específico)

#### Cidades com Maior Volume Problemático

| Cidade | UF | Casos | Valor Total | Extrator Atual | Problema | Status |
|--------|-----|-------|-------------|----------------|----------|--------|
| #[São Paulo] | SP | #[N] | #[R$ X] | NfseGeneric | #[Valor] | #[Já existe específico?] |
| #[Belo Horizonte] | MG | #[N] | #[R$ X] | NfseGeneric | #[Vencimento] | #[Necessita específico] |
| #[Montes Claros] | MG | #[N] | #[R$ X] | NfseCustomMontesClaros | #[OK] | ✅ Funcionando |

#### Análise de Layout por Cidade

**Cidades que precisam de extrator específico:**

```yaml
Cidade: #[Nome]
CNPJ Padrão: #[XX.XXX.XXX/XXXX-XX] (se houver)
Problemas Identificados:
  - #[Campo X: descrição do problema]
  - #[Campo Y: descrição do problema]
Padrão Único: #[Sim/Não - justificar]
Prioridade: #[Alta/Média/Baixa]
```

**Cidades cobertas por extrator genérico (bom):**
```yaml
Cidade: #[Nome]
Taxa de Sucesso: #[X%]
Observação: "#[Funciona bem, manter genérico]"
```

### 4. ANÁLISE POR TIPO DE ERRO

#### Padrões de Erro Mais Comuns

| Tipo de Erro | Frequência | % dos Casos Problemáticos | Fácil Correção? | Impacto Financeiro |
|--------------|------------|---------------------------|-----------------|-------------------|
| Valor com formato diferente | #[N] | #[X%] | ✅ Sim - ajuste regex | #[R$ X] |
| Vencimento em formato americano | #[N] | #[X%] | ✅ Sim - parse_date | #[R$ X] |
| Número da nota com prefixo | #[N] | #[X%] | ✅ Sim - regex | #[R$ X] |
| PDF protegido por senha | #[N] | #[X%] | ⚠️ Médio - add CNPJ | #[R$ X] |
| Layout completamente diferente | #[N] | #[X%] | ❌ Não - novo extrator | #[R$ X] |

#### Correções "Quick Win" (Baixo Esforço, Alto Impacto)

```yaml
Correção 1:
  Problema: "#[Descrição curta]"
  Casos Afetados: #[N]
  Valor Total: #[R$ X]
  Solução: "#[Ajuste simples]"
  Tempo Estimado: #[X minutos]
  Prioridade: 🔴 ALTA

Correção 2:
  ...
```

### 5. MATRIZ DE PRIORIZAÇÃO

#### Quadrante de Prioridade (Impacto vs Esforço)

```
                    BAIXO ESFORÇO          ALTO ESFORÇO
                 ┌──────────────────┬──────────────────┐
    ALTO         │  🔴 QUICK WINS   │  🟡 PROJETOS     │
   IMPACTO       │  (Fazer primeiro)│  (Planejar)      │
                 │                  │                  │
   Valor > R$10K │  - Ajuste regex  │  - Novo extrator │
   Recorrente    │  - Parse data    │    específico    │
                 │  - CNPJ senha    │  - Refatoração   │
                 ├──────────────────┼──────────────────┤
   BAIXO         │  🟢 PREENCHER    │  ⚫ EVITAR       │
   IMPACTO       │  (Quando sobrar  │  (Não fazer)     │
                 │   tempo)         │                  │
   Valor < R$1K  │  - Ajuste minor  │  - Caso único    │
   Esporádico    │  - Log melhorado │  - Volume baixo  │
                 └──────────────────┴──────────────────┘
```

#### Ranking de Prioridade Final

| Pos | Ação | Fornecedor/Cidade | Impacto (R$) | Esforço (h) | ROI | Prazo |
|-----|------|-------------------|--------------|-------------|-----|-------|
| 1 | #[Criar extrator X] | #[Fornecedor] | #[R$ X] | #[4h] | #[Alto] | #[1 semana] |
| 2 | #[Ajustar regex Y] | #[Cidade] | #[R$ X] | #[1h] | #[Alto] | #[2 dias] |
| 3 | ... | ... | ... | ... | ... | ... |

### 6. RECOMENDAÇÕES ESTRATÉGICAS

#### Curtos Prazo (Esta Semana)

```yaml
Ação 1:
  Tarefa: "#[Implementar correção específica]"
  Responsável: #[Nome]
  Tempo: #[X horas]
  Entregável: #[O que será entregue]
  Validação: #[Como saber se funcionou]

Ação 2:
  ...
```

#### Médio Prazo (Este Mês)

```yaml
Projeto 1:
  Nome: "#[Criar extrator para Fornecedor X]"
  Justificativa: "#[N casos/mês, valor R$ X]"
  Fases:
    1. Coleta de amostras (#[N] PDFs)
    2. Análise de padrões
    3. Desenvolvimento do extrator
    4. Testes e validação
  Tempo Total: #[X horas]
```

#### Decisões de "Não Fazer"

```yaml
Caso 1:
  Situação: "#[Fornecedor Y com problema]"
  Justificativa: "#[Por que não vale a pena]"
  Alternativa: "#[Tratamento manual / ignorar]"
  Reavaliação: "#[Rever em X meses se volume aumentar]"
```

### 7. IMPACTO FINANCEIRO PROJETADO

#### Se Todas as Correções Forem Implementadas

| Métrica | Atual | Projetado | Melhoria |
|---------|-------|-----------|----------|
| Taxa de Sucesso | #[X%] | #[Y%] | +#[Z%] |
| Valor em "CONFERIR" | #[R$ X] | #[R$ Y] | -#[Z%] |
| Casos Manuais/Mês | #[N] | #[M] | -#[P%] |
| Tempo de Revisão | #[X h] | #[Y h] | -#[Z h] |

#### Retorno sobre Investimento (ROI)

```
Custo das correções: #[X horas * R$/hora = R$ Y]
Economia projetada: #[Redução de Z horas/mês * 12 meses * R$/hora = R$ W]
ROI: #[(W-Y)/Y * 100]% em 12 meses
Payback: #[X meses]
```

---

## Comandos para Aprofundamento

```bash
# Analisar um fornecedor específico em detalhe
FORNECEDOR="NOME DO FORNECEDOR"
grep -i "$FORNECEDOR" data/output/relatorio_lotes.csv | awk -F';' '{print $2, $3, $6, $7, $8, $9, $16}' | column -t

# Listar todos os PDFs de um fornecedor problemático
FORNECEDOR="NOME"
grep -i "$FORNECEDOR" data/output/relatorio_lotes.csv | awk -F';' '{print $21}' | while read pasta; do ls "$pasta"/*.pdf 2>/dev/null; done

# Análise temporal (evolução dos erros)
awk -F';' 'NR>1 {print substr($2,1,7)}' data/output/relatorio_lotes.csv | sort | uniq -c | sort

# Agrupar por assunto do email (padrões)
awk -F';' 'NR>1 && $3=="CONFERIR" {print $17}' data/output/relatorio_lotes.csv | sort | uniq -c | sort -rn | head -20
```

---

## Checklist de Decisão

Para cada fornecedor/cidade identificada:

- [ ] Quantidade de casos justifica automatização? (>5 casos ou >R$ 10K)
- [ ] Layout é estável ou varia muito?
- [ ] Existe CNPJ ou padrão único para identificação?
- [ ] O problema é apenas regex ou requer lógica complexa?
- [ ] Já existe extrator similar que pode ser ajustado?
- [ ] Volume é recorrente (mensal) ou esporádico?
- [ ] Impacto na exportação Sheets é crítico?

**Se 5+ itens positivos → Criar extrator específico**  
**Se 3-4 itens → Ajustar extrator genérico**  
**Se <3 itens → Tratamento manual**
