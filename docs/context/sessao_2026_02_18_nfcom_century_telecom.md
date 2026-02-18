# Sessão 2026-02-18: Correção NFComExtractor para Century Telecom

## Resumo

Análise de saúde do `relatorio_lotes.csv` identificou falsos positivos e um erro real de extração no layout NFCom da Century Telecom. Correção aplicada no `NFComExtractor`.

---

## Problemas Analisados

### 1. GOX S.A. - 40 casos "NF sem valor encontrada" ❌ NÃO É ERRO

**Diagnóstico:** Falso positivo - não é erro de extração.

**Causa:** GOX envia apenas boleto por e-mail, sem NF/NFSE anexa. O sistema espera uma NF para comparar com o boleto, mas ela não existe.

**Evidência:**
```
📁 Lote: email_20260218_075519_d3908742_bol_2041163
   Status: CONFERIR
   Divergência: Conferir boleto (R$ 630.00) - NF sem valor encontrada
   DANFEs: 0 | Boletos: 1 | NFSEs: 0 | Outros: 0
```

**Ação:** Caso de negócio - considerar como `SEM_NF` ou ajustar lógica de conciliação para fornecedores que só enviam boleto.

---

### 2. Century Telecom - 6 casos NFCom sem valor ✅ CORRIGIDO

**Diagnóstico:** Erro real de extração - layout NFCom diferente não reconhecido.

**Causa:** O `NFComExtractor` não tinha padrões para o layout específico da Century Telecom:
- Valor: `TOTAL A PAGAR 483,38` (sem R$)
- Número: `N. 7.731 - SÉRIE 1` 
- Fornecedor: Nome na primeira linha do documento
- CNPJ: Após `CNPJ/CPF INSCRIÇÃO ESTADUAL`

**Layout Century Telecom (NFCom):**
```
Century Telecom LTDA
RUA ALICE TERAIAMA N.121
Bairro Pilar,BELO HORIZONTE - MG
Fone: (31) 3514-7800, CEP:30390090
CNPJ/CPF INSCRIÇÃO ESTADUAL
01.492.641/0001-73 0622450600042
Documento Auxiliar da Nota Fiscal Fatura de Serviços de Comunicação Eletrônica
...
N. 7.731 - SÉRIE 1
...
VENCIMENTO 05/02/2026
TOTAL A PAGAR 483,38
...
VALOR TOTAL DA NOTA
0,00 0,00 483,38
```

**Correção Aplicada:** `extractors/nfcom.py`

```python
# _extract_numero_nota - novo padrão
r"(?i)\bN\.\s*(\d+(?:\.\d+)*)\s*-\s*S[ÉE]RIE"

# _extract_valor_total - novos padrões
r"(?i)TOTAL\s+A\s+PAGAR\s+(\d{1,3}(?:\.\d{3})*,\d{2})"
r"(?i)VALOR\s+TOTAL\s+DA\s+NOTA\s+[\d,]+\s+[\d,]+\s+(\d{1,3}(?:\.\d{3})*,\d{2})"

# _extract_cnpj_prestador - novos padrões
r"(?i)CNPJ/CPF\s+INSCRI[ÇC][ÃA]O\s+ESTADUAL\s*\n?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})"
r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})"  # fallback

# _extract_fornecedor_nome - novo padrão
r"^([A-ZÀ-Ú][A-Za-zÀ-ú0-9\s\-\.]+(?:LTDA|S\.?A\.?|ME|EPP|EIRELI))\s*$"
```

**Resultado após correção:**
```
📄 05_Nota_fiscal_7731.pdf
   Número: 7.731
   Valor: R$ 483.38
   Fornecedor: Century Telecom LTDA
   Vencimento: 2026-02-05

📄 06_Nota_fiscal_7780.pdf
   Número: 7.780
   Valor: R$ 208.76
   Fornecedor: Century Telecom LTDA

📄 07_Nota_fiscal_7792.pdf
   Número: 7.792
   Valor: R$ 444.42
   Fornecedor: Century Telecom LTDA

📄 08_Nota_fiscal_7804.pdf
   Número: 7.804
   Valor: R$ 1323.68
   Fornecedor: Century Telecom LTDA
```

