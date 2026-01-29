# Prompt: Validação de Correção de Extração

> **Uso:** Validar se uma correção aplicada resolveu o problema sem causar regressões
> 
> **Momento:** Após implementar correção em extrator ou criar novo extrator

---

## Input da Correção

```yaml
# Identificação da correção
CASO_ORIGINAL: #[ex: CASO #220]
TIPO_CORRECAO: #[Ajuste Regex / Novo Extrator / Correção de Roteamento / Outro]
ARQUIVOS_MODIFICADOS:
  - #[extractors/nome_extrator.py]
  - #[extractors/__init__.py] (se alterou ordem)

# Descrição da mudança
MUDANCA_DESCRICAO: |
  [O que foi alterado?]
  [Ex: "Ajustado regex de _extract_valor para capturar padrão 'Valor dos Serviços'"]
  [Ex: "Criado TcfTelecomExtractor para NFSe específica"]

# Caso de teste principal
BATCH_TESTE: #[email_20260129_084433_5fafb989]
PDF_TESTE: #[01_nota_fiscal_tipo0_n521912_c128326_1767712922.pdf]

# Valores esperados após correção
VALORES_ESPERADOS:
  tipo_documento: #[NFSE/BOLETO/DANFE/OUTRO]
  valor_total: #[700.00]
  numero_nota: #[521912]
  vencimento: #[2026-01-15]
  fornecedor_nome: #[TCF Telecom]
  status_conciliacao: #[CONCILIADO/CONFERIR/PAREADO_FORCADO]
```

---

## Template de Validação

### 1. PRÉ-VALIDAÇÃO (Backup)

```bash
# Executar antes de aplicar a correção

# 1. Backup do CSV atual
cp data/output/relatorio_lotes.csv data/output/relatorio_lotes.csv.bak.$(date +%Y%m%d_%H%M%S)

# 2. Backup do código modificado (se ainda não estiver no git)
cp extractors/[nome_extrator].py extractors/[nome_extrator].py.bak

# 3. Registrar estado atual do caso de teste
grep <BATCH_TESTE> data/output/relatorio_lotes.csv > /tmp/caso_antes.csv

# 4. (NOVO) Validar regressão usando batches específicos - MUITO MAIS RÁPIDO!
# Processa apenas os batches afetados pela correção
python scripts/validate_extraction_rules.py --batch-mode --temp-email \
    --batches <BATCH_ID_1>,<BATCH_ID_2>,<BATCH_ID_3>

# Alternativa: Validar TODOS os batches (mais lento, use com cautela)
# python scripts/validate_extraction_rules.py --batch-mode --temp-email
```

### 2. TESTE UNITÁRIO DO CASO ESPECÍFICO

```bash
# Testar o PDF específico após correção
python scripts/inspect_pdf.py <PDF_TESTE>
```

**Resultado esperado:**

| Campo | Valor Obtido | Valor Esperado | Status |
|-------|--------------|----------------|--------|
| Tipo | #[NFSE] | #[VALORES_ESPERADOS.tipo_documento] | [✓/✗] |
| Extrator | #[TcfTelecomExtractor] | #[NomeDoExtratorEsperado] | [✓/✗] |
| Valor | #[R$ 700,00] | #[R$ 700,00] | [✓/✗] |
| Número | #[521912] | #[521912] | [✓/✗] |
| Vencimento | #[2026-01-15] | #[2026-01-15] | [✓/✗] |
| Fornecedor | #[TCF Telecom] | #[TCF Telecom] | [✓/✗] |

**Texto bruto extraído (confirmar):**
```
#[Trechos relevantes do texto extraído para confirmar que a fonte está correta]
```

### 3. TESTE DE REPROCESSAMENTO DO BATCH

```bash
# Reprocessar o batch completo
python run_ingestion.py --batch-folder <BATCH_TESTE>

# Ou reprocessar todos os batches se necessário
# python run_ingestion.py --reprocess
```

**Verificação no CSV:**

