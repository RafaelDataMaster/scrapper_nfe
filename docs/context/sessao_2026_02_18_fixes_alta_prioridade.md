# Sessão 2026-02-18: Correções de Alta Prioridade

## Resumo

Esta sessão implementou as 3 correções de alta prioridade identificadas na análise de saúde do `relatorio_lotes.csv`:

1. **Fix 1**: Melhorar extração de fornecedor em boletos (filtrar headers/labels/endereços)
2. **Fix 2**: Suporte para boletos com beneficiário pessoa física (CPF)
3. **Fix 3**: Agregação de múltiplas NFs para pareamento com boleto único

## Arquivos Modificados

### 1. `scrapper/extractors/boleto.py`

#### Mudanças em `_looks_like_header_or_label()` (L334-460)

Expandida a lista de tokens que indicam que a string capturada NÃO é um nome de fornecedor válido:

- **Avisos de cobrança**: "DIAS VENCIDO", "SERÁ SUSPENSO", "SPC/SERASA", etc.
- **Labels simples**: "BENEFICIÁRIO", "CEDENTE", "SACADO", "PAGADOR"
- **Prefixos de endereço**: "RUA ", "AVENIDA ", "AV ", "TRAVESSA ", etc.
- **Padrões OCR corrompidos**: "= CNPJ", "| CNPJ", "- CNPJ"
- **Frases de contrato**: "AO ASSINAR", "DECLARO QUE"

Adicionada validação para padrões específicos:

- UF + "CNPJ" (ex: "MG CNPJ")
- "Beneficiário" colado com nome (ex: "BeneficiárioREPROMAQ")

#### Nova função `_looks_like_address()` (L1400-1456)

Detecta quando a string capturada é um endereço e não um nome de empresa:

```python
def _looks_like_address(self, s: str) -> bool:
    # Detecta prefixos de endereço (RUA, AVENIDA, etc.)
    # Detecta padrões de CEP, número, bairro, UF
    # Evita capturar endereços como nome de fornecedor
```

#### Melhorias em `_extract_cnpj_beneficiario()` (L682-737)

Agora suporta extração de CPF além de CNPJ:

- Busca CPF após "Beneficiário" ou "Cedente"
- Fallback para qualquer CPF no documento

#### Nova função `_extract_cpf_beneficiario()` (L721-737)

Extrai CPF de beneficiário pessoa física para boletos de pessoas físicas.

#### Melhorias em `_extract_fornecedor_nome()` (L1396-1450)

Adicionado fallback para pessoa física:

- Busca nome na mesma linha do CPF
- Padrão "Beneficiário <NOME> CPF <cpf>"
- Padrão "Cedente <NOME> <cpf>"

### 2. `scrapper/extractors/utils.py`

#### Melhorias em `normalize_entity_name()` (L496-680)

**Novos prefixos removidos:**

```python
r"^CNPJ\s*[:\s]*",  # "CNPJ" ou "CNPJ:" sozinho no início
r"^CPF\s*[:\s]*",   # "CPF" ou "CPF:" sozinho no início
```

**Novos sufixos removidos:**

```python
r"\s+CPF/CNPJ\s*$",
r"\s+\|\s+CNL\.\s*$",  # "| CNL." (ex: VERO S.A. CNL.)
r"\s+CNL\.\s*$",
r"\s+=\s+CNPJ\s*$",
r"\s+Endereço\s*$",
r"\s+CNPJ:\s*Al\s+.*$",  # Texto truncado
r"\s+ao\s+assinar\s*$",
r"\s+Gerente\s+de\s+conta:.*$",
r"\s+\*{4,}/\*{4,}\s*$",  # CNPJ mascarado
r"\s+\d{3,4}[-/]?\d*\s*$",  # Códigos de agência
```

**Novas limpezas pós-processamento:**

