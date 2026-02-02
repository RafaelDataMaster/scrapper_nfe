# Tratamento de PDFs Protegidos por Senha

Este documento descreve o mecanismo de tratamento de PDFs protegidos por senha e o fallback para extração via corpo do email.

## Visão Geral

O sistema possui dois mecanismos complementares para lidar com PDFs protegidos:

1. **Tentativa de Desbloqueio por Força Bruta**: Tenta abrir o PDF com senhas candidatas baseadas em CNPJs
2. **Fallback para Email Body**: Para fornecedores específicos (ex.: Sabesp), extrai dados do corpo do email quando o PDF não pode ser aberto

## 1. Desbloqueio de PDFs por Força Bruta

### Localização do Código
- **Arquivo**: `strategies/pdf_utils.py`
- **Funções principais**:
  - `gerar_candidatos_senha()`: Gera lista de senhas candidatas
  - `abrir_pdfplumber_com_senha()`: Abre PDFs com pdfplumber
  - `abrir_pypdfium_com_senha()`: Abre PDFs com pypdfium2

### Geração de Candidatos de Senha

Para cada CNPJ em `config/empresas.py`, são gerados candidatos:
- CNPJ completo (14 dígitos)
- 4 primeiros dígitos
- 5 primeiros dígitos
- 8 primeiros dígitos (raiz do CNPJ - mais comum)

```python
# Exemplo de candidatos para CNPJ 12345678000199
candidatos = ["12345678000199", "1234", "12345", "12345678"]
```

### Fluxo de Abertura

```
1. Tentar abrir sem senha
   ├─ Sucesso → Retorna PDF aberto
   └─ Falha (senha requerida) → Continua...

2. Gerar candidatos de senha (baseados em CNPJs)

3. Para cada candidato:
   ├─ Tentar abrir com senha
   ├─ Sucesso → Log INFO + Retorna PDF
   └─ Falha → Próximo candidato

4. Nenhuma senha funcionou:
   └─ Log INFO "senha desconhecida" + Retorna None
```

### Níveis de Log

| Situação | Nível | Mensagem |
|----------|-------|----------|
| PDF aberto sem senha | DEBUG | `PDF aberto sem senha (pdfplumber): arquivo.pdf` |
| PDF protegido detectado | DEBUG | `PDF arquivo.pdf: protegido por senha, tentando desbloqueio` |
| Senha encontrada | INFO | `✅ PDF desbloqueado com senha 'XXXX' (pdfplumber): arquivo.pdf` |
| Nenhuma senha funcionou | INFO | `PDF arquivo.pdf: senha desconhecida (pdfplumber)` |

## 2. Fallback para Email Body

### Quando o Fallback é Usado

O `BatchProcessor` tenta extrair dados do corpo do email quando:
1. O PDF não pôde ser processado (senha desconhecida, corrompido, etc.)
2. O email tem corpo texto/HTML disponível
3. Um extrator especializado reconhece o email

### Extratores de Email Body

| Extrator | Fornecedor | Detecta Por | Retorna |
|----------|------------|-------------|---------|
| `SabespWaterBillExtractor` | Sabesp | Sender `@sabesp.com.br` ou subject | `UTILITY_BILL` / `WATER` |
| `EmailBodyExtractor` | Genérico | Qualquer email com dados úteis | `InvoiceData` |

### Fluxo no BatchProcessor

```python
# core/batch_processor.py - _extract_from_email_body()

1. Verifica se tem corpo de email disponível
   └─ Não → Retorna None

2. Verifica se é email da Sabesp (SabespWaterBillExtractor.can_handle_email)
   ├─ Sim → Extrai com SabespWaterBillExtractor
   │        Retorna OtherDocumentData (UTILITY_BILL/WATER)
   └─ Não → Continua...

3. Tenta extrator genérico (EmailBodyExtractor)
   ├─ Encontrou valor/numero/link → Retorna InvoiceData
   └─ Não encontrou nada útil → Retorna None
```

## 3. Caso Sabesp (Exemplo Prático)

### Problema Original
- PDFs da Sabesp são protegidos com senha = 3 primeiros dígitos do CPF do titular
- CPF do titular não está disponível no sistema (apenas CNPJs de empresas)
- Resultado: PDF não pode ser aberto

### Solução Implementada
- O `SabespWaterBillExtractor` extrai todos os dados do corpo HTML do email
- O PDF é ignorado (não é necessário)
- Dados extraídos: valor, vencimento, número de fornecimento, código de barras, unidade

### Detecção de Email Sabesp

O extrator detecta emails da Sabesp por:

