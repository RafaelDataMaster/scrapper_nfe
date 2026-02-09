# Sessão 2026-02-05/06 - Timeout em PDFs (RESOLVIDO)

## Status: ✅ RESOLVIDO

---

## Contexto da Sessão

### O que foi feito (05/02/2026)

1. **Criado `TIMFaturaExtractor`** - Novo extrator para faturas da TIM S.A.
2. **Corrigido `pdf_utils.py`** - PDFs protegidos com `PdfminerException` sem mensagem agora são detectados corretamente
3. **Ajustada ordem de prioridade** - `TIMFaturaExtractor` vem antes de `NfseCustomMontesClaros` e `UtilityBillExtractor`
4. **Testes atualizados** - 636 passed, 1 skipped

### Problema encontrado (05/02/2026)

Durante reprocessamento, timeout de 90s em arquivos PDF.

---

## ✅ PROBLEMA RESOLVIDO (06/02/2026)

### Causa Real Identificada

O problema **NÃO era o `BoletoExtractor`** com backtracking catastrófico de regex.

A causa real era o `abrir_pdfplumber_com_senha()` em `pdf_utils.py` que:

1. Tentava `extract_text()` para verificar se o PDF abriu corretamente
2. Para PDFs com elementos vetoriais complexos (como QR codes), o `pdfminer` travava processando milhares de operações de desenho
3. Se o PDF era escaneado (sem texto nativo), o código interpretava como "pode ser protegido por senha" e entrava no loop de 234 candidatos de senha
4. Para cada candidato, tentava `extract_text()` novamente (potencialmente travando cada vez)

### Arquivo Problemático

- **Batch:** `email_20260205_131749_6cb7ddf4`
- **Arquivo:** `01_csc_boleto.pdf` (223KB)
- **Tipo:** Boleto do Banco Inter emitido pela Partners RL para CSC Gestão
- **Característica:** PDF com imagem escaneada + QR Code vetorial complexo

### Solução Implementada

Correção em `scrapper/strategies/pdf_utils.py`:

```python
# ANTES (problemático):
pdf = pdfplumber.open(file_path)
if pdf.pages:
    test_text = pdf.pages[0].extract_text()  # TRAVAVA AQUI!
    if test_text and len(test_text.strip()) > 10:
        return pdf
    else:
        pdf.close()  # Entrava no loop de senhas desnecessariamente

# DEPOIS (corrigido):
pdf = pdfplumber.open(file_path)
if pdf.pages:
    # Não tenta extract_text() - apenas verifica se abriu
    # Se for escaneado, a estratégia de extração usará OCR posteriormente
    return pdf
```

### Resultado

| Métrica              | Antes          | Depois               |
| -------------------- | -------------- | -------------------- |
| Tempo para abrir PDF | 90s+ (timeout) | 0.01s                |
| Testes passando      | N/A            | 636 passed           |
| Extração do boleto   | Timeout        | Sucesso (OCR em ~4s) |

### Campos Extraídos Corretamente

| Campo             | Valor                                                  |
| ----------------- | ------------------------------------------------------ |
| tipo_documento    | BOLETO                                                 |
| cnpj_beneficiario | 28.380.247/0001-08                                     |
| fornecedor_nome   | PARTNERS RL SOLUCOES EM TECNOLOGIA LTDA                |
| empresa           | CSC                                                    |
| vencimento        | 2026-01-23                                             |
| valor_documento   | R$ 750,00                                              |
| banco_nome        | BANCO INTER S.A.                                       |
| linha_digitavel   | 07790.00116 12016.798097 05560.207440 1 13350000075000 |

---

## Lições Aprendidas

1. **Não assumir que PDFs sem texto são protegidos por senha** - podem ser apenas escaneados
2. **Evitar `extract_text()` para validação** - pode travar em PDFs com elementos vetoriais complexos
3. **QR Codes em PDF** - geram milhares de operações de desenho que o pdfminer processa lentamente
4. **Diagnóstico incremental** - testar cada componente isoladamente para identificar o gargalo real

---

## Arquivos Modificados

### `scrapper/strategies/pdf_utils.py`

- Removido `extract_text()` do fluxo de verificação de abertura
- PDF que abre sem erro é retornado imediatamente
- PDFs escaneados são tratados pela estratégia de extração (OCR) posteriormente

---

## Próximos Passos (Opcional)

### Melhorias Futuras (baixa prioridade)

1. **Limpar nome do fornecedor OCR** - O OCR captura ruído do logo do banco ("y ] ntetr -" antes do nome)
2. **Criar extrator específico para Banco Inter** - Otimizar extração de boletos Inter se necessário
3. **Monitorar** - Verificar se há outros PDFs com comportamento similar

### Não é mais necessário

- ~~Criar `CscBoletoExtractor` específico~~ - O `BoletoExtractor` genérico funciona corretamente
- ~~Refatorar regex do `BoletoExtractor`~~ - Os regex não eram o problema

---

## Commits/Alterações

### 06/02/2026

- `scrapper/strategies/pdf_utils.py` - Fix: não usar extract_text() para validação de abertura

### 05/02/2026

- `scrapper/extractors/tim_fatura_extractor.py` - CRIADO
- `scrapper/strategies/pdf_utils.py` - Detecção de PdfminerException sem mensagem
- `scrapper/extractors/__init__.py` - Ordem de imports alterada

---

## Status dos Testes

- ✅ 636 passed, 1 skipped
- ✅ Reprocessamento do batch problemático: SUCESSO
