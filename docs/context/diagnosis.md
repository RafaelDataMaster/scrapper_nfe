# Prompt: Diagnóstico Rápido de Caso Problemático

> **Uso:** Execute este prompt quando identificar um caso específico com problema no `relatorio_lotes.csv` ou `analise_pdfs_detalhada.txt`
> 
> **Ferramentas:** `scripts/inspect_pdf.py`, `scripts/check_problematic_pdfs.py`, `scripts/analyze_logs.py --batch <id>`

---

## Input do Caso (preencha com os dados do CSV/análise)

```yaml
CASO_ID: #[número do caso na análise, ex: CASO #220]
BATCH_ID: #[ex: email_20260129_084433_5fafb989]
PASTA_FONTE: #[ex: temp_email/email_20260129_084433_5fafb989]

# Dados do CSV relatorio_lotes.csv:
CSV_STATUS:
  outros: #[quantidade de documentos tipo OUTRO]
  nfses: #[quantidade de NFSEs]
  valor_total: #[ex: R$ 0.00]
  fornecedor: #[ex: "TCF Telecom"]
  vencimento: #[ex: "" ou "2026-01-15"]
  numero_nota: #[ex: "" ou "521912"]
  email_subject: #[assunto do email]
  email_sender: #[remetente]

# Problema identificado:
PROBLEMA_TIPO: #[ESCOLHA UM]
  - [ ] Valor zero mas PDF tem valor
  - [ ] Número da nota não extraído
  - [ ] Vencimento não extraído
  - [ ] Fornecedor incorreto/genérico
  - [ ] Classificado como OUTRO mas é NFSE/Boleto
  - [ ] Classificado como NFSE mas é OUTRO
  - [ ] Nenhum extrator compatível

# Arquivos PDF no batch (listar nomes):
PDFS:
  - #[ex: 01_nota_fiscal_tipo0_n521912_c128326_1767712922.pdf]
  - #[ex: 02_boleto_12345.pdf]
```

---

## Scripts de Diagnóstico (execute antes deste prompt)

Execute estes comandos no terminal para coletar dados:

```bash
# 1. Inspecionar o batch completo
python scripts/inspect_pdf.py --batch <BATCH_ID>

# 2. Ver texto bruto de um PDF específico
python scripts/inspect_pdf.py <nome_pdf.pdf> --raw > temp_diagnostico.txt

# 3. Analisar logs específicos do batch (se houver)
python scripts/analyze_logs.py --batch <BATCH_ID>

# 4. Verificar correlação NF↔Boleto no CSV
python scripts/check_problematic_pdfs.py --csv data/output/relatorio_lotes.csv
```

---

## Template de Resposta Esperada

### 1. ANÁLISE VISUAL DOS PDFs

**Para cada PDF no batch:**

| Arquivo | Páginas | Texto (chars) | Classificação Sugerida | Valores Detectados |
|---------|---------|---------------|------------------------|-------------------|
| #[nome] | #[n] | #[chars] | #[NFSE/Boleto/Admin/Desconhecido] | #[R$ X,XX] |

### 2. TESTE DE EXTRATORES

**Ordem de prioridade dos extratores:**

```
#[Priority] [Extrator Name]                 [Status]
00          BoletoRepromaqExtractor          [OK] SELECIONADO / [X] Não compatível
01          EmcFaturaExtractor               [OK] SELECIONADO / [X] Não compatível
...
15          DanfeExtractor                   [OK] SELECIONADO / [X] Não compatível
```

### 3. DIAGNÓSTICO TÉCNICO DETALHADO

#### Campo Problemático: #[VALOR/NÚMERO/VENCIMENTO/FORNECEDOR/TIPO]

**O que deveria ter sido extraído:**
```
#[Valor correto esperado, ex: R$ 700,00]
#[Local no PDF onde aparece, ex: "Valor Total: R$ 700,00" na seção inferior]
```

**O que foi extraído:**
```
#[Valor incorreto ou ausente]
```

**Análise do texto bruto (trechos relevantes):**
```
#[Cole aqui os trechos do texto bruto que contêm a informação]
#[Ex: "Valor Total R$ 700,00" vs "Valor dos Serviços R$ 0,00"]
```