- Remove código de agência/conta no final (3-4 dígitos)
- Remove CNPJ mascarado (**\*\***/**\*\*\*\***)
- Remove padrão "| CNPJ..." no final
- Remove "= CNPJ" no final
- Remove "CNL." ou "| CNL." no final

### 3. `scrapper/core/document_pairing.py`

#### Melhorias em `_parear_notas_boletos()` (L703-812)

Adicionada Fase 2 de pareamento: **Agregação de NFs**

Quando há múltiplas NFs órfãs e um boleto órfão, tenta agregar:

- Soma os valores de todas as NFs órfãs
- Se a soma bate com o valor do boleto (dentro da tolerância), cria par agregado

#### Nova função `_try_aggregate_nfs_for_boleto()` (L814-887)

```python
def _try_aggregate_nfs_for_boleto(
    self,
    notas_orfas: Dict[str, Dict[str, Any]],
    boletos_orfaos: Dict[str, Dict[str, Any]],
    batch: "BatchResult",
) -> List[DocumentPair]:
    """
    Agrega múltiplas NFs para parear com boleto único.

    Caso de uso: Email com NF R$360 + NF R$240 e boleto R$600.
    Soma das NFs (360+240=600) bate com o boleto.
    """
```

Características:

- Só ativa quando há 2+ notas órfãs e exatamente 1 boleto órfão
- Cria número combinado (ex: "NF1+NF2")
- Marca na divergência que são NFs agregadas
- Usa sufixo "\_agregado" no pair_id

## Casos Corrigidos

### Fornecedores Inválidos (antes → depois)

| Antes                                              | Depois             |
| -------------------------------------------------- | ------------------ |
| "APÓS 15 DIAS VENCIDO, O SERVIÇO SERÁ SUSPENSO..." | `None` (rejeitado) |
| "CPF/CNPJ"                                         | `None` (rejeitado) |
| "MG CNPJ"                                          | `None` (rejeitado) |
| "RUA CAPITAO MENEZES, 68 - CENTRO (NEPOMUCENO/MG)" | `None` (rejeitado) |
| "VERO S.A. CNL. \| CNPJ"                           | "VERO S.A."        |
| "BeneficiárioREPROMAQ..."                          | "REPROMAQ..."      |
| "Skymail LTDA 393"                                 | "Skymail LTDA"     |
| "EMPRESA... **\*\***/**\*\*\*\***"                 | "EMPRESA..."       |

### Boletos Pessoa Física

Agora extrai corretamente nome de beneficiário quando o documento tem CPF em vez de CNPJ.

### Agregação de NFs

Exemplo: Email com documentos:

- NFCom R$360 (WN TELECOM)
- NFS-e R$240 (WN TELECOM)
- Boleto R$600

**Antes**: Criava 2 pares separados, boleto ficava órfão ou pareado com apenas uma NF.

**Depois**: Cria 1 par agregado com valor_nf=600, valor_boleto=600, status=CONCILIADO.

## Testes

Todos os 639 testes existentes passaram após as mudanças:

```
===== 639 passed, 1 skipped, 2 subtests passed in 6.85s =====
```

## Correções de Prioridade Média (Implementadas)

### Item 4: Melhorar Classificação de Documentos Administrativos

**Arquivo**: `extractors/admin_document.py`

Adicionados novos padrões no `AdminDocumentExtractor.can_handle()` para capturar documentos que estavam sendo classificados incorretamente como NF/NFSE:

**Novos padrões de contrato:**

- `CONTRATO DE ALUGUEL`
- `CONTRATO DE LOCAÇÃO`
- `CONTRATO DE PRESTAÇÃO`
- `CONTRATO DE SERVIÇO`

**Novos padrões de demonstrativos:**

- `DEMONSTRATIVO DE PAGAMENTO`
- `DEMONSTRATIVO DE FATURAMENTO`
- `DEMONSTRATIVO DE SERVIÇOS` (exceto locação)
- `DEMONSTRATIVO FINANCEIRO/MENSAL/DETALHADO`

**Novos padrões de propostas:**

- `PROPOSTA COMERCIAL`
- `PROPOSTA DE SERVIÇO`
- `PROPOSTA TÉCNICA`
- `ORÇAMENTO`

**Novos padrões de termos/acordos:**

- `TERMO DE ACEITE/ADESÃO/COMPROMISSO/RESPONSABILIDADE`
- `ACORDO DE NÍVEL DE SERVIÇO`
- `SLA`

**Novos padrões de atestados/relatórios:**

- `ATESTADO DE CAPACIDADE/TÉCNICO`
- `DECLARAÇÃO DE SERVIÇOS`
- `RELATÓRIO DE ATIVIDADES/MENSAL/TÉCNICO`

**NOTA**: `DEMONSTRATIVO DE LOCAÇÃO` foi excluído pois é documento fiscal válido (recibo de aluguel).

### Item 5: Fallback para Email Body (PDFs Protegidos)

**Status**: Já implementado anteriormente!

O `BatchProcessor` já possui lógica para:

1. Detectar emails da Sabesp (PDF protegido por senha)
2. Usar `SabespWaterBillExtractor` para extrair dados do corpo HTML do email
3. Fallback genérico via `EmailBodyExtractor` para outros casos

Condição de ativação (L242-251 em `batch_processor.py`):

- Se não há documento válido do PDF (com fornecedor ou valor > 0)
- Então extrai dados do corpo do email

### Melhorias Adicionais na Extração de Fornecedor

**Arquivo**: `extractors/boleto.py` - `_looks_like_header_or_label()`

Adicionados mais tokens para rejeitar strings inválidas:

- Cabeçalhos de documentos: "DOCUMENTO AUXILIAR", "NOTA FISCAL FATURA", "DADOS DA CONTRATANTE"
- Avisos: "ESTE DOCUMENTO NÃO", "NÃO QUITA", "DÉBITOS ANTERIORES"
- Labels: "RAZÃO SOCIAL", "NOME EMPRESARIAL", "UTILIDADE"
- Padrões específicos: strings que terminam com "CPF/CNPJ", "CNPJ" solto, etc.

**Arquivo**: `extractors/utils.py` - `normalize_entity_name()`

Adicionadas mais limpezas de sufixos:

- `CPF/CNPJ` no final
- `CPF` ou `CNPJ` solto no final
- Lixo OCR tipo "CNPJ . .61"
- `Nome Empresarial` no final

## Resultados Após Reprocessamento

**Antes das correções:**

- CONFERIR: 1,263 (89.0%)
- CONCILIADO: 131 (9.2%)
- PAREADO_FORCADO: 19 (1.3%)
- DIVERGENTE: 6 (0.4%)

**Após correções de alta prioridade:**

- CONFERIR: 1,281 (88.4%)
- **CONCILIADO: 145 (10.0%)** ← +14 casos!
- PAREADO_FORCADO: 16 (1.1%)
- DIVERGENTE: 6 (0.4%)

**Fornecedores corrigidos:**

- "VERO S.A. CNL. | CNPJ" → "VERO S.A."
- "FORGETECH... Endereço" → "FORGETECH..."
- "ZA D M = CNPJ" → "ZA D M"
- "Skymail LTDA 393" → "Skymail LTDA"

## Próximos Passos

### Prioridade Baixa

6. Reprocessar lotes para aplicar correções de média prioridade
7. Adicionar testes específicos para novos padrões de AdminDocument
8. Revisar fornecedores problemáticos restantes (~20 casos)

## Comandos Úteis

```bash
# Rodar testes
python -m pytest tests/ -v

# Reprocessar lotes
python run_ingestion.py --reprocess

# Verificar saúde do relatório
python -c "import pandas as pd; df = pd.read_csv('data/output/relatorio_lotes.csv', sep=';'); print(df['status_conciliacao'].value_counts())"

# Verificar fornecedores problemáticos
python -c "import pandas as pd; df = pd.read_csv('data/output/relatorio_lotes.csv', sep=';'); print(df[df['fornecedor'].str.contains('CNPJ|DOCUMENTO|NÃO QUITA', na=False, case=False)][['fornecedor']].drop_duplicates())"
```

## Correções Adicionais - Segunda Rodada (14:19 - 18/02/2026)

Após reprocessamento, foram identificados ~70+ casos adicionais de fornecedores com lixo. Implementadas correções em duas camadas.

### Arquivos Modificados

#### 1. `extractors/utils.py` - `normalize_entity_name()`

**Novos sufixos removidos:**

```python
# Emails/usernames colados ao nome da empresa
r"\s+joaopmsoares\s*$",
r"\s+janaina\.campos\s*$",
r"\s+financeiro\s*$",
r"\s+comercial\s*$",
r"\s+COMERCIAL\s*$",
r"\s+CONEXAOIDEALMG\s*$",

# Sites www colados
r"\s+www\.[a-z0-9\-]+\.[a-z\.]+\s*$",

# Padrões "inscrita no CNPJ"
r",?\s+inscrita?\s+no\s+CNPJ.*$",
r"\s+CNPJ/MF\s+sob.*$",
r"\s+CNPJ/CPF\s*$",
r"\s+CNPJ\s*$",

# Endereços com ENDEREÇO AV.
r"\s+ENDEREÇO\s+AV\.?.*$",

# Padrões de cidade/UF
r"\s+-\s+[A-Z]{2}\s+-\s+[A-Z][a-zA-Z\s]+$",  # "- CE - FORTALEZA"
r"\s+-\s+[A-Z][a-zA-Z\s]+/\s*[A-Z]{2}\s*$",  # "- CARMO/ RJ"
r"\s+CENTRO\s+NOVO\s+.*$",
r"\s+PC\s+PRESIDENTE\s+.*$",

# Frases genéricas
r"^Valor\s+da\s+causa\s*$",
r"^No\s+Internet\s+Banking.*$",
r"^para\s+pagamento:.*$",
r"^FAVORECIDO:.*$",

# Nome Fantasia e NOTA DE DÉBITO
r"\s+Nome\s+Fantasia\s+.*$",
r"\s+NOTA\s+DE\s+D[ÉE]BITO\s+",

# Strings muito genéricas
r"^SISTEMAS\s+LTDA\s*$",
r"^UTILIDADE\s*$",
```

**Strings completamente rejeitadas (retorna vazio):**

- Domínios `.com.br` / `.net.br` como nome (`dcadvogados.com.br`)
- `Florida33134USA` e endereços americanos
- `CEP: ...` como nome
- `Valor da causa`
- `No Internet Banking ou DDA...`
- `para pagamento: FAVORECIDO: ...`
- `Contas a Receber` / `Contas a Pagar`
- UFs sozinhas: `MG`, `SP`, `RJ`, `CNPJ`, `CPF`, `CEP`
- `CENTRO NOVO ...`
- `PC PRESIDENTE ...` / `PRAÇA PRESIDENTE ...`
- `SISTEMAS LTDA` (muito genérico)
- `UTILIDADE`

#### 2. `extractors/boleto.py` - `_looks_like_header_or_label()`

**Novos tokens de rejeição:**

```python
# Frases genéricas
"VALOR DA CAUSA",
"NO INTERNET BANKING",
"DDA O SACADO",
"SERA PJBANK",
"PARA PAGAMENTO:",
"FAVORECIDO:",
"NOME FANTASIA",
"NOTA DE DÉBITO",
"UTILIDADE",
"SISTEMAS LTDA",
"CONEXAOIDEALMG",

# Emails/usernames colados
"JOAOPMSOARES",
"JANAINA.CAMPOS",
"@GMAIL", "@HOTMAIL", "@OUTLOOK", "@YAHOO",

# Sites www
"WWW.",

# Padrões "inscrita no CNPJ"
"INSCRITA NO CNPJ",
"CNPJ/MF SOB",

# Departamentos
"CONTAS A RECEBER",
"CONTAS A PAGAR",

# Endereços com cidade/UF
"CENTRO NOVO HAMBURGO",
"PC PRESIDENTE",
"/ RS", "/ RJ", "/ MG", "/ SP", "/ PR", "/ SC", "/ BA", "/ GO", "/ DF",

# Padrões de endereço anteriores
"ENDEREÇO MUNICÍPIO CEP",
"MUNICÍPIO CEP",
"TAXID", "TAX ID",
"MUDOU-SE",
"INSCRIÇÃO MUNICIPAL",

# Padrões de documentos/hashes OCR
"F50C0E532", "CC14E2BBF", "0F6C6302D",
```

**Novos padrões regex:**

```python
# Emails colados ao nome
r"LTDA\s+(financeiro|comercial|joaopmsoares|janaina|conexaoidealmg)\s*$"

# Frases genéricas
r"^VALOR\s+DA\s+CAUSA\s*$"
r"^NO\s+INTERNET\s+BANKING"
r"^PARA\s+PAGAMENTO:"
r"^FAVORECIDO:"

# Nome Fantasia colado
"NOME FANTASIA" in s_up

# NOTA DE DÉBITO no meio
r"NOTA\s+DE\s+D[ÉE]BITO"

# Muito genérico
r"^SISTEMAS\s+LTDA\s*$"

# UFs sozinhas ou CNPJ/CPF/CEP
r"^(MG|SP|RJ|PR|SC|RS|BA|GO|DF|ES|PE|CE|PA|MA|MT|MS|CNPJ|CPF|CEP|DESO|LIGHT)$"

# Contas a Receber/Pagar
r"CONTAS\s+A\s+(RECEBER|PAGAR)"

# Centro Novo (endereço)
r"CENTRO\s+NOVO\s+"

# Termina com CNPJ
r"\s+CNPJ(/CPF)?\s*$"

# Inscrita no CNPJ
r",\s*INSCRIT[AO]\s+NO"
```

### Casos Corrigidos (Segunda Rodada)

| Padrão Problemático                                            | Qtd | Resultado                                              |
| -------------------------------------------------------------- | --- | ------------------------------------------------------ |
| `DOCUMENTO AUXILIAR DA NOTA FISCAL...`                         | 21  | Rejeitado                                              |
| `REGUSDOBRASILLTDA - Endereço Município CEP PARAIBA`           | 9   | `REGUSDOBRASILLTDA`                                    |
| `OBVIO BRASIL SOFTWARE E SERVICOS S.A. / -1 1 ( ) Mudou-se`    | 8   | `OBVIO BRASIL SOFTWARE E SERVICOS S.A.`                |
| `Florida33134USA TAXID95- MOCCOMUNICACAOS/A`                   | 8   | Rejeitado                                              |
| `MBSCONTACTCENTERLTDA joaopmsoares`                            | 7   | `MBSCONTACTCENTERLTDA`                                 |
| `WNEWERTECHNOLOGYDESENVOLVIMENTODESISTEMASLTDA janaina.campos` | 6   | `WNEWERTECHNOLOGYDESENVOLVIMENTODESISTEMASLTDA`        |
| `Contas a Receber`                                             | 6   | Rejeitado                                              |
| `CENTRO NOVO HAMBURGO/ RS`                                     | 6   | Rejeitado                                              |
| `ANIELINFORMATICALTDA COMERCIAL`                               | 6   | `ANIELINFORMATICALTDA`                                 |
| `Valor da causa`                                               | 5   | Rejeitado                                              |
| `No Internet Banking ou DDA o sacado sera PJBank`              | 5   | Rejeitado                                              |
| `Florida33134USA`                                              | 5   | Rejeitado                                              |
| `CONEXAOIDEALESTRATEGICALTDA CONEXAOIDEALMG`                   | 5   | `CONEXAOIDEALESTRATEGICALTDA`                          |
| `UTILIDADE`                                                    | 4   | Rejeitado                                              |
| `SISTEMAS LTDA`                                                | 4   | Rejeitado                                              |
| `Rede Mulher de Televisao Ltda CNPJ`                           | 4   | `Rede Mulher de Televisao Ltda`                        |
| `PSPINTERMEDIACAODESERVICOSLTDA FINANCEIRO`                    | 4   | `PSPINTERMEDIACAODESERVICOSLTDA`                       |
| `para pagamento: FAVORECIDO: CONCEITO A EM AUDIOVISUAL S.A.`   | 4   | Rejeitado                                              |
| `NEW CONT ASSESSORIA... Nome Fantasia NEW CONT...`             | 4   | `NEW CONT ASSESSORIA EMPRESARIAL E CONTABILIDADE LTDA` |
| `ALARES INTERNET S/A, inscrita no CNPJ/MF sob o nº`            | 4   | `ALARES INTERNET S/A`                                  |
| `VOICECORP TELECOMUNICACOES LTDA www.voicecorp.com.br`         | 2   | `VOICECORP TELECOMUNICACOES LTDA`                      |
| `dcadvogados.com.br F50C0E532 Inscrição Municipal`             | 2   | Rejeitado                                              |
| `comunix.net.br R vel pela Retoncã...`                         | 2   | Rejeitado                                              |
| `DB3 SERVICOS - CE - FORTALEZA`                                | 9   | `DB3 SERVICOS`                                         |
| `GIGA MAIS FIBRA - RJ - CARMO`                                 | 6   | `GIGA MAIS FIBRA`                                      |
| `PSP INTERMEDIACAO DE SERVICOS LTDA ENDEREÇO AV. AMAZONAS`     | 3   | `PSP INTERMEDIACAO DE SERVICOS LTDA`                   |
| `MG` (sozinho)                                                 | 3   | Rejeitado                                              |
| `CNPJ` (sozinho)                                               | 4   | Rejeitado                                              |

**Total de casos problemáticos corrigidos: ~70+**

### Testes

Todos os 639 testes passaram após as correções da segunda rodada:

```
===== 639 passed, 1 skipped in 7.90s =====
```

## Testes

Todos os 639 testes passaram após as correções de alta, média prioridade e segunda rodada.
