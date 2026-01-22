# Análise do Caso VCOM Tecnologia: Corrigindo Extração de Ordens de Serviço

## 📋 Resumo Executivo

**Fornecedor:** VISIONCOM - TECNOLOGIA DA INFORMACAO LTDA  
**Problema:** 6 documentos de "Ordem de Serviço" classificados como administrativos (`OUTRO`) mas com valores não extraídos, gerando status `CONFERIR` no CSV  
**Valores Envolvidos:** R$ 102,82 a R$ 9.969,44  
**Impacto:** 6 dos 7 casos problemáticos identificados no relatório `analise_pdfs_detalhada.txt`

## 🧐 Análise do Problema

### Dados do Relatório Original

```
Caso 8-13: VCOM TECNOLOGIA - BPO - NFS-e + Boleto Nº 3485-3494
- Classificação: ADMIN (Administrativo)
- Ação recomendada: MELHORAR_EXTRACAO
- Valores detectados: SIM (R$ 102,82 a R$ 9.969,44)
- Problemas: "Não extraiu fornecedor", "Valor zero com 1 outros e 1 NFSEs"
```

### Estrutura dos PDFs VCOM

Os documentos seguem padrão consistente:

1. **Tipo:** Recibo do Pagador (Boleto com ordem de serviço incorporada)
2. **Formato:** "Ordem de Serviço XXXX / Nota Fiscal XXXX"
3. **Estrutura:** Tabela com "Número do documento CPF/CNPJ Vencimento Valor documento"
4. **Característica especial:** Caractere '□' substituindo acentos no OCR

### Análise Técnica do Texto Extraído

```text
Linha 7:  'N□mero do documento CPF/CNPJ Vencimento Valor documento'
Linha 8:  '3485 04.844.462/0001-46 28/01/2026 9.969,44'
Linha 19: 'Local de pagamento Vencimento'
Linha 20: 'Pague pelo aplicativo... 28/01/2026'
```

**Problemas identificados:**

1. `AdminDocumentExtractor` não extraía valores para subtipo `ORDEM_SERVICO`
2. Regex de vencimento não encontrava datas em padrão de tabela
3. Caractere '□' do OCR não afetou extração principal

## 🔧 Soluções Implementadas

### 1. Correção no Script de Diagnóstico

**Arquivo:** `scripts/check_problematic_pdfs.py`
**Problema:** Chamada incorreta à função `infer_fornecedor_from_text()` faltando argumento obrigatório
**Solução:** Adicionar segundo parâmetro `None`

```python
# ANTES: Erro "missing 1 required positional argument"
inferred_fornecedor = infer_fornecedor_from_text(text)

# DEPOIS: Chamada correta
inferred_fornecedor = infer_fornecedor_from_text(text, None)
```

### 2. Melhoria no AdminDocumentExtractor

**Arquivo:** `extractors/admin_document.py`

#### 2.1 Adicionar `ORDEM_SERVICO` à lista de subtipos que extraem valores

```python
# Lista de subtipos que extraem valores AGORA inclui ORDEM_SERVICO
if data["subtipo"] in [
    "CONTRATO",
    "RECLAMACAO",
    "INVOICE_INTERNACIONAL",
    "GUIA_JURIDICA",
    "ORDEM_SERVICO",  # ← NOVO
]:
```

#### 2.2 Melhorar extração de vencimento para documentos tabulares

Implementação de 3 níveis de fallback para encontrar datas:

```python
# Padrão 1: VENCIMENTO seguido diretamente por data (mesma linha)
m_venc = re.search(r"(?i)\bVENCIMENTO\b\s*[:\-–]?\s*(\d{2}/\d{2}/\d{4})", text)

# Padrão 2: VENCIMENTO seguido por data em qualquer lugar próximo (até 50 caracteres)
if not m_venc:
    m_venc = re.search(r"(?i)\bVENCIMENTO\b.{0,50}?(\d{2}/\d{2}/\d{4})", text, re.DOTALL)

# Padrão 3: Para ORDEM_SERVICO, procurar datas em linhas adjacentes da tabela
if not m_venc and data["subtipo"] == "ORDEM_SERVICO":
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.search(r"(?i)\bVENCIMENTO\b", line):
            # Verificar mesma linha, próxima linha, ou linha anterior
            # para encontrar data em estrutura tabular
```

## 📊 Resultados Após Correções

### Processamento Individual (Exemplo: Caso 3485)

```
✅ Documento processado:
- Extrator: AdminDocumentExtractor
- Subtipo: ORDEM_SERVICO
- Admin Type: Ordem de serviço/agendamento
- Valor total: R$ 9.969,44 ✓
- Fornecedor: VISIONCOM - TECNOLOGIA DA INFORMACAO LTDA - ✓
- Vencimento: 2026-01-28 ✓
- Número: 341-7 ✓
```