1. **Sender**: Contém `sabesp.com.br`, `fatura_sabesp`, `fatura.sabesp`, `noreply@sabesp`
2. **Subject**: Contém `sabesp`, `fatura por e-mail`, `sua fatura digital`
3. **Corpo** (fallback): Contém `sabesp` + `fornecimento`, ou 3+ indicadores típicos

### Dados Extraídos

```python
{
    "tipo_documento": "UTILITY_BILL",
    "subtipo": "WATER",
    "fornecedor_nome": "SABESP",
    "cnpj_fornecedor": "43.776.517/0001-80",  # Fixo
    "valor_total": 138.56,
    "vencimento": "2026-01-20",
    "numero_documento": "86040721896813",  # Número de fornecimento
    "instalacao": "86040721896813",
    "linha_digitavel": "826600000010385600970912...",
    "observacoes": "Unidade: TAUBATE"
}
```

## 4. Logging e Relatórios

### Problema de Ruído nos Relatórios

Antes da correção, o fluxo era:
1. PDF da Sabesp falha (senha desconhecida) → Log INFO
2. Email body extrai com sucesso → Log INFO
3. `analyze_logs.py` conta o PDF como "protegido por senha" → Aparece como problema

Isso gerava **falsos positivos** nos relatórios, já que a extração foi bem-sucedida.

### Solução: Ajuste de Logging

O sistema agora:
1. Quando detecta email de fornecedor com extrator de email body (ex.: Sabesp)
2. E o PDF falha por senha
3. Loga a falha do PDF com nível mais baixo (DEBUG) ou adiciona contexto indicando que email body será usado
4. O relatório de `analyze_logs.py` ignora esses casos ou os marca como "resolvidos via email"

### Verificação de Saúde

Para verificar se a extração Sabesp está funcionando:

```bash
# Buscar lotes Sabesp no CSV
grep -i "sabesp" data/output/relatorio_lotes.csv

# Verificar documentos WATER
python -c "
import pandas as pd
df = pd.read_csv('data/output/relatorio_consolidado.csv', sep=';')
sabesp = df[df['subtipo']=='WATER']
print(sabesp[['fornecedor_nome','valor_total','vencimento']].head(10))
"
```

## 5. Adicionando Suporte para Novos Fornecedores

Se um novo fornecedor também envia PDFs protegidos com dados no email:

### Passo 1: Criar Extrator Especializado

```python
# extractors/novo_fornecedor.py

class NovoFornecedorExtractor:
    @classmethod
    def can_handle_email(cls, email_subject, email_sender, email_body):
        # Lógica de detecção
        pass
    
    def extract(self, email_body, email_subject, email_sender):
        # Lógica de extração
        return {"tipo_documento": "...", "valor_total": ...}
```

### Passo 2: Registrar no BatchProcessor

```python
# core/batch_processor.py - _extract_from_email_body()

# Adicionar antes do EmailBodyExtractor genérico:
from extractors.novo_fornecedor import NovoFornecedorExtractor

if NovoFornecedorExtractor.can_handle_email(...):
    extractor = NovoFornecedorExtractor()
    data = extractor.extract(...)
    # Criar documento e retornar
```

### Passo 3: Criar Testes

```python
# tests/test_novo_fornecedor_extractor.py
```

## 6. Arquivos Relacionados

| Arquivo | Propósito |
|---------|-----------|
| `strategies/pdf_utils.py` | Funções de desbloqueio de PDF |
| `extractors/sabesp.py` | Extrator Sabesp via email body |
| `extractors/email_body_extractor.py` | Extrator genérico de email body |
| `core/batch_processor.py` | Orquestra extração (PDF → email body fallback) |
| `config/empresas.py` | CNPJs usados para gerar candidatos de senha |
| `scripts/analyze_logs.py` | Análise de logs (conta PDFs protegidos) |

## 7. Troubleshooting

### PDF não abre mesmo com CNPJ cadastrado

1. Verificar se o CNPJ está em `config/empresas.py`
2. Verificar se a senha usa formato diferente (ex.: CPF ao invés de CNPJ)
3. Considerar criar extrator de email body se os dados estiverem disponíveis

### Extração Sabesp retorna valores zerados

1. Verificar se o corpo do email está sendo capturado (`email_body_text`)
2. Verificar se o formato HTML mudou (ajustar regex em `SabespWaterBillExtractor`)
3. Inspecionar email com `scripts/inspect_pdf.py --batch <batch_id>`

### Relatório mostra muitos "PDFs protegidos" mesmo com extração OK

1. Verificar se o fornecedor tem extrator de email body
2. Ajustar logging para não contar como erro quando email body funciona
3. Verificar se `analyze_logs.py` está filtrando corretamente
