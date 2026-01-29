# Rastreamento de Correções entre Sessões

> **Problema:** Batch IDs (`email_YYYYMMDD_HHMMSS_hash`) são **voláteis** - mudam a cada `clean_dev` + `run_ingestion`
>
> **Solução:** Referências estáveis baseadas em características do documento, não no batch ID

---

## ⚠️ O Problema

### Cenário Problemático

```
SESSÃO 1 (29/01):
  - Identifico erro no FishTV
  - Batch afetado: email_20260129_084433_c5c04540
  - Crio extrator TunnaFaturaExtractor
  - Valido com: --batches email_20260129_084433_c5c04540
  - Registro snapshot com esse batch ID

DIA SEGUINTE - Usuário roda:
  $ python scripts/clean_dev.py        # Limpa tudo
  $ python run_ingestion.py            # Baixa emails novos

SESSÃO 2 (30/01):
  - Tento usar snapshot anterior
  - Batch email_20260129_084433_c5c04540 NÃO EXISTE MAIS!
  - Erro: "Batch não encontrado"
  - Tenho que rediagnosticar tudo → Retrabalho!
```

### Por que Isso Acontece?

| Aspecto | Batch ID | Características do Documento |
|---------|----------|------------------------------|
| **Estabilidade** | ❌ Volátil (muda a cada ingestão) | ✅ Estável (não muda) |
| **Baseado em** | Timestamp + hash aleatório | Conteúdo do documento |
| **Reproduzível?** | ❌ Não | ✅ Sim |
| **Útil para correção?** | ❌ Apenas na mesma sessão | ✅ Persiste entre sessões |

---

## ✅ A Solução: Referências Estáveis

### 1. Identificadores Estáveis

Use características que **não mudam** entre ingestões:

```yaml
Identificadores Estáveis:
  fornecedor: "TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA"
  cnpj: "12.345.678/9012-34"  # Se disponível
  tipo_documento: "OUTRO" (FATURA)
  numero_documento: "000.010.731"
  padrao_email: "faturamento@fishtv.com.br"  # Sender
  assunto_email: "Fatura de Serviços - FishTV"
  
Identificador Volátil (evitar em snapshots):
  batch_id: "email_20260129_084433_c5c04540"  # ❌ Muda a cada ingestão!
```

### 2. Como Localizar um Caso em Nova Sessão

#### Método 1: Busca por Fornecedor + Tipo

```bash
# Liste todos os batches atuais
Get-ChildItem temp_email/ -Directory | Select-Object Name

# Busque no CSV por fornecedor
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA"

# Ou busque por número de documento
Get-Content data/output/relatorio_lotes.csv | Select-String "000\.010\."
```

#### Método 2: Inspeção de Metadados

```bash
# Verifique metadata.json de cada batch recente
foreach ($batch in (Get-ChildItem temp_email/ -Directory | Select-Object -Last 10)) {
    $metadata = Get-Content "$($batch.FullName)\metadata.json" | ConvertFrom-Json
    if ($metadata.sender -like "*fishtv*" -or $metadata.subject -like "*fatura*") {
        Write-Host "Encontrado: $($batch.Name) - $($metadata.subject)"
    }
}
```

#### Método 3: Validação por Padrão (Melhor!)

```bash
# Valide usando o extrator diretamente
# Isso funciona INDEPENDENTE do batch ID

python -c "
from extractors.tunna_fatura import TunnaFaturaExtractor
import json, os

extractor = TunnaFaturaExtractor()
for batch in os.listdir('temp_email/')[:20]:
    batch_path = os.path.join('temp_email/', batch)
    if os.path.isdir(batch_path):
        for pdf in os.listdir(batch_path):
            if pdf.endswith('.pdf'):
                from strategies.pdf_utils import extract_text
                text = extract_text(os.path.join(batch_path, pdf))
                if extractor.can_handle(text):
                    print(f'ENCONTRADO: {batch} - {pdf}')
                    break
"
```

---

## 📝 Formato de Snapshot Atualizado

### ❌ Formato Antigo (Problemático)

```markdown
**Estado dos Dados:**
- **Batches processados:** email_20260129_084433_c5c04540  ❌ Não existe mais!
- **CSV:** Últimas entradas: 000.010.731, 000.010.732, 000.010.733
```

### ✅ Formato Novo (Robusto)

```markdown
**Estado dos Dados:**
- **Correção aplicada a:** Fornecedor TUNNA ENTRETENIMENTO (FATURAS FishTV)
- **Números de documento:** 000.010.731, 000.010.732, 000.010.733
- **Padrão de e-mail:** Assunto contém "Fatura de Serviços - FishTV"
- **Validação original:** 3 batches do dia 29/01 (IDs já obsoletos)

**Para reencontrar em nova sessão:**
```bash
# Busque no CSV pelo fornecedor
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA"

# Ou valide que o extrator ainda captura
python scripts/validate_extraction_rules.py --batch-mode --temp-email
```
```

---

## 🔄 Workflow Correto para Sessões Múltiplas

### Na Primeira Sessão (Quando Cria a Correção)

```markdown
1. Diagnostica problema → Identifica fornecedor + padrão
2. Cria extrator específico
3. Valida com batches atuais (usa batch IDs temporariamente)
4. **Registra snapshot com:**
   - Nome do fornecedor (estável)
   - Tipo de documento (estável)
   - Padrões de identificação (estáveis)
   - Números de documento processados (estáveis)
   - Batch IDs apenas como referência temporal ("processados em 29/01")
5. **NÃO confie em batch IDs para próxima sessão!**
```

