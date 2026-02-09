# Sessão 2026-02-06: Correções Extração de Valores (Boletos e NFSe)

## Resumo Executivo

Esta sessão focou em diagnosticar e corrigir problemas na pipeline de ingestão/extração/pareamento de documentos (NFSe, DANFE, BOLETO, e outros) que estavam causando valores incorretos no relatório `relatorio_lotes.csv`.

---

## Problemas Identificados

### 1. Faturas CEMIG com valores incorretos
- **Sintoma**: 166 de 224 faturas CEMIG (≈74%) apareciam com `valor_compra < R$ 10`
- **Causa raiz**: O extrator capturava valores parciais/tributos ao invés do "Valor a Pagar"
- **Exemplo**: Valor extraído era centavos quando deveria ser R$ 205,05

### 2. XMLs NFCom não reconhecidos
- **Sintoma**: Lotes com fornecedor vazio mesmo havendo XML com dados estruturados
- **Causa raiz**: `XmlExtractor` não tinha suporte para NFCom (Nota Fiscal de Comunicação - modelo 62)
- **Exemplo**: XMLs de MITelecom não eram processados

### 3. PDFs protegidos por senha
- **Observação**: O sistema já possui mecanismo de desbloqueio automático (`abrir_pdfplumber_com_senha` / `abrir_pypdfium_com_senha`)
- **Comportamento**: Gera candidatos de senha a partir dos CNPJs cadastrados
- **Status**: Funcionando corretamente (logs confirmam: "✅ PDF desbloqueado com senha '0692' ...")

---

## Correções Implementadas

### 1. `UtilityBillExtractor` - Padrão CEMIG
**Arquivo**: `extractors/utility_bill_extractor.py`

Adicionado padrão específico para faturas CEMIG que captura corretamente o "valor a pagar" no layout característico (padrão com MÊS/ANO + DATA + VALOR).

```python
# Novo padrão adicionado para CEMIG
# Captura: MÊS/ANO DATA_VENCIMENTO VALOR_A_PAGAR
# Ex: "JAN/26 10/02/2026 205,05"
```

### 2. `XmlExtractor` - Suporte a NFCom
**Arquivo**: `extractors/xml_extractor.py`

Adicionado suporte completo para NFCom (Nota Fiscal de Comunicação):
- Detecção do namespace `http://www.portalfiscal.inf.br/nfcom`
- Novo método `_extract_nfcom()` para extrair:
  - Fornecedor (razão social)
  - CNPJ do emitente
  - Número da NF
  - Valor total
  - Data de vencimento
- Adicionado import `datetime` necessário

---

## Estatísticas do Relatório (Antes das Correções)

| Métrica | Valor |
|---------|-------|
| Total de lotes | 1.156 |
| Status CONFERIR | 1.039 (89.9%) |
| Status CONCILIADO | 94 (8.1%) |
| Status PAREADO_FORCADO | 18 |
| Status DIVERGENTE | 5 |
| Valor compra total | R$ 9.247.384,36 |
| Valor boleto total | R$ 2.889.308,15 |
| Lotes com valor_compra = 0 | 116 |
| Lotes com valor_compra < R$ 10 | 174 |

---

## Lógica de Determinação do `valor_compra`

**Prioridade** (implementada em `BatchResult.get_valor_compra_fonte()` e `DocumentPair.to_summary()`):

1. NFS-e (maior prioridade)
2. DANFE
3. OUTROS
4. BOLETO (menor prioridade)

**Importante**: O código **não soma** valores de múltiplos documentos - utiliza apenas o primeiro valor adequado encontrado na ordem de prioridade.

---

## Validação

### Testes Executados
- Full test-suite: **639 passed, 1 skipped**
- Testes de XML e utilitários: ✅ Passaram
- Testes unitários existentes: ✅ Continuam verdes

---

## Próximos Passos Recomendados

### Reprocessamento
- [ ] Reprocessar batches problemáticos (CEMIG, fornecedor vazio) em staging
- [ ] Gerar novo `relatorio_lotes.csv` e comparar diff before/after
- [ ] Priorizar: WN TELECOM, GOX, FORGETECH, CEMIG, MITelecom/NFCom, SABESP

### Testes Adicionais
- [ ] Adicionar testes unitários para extração CEMIG (com/sem "R$")
- [ ] Adicionar testes para extração de XML NFCom
- [ ] Adicionar testes de integração para PDFs protegidos + corpo HTML

### Observabilidade
- [ ] Garantir logs informativos ("duplicata detectada", "PDF desbloqueado com senha X")
- [ ] Configurar alertas se % de CONFERIR aumentar após deploy

### Deploy
- [ ] Abrir PR com mudanças + changelog
- [ ] Deploy em staging + reprocessamento de amostras
- [ ] Se OK, deploy em produção
- [ ] Monitorar por 24-72h

---

## Notas Técnicas

### Fallback para PDFs com senha dinâmica
Para PDFs que usam senha baseada no CPF/CNPJ do titular (ex: Sabesp), o sistema possui extratores que processam o corpo do e-mail HTML como fallback.

### Diff do Relatório
Recomenda-se criar script/rotina para gerar diffs do `relatorio_lotes.csv` antes/depois do reprocessamento para validar correções de negócio.

### Monitoramento Contínuo
Considerar executar script `analyze_batch_health.py` diariamente para detecção precoce de regressões.

---

## Arquivos Modificados

| Arquivo | Tipo de Alteração |
|---------|-------------------|
| `extractors/utility_bill_extractor.py` | Adicionado padrão CEMIG |
| `extractors/xml_extractor.py` | Adicionado suporte NFCom + import datetime |

---

*Documentação gerada em: 2026-02-06*
