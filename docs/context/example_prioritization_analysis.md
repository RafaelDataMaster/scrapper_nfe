# Exemplo Prático: Análise de Priorização

> **Baseado em:** `data/output/analise_pdfs_detalhada.txt`  
> **Data:** Análise real dos casos problemáticos

---

## ⚠️ AVISO IMPORTANTE: Volatilidade dos Batch IDs

> **Batch IDs (`email_YYYYMMDD_HHMMSS_hash`) são voláteis!**

Este exemplo mostra análise por **fornecedor e padrão**, não por batch ID específico. 

**Por quê?** Quando você roda:
```bash
python scripts/clean_dev.py      # Limpa tudo
python run_ingestion.py          # Baixa emails novos
```

Os batch IDs mudam completamente! Um caso que era `email_20260129_084433_c5c04540` vira `email_20260130_090000_abc12345`.

**Solução:** Sempre use identificadores estáveis:
- ✅ **Fornecedor** (ex: "TUNNA ENTRETENIMENTO")
- ✅ **CNPJ** (ex: "12.345.678/9012-34")
- ✅ **Padrão de email** (ex: "faturamento@fishtv.com.br")
- ✅ **Tipo de documento** (ex: "FATURA com padrão FAT/XXXXX")
- ❌ **Batch ID** (ex: `email_20260129_084433_c5c04540`) - volátil!

**Para rastreamento entre sessões:** Veja [`correction_tracking.md`](./correction_tracking.md)

---

---

## Comandos Executados para Coleta

```bash
# 1. Contar casos por severidade
grep -c "Nível de severidade: ALTA" data/output/analise_pdfs_detalhada.txt
grep -c "Nível de severidade: MEDIA" data/output/analise_pdfs_detalhada.txt

# 2. Extrair fornecedores com problemas
grep "Fornecedor:" data/output/analise_pdfs_detalhada.txt | sort | uniq -c | sort -rn | head -15

# 3. Contar problemas por tipo
grep -c "Valor zero" data/output/analise_pdfs_detalhada.txt
grep -c "Vencimento vazio" data/output/analise_pdfs_detalhada.txt
grep -c "Número da nota não extraído" data/output/analise_pdfs_detalhada.txt

# 4. Identificar padrões de remetente/email
grep "Remetente:" data/output/analise_pdfs_detalhada.txt | sort | uniq -c | sort -rn | head -10
```

---

## Resultado da Análise (Simulação com dados reais)

### 1. RESUMO EXECUTIVO

```
Período Analisado: 2026-01-29 (processamento atual)
Total de Casos Analisados: ~50 casos problemáticos
Documentos Fiscais Afetados: Predominantemente NFSE
Valor Total em Risco: ~R$ 50.000+ (estimado)
```

**Distribuição por Severidade:**

| Severidade | Quantidade | % do Total | Observação |
|------------|------------|------------|------------|
| 🔴 ALTA | ~35 | ~70% | Bloqueiam exportação Sheets |
| 🟡 MÉDIA | ~15 | ~30% | Necessitam revisão manual |
| 🟢 BAIXA | 0 | 0% | - |

**Problemas Críticos Identificados:**

| Problema | Quantidade | Padrão | Observação |
|----------|------------|--------|------------|
| Valor Zero (PDF≠0) | ~25 | NFSEs com valor não extraído | Principal problema |
| Vencimento Vazio | ~20 | Datas não capturadas | Impacta cálculo de situação |
| Número Nota Vazio | ~15 | NFs sem identificação | Dificulta rastreamento |
| Fornecedor Genérico | ~8 | Pegou label do campo | Dados incorretos |

---

### 2. ANÁLISE POR FORNECEDOR (Recorrência)

#### Top Fornecedores Problemáticos Identificados