```bash
# Comparar antes e depois
echo "=== ANTES ===" && grep <BATCH_TESTE> data/output/relatorio_lotes.csv.bak.* | tail -1
echo "=== DEPOIS ===" && grep <BATCH_TESTE> data/output/relatorio_lotes.csv
```

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Valor | #[R$ 0,00] | #[R$ 700,00] | #[✓ 100%] |
| Status | #[CONFERIR] | #[CONCILIADO] | #[✓ Corrigido] |
| Divergência | #[Texto] | #[vazio] | #[✓ Removida] |

### 4. TESTE DE REGRESSÃO (CRÍTICO)

```bash
# Validar que não quebrou outros casos
# OPÇÃO 1: Testar apenas batches específicos (RECOMENDADO - muito mais rápido!)
# Processa apenas os batches que usam o mesmo extrator ou extratores similares
python scripts/validate_extraction_rules.py --batch-mode --temp-email \
    --batches <BATCH_AFETADO_1>,<BATCH_AFETADO_2>,<BATCH_SIMILAR_1>

# OPÇÃO 2: Testar todos os batches (use com cautela - pode demorar muito!)
# python scripts/validate_extraction_rules.py --batch-mode --temp-email

# OPÇÃO 3: Testar amostra representativa (equilíbrio entre cobertura e velocidade)
# Escolha ~10 batches variados: NFSe, Boleto, DANFE, Outros
# python scripts/validate_extraction_rules.py --batch-mode --temp-email \
#     --batches batch_nfse_1,batch_boleto_1,batch_danfe_1,batch_outro_1
```

**Casos de teste de regressão (mínimo 5):**

| Caso | Tipo | Antes (Valor) | Depois (Valor) | Status |
|------|------|---------------|----------------|--------|
| #[Caso 1 - mesmo extrator] | #[NFSE] | #[R$ X] | #[R$ X] | [✓/✗] |
| #[Caso 2 - extrator similar] | #[NFSE] | #[R$ Y] | #[R$ Y] | [✓/✗] |
| #[Caso 3 - boleto] | #[BOLETO] | #[R$ Z] | #[R$ Z] | [✓/✗] |
| #[Caso 4 - DANFE] | #[DANFE] | #[R$ W] | #[R$ W] | [✓/✗] |
| #[Caso 5 - administrativo] | #[OUTRO] | #[R$ V] | #[R$ V] | [✓/✗] |

**Estatísticas de regressão:**

```bash
# Contar casos com valor zero (não deve aumentar)
echo "Casos valor zero (antes):" && grep -c ";0,0;" data/output/relatorio_lotes.csv.bak.*
echo "Casos valor zero (depois):" && grep -c ";0,0;" data/output/relatorio_lotes.csv

# Contar casos CONFERIR (não deve aumentar significativamente)
echo "Casos CONFERIR (antes):" && grep -c "CONFERIR" data/output/relatorio_lotes.csv.bak.*
echo "Casos CONFERIR (depois):" && grep -c "CONFERIR" data/output/relatorio_lotes.csv
```

### 5. TESTE DE EXPORTAÇÃO SHEETS

```bash
# Validar exportação (dry-run)
python scripts/export_to_sheets.py --dry-run
```

**Validações:**

- [ ] Exportação completa sem erros
- [ ] Coluna VALOR preenchida corretamente
- [ ] Coluna FORNECEDOR preenchida corretamente
- [ ] Coluna VENCIMENTO preenchida corretamente
- [ ] Coluna NF preenchida corretamente
- [ ] Coluna SITUACAO calculada corretamente

**Exemplo de linha exportada:**

| PROCESSADO | RECEBIDO | ASSUNTO | EMPRESA | VENCIMENTO | FORNECEDOR | NF | VALOR | SITUACAO |
|------------|----------|---------|---------|------------|------------|-----|-------|----------|
| #[data] | #[data] | #[assunto] | #[empresa] | #[venc] | #[forn] | #[nf] | #[valor] | #[OK] |

### 6. TESTE DE CORRELAÇÃO NF↔BOLETO (se aplicável)

```bash
# Verificar casos pareados
grep "CONCILIADO" data/output/relatorio_lotes.csv | grep <padrao_fornecedor> | head -5

# Verificar diferenças de valor
grep "diferenca_valor" data/output/relatorio_lotes.csv | grep -v ";0,0;" | head -5
```