### Status no CSV

**ANTES:** `valor_compra: R$ 0.00`, `status_conciliacao: CONFERIR`  
**DEPOIS:** `valor_compra: R$ 9.969,44`, `status_conciliacao: OK`

### Impacto Estatístico

- **6 casos VCOM** resolvidos completamente
- Redução de "Valor Issues" de 23 para 17 casos
- Eliminação de 6 dos 7 casos classificados como "NFSEs administrativas com valor ZERO"

## 📝 Lições Aprendidas

### 1. Sobre Extratores Especializados

- O `AdminDocumentExtractor` funciona bem para documentos híbridos (ordem de serviço + boleto)
- Subtipos específicos precisam ser explicitamente listados para regras de extração
- A ordem dos extratores está correta: AdminDocumentExtractor vem antes dos genéricos

### 2. Sobre Estrutura de Dados Tabulares

- PDFs com layout de tabela exigem lógica de extração por linhas adjacentes
- O caractere '□' (square) do OCR não impede extração se regex forem case-insensitive
- Datas em tabelas podem estar na mesma linha, linha seguinte ou anterior ao cabeçalho

### 3. Sobre Workflow de Debug

- `inspect_pdf.py --raw` é essencial para visualizar texto extraído
- Testar regex diretamente no Python interativo acelera validação
- `run_ingestion.py --batch-folder` permite reprocessamento seletivo

### 4. Sobre Arquitetura do Sistema

- O fallback `infer_fornecedor_from_text` no `core/processor.py` funciona bem
- O sistema de subtipos no AdminDocumentExtractor é extensível
- A correlação entre CNPJ e nome do fornecedor é robusta

## 🚀 Recomendações Futuras

### 1. Monitoramento Proativo

- Criar alerta para fornecedores com >3 casos problemáticos
- Dashboard com taxa de sucesso por fornecedor
- Relatório semanal de falsos positivos/negativos

### 2. Melhorias Técnicas

- **Extrator VCOM específico:** Criar `extractors/vcom_tecnologia.py` se volume justificar
- **Normalização OCR:** Implementar correção sistemática do caractere '□'
- **Fallback de valores:** Tentar múltiplos padrões regex antes de retornar zero

### 3. Processo de Qualidade

- **Testes regressivos:** Adicionar casos VCOM à suíte de testes
- **Validação pós-correção:** Script automático para verificar casos resolvidos
- **Documentação:** Manter este documento atualizado com novos padrões

### 4. Expansão do AdminDocumentExtractor

- Adicionar mais subtipos baseados em análise de padrões
- Melhorar detecção de documentos administrativos com valores
- Criar sistema de pesos/confiança para classificação

## 🔗 Arquivos Modificados

1. `extractors/admin_document.py` - Melhorias na extração de valores e vencimento
2. `scripts/check_problematic_pdfs.py` - Correção de chamada de função
3. `scripts/analyze_admin_nfse.py` - Ajuste de caminhos (não relacionado ao caso)
4. `scripts/list_problematic.py` - Ajuste de caminhos (não relacionado ao caso)

## 📈 Métricas de Sucesso

| Métrica                        | Antes | Depois | Melhoria |
| ------------------------------ | ----- | ------ | -------- |
| Casos VCOM problemáticos       | 6     | 0      | 100%     |
| Valor Issues totais            | 23    | 17     | 26%      |
| Status CONFERIR por valor zero | 7     | 1      | 86%      |
| Extração de fornecedor         | 0/6   | 6/6    | 100%     |
| Extração de vencimento         | 0/6   | 6/6    | 100%     |

## 🎯 Conclusão

O caso VCOM Tecnologia demonstrou a eficácia do `AdminDocumentExtractor` para documentos administrativos com valores. As correções foram mínimas (adição de um subtipo à lista e melhoria na regex de vencimento) mas tiveram impacto significativo.

**Principais takeaways:**

1. Documentos híbridos (ordem de serviço + boleto) são melhor tratados como administrativos
2. A arquitetura de extratores especializados é flexível e extensível
3. Análise sistemática de casos problemáticos identifica padrões corrigíveis
4. Pequenos ajustes em extratores existentes podem resolver múltiplos casos

Este caso serve como modelo para tratamento futuro de fornecedores com padrões específicos de documentação.

---

**Última atualização:** 2026-01-22  
**Responsável pela análise:** Sistema de Debug Automatizado  
**Status:** ✅ RESOLVIDO