| Rank | Fornecedor/Remetente | Casos | Tipo Principal | Problema | Cidade/UF | Ação Recomendada |
|------|---------------------|-------|----------------|----------|-----------|------------------|
| 1 | **atendimento@cemig.com.br** | 4 | Conta de Energia | Valor zero, venc vazio | MG (várias cidades) | 🔴 Verificar EnergyBillExtractor |
| 2 | **fishtv@fishtv.com** | 3 | NFSE/DANFE | Valor zero, num nota vazio | ? | 🔴 Criar extrator específico |
| 3 | **TCF Telecom** | 2 | NFSE | Valor zero | ? | 🟡 Ajustar NfseGeneric |
| 4 | **Equinix Orders** | 3 | Ordem de Serviço | Valor zero (documento adm) | - | 🟢 OK - Documento adm sem valor |
| 5 | **facturacionufinet@ufinet.com** | 3 | Fatura/Boleto | Fornecedor vazio, valor zero | ? | 🔴 Criar extrator Ufinet |
| 6 | **contasapagar@soumaster.com.br** | 3 | Vários | Mix de documentos | - | 🟢 Diversos - analisar caso a caso |
| 7 | **financeiro@semelclavras.com.br** | 2 | NFSE/Boleto | Fornecedor vazio | Clávras-MG | 🟡 Ajustar existente |
| 8 | **Ufinet Brasil SA** | 2 | NFSE | Fornecedor detectado mas valor zero | ? | 🔴 Mesmo caso do item 5 |

#### Análise Detalhada dos Principais

**🔴 1. CEMIG (Companhia Energética de Minas Gerais)**
```yaml
Fornecedor: CEMIG DISTRIBUIÇÃO S.A.
CNPJ: 06.981.180/0001-16 (padrão)
Quantidade: 4 casos (CASOS #181, #182, #183, #184, #462)
Valor Total: ~R$ 1.000+ estimado
Recorrência: Mensal (contas de energia)
Layout: Estável (faturas padrão)
Problema: 
  - "Classificação sugerida: NFSE" (incorreto - é conta de energia)
  - Valor zero no CSV
  - Vencimento vazio
Análise: EnergyBillExtractor existe mas não está detectando
Solução: Verificar can_handle do EnergyBillExtractor
Prioridade: 🔴 ALTA (volume mensal garantido)
ROI: Alto - contas recorrentes mensais
```

**🔴 2. FishTV**
```yaml
Fornecedor: fishtv@fishtv.com
Documento: DANFE (Nota Fiscal FAT/10731, FAT/10732, FAT/10733)
Quantidade: 3 casos
Problema:
  - "Classificação sugerida: NFSE" (incorreto - é DANFE)
  - Valor zero
  - Vencimento vazio
  - Assunto sugere "Nota Fiscal"
Análise: 
  - PDF: "01_DANFEFAT0000010731.pdf" - tem "DANFE" no nome
  - Layout específico "FAT/XXXXX"
Solução: 
  - Opção A: Ajustar DanfeExtractor para capturar padrão FAT
  - Opção B: Criar FishTVExtractor se houver mais fornecedores com layout similar
Prioridade: 🔴 ALTA (padrão recorrente)
```

**🔴 3. Ufinet**
```yaml
Fornecedor: Ufinet Brasil SA / facturacionufinet@ufinet.com
Documento: Fatura/Boleto
Quantidade: 3 casos (#228, #232, #427)
Problema:
  - "Classificação sugerida: DESCONHECIDO"
  - Fornecedor vazio ou incorreto
  - Valor zero
Padrão Identificado:
  - Assunto: "Notificação Automática Ufinet - Documento XXXXX"
  - Arquivos: "01_000000135_06_FilialMG.pdf", "02_Boleto_ubr1_000042984.pdf"
  - Boleto detectado com valor (R$ 6.000,00) mas não extraído para CSV
Análise: 
  - Mistura de fatura (documento adm) + boleto
  - Layout específico da Ufinet
Solução: Criar UfinetExtractor
  - Prioridade: 4-5 (depois de específicos mais urgentes)
  - Detectar por: CNPJ ou email @ufinet.com
  - Extrair: Valor do boleto, vencimento da linha digitável
Prioridade: 🔴 ALTA (valor alto - R$ 6.000 no caso #427)
```

---

### 3. ANÁLISE POR CIDADE (NFSe Específico)