**Validações de correlação:**

- [ ] NF e Boleto do mesmo lote estão pareados
- [ ] Valores conferem (diferença = 0 ou explicada)
- [ ] Vencimento foi herdado do boleto para NF
- [ ] Fornecedor foi herdado da NF para boleto

### 7. ANÁLISE DE LOGS PÓS-CORREÇÃO

```bash
# Verificar se surgiram novos erros/warnings
python scripts/analyze_logs.py --errors-only --today
```

**Métricas de log:**

| Métrica | Antes | Depois | Status |
|---------|-------|--------|--------|
| Erros | #[N] | #[N] | [✓/⚠/✗] |
| Warnings | #[N] | #[N] | [✓/⚠/✗] |
| Lotes lentos | #[N] | #[N] | [✓/⚠/✗] |

**Novos erros introduzidos (deve ser zero):**
```
#[Listar qualquer novo erro que apareceu]
```

---

## Critérios de Aprovação

### Aprovação Total (todos devem passar)

- [ ] Caso específico corrigido (todos os campos)
- [ ] Nenhuma regressão em casos existentes
- [ ] Exportação Sheets funcionando
- [ ] Nenhum novo erro nos logs
- [ ] Correlação NF↔Boleto intacta (se aplicável)

### Aprovação Parcial (aceitável com ressalvas)

- [ ] Caso específico corrigido
- [ ] Regressão mínima (< 5 casos afetados negativamente)
- [ ] Ressalvas documentadas
- [ ] Plano para corrigir regressões

### Rejeição (deve refazer)

- [ ] Caso específico não corrigido
- [ ] Regressão significativa (>= 5 casos)
- [ ] Novos erros críticos nos logs
- [ ] Quebra exportação Sheets

---

## Documentação da Correção

Se aprovado, documente:

```yaml
# Resumo da correção
DATA: #[YYYY-MM-DD]
AUTOR: #[Nome]
CASOS_AFETADOS: #[N casos corrigidos]
REGRESSOES: #[0 ou lista]

# Descrição para changelog
DESCRICAO: |
  [Correção/implementação realizada]
  
# Casos de teste que devem ser monitorados
MONITORAMENTO:
  - #[BATCH_ID_1]
  - #[BATCH_ID_2]
```

---

## Comandos para Verificação Rápida

### Validação de Regressão (pós-correção)

```bash
# Testar apenas batches específicos (RECOMENDADO)
python scripts/validate_extraction_rules.py --batch-mode --temp-email \
    --batches <BATCH_ID_1>,<BATCH_ID_2>

# Testar com correlação e validações completas
python scripts/validate_extraction_rules.py --batch-mode --temp-email \
    --batches <BATCH_ID> \
    --validar-prazo --exigir-nf --apply-correlation

# Inspecionar PDF específico
python scripts/inspect_pdf.py <nome_arquivo.pdf>
python scripts/inspect_pdf.py --batch <batch_id>
```

### Comparação de Resultados

```bash
# Verificar mudanças no CSV
grep <BATCH_ID> data/output/relatorio_lotes.csv

# Comparar com backup
diff data/output/relatorio_lotes.csv.bak.* data/output/relatorio_lotes.csv | grep <BATCH_ID>

# Contar casos corrigidos
grep "CONCILIADO" data/output/relatorio_lotes.csv | wc -l
grep "CONFERIR" data/output/relatorio_lotes.csv | wc -l
```

---

## Rollback (se necessário)

Se a validação falhar:

```bash
# 1. Restaurar backup do código
cp extractors/[nome_extrator].py.bak.<timestamp> extractors/[nome_extrator].py

# 2. Restaurar CSV (se necessário)
cp data/output/relatorio_lotes.csv.bak.<timestamp> data/output/relatorio_lotes.csv

# 3. Reverter alterações no git
git checkout extractors/[nome_extrator].py
# Ou: git checkout extractors/__init__.py

# 4. Limpar lotes reprocessados (opcional)
# rm -rf temp_email/<batch_id>_reprocessed
```