### Na Sessão Futura (Quando Retoma)

```markdown
1. Lê snapshot anterior
2. **Ignora batch IDs antigos**
3. Busca no CSV atual pelo fornecedor/tipo
4. Ou valida extrator diretamente nos batches atuais
5. Se encontrou casos do mesmo fornecedor → Validação bem-sucedida
6. Se não encontrou → Pode ser que não haja emails novos desse fornecedor
```

---

## 🛡️ Checklist para Snapshots Resilientes

Antes de finalizar uma sessão, verifique:

- [ ] **Fornecedor** está claramente identificado?
- [ ] **Tipo de documento** foi especificado?
- [ ] **Padrões de detecção** estão documentados?
- [ ] Batch IDs são mencionados apenas como "referência histórica"?
- [ ] Comandos de busca por fornecedor/tipo estão incluídos?
- [ ] Extrator criado tem `can_handle()` robusto para reencontrar casos?

---

## 📋 Exemplo de Snapshot Robusto

```markdown
### Snapshot: 29/01/2026 - 09:30 - PAUSA_ORQUESTRACAO

**Contexto da Sessão:**
- Orquestração: Correção #1 CONCLUÍDA, #2 PENDENTE
- Tempo: ~46 minutos

**Correção #1: TunnaFaturaExtractor** ✅ CONCLUÍDA
- **Fornecedor:** TUNNA ENTRETENIMENTO E AUDIOVISUAL LTDA
- **Tipo:** FATURA COMERCIAL (tipo_documento="OUTRO", subtipo="FATURA")
- **Padrão de detecção:** "TUNNA" + "FATURA" OU "FAT/XXXXX"
- **Números processados:** 000.010.731, 000.010.732, 000.010.733
- **E-mail:** faturamento@fishtv.com.br
- **Referência temporal:** 3 batches processados em 29/01/2026

**Arquivos Criados/Modificados:**
- extractors/tunna_fatura.py (novo)
- extractors/__init__.py (ordem do registry)
- scripts/validate_extraction_rules.py (flags --temp-email, --batches)

**Validação Original:**
- 3 batches FishTV validados (IDs: email_20260129_084433_...)
- Zero regressões confirmadas

**Para Reencontrar em Nova Sessão:**
```bash
# Opção 1: Buscar no CSV por fornecedor
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA" | Select-Object -Last 5

# Opção 2: Validar extrator em todos os batches atuais
python scripts/validate_extraction_rules.py --batch-mode --temp-email

# Opção 3: Procurar por padrão de assunto nos metadados
Get-ChildItem temp_email/ | ForEach-Object { 
    $m = Get-Content "$($_.FullName)\metadata.json" | ConvertFrom-Json
    if ($m.subject -like "*FishTV*") { $_.Name }
}
```

**Decisões Importantes:**
- FishTV = FATURAS COMERCIAIS (não fiscais) → tipo="OUTRO"
- OCR corrompe "Nº" → usar regex tolerante `N[�º]?`

**Pendências:**
- Aguardar correção #2 (Vencimento em Boletos)
```

---

## 🚨 O Que NÃO Fazer

### ❌ Anti-Pattern 1: Depender de Batch IDs

```markdown
# ❌ ERRADO - Snapshot frágil
**Batches afetados:** email_20260129_084433_c5c04540

# Para validar:
python scripts/validate_extraction_rules.py --batches email_20260129_084433_c5c04540
# → Falha no dia seguinte quando ID muda!
```

### ✅ Pattern Correto: Referência por Característica

```markdown
# ✅ CERTO - Snapshot resiliente
**Fornecedor afetado:** TUNNA ENTRETENIMENTO

# Para validar:
# 1. Encontre batches atuais do fornecedor
Get-Content data/output/relatorio_lotes.csv | Select-String "TUNNA"
# → Mostra batches atuais (IDs novos)

# 2. Valide extrator
python scripts/validate_extraction_rules.py --batch-mode --temp-email
```

---

## 🔄 Atualizando Snapshots Existentes

Se você tem snapshots antigos com batch IDs, atualize-os:

```markdown
### Snapshot Antigo (a atualizar):
**Batches:** email_20260129_084433_c5c04540, email_20260129_084433_ecf8dd6f

### Atualização:
# 1. Identifique o fornecedor desses batches (no CSV antigo ou memória)
# 2. Substitua batch IDs por:
**Fornecedor:** TUNNA ENTRETENIMENTO
**Tipo:** Faturas FishTV
**Referência:** Batches processados em 29/01 (IDs: c5c04540, ecf8dd6f...)
```

---

## 💡 Recomendações Finais

### Para o Usuário (Quando Rodar Ingestão)

```bash
# Antes de rodar clean_dev + run_ingestion:
# 1. Salve uma cópia do CSV atual (para referência)
cp data/output/relatorio_lotes.csv data/output/relatorio_lotes_20260129.csv

# 2. Verifique se há orquestração em andamento
# Se sim, finalize ou documente o estado primeiro!
```

### Para o Orquestrador (Quando Retomar)

```markdown
1. SEMPRE ignore batch IDs de snapshots antigos
2. Use fornecedor + tipo para reencontrar casos
3. Se não encontrar casos do fornecedor → pode ser normal (sem emails novos)
4. Valide que o extrator ainda funciona com --batch-mode --temp-email
5. Se o extrator não capturar nada → pode ser problema ou simplesmente não há casos
```

---

**Resumo:** Batch IDs são como ponteiros de memória voláteis - usem fornecedor, tipo e padrões como "chaves primárias" estáveis para rastreamento entre sessões!