#### Cidades/Fornecedores com Layout Problemático

| Cidade/Origem | Casos | Extrator Atual | Problema | Ação |
|---------------|-------|----------------|----------|------|
| Montes Claros-MG | 0 (nos problemáticos) | NfseCustomMontesClaros | Funcionando | ✅ Manter |
| Vila Velha-ES | 0 (nos problemáticos) | NfseCustomVilaVelha | Funcionando | ✅ Manter |
| Nepomuceno-MG | 2 | NfseGeneric | Número da nota "0" ou vazio | 🟡 Verificar |
| ? (FishTV) | 3 | Classificado como NFSE (errado) | É DANFE, não NFSE | 🔴 Corrigir |
| ? (TCF Telecom) | 2 | NfseGeneric | Valor zero | 🟡 Ajustar |

#### Observações

- **NFSe Montes Claros** e **Vila Velha**: Extratores específicos funcionando bem (não aparecem nos problemáticos)
- **NFSe genéricas**: Maioria dos problemas são classificação incorreta (DANFE como NFSE) ou valor não extraído
- **Necessidade**: Não identificada necessidade de novo extrator de cidade específica nesta amostra

---

### 4. ANÁLISE POR TIPO DE ERRO

#### Padrões Identificados nos Casos

| Tipo de Erro | Frequência | Fácil Correção? | Causa Provável |
|--------------|------------|-----------------|----------------|
| Valor zero com PDF tendo valor | 25+ | ⚠️ Médio | Regex pegando campo errado (R$ 0,00 ao invés do valor real) |
| Classificação NFSE vs DANFE | 5+ | ✅ Sim | DANFE com "Nota Fiscal" no texto foi para NfseGeneric |
| Vencimento vazio em boleto | 10+ | ✅ Sim | Não extraído da linha digitável |
| Fornecedor genérico | 8 | ✅ Sim | Pegou "CNPJ FORNECEDOR" ou similar |
| Documento DESCONHECIDO | 15+ | ❌ Não | Layout não coberto por nenhum extrator |

#### Correções "Quick Win" Identificadas

```yaml
Quick Win 1: Ajuste de Classificação DANFE vs NFSE
  Problema: DANFEs com "Nota Fiscal" no texto sendo classificados como NFSE
  Casos: FishTV (#205, #207, #209), outros
  Solução: Refinar can_handle do NfseGeneric para verificar DANFE primeiro
  Tempo: 30 minutos
  Impacto: 5+ casos corrigidos
  Prioridade: 🔴 ALTA

Quick Win 2: Extrair Vencimento da Linha Digitável
  Problema: Boletos com vencimento vazio no CSV
  Casos: Vários boletos com linha digitável presente
  Solução: Usar função existente decode_linha_digitavel no BoletoExtractor
  Tempo: 1 hora
  Impacto: 10+ casos corrigidos
  Prioridade: 🔴 ALTA

Quick Win 3: Filtro de Fornecedor Genérico
  Problema: "CNPJ FORNECEDOR", "FORNECEDOR", etc. sendo extraídos
  Casos: 8 casos
  Solução: Adicionar validação em extractors/utils.py
  Tempo: 30 minutos
  Impacto: 8 casos corrigidos
  Prioridade: 🟡 MÉDIA
```

---

### 5. MATRIZ DE PRIORIZAÇÃO

#### Quadrante de Decisão

```
                    BAIXO ESFORÇO          ALTO ESFORÇO
                 ┌──────────────────┬──────────────────┐
    ALTO         │  🔴 QUICK WIN 1  │  🔴 PROJETO 1    │
   IMPACTO       │  Ajuste DANFE/   │  Extrator Ufinet │
                 │  NFSE            │                  │
                 │  (30 min)        │  (4 horas)       │
                 ├──────────────────┼──────────────────┤
   MÉDIO         │  🔴 QUICK WIN 2  │  🟡 PROJETO 2    │
   IMPACTO       │  Venc. Boleto    │  Extrator FishTV │
                 │  (1 hora)        │  (se recorrente) │
                 ├──────────────────┼──────────────────┤
   BAIXO         │  🟢 QUICK WIN 3  │  ⚫ NÃO FAZER    │
   IMPACTO       │  Filtro Forn.    │  Casos únicos    │
                 │  genérico        │  esporádicos     │
                 └──────────────────┴──────────────────┘
```