**Causa raiz identificada:**
- [ ] Regex não captura variação de layout (padrão diferente)
- [ ] OCR falhou (PDF em imagem, texto ilegível)
- [ ] Roteamento errado (extrator genérico selecionado antes do específico)
- [ ] Padrão negativo bloqueando (extrator recusou documento válido)
- [ ] Campo não existe no PDF (documento administrativo sem valor)
- [ ] Múltiplos valores conflitantes (sistema pegou o menor/maior errado)

### 4. MATRIZ DE IMPACTO

| Critério | Avaliação |
|----------|-----------|
| **Severidade** | #[ALTA/MÉDIA/BAIXA] |
| **Frequência** | #[Único/Padrão frequente/Episódico] |
| **Bloqueia exportação Sheets** | #[Sim/Não] |
| **Afeta conciliação NF↔Boleto** | #[Sim/Não] |
| **Impacto financeiro** | #[Valor estimado ou "N/A"] |

### 5. AÇÃO RECOMENDADA

#### Opção A: Ajustar Extrator Existente
```yaml
Arquivo: #[extractors/nome_extrator.py]
Método: #[_extract_valor / _extract_numero_nota / can_handle]
Mudança: #[Descrição da alteração no regex ou lógica]
Regex Atual: #[padrão atual que falha]
Regex Sugerido: #[novo padrão proposto]
Testes: #[Lista de casos que devem passar]
```

#### Opção B: Criar Novo Extrator Específico
```yaml
Prioridade: #[1-15 - posição no registry]
Classe: #[NomeDoExtrator]
Padrão identificador: #[CNPJ único, termo específico, etc.]
Campos especiais: #[lista de campos com padrões únicos]
```

#### Opção C: Correção Manual/Dados
```yaml
Justificativa: #[Por que não vale automatizar]
Ação manual: #[O que fazer com este caso específico]
```

### 6. VALIDAÇÃO PÓS-CORREÇÃO

**Como testar a correção:**

```bash
# 1. Testar o PDF específico após alterações
python scripts/inspect_pdf.py <nome_pdf.pdf>

# 2. Reprocessar o batch específico
python run_ingestion.py --batch-folder <PASTA_FONTE>

# 3. Verificar CSV de saída
grep <BATCH_ID> data/output/relatorio_lotes.csv

# 4. Validar exportação para Sheets (dry-run)
python scripts/export_to_sheets.py --dry-run
```

**Critérios de aceitação:**
- [ ] Valor extraído correto: #[R$ X,XX]
- [ ] Número da nota extraído: #[número]
- [ ] Vencimento extraído: #[data]
- [ ] Fornecedor correto: #[nome]
- [ ] Tipo classificado corretamente
- [ ] Correlação NF↔Boleto funcionando (se aplicável)
- [ ] Não quebra outros casos existentes

---

## Notas de Debug

**Para casos de VALOR ZERO com NFSE:**
- Verificar se há múltiplos valores no PDF (ex: R$ 0,00, R$ 0,00, R$ 700,00)
- O sistema pode estar pegando o primeiro valor ao invés do maior/correto
- Padrão comum: "Valor dos Serviços R$ 0,00" vs "Valor Total R$ 700,00"

**Para casos de VENCIMENTO VAZIO:**
- Verificar se o PDF tem formato de data diferente (DD/MM/AAAA vs AAAA-MM-DD)
- Documentos administrativos geralmente não têm vencimento
- Boletos têm vencimento embutido na linha digitável (códigos 40-44)

**Para casos de CLASSIFICAÇÃO ERRADA:**
- Verificar a ordem dos extratores no `extractors/__init__.py`
- Extratores específicos devem vir ANTES dos genéricos
- Verificar padrões negativos no `can_handle()` que podem estar bloqueando

**Para casos de FORNECEDOR GENÉRICO:**
- Padrões como "CNPJ FORNECEDOR", "FORNECEDOR", "CPF Fornecedor:" indicam falha
- Verificar se o extrator está pegando o campo antes do valor ser preenchido
- Empresas internas (CSC, RBC, MOC, etc.) não devem ser fornecedores

---

## Após Identificar a Causa

### Se Precisar Criar/Ajustar Extrator

Ao implementar a correção, siga os padrões do projeto:

1. **Para novo extrator:** Use [`creation.md`](./creation.md) + [`coding_standards.md`](./coding_standards.md)
2. **Para ajuste simples:** Mantenha consistência com o código existente
3. **Sempre:**
   - Type hints obrigatórios
   - Docstrings nos métodos públicos
   - Valide com `basedpyright`
   - Teste regressão com `validate_extraction_rules.py`