**Status:** ✅ Aplicado e verificado

---

### 3. LOCALIZA RENT A CAR - 2 casos ❌ NÃO É ERRO

**Diagnóstico:** Classificação incorreta - documento não é NF.

**Causa:** O arquivo `demonstrativo.pdf` é um **Demonstrativo de Locação de Veículo** (contrato interno da Localiza), não uma NF/NFSE. O sistema está classificando como NFSE incorretamente.

**Exemplo de conteúdo:**
```
Contrato de Aluguel de Carros/Proposta de Seguro N° UMCF009245
Fechado
ACIMOC-16362
Empresa: 15275650 MOC COMUNICACAO S/A
...
Demonstrativo de Valores: Valor Unitário Desconto (%) ...
TOTAL GERAL 1345,51
```

**Ação:** Melhorar classificação no `OutrosExtractor` ou criar filtro para documentos de locação de veículo.

---

## Métricas da Análise

| Categoria | Quantidade | % do Total |
|-----------|------------|------------|
| Total de lotes | 1.419 | 100% |
| CONCILIADO | 131 | 9.2% |
| CONFERIR | 1.263 | 89.0% |
| PAREADO_FORCADO | 19 | 1.3% |
| DIVERGENTE | 6 | 0.4% |

### Categorias de Divergência

| Problema | Ocorrências | % |
|----------|-------------|---|
| Sem boleto para comparação | 882 | 62.2% |
| Documento genérico | 438 | 30.9% |
| NF sem valor encontrada | 371 | 26.1% |
| Vencimento não encontrado | 338 | 23.8% |
| Documento administrativo | 95 | 6.7% |

### Top Fornecedores com Problemas

1. **CEMIG DISTRIBUIÇÃO S.A.** — 251 lotes
2. **SEMPRE TELECOMUNICACOES LTDA** — 47 lotes
3. **GOX S.A.** — 40 lotes
4. **EDP São Paulo** — 31 lotes
5. **PITTSBURG FIP MULTIESTRATEGIA** — 30 lotes

---

## Arquivos Modificados

| Arquivo | Alteração |
|---------|-----------|
| `extractors/nfcom.py` | Novos padrões para layout Century Telecom |

---

## Lições Aprendidas

### 1. NFCom tem layouts muito variados
Cada operadora de telecom pode ter um layout NFCom diferente. O `NFComExtractor` precisa ser flexível:
- Valor pode estar com ou sem `R$`
- Número da nota pode ter formatos como `N. X.XXX - SÉRIE Y`
- Fornecedor pode estar na primeira linha (sem label)

### 2. "NF sem valor" nem sempre é erro de extração
Muitos casos são:
- Fornecedor que só envia boleto (GOX)
- Documento classificado incorretamente (demonstrativos LOCALIZA)
- Documento administrativo/não-fiscal

### 3. Analisar batch real antes de corrigir
Sempre verificar o PDF original antes de assumir que é erro do extrator:
```bash
# Ver arquivos do batch
ls temp_email/email_XXXXXXXXX/

# Extrair texto do PDF
python -c "import pdfplumber; print(pdfplumber.open('arquivo.pdf').pages[0].extract_text())"
```

---

## Próximos Passos

1. **Reprocessar lotes Century Telecom** para aplicar correção
2. **Investigar CEMIG** (251 casos) - maior volume de problemas
3. **Considerar status `SEM_NF`** para fornecedores que só enviam boleto

---

## Comandos Úteis

```bash
# Testar extrator NFCom em um PDF
python -c "
import pdfplumber
from extractors.nfcom import NFComExtractor

with pdfplumber.open('arquivo.pdf') as pdf:
    text = ''.join(p.extract_text() or '' for p in pdf.pages)

print('can_handle:', NFComExtractor.can_handle(text))
print(NFComExtractor().extract(text))
"

# Verificar batches de um fornecedor
python -c "
import pandas as pd
df = pd.read_csv('data/output/relatorio_lotes.csv', sep=';')
print(df[df['fornecedor'].str.contains('FORNECEDOR', na=False)][['batch_id', 'divergencia', 'valor_compra']])
"
```

---

*Sessão realizada em 18/02/2026*