#### Ranking de Prioridade Final

| Pos | Ação | Fornecedor/Cidade | Impacto (Casos) | Esforço | ROI | Prazo Sugerido |
|-----|------|-------------------|-----------------|---------|-----|----------------|
| 1 | Ajustar can_handle NfseGeneric | DANFEs diversos | 5+ casos | 30 min | 🔥🔥🔥 | Hoje |
| 2 | Extrair vencimento do boleto | Boletos diversos | 10+ casos | 1 h | 🔥🔥🔥 | Amanhã |
| 3 | Verificar EnergyBillExtractor | CEMIG | 4 casos/mês | 2 h | 🔥🔥 | Esta semana |
| 4 | Criar UfinetExtractor | Ufinet | 3 casos + alto valor | 4 h | 🔥🔥 | Esta semana |
| 5 | Analisar FishTV | FishTV | 3 casos | 3 h | 🔥 | Próxima semana |
| 6 | Filtro fornecedor genérico | Vários | 8 casos | 30 min | 🔥 | Quando sobrar |

---

### 6. RECOMENDAÇÕES IMEDIATAS

#### Ações para Hoje (Quick Wins)

1. **Ajustar NfseGeneric.can_handle()** para não capturar DANFEs
   - Adicionar verificação: se tem "DANFE" no texto ou nome do arquivo, retornar False
   - Casos afetados: FishTV e possivelmente outros

2. **Verificar EnergyBillExtractor**
   - Por que não está detectando faturas CEMIG?
   - Adicionar padrão se necessário

#### Ações para Esta Semana

1. **Criar UfinetExtractor**
   - CNPJ ou email como identificador
   - Extrair valor do boleto (já detectado no PDF)
   - Extrair vencimento da linha digitável

2. **Melhorar extração de vencimento em boletos**
   - Usar código de barras/linha digitável quando campo não encontrado no texto

#### Decisões de "Não Fazer" (por enquanto)

```yaml
Equinix Orders:
  Justificativa: "Documentos administrativos (ordens de serviço) sem valor fiscal"
  Ação: "Manter como OUTRO sem valor - está correto"
  
Casos únicos:
  Justificativa: "Volume insuficiente para justificar desenvolvimento"
  Ação: "Correção manual quando necessário"
```

---

## Comandos para Aprofundamento Específico

```bash
# Analisar CEMIG em detalhe
grep -A5 -B5 "atendimento@cemig.com.br" data/output/analise_pdfs_detalhada.txt

# Ver todos os casos FishTV
grep -A10 "fishtv@fishtv.com" data/output/analise_pdfs_detalhada.txt

# Listar PDFs da Ufinet para análise
grep -B5 -A20 "facturacionufinet" data/output/analise_pdfs_detalhada.txt | grep "PDF:"

# Contar casos por tipo de ação recomendada
grep "Ação recomendada:" data/output/analise_pdfs_detalhada.txt | sort | uniq -c | sort -rn
```

---

## Conclusão

**Principais Achados:**
1. **70% dos problemas** são "Valor Zero" quando PDF tem valor
2. **CEMIG** é o fornecedor recorrente mais crítico (contas mensais)
3. **Ufinet** tem valor alto mas baixo volume
4. **Maioria dos erros** são ajustáveis com baixo esforço (Quick Wins)

**Investimento Recomendado:**
- Tempo total estimado: ~8-10 horas
- Casos corrigidos: ~40+ (80% dos problemáticos)
- ROI: Alto - resolve maioria dos casos recorrentes

**Próximos Passos:**
1. Executar Quick Win 1 (hoje) - ajuste DANFE/NFSE
2. Executar Quick Win 2 (amanhã) - vencimento boleto
3. Criar UfinetExtractor (esta semana)
4. Reprocessar batches afetados
5. Validar em exportação Sheets
