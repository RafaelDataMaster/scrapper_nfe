# Sistema de Extração de Documentos Fiscais (v0.3.x)

Sistema para extração e processamento de documentos fiscais (DANFE, NFSe e Boletos) a partir de PDFs, com suporte a **processamento em lote** e **correlação automática** entre documentos.

## Colunas Extraídas (PAF)

### Planilha 1

- PROCESSADO
- RECEBIDO
- ASSUNTO
- EMPRESA (nossa)
- VENCIMENTO
- FORNECEDOR
- NF (número da nota)
- VALOR
- AVISOS (Divergência ou possíveis falhas na informação)

### Planilha 2

- PROCESSADO
- RECEBIDO
- ASSUNTO
- EMPRESA (nossa)
- FORNECEDOR
- NF (número da nota)
- LINK (link do portal fiscal)
- CÓDIGO (para liberaçao da nota)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue.svg)](./docs/)

## To Do - Notas mentais

- [ ] Corrigir os ultimos erros e fazer o cara crachá das tabelas enviada pela pela Melyssa com os dados atuais de contrato.
- [ ] **Verificar se o projeto roda corretamente em container de docker e testar local mesmo no docker desktop do windows**.
- [ ] Lembrar de atualizar os dados do imap pro email da empresa.
- [ ] Procurar APIs da openAI para OCR e valibdadção dos dados no documento no caso para a coluna NF num primeiro momento.
- [ ] Quando o projeto estiver no estágio real pra primeira release ler git-futuro.md e pesquisar ferramentas/plugins/qualquer coisa que ajude a melhorar a maluquice que é os commits e tudo mais.
- [ ] Verificar cada caso a fundo dos pdfs e avaliar possíveis estratégias para os casos onde o pdf em si não esta anexado no email (link de prefeitura ou redirecionador de terceiros) [LOW_PRIORITY].

# Estudar por agora

Avaliar criação de um RAG de melhorias constantes, com context prompt e automanuntenabilidade.

## Done

### 19/02/2026

- [x] **Correções Finais de Normalização de Fornecedor**: Resolvido problema de ordem de operações em `normalize_entity_name()`
    - **Problema**: Verificações de padrões inválidos eram feitas **antes** da remoção de números
        - `Florida 33134 USA` → verificação de `^Florida\s+USA$` falhava → números removidos → `Florida USA` passava
        - `Rede Mulher... CNPJ: -8` → após limpar números, sobrava `CNPJ` no final
    - **Solução em `extractors/utils.py`**:
        - **Limpeza final de sufixos** (linhas 916-922): Remove `CNPJ`, `CPF`, `CEP` que sobraram após toda normalização
        - **Verificações finais** (linhas 928-961): Rejeita `Florida USA`, strings curtas (<3 chars), siglas genéricas (MG, SP, USA, etc.)
    - **Casos corrigidos**:
        - `Florida 33134 USA` → `""` (rejeitado)
        - `Rede Mulher de Televisao Ltda CNPJ: -8` → `Rede Mulher de Televisao Ltda`
        - `Empresa XYZ CPF: 123` → `Empresa XYZ`
    - **Resultado**: 2 casos `Florida USA` e 4 casos sufixo `CNPJ` corrigidos
- [x] **Testes Adicionais**: Novos casos em `tests/test_extractor_utils.py::TestNormalizeEntityName`
    - `Florida 33134 USA` → `""`
    - `Rede Mulher de Televisao Ltda CNPJ: -8` → sem sufixo
    - **Total**: 661 testes passando, 1 pulado
- [x] **Documentação de Contexto**: Atualização para memória vetorizada
    - Atualizado `docs/context/sessao_2026_02_19_pendencias.md` com correções finais
    - Criado `docs/context/sessao_2026_02_19_normalizacao_final.md` (novo)
    - Atualizado `docs/context/README.md` com índice e seção de correções
    - Atualizado `docs/context/vector_db_guide.md` com nota sobre re-indexação
- [x] **Re-indexação do Banco Vetorial**: `python scripts/ctx.py --reindex`
    - 34 arquivos, 122 chunks indexados
    - Novos documentos disponíveis para busca semântica

### 18/02/2026

- [x] **Fix NFCom Century Telecom**: Extrator `nfcom.py` não reconhecia variante de layout da Century
    - Novos padrões para número da nota: `Número\s*[:\s]*(\d+[\.\d]*)`
    - Novos padrões para valor: `Valor Total da Nota\s*[:\s]*([\d\.,]+)`
    - Novos padrões para CNPJ/fornecedor específicos da Century
    - **Resultado**: ~40 casos Century agora extraem corretamente
- [x] **Agregação de NFs para Pareamento**: Novo algoritmo em `document_pairing.py`
    - Quando há múltiplas NFs órfãs + 1 boleto órfão, tenta agregar NFs
    - Se soma dos valores das NFs bate com boleto, cria par agregado
    - **Exemplo**: Email com NF R$360 + NF R$240 + Boleto R$600 → Par agregado CONCILIADO
    - **Resultado**: +14 casos CONCILIADO
- [x] **Limpeza de Fornecedores (Segunda Rodada)**: ~70+ casos problemáticos corrigidos
    - **`extractors/boleto.py`** - `_looks_like_header_or_label()` expandido com ~50 novos tokens:
        - Frases: `VALOR DA CAUSA`, `NO INTERNET BANKING`, `FAVORECIDO:`, `NOME FANTASIA`, `NOTA DE DÉBITO`
        - Emails colados: `JOAOPMSOARES`, `JANAINA.CAMPOS`, `@GMAIL`, `WWW.`
        - Endereços: `CENTRO NOVO HAMBURGO`, `PC PRESIDENTE`, `/ RS`, `/ RJ`, `ENDEREÇO MUNICÍPIO CEP`
        - Labels: `CONTAS A RECEBER`, `INSCRITA NO CNPJ`, `TAXID`, `MUDOU-SE`, `INSCRIÇÃO MUNICIPAL`
    - **`extractors/utils.py`** - `normalize_entity_name()` com ~40 novos padrões:
        - Sufixos: `joaopmsoares`, `financeiro`, `comercial`, `www.site.com.br`, `Nome Fantasia ...`
        - Sufixos: `, inscrita no CNPJ/MF`, `CNPJ/CPF`, `- Endereço Município CEP PARAIBA`
        - Sufixos: `/ -1 1 ( ) Mudou-se`, `TAXID95-`, `Florida33134USA`
        - Rejeição completa: domínios `.com.br`, `Contas a Receber`, `Valor da causa`, UFs sozinhas
    - **Casos corrigidos**:
        - `EMPRESALTDA joaopmsoares` → `EMPRESALTDA`
        - `EMPRESA - Endereço Município CEP PARAIBA` → `EMPRESA`
        - `EMPRESA, inscrita no CNPJ/MF sob o nº` → `EMPRESA`
        - `Florida33134USA TAXID95-` → Rejeitado
        - `DOCUMENTO AUXILIAR DA NOTA FISCAL...` → Rejeitado (21 casos)
        - `Contas a Receber` → Rejeitado
        - `CENTRO NOVO HAMBURGO/ RS` → Rejeitado
- [x] **Documentação**: Atualizado `docs/context/sessao_2026_02_18_fixes_alta_prioridade.md` e `docs/context/README.md`

### 09/02/2026

- [x] **Análise de Saúde do `relatorio_lotes.csv`**: Diagnóstico completo de qualidade das extrações
    - Identificados 1.238 lotes, 90,9% com valor extraído, 118 CONCILIADO, 1.097 CONFERIR
    - Detectadas 26 linhas quebradas no CSV por `\n` no campo `email_subject`
    - Identificados padrões de fornecedores incorretos (Giga+, RSM, Regus, etc.)
- [x] **Sanitização de campos CSV**: `run_ingestion.py` agora remove `\n`, `\r`, `;` de `email_subject`, `email_sender` e `divergencia` antes de exportar
- [x] **Correção de fornecedor Giga+/DB3**: Boletos extraíam "forma, voc assegura que seu pagamento é seguro" como fornecedor
    - **`extractors/boleto.py`**: Adicionados termos à blacklist em `_looks_like_header_or_label()`:
        - "PAGAMENTO", "SEGURO", "ASSEGURA", "FORMA,", "DESSA FORMA"
        - "CPF OU CNPJ", "CONTATO CNPJ", "E-MAIL", "ENDEREÇO", "MUNICÍPIO", "CEP "
    - Resultado: 15 → 0 ocorrências, fornecedor agora extrai "DB3 SERVICOS - CE - FORTALEZA"
- [x] **Normalização de nomes de fornecedor**: `extractors/utils.py` → `normalize_entity_name()` expandido:
    - Prefixos removidos: `E-mail`, `Beneficiario`, `Nome/NomeEmpresarial`, `Nome / Nome Empresarial E-mail`, `Razão Social`
    - Sufixos removidos: `CONTATO`, `CPF ou CNPJ`, `- CNPJ`, `| CNPJ - CNPJ`, `|` solto, `- Endereço...`, `Endereço Município CEP...`
    - Exemplos corrigidos:
        - `E-mail RSMBRASILAUDITORIAECONSULTORIALTDA CONTATO` → `RSMBRASILAUDITORIAECONSULTORIALTDA`
        - `PITTSBURG FIP MULTIESTRATEGIA CPF ou CNPJ` → `PITTSBURG FIP MULTIESTRATEGIA`
        - `VERO S.A. CNL. | CNPJ - CNPJ` → `VERO S.A. CNL.`
- [x] **Centralização da normalização**: `core/batch_result.py` e `core/document_pairing.py` agora usam `normalize_entity_name()` de `extractors/utils.py` em vez de lógica duplicada
- [x] **Documentação**: Criado `docs/context/sessao_2026_02_09_saude_extracao.md` com relatório completo e comandos de verificação

### 06/02/2026

- [x] **Fix Timeout em PDFs com QR Code vetorial**: PDFs com QR Codes complexos causavam timeout de 90s no pdfminer
    - **Causa**: `abrir_pdfplumber_com_senha()` chamava `extract_text()` para validar abertura do PDF
    - **`strategies/pdf_utils.py`**: Removido `extract_text()` do fluxo de validação - PDF que abre sem erro é retornado imediatamente
    - **Resultado**: Tempo de abertura 90s+ → 0.01s, extração via OCR em ~4s
    - **Batch exemplo**: `email_20260205_131749_6cb7ddf4` (boleto Banco Inter/Partners RL)
- [x] **Padrão CEMIG no UtilityBillExtractor**: 166 de 224 faturas CEMIG (74%) tinham valores incorretos
    - **`extractors/utility_bill.py`**: Adicionado padrão específico para capturar "valor a pagar" no layout CEMIG
    - Padrão: `MÊS/ANO DATA_VENCIMENTO VALOR_A_PAGAR` (ex: "JAN/26 10/02/2026 205,05")
- [x] **Suporte a NFCom no XmlExtractor**: XMLs de NFCom (Nota Fiscal de Comunicação - modelo 62) não eram processados
    - **`extractors/xml_extractor.py`**:
        - Detecção do namespace `http://www.portalfiscal.inf.br/nfcom`
        - Novo método `_extract_nfcom()` para extrair fornecedor, CNPJ, número NF, valor, vencimento
        - Usado por operadoras de telecom (MITelecom, etc.)
- [x] **Documentação**: Criado `docs/context/sessao_2026_02_06_correcoes_extracao_valores.md`

### 05/02/2026

- [x] **TIMFaturaExtractor**: Novo extrator para faturas da TIM S.A.
    - **Arquivo novo**: `extractors/tim_fatura.py`
    - Detecta por padrões "TIM S.A." + "FATURA" + CNPJ da TIM
    - Extrai: número da fatura, valor total, vencimento, CNPJ
    - Posicionado no registry antes de `NfseCustomMontesClaros` e `UtilityBillExtractor`
- [x] **Correção de detecção de PDFs protegidos**: `pdf_utils.py` agora detecta `PdfminerException` sem mensagem corretamente
- [x] **Testes**: 636 passed, 1 skipped
- [x] **Documentação**: Criado `docs/context/sessao_2026_02_05_timeout_tim.md`

### 04/02/2026

- [x] **Correção de extração de fornecedores em DANFE e Boletos (NFCom)**:
    - **`extractors/danfe.py`** - Melhorias significativas:
        - Adicionados CNPJs no mapeamento `CNPJ_TO_NOME` para correção automática via CNPJ:
            - VOGEL SOL. EM TEL. E INF. S.A. (05.872.814/0007-25, 05.872.814/0001-11)
            - Century Telecom LTDA (01.492.641/0001-73)
            - ALGAR TELECOM S/A (71.208.516/0001-74)
            - NIPCABLE DO BRASIL TELECOM LTDA (05.334.864/0001-63)
        - Novos padrões inválidos em `_is_invalid_fornecedor()`:
            - `CPF/CNPJ INSCRIÇÃO ESTADUAL` (cabeçalho de tabela)
            - `BETIM / MG - CEP:` e padrão genérico `CIDADE / UF - CEP`
            - `Nº DO CLIENTE:` (fragmento de NFCom)
            - `(-) Desconto / Abatimentos`, `Outras deduções` (tabela de descontos)
            - `- INSC. EST.`, `FATURA DE SERVIÇO` (fragmentos de cabeçalho NFCom)
        - Novo padrão NFCom para layout VOGEL/ALGAR: `DOCUMENTO AUXILIAR NOME\nDA NOTA FISCAL`
        - Correção do regex para aceitar "S/A" (com barra) além de "S.A."
    - **`extractors/boleto.py`** - Novos tokens inválidos em `_looks_like_header_or_label()`:
        - "DESCONTO", "ABATIMENTO", "OUTRAS DEDUÇÕES"
        - "MORA / MULTA", "OUTROS ACRÉSCIMOS", "VALOR COBRADO"
        - "(=)", "(-)", "(+)" (símbolos de operações em tabelas)
    - **Resultados após correções**:
        - Fornecedores problemáticos no relatório de lotes: 9 → 0 ✅
        - Fornecedores problemáticos no DANFE: 29 → 0 ✅
        - Batches com fornecedor válido: 922 → 929 (87.8%)
        - Severidade CRÍTICA/ALTA: 0 ✅

### 03/02/2026

- [x] **Melhorias na extração de vencimentos e análise de saúde**:
    - **`extractors/utility_bill.py`**:
        - Adicionados padrões para datas com pontos (`DD.MM.YYYY`) — ex.: EDP Nota de Débito
        - Novo padrão específico para capturar `Data Vencimento` em layout tabular (EDP)
        - Reorganização dos regex (mais específicos primeiro)
    - **`extractors/utils.py`**:
        - `parse_date_br` agora normaliza `.` → `/` para suportar formato `DD.MM.YYYY`
    - **`scripts/analyze_batch_health.py`** - Melhorias substanciais:
        - Identificação de tipo de documento (NFSE, BOLETO, UTILITY\_\*)
        - Severidade contextual (ex.: NFS-e sem vencimento = INFO, não erro)
        - Detecção de PDFs protegidos por senha (Sabesp) → `PDF_PROTEGIDO_OK` / INFO
        - `STATUS_CONFERIR` tratado como informativo (INFO) em vez de BAIXA
        - Agrupamento por fornecedor e relatório mais rico
    - **Resultados após correções**:
        - Batches com problemas reais (severidade ≥ MÉDIA): 36 (3.6%)
        - Casos informativos esperados: STATUS_CONFERIR: 512 | NFSE_SEM_VENCIMENTO: 30 | PDF_PROTEGIDO_OK: 3
        - 3 "erros" do log eram PDFs protegidos por senha (Sabesp) — dados obtidos via corpo do e-mail

- [x] **Correção de 4 casos de Severidade ALTA na análise de saúde dos batches**:
    - **TIM vs MULTIMIDIA**: Bug de substring match onde "TIM" era encontrado dentro de "MULTIMIDIA"
        - `extractors/outros.py`: Separação de `KNOWN_SUPPLIERS` em dois grupos - `KNOWN_SUPPLIERS_WORD_BOUNDARY` (usa regex `\bTIM\b`) e `KNOWN_SUPPLIERS` (substring match)
        - Adicionados "AMERICAN TOWER" e "GLOBENET" como fornecedores conhecidos
        - Corrigidos 2 casos: TIM → AMERICAN TOWER DO BRASIL (R$ 7.847,23 cada)
    - **Original (watermark Santander)**: OCR lendo watermark do banco como nome do beneficiário
        - `extractors/comprovante_bancario.py`: Adicionada lista `INVALID_SUPPLIER_NAMES` com watermarks/labels bancários
        - Novo padrão específico para formato Santander: "Nome/Razão Social do Beneficiário Original CPF/CNPJ do Beneficiário EMPRESA"
        - Limpeza de sufixos "Original", "Copia", "Via" do nome do beneficiário
        - Corrigido 1 caso: Original → ESPN DO BRASIL (R$ 5.635,71)
    - **Marco Túlio Lima (contato comercial)**: Sistema extraindo nome de contato como fornecedor em Ordens de Serviço
        - `extractors/admin_document.py`: Adicionada lista de fornecedores conhecidos para ORDEM_SERVICO (GlobeNet, VTAL, Equinix, Lumen, American Tower)
        - Validação para evitar nomes de contato como "Marco Túlio" serem extraídos como fornecedor
        - Corrigido 1 caso: Marco Túlio Lima → GlobeNet Cabos Submarinos S.A. (R$ 26.250,00)
- [x] **Resultado final da análise de saúde**:
    - Severidade CRÍTICA: 0 ✅
    - Severidade ALTA: 0 ✅ (eram 4, agora zerado!)
    - Fornecedores válidos: 868 (86.3%)
    - Total de batches analisados: 1006

### 02/02/2026

- [x] **CscNotaDebitoExtractor**: Novo extrator para documentos CSC/Linnia tipo "NOTA DÉBITO / RECIBO FATURA"
    - Arquivo novo: `extractors/csc_nota_debito.py` com 25 testes
    - Detecta por CNPJ `38.323.227/0001-40` e padrões "NOTA DÉBITO / RECIBO FATURA"
    - Extrai: numero_documento, valor_total, data_emissao, competencia, tomador
    - Retorna tipo OUTRO com subtipo NOTA_DEBITO
    - Tolerância a OCR ruidoso (letras espaçadas: "N O T A D É B I T O")
    - Corrigidos 7 casos CSC/Linnia totalizando ~R$ 24.966
- [x] **REPROMAQ Extrato de Locação**: Correção para documentos de locação REPROMAQ classificados incorretamente
    - `nfse_generic.py`: Adicionado "EXTRATO DE LOCAÇÃO" na lista de rejeição
    - `outros.py`: Suporte para detectar "EXTRATO DE LOCAÇÃO" e "FATURA DE LOCAÇÃO"
    - Novos padrões para extrair número do recibo (S09679) e valor total
    - Exceção na regra de impostos para faturas de locação
    - Subtipo LOCACAO para documentos de locação
- [x] **Correção de regex para extração de número da nota**: Ajustes nos padrões de extração para capturar números em formatos não cobertos anteriormente:
    - **NfseGenericExtractor**: Adicionados padrões para números em linha separada do "Nº" (TCF Services com 15 dígitos), números curtos de 3+ dígitos ("Numero: 347"), e formato "Recibo número: 59/2026"
    - **MugoExtractor**: Alterado limite de `\d{6,12}` para `\d{4,15}` para capturar números de 5 dígitos como "71039"
    - Corrigidos 12 casos de NFSE_SEM_NUMERO (TCF Services, MUGO, ATIVE, GAC) totalizando ~R$ 4.657
- [x] **SabespWaterBillExtractor**: Novo extrator para faturas da Sabesp que extrai dados do corpo do email HTML (PDFs protegidos por senha com CPF do titular)
    - Detecta por sender @sabesp.com.br, subject ou padrões no corpo
    - Extrai: valor, vencimento, número de fornecimento, código de barras
    - Retorna tipo UTILITY_BILL com subtipo WATER
- [x] **Documentação de PDF Password Handling**: Novo arquivo `docs/context/pdf_password_handling.md` documentando comportamento de fallback para PDFs protegidos por senha
- [x] **Ajustes em analyze_logs.py**: Melhorias nos padrões de regex para correlação de logs, atualizado `docs/context/log_correlation.md` com novos exemplos
- [x] **Documentação de comandos para agentes IA**: Atualizado `docs/context/commands_reference.md` com dicas sobre comandos PowerShell problemáticos e alternativas confiáveis

### 30/01/2026

- [x] **Criação de extratores especializados para casos específicos de OCR e contratos**:
    - **AditivoContratoExtractor**: Para aditivos de contrato (ALARES, contratos de locação), detectando CNPJs conhecidos e padrões como "ADITIVO AO CONTRATO", corrige problema de fornecedor sendo sobrescrito por dados do email (R$ 10.072 corrigidos)
    - **OcrDanfeExtractor**: Para DANFEs com texto corrompido por OCR (Auto Posto, postos de gasolina), detecta padrões como "RECEHEMOS", "HINAT", "CIVCRE" e usa regex tolerantes a corrupção
- [x] **Correção na lógica de extração do corpo do email**: BatchProcessor modificado para não sobrescrever documentos PDF válidos (com fornecedor) com dados do email body, resolvendo casos onde aditivos e documentos válidos perdiam o fornecedor correto
- [x] **Correção de fornecedor genérico em NFSe**: NfseGenericExtractor agora rejeita textos como "PRESTADOR DE SERVIÇOS" sem nome real do fornecedor
- [x] **Refatoração de EnergyBillExtractor para UtilityBillExtractor**: Unificação de extratores de contas de energia e água em um único extrator com subtipos "ENERGY" e "WATER", mapeando corretamente para OtherDocumentData e eliminando 80 casos NFSE_SEM_NUMERO (R$ 173K)
- [x] **Análise de erros com critérios reais**: Identificação de que 99,5% dos "erros" reportados eram falsos positivos (comportamento correto segundo regras de negócio), apenas 1 erro real permanece (Auto Posto com texto truncado)
- [x] **Valor total corrigido**: ~R$ 118.236,39 em documentos que antes tinham fornecedor vazio/errado e agora estão corretos

### 29/01/2026

- [x] **Criação de extratores especializados para faturas comerciais**:
    - **TunnaFaturaExtractor**: Para faturas da Tunna Entretenimento e Audiovisual LTDA (FishTV), detectando padrões "TUNNA" + "FATURA"/"FAT/" e número de fatura no formato `000.XXX.XXX`
    - **UfinetExtractor**: Para faturas da Ufinet Brasil S.A., extraindo número da fatura, CNPJ, valor total e vencimento de documentos comerciais de telecomunicações
- [x] **Correção de extração de vencimento em boletos via código de barras**: Implementação do método `_decode_vencimento_from_linha_digitavel()` no BoletoExtractor, que calcula a data de vencimento a partir do fator de vencimento (posições 33-36 da linha digitável), incluindo tratamento para reinício do fator a cada 10000 dias desde 2025-02-22
- [x] **Limpeza de logs e redução de verbosidade**: Ajuste de logs desnecessários de WARNING para DEBUG em `strategies/pdf_utils.py` e `core/processor.py`, reduzindo poluição no output durante o processamento em lote

### 28/01/2026

- [x] **Implementação de extratores específicos para casos problemáticos**: Criação de três extratores especializados para resolver problemas de classificação e extração de valores:
    - **AcimocExtractor**: Para boletos da Associação Comercial Industrial e de Serviços de Montes Claros, que estavam sendo capturados incorretamente pelo AdminDocumentExtractor com valor R$ 0,00
    - **MugoExtractor**: Para faturas da MUGO TELECOMUNICAÇÕES LTDA, resolvendo casos de PDFs não reconhecidos e extração de valores
    - **ProPainelExtractor**: Para documentos da PRÓ - PAINEL LTDA (boletos PIX e faturas de locação), que não eram reconhecidos pelos extratores existentes
- [x] **Correções estruturais de campos CNPJ**: Ajuste dos campos CNPJ conforme tipo de documento:
    - MugoExtractor: Alterado `cnpj_beneficiario` para `cnpj_prestador` (NFSe)
    - ProPainelExtractor: Lógica condicional (`cnpj_beneficiario` para BOLETO, `cnpj_prestador` para NFSE)
- [x] **AdminDocumentExtractor menos agressivo**: Adição de padrões negativos para evitar captura de boletos e documentos de fornecedores específicos, com sistema de scoring para rejeitar documentos que parecem ser boletos
- [x] **Correções técnicas**: Resolução de erros `Cannot access attribute "strftime" for class "str"` nos métodos de extração de datas, ajuste de padrões regex para melhorar extração de números de documento

### 27/02/2026

- [x] Fazer um script pra automatizar a analise de logs, feito scripts\analyze_logs.py
- [x] Extrator para os casos da Telcables criado, extractors\nfcom_telcables_extractor.py

### 26/01/2026

- [x] **Resolução do problema Carrier Telecom vs faturas de energia**: Remoção do CarrierTelecomExtractor e criação do EnergyBillExtractor
    - Identificado que Carrier Telecom S/A (CNPJ 38323230000164) é uma de nossas empresas, não um fornecedor externo
    - O extrator original estava sendo ativado indevidamente em faturas de energia onde Carrier Telecom aparece como cliente
    - Criado EnergyBillExtractor especializado para faturas de energia (EDP, CEMIG, COPEL, etc.)
    - Detecta distribuidoras de energia por múltiplos indicadores (DISTRIB DE ENERGIA, CONSUMO, KWH, etc.)
    - Extrai campos específicos: fornecedor, CNPJ, número da nota, valor total, vencimento, período de referência
- [x] **Aprimoramento do script inspect_pdf.py para análise detalhada de batches**:
    - Adicionado modo batch (`--batch`) para analisar todos os PDFs de um lote do temp_email
    - Exibe informações de extratores testados e qual foi selecionado (ordem de prioridade)
    - Mostra campos que seriam exportados para relatorio_lotes.csv
    - Informações automáticas do batch (ID, data, pasta)
    - Estatísticas consolidadas de extratores, tipos e empresas no modo batch

### 23/01/2026

- [x] Aprimora classificação de documentos
    - Trocado a ordem do SicoobExtractor porque aparentemente ele é pior que o generico, avaliar o porque e oque pode ser feito. (issue)
    - Adiciona padrões para NFSEs municipais e documentos de serviço público
    - Atualiza título do relatório de análise de PDFs para maior clareza
    - Remove arquivo obsoleto de análise de NFSEs administrativas com valor zero
    - Adiciona relatório simples para lotes problemáticos

### 22/01/2026

- [x] **Resolução do caso VCOM Tecnologia**: Correção do AdminDocumentExtractor para extrair valores de ordens de serviço e melhoria na extração de vencimento para documentos tabulares, resolvendo 6 casos de documentos classificados como administrativos com valores não extraídos.
- [x] **Correção de scripts de diagnóstico**: Ajuste no check_problematic_pdfs.py para chamada correta da função infer_fornecedor_from_text com argumento faltante.
- [x] **Análise sistemática de casos problemáticos**: Identificação e correção de 6 casos VCOM onde documentos de ordem de serviço não extraíam valores, reduzindo "Valor Issues" de 23 para 17 casos.
- [x] **Documentação das correções**: Criação de análise detalhada em docs/analysis/caso_vcom_tecnologia_correcoes.md para referência futura e aprendizado do sistema.
- [x] **Padronização completa da suíte de testes**: Correção de 9 testes que estavam falhando após padronização para pytest, incluindo:
    - Correção do teste `test_admin_pairing.py` para não usar "contrato" no nome do arquivo (ativava filtro de documento auxiliar)
    - Ajuste do AdminDocumentExtractor para aceitar documentos com padrão "DOCUMENTO: 000000135"
    - Melhoria na extração de fornecedor no OutrosExtractor com padrão "Fornecedor: NOME LTDA"
    - Correção da detecção de chave de acesso de 44 dígitos com regex robusta `(?<!\d)\d{44}(?!\d)`
    - Ajuste nos mocks de timeout para apontar corretamente para `config.settings`
- [x] **Ajustes no extrator Carrier Telecom**: Remoção de "DOCUMENTO AUXILIAR DA NOTA FISCAL" dos indicadores fortes de NFSe no NfseGenericExtractor, evitando falsos positivos em DANFEs e garantindo que o CarrierTelecomExtractor específico tenha prioridade.
- [x] **Melhoria na extração de número da nota**: Adição de padrão `Nota\s*Fiscal\s*Fatura\s*[:\-]?\s*(\d{1,15})` no NfseGenericExtractor para capturar melhor números em documentos como "NOTA FISCAL FATURA: 114".
- [x] **Resultado final**: Suíte de testes com 547 testes (546 passando, 1 pulado), todos os extratores funcionando corretamente e sistema pronto para execução integrada.

### 21/01/2026

- [x] **Criação do CarrierTelecomExtractor para documentos específicos**: Extrator dedicado para documentos da Carrier Telecom/TELCABLES BRASIL LTDA que possuem características únicas como "DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA" e linha digitável para débito automático.
- [x] **Solução para problema do caractere 'Ê' no OCR**: Implementação de normalização robusta de texto OCR para tratar caracteres especiais como 'Ê' que eram usados como substitutos de espaços, garantindo que padrões como "TOTALÊAÊPAGAR:ÊR$Ê29.250,00" sejam reconhecidos corretamente.
- [x] **Aprimoramento do AdminDocumentExtractor para evitar falsos positivos**: Implementação de padrões negativos e sistema de pontuação para detectar documentos fiscais (NFSEs/DANFEs) e evitar classificação incorreta como documentos administrativos.
- [x] **Análise e correção de casos problemáticos**: Identificação de 21 casos onde documentos fiscais eram classificados como "outros" com valor zero, com correções específicas para TCF TELECOM, BOX BRAZIL e outros provedores.
- [x] **Validação com testes unitários**: Criação de testes específicos para validar a detecção correta de documentos administrativos genuínos e rejeição de documentos fiscais.
- [x] **Scripts de análise automatizada**: Desenvolvimento de scripts para análise de PDFs problemáticos e geração de relatórios detalhados sobre casos de classificação incorreta.

### 20/01/2026

- [x] **Correção do problema de valores zerados para documentos "Outros" no CSV final**: Ajuste na lógica de documentos auxiliares para garantir que documentos com **valor_total > 0** não sejam ignorados no pareamento.
- [x] **Integração completa de avisos de documento administrativo**: Correção na propagação de avisos do CorrelationResult para o DocumentPair, garantindo que avisos **[POSSÍVEL DOCUMENTO ADMINISTRATIVO - ...]** apareçam no CSV.
- [x] **Reordenação de extratores**: OutrosExtractor agora tem prioridade sobre NfseGenericExtractor, evitando classificação incorreta de documentos de locação/fatura como NFSe.
- [x] **Adição de logs detalhados**: Melhor monitoramento da extração de documentos "Outros" e da lógica de pareamento.

### 19/01/2026

- [x] **Adição de identificador de email administrativo, para os casos que tem anexo mas não contem valores / dados úteis.** É decidido manter eles e adicionar o aviso pois a lógica de exclusão poderia perder emails importantes.

### 16/01/2026

- [x] **Correção na falha do uso do extrator especifico pra repromaq, agora funcionando evitando falha catastrófica de backtraking no regex**

### 15/01/2026

- [x] **Correção de data de recebimento do email da cemig**
- [x] **Correção em quesito de granularidade da politica de timeout do pdfplumber**.
- [x] **Adicionado nos logs para melhor acompanhamento dos extratores**

### 14/01/2026

- [x] **Tratamento de PDF com senha em todas as estratégias de extração**: Centralizado código de desbloqueio de PDFs protegidos
    - Novo módulo `strategies/pdf_utils.py` com funções compartilhadas:
        - `gerar_candidatos_senha()`: Gera candidatos baseados em CNPJs (completo, 4, 5 e 8 primeiros dígitos)
        - `abrir_pdfplumber_com_senha()`: Abre PDFs com pdfplumber tentando senhas automaticamente
        - `abrir_pypdfium_com_senha()`: Abre PDFs com pypdfium2 tentando senhas automaticamente
    - `NativePdfStrategy`: Agora desbloqueia PDFs protegidos antes da extração nativa (muito mais rápido que OCR)
    - `TablePdfStrategy`: Agora desbloqueia PDFs protegidos antes da extração de tabelas
    - `TesseractOcrStrategy`: Refatorado para usar funções compartilhadas
    - Benefícios: PDFs vetoriais protegidos agora são extraídos nativamente (performance e precisão), casos híbridos continuam funcionando com `HYBRID_OCR_COMPLEMENT`
- [x] **Nova coluna RECEBIDO nas planilhas Google Sheets**: Data de recebimento do email agora é exibida separada da data de processamento
    - Aba `anexos`: PROCESSADO, RECEBIDO, ASSUNTO, N_PEDIDO, EMPRESA, VENCIMENTO, FORNECEDOR, NF, VALOR, SITUACAO, AVISOS (11 colunas)
    - Aba `sem_anexos`: PROCESSADO, RECEBIDO, ASSUNTO, N_PEDIDO, EMPRESA, FORNECEDOR, NF, LINK, CODIGO (9 colunas)
    - Campo `email_date` adicionado à classe base `DocumentData` e propagado para todos os tipos de documento
    - `BatchProcessor._parse_email_date()`: Converte `received_date` do metadata (RFC 2822, ISO, BR) para formato ISO
    - `DocumentPair.to_summary()`: Exporta coluna `data` no `relatorio_lotes.csv`
    - `EmailAvisoData.from_metadata()`: Extrai `email_date` do metadata para avisos sem anexo
    - Atualizado `to_anexos_row()` em `InvoiceData`, `DanfeData`, `BoletoData`, `OtherDocumentData`
    - Atualizado `to_sem_anexos_row()` em `EmailAvisoData`
    - `load_lotes_from_csv()` e `load_avisos_from_csv()` atualizados para carregar `email_date`
- [x] **Status de conciliação "CONCILIADO"**: Trocado status "OK" por "CONCILIADO" quando NF e boleto são encontrados e valores conferem
    - Mais descritivo para o usuário entender que os documentos foram pareados com sucesso
    - Alterado em `DocumentPairingService._calculate_status()` e `CorrelationService._validate_cross_values()`
    - `CorrelationResult.is_ok()` atualizado para verificar status "CONCILIADO"
- [x] **Vencimento vazio quando não encontrado**: Removido fallback que colocava data de processamento quando vencimento não era encontrado
    - Coluna VENCIMENTO fica vazia/nula se não encontrado
    - Aviso `[VENCIMENTO NÃO ENCONTRADO - verificar urgente]` adicionado à coluna AVISOS
    - Alterado em `DocumentPairingService._create_pair()`, `BatchResult.to_summary()` e `CorrelationService._apply_vencimento_alerta()`
- [x] **Fix configuração de logging**: Logs agora são salvos corretamente em arquivo com rotação
    - `config/settings.py`: Logger raiz configurado com `RotatingFileHandler` (10MB, 5 backups)
    - Todos os módulos que usam `logging.getLogger(__name__)` agora herdam a configuração automaticamente
    - Removido `logging.basicConfig()` de `run_ingestion.py`, `export_to_sheets.py` e `ingest_emails_no_attachment.py`
    - Logs salvos em `logs/scrapper.log` com formato: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### 12/01/2026

- [x] script de limpeza dos arquivos.
- [x] integração com o google sheets.
- [x] script para analise dos emails durante a ingestão
- [x] implementação no run ingestion mais robusto aplicando filtro criado com base na analise dos emails em inbox.
- [x] **Refatoração do `export_to_sheets.py`**: Fonte de dados padrão alterada para `relatorio_lotes.csv`
    - **ANTES**: Usava `relatorio_consolidado.csv` (1 linha por documento extraído)
    - **AGORA**: Usa `relatorio_lotes.csv` (1 linha por e-mail/lote) - mais simples para usuário final
    - Nova função `load_lotes_from_csv()` para carregar do relatório de lotes
    - Nova flag `--use-consolidado` para usar o modo detalhado anterior
    - Nova flag `--csv-lotes` para especificar CSV de lotes customizado
- [x] **Fix integração CSVs ↔ Google Sheets**: Corrigido mapeamento de colunas
    - `export_avisos_to_csv()` agora gera 2 CSVs: formato Sheets + relatório simples
    - `_save_partial_aviso()` salva mais campos para reconstrução completa
    - `_merge_partial_results_into_result()` reconstrói com todos os campos
    - `export_partial_results_to_csv()` gera CSV compatível com `load_avisos_from_csv()`

### 09/01/2026

- [x] **Extrator específico para boletos REPROMAQ/Bradesco** (`extractors/boleto_repromaq.py`)
    - Resolve problema de **catastrophic backtracking** no `BoletoExtractor` genérico
    - **Causa raiz**: OCR de baixa qualidade gera texto "sujo" onde colunas vizinhas invadem os dados (ex: dígito da "Carteira" aparece entre o label "Valor do Documento" e o valor real)
    - Regexes gulosos (`.*`, `[\s\S]*`) entram em loop infinito tentando fazer match
    - **Solução**: Abordagem baseada em linhas + regexes com limites rígidos de caracteres
    - Performance: **~10x mais rápido** que o extrator genérico (0.03s vs 0.27s)
    - Tolerância a erros de OCR: `REPROMAQ` → `REPROMAO` (Q confundido com O)
- [x] **Script genérico `test_extractor_routing.py`**: Testa qual extrator seria usado para qualquer PDF
    - Mostra tempo de `can_handle()` e `extract()` para identificar gargalos
    - Flag `--texto` para ver o texto OCR extraído (útil para debug de regex)
- [x] **Limpeza de scripts de debug**: Removidos arquivos de diagnóstico pontual
    - `diagnose_batch_939db0f8.py`, `diagnose_bottleneck.py`, `diagnose_imports.py`
    - `test_extractor_timing.py`, `test_ocr_issue.py`, `benchmark_ocr.py`
    - `scripts/debug_batch.py`

### 08/01/2026

- [x] **Fix detecção de empresa (coluna EMPRESA)**: Sistema agora detecta corretamente a empresa em todos os tipos de documento
    - Criado módulo `core/empresa_matcher_email.py` específico para e-mails sem anexo
    - Adicionada detecção de empresa em XMLs no `batch_processor._process_xml()`
    - Fix de encoding para XMLs municipais (utf-8 → latin-1 → cp1252)
    - Coluna `empresa` adicionada ao `relatorio_lotes.csv` via `DocumentPair`
    - **22/22 lotes com empresa detectada** (antes: 17/22)
- [x] **Fix falso positivo MASTER**: Domínio `soumaster.com.br` causava match incorreto
    - Corrigido `empresa_matcher.py` para exigir boundary match em domínios
    - Criada lógica de contexto seguro (campo "Para:", "Tomador:") vs ignorar ("frase de segurança")
    - E-mails sem anexo agora detectam empresa corretamente (100% de taxa)
- [x] **Módulo `empresa_matcher_email.py`**: Detector otimizado para e-mails encaminhados
    - Remove domínios internos (soumaster.com.br, gmail.com)
    - Remove URLs de tracking (click._, track._)
    - Prioriza contexto seguro sobre contexto de senha/segurança

### 07/01/2026

- [x] extrator específico pra nfse de Vila Velha e Montes Claros
- [x] **email_20260105_125517_cc334d1b** e **email_20260105_125518_48a68ac5**: Divergência de R$ -6.250,00
    - Caso de **múltiplas NFs no mesmo email** (2 NFs + 2 Boletos)
    - Fornecedor: MAIS CONSULTORIA E SERVICOS LTDA
    - **RESOLVIDO**: Implementado `core/document_pairing.py` que:
        - Pareia NF↔Boleto por número da nota no nome do arquivo ou conteúdo
        - Gera uma linha no relatório para cada par (em vez de uma linha por email)
        - Casos como Locaweb (sem número de nota) são pareados por valor

### 06/01/2026

- [x] **Refatoração DRY dos extratores**: Criado módulo `extractors/utils.py` com funções compartilhadas
    - Funções de parsing: `parse_br_money()`, `parse_date_br()`, `extract_best_money_from_segment()`
    - Funções de CNPJ/CPF: `extract_cnpj()`, `extract_cnpj_flexible()`, `format_cnpj()`
    - Funções de normalização: `strip_accents()`, `normalize_entity_name()`, `normalize_text_for_extraction()`
    - Regex compilados compartilhados: `BR_MONEY_RE`, `CNPJ_RE`, `CPF_RE`, `BR_DATE_RE`
    - Removidas ~100 linhas de código duplicado em 6 arquivos (`danfe.py`, `outros.py`, `nfse_generic.py`, `boleto.py`, `net_center.py`, `sicoob.py`)
    - **278 testes passando** após refatoração
- [x] **Ingestão de e-mails sem anexo**: Script `ingest_emails_no_attachment.py` processa e-mails que contêm apenas links de NF-e (prefeituras, Omie, etc.)
    - Extrai link da NF-e, código de verificação, número da nota e fornecedor
    - Gera avisos no formato `EmailAvisoData` para auditoria
    - Exporta para CSV em `data/output/avisos_emails_sem_anexo_latest.csv`
- [x] **Flag `--keep-history`**: Versionamento de CSVs agora é opcional
    - Por padrão: só salva `_latest.csv` (sobrescreve)
    - Com `--keep-history`: salva versão com timestamp + latest
    - Útil durante testes com novos e-mails/casos

### 05/01/2026

- [x] Verificação de dados em fallback com diversos documentos e contexto do próprio email. Adicionado avisos de divergencia para falta de data de vencimento onde é colocado a data do processamento mais um texto explicativo para verificar.
- [x] **Fix EMC Fatura de Locação**: PDF multi-página extraía apenas primeiro valor (R$ 130,00 vs R$ 37.817,48)
    - Criado extrator especializado `EmcFaturaExtractor` em `extractors/emc_fatura.py`
    - Procura "TOTAL R$ XX.XXX,XX" na última página do documento
    - Reconhece faturas de locação EMC Tecnologia com múltiplas páginas de itens
    - **1 lote DIVERGENTE → OK** (email_20260105_125519_9b0b0752)

### 02/01/2026

- [x] **Fix MATRIXGO**: DANFSe classificado como boleto (chave de acesso confundida com linha digitável)
    - Corrigido `find_linha_digitavel()` para excluir chaves de acesso NFS-e
    - Corrigido `BoletoExtractor.can_handle()` para excluir documentos DANFSe
    - **2 lotes DIVERGENTE → OK**
- [x] **Fix Sigcorp**: XML municipal SigISS não era reconhecido
    - Adicionado método `_extract_nfse_sigiss()` no `xml_extractor.py`
    - Suporte ao formato XML SigISS (Marília-SP e outras prefeituras)
    - **1 lote sem extração → OK**
- [x] **Implementar a refatoração descrito em refatora.md incluindo alteraçãos no models e process** ✅ (v0.2.x - Batch Processing)
- [x] **Batch Processing v0.2.x**: Módulos `BatchProcessor`, `CorrelationService`, `EmailMetadata`, `BatchResult`, `IngestionService`
- [x] **Correlação DANFE/Boleto**: Herança automática de campos entre documentos do mesmo lote
- [x] **Novo script `inspect_pdf.py`**: Inspeção rápida com busca automática em `failed_cases_pdf/` e `temp_email/`
- [x] **164 testes unitários**: Cobertura completa incluindo novos módulos de batch
- [x] **Documentação atualizada**: Guias de debug, testing, extending e migration atualizados para v0.2.x
- [x] **Limpeza de scripts**: Removidos scripts obsoletos (`debug_pdf.py`, `diagnose_failures.py`, `analyze_boletos.py`, etc.)

### 30/12/2025

- [x] Correção na análise de linhas digitaveis, priorizando o uso do extractor de boleto.

### 29/12/2025

- [x] Separação de amostras de pdfs para validação de extração de dados.
- [x] Criação do primeiro extrator específico.
- [x] Adicionado a flag de reavaliação no script de validação de extração.

### 26/12/2025 - Dia 10

- [x] **Fazer a limpeza e catalogação dos pdfs na pasta de C:Dados**

### 24/12/2025 - Dia 9

- [x] **Concertar/adicionar a logica de extração das NSFE, DANFES, etc, pra funcionar com os casos falhos.**
    - Suporte completo a múltiplos tipos além de NFSe: **DANFE** e **OUTROS** (faturas/demonstrativos)
    - Roteamento por extrator via `can_handle()` (plugins) para evitar DANFE/OUTROS caindo como NFSe
    - Novos extratores especializados: `DanfeExtractor` e `OutrosExtractor`
    - Novos modelos de dados: `DanfeData` e `OtherDocumentData` (padronizando `DocumentData`)
    - Relatórios/CSVs de validação separados e debug por tipo (incluindo `danfe_sucesso_debug.csv` e `outros_sucesso_debug.csv`)
    - Renomeação do fallback de NFSe: `GenericExtractor` → `NfseGenericExtractor` (módulo legado removido)
    - Correção do script de validação no Windows: stdout/stderr em UTF-8 (evita `UnicodeEncodeError`)
    - OUTROS/Locaweb: preenchimento de `empresa` via fallback por domínio/e-mail quando não existe CNPJ nosso no texto
    - OUTROS/Locação: correção de extração de valor quando aparece como “Total a Pagar no Mês … 2.855,00” (sem “R$”) + teste unitário

### 23/12/2025 - Dia 8

- [x] Focar em um primeiro momento a extração das seguintes colunas [(Data inicio/recebimento do pedido),(setor que fez o pedido aparentemente pode deixar pra la mas se tiver bom),EMPRESA(nós),FORNECEDOR(eles),NF,EMISSÃO,VALOR,VENCIMENTO,]
- [x] Boletos: FORNECEDOR robusto (não captura linha digitável e não fica vazio por falso positivo de "empresa nossa")
- [x] Classificação de boleto mais resiliente a OCR/quebras (keywords corrompidas)

### 22/12/2025 - Dia 7

- [x] Alinhamento dos modelos de extração com o requisitado pra um primeiro momento com PAF
- [x] Refatoração do script de debug_pdf pra ficar condizente com o MVP

### 19/12/2025 - Dia 6

- [x] **Refatoração SOLID completa (production-ready):**
    - Implementados 4 princípios SOLID: LSP, OCP, SRP, DIP
    - Criado módulo `core/exporters.py` com classes separadas (FileSystemManager, AttachmentDownloader, DataExporter)
    - Adicionada classe base `DocumentData` com `doc_type` para extensibilidade (OCP)
    - Implementada injeção de dependências no `BaseInvoiceProcessor` e `run_ingestion.py` (DIP)
    - Padronizado tratamento de erros nas estratégias (LSP)
    - Criado esqueleto de `GoogleSheetsExporter` para futura integração
    - **43/43 testes passando** (14 novos testes SOLID + 23 existentes + 6 estratégias)
    - Documentação completa: `solid_refactoring_report.md` e `solid_usage_guide.md`
    - Projeto agora permite adicionar novos tipos de documento sem modificar código existente
- [x] Validação completa dos 10 boletos extraídos (100% de taxa de sucesso)
- [x] Corrigidos 3 casos críticos de extração:
    - `numero_documento` capturando data em vez do valor correto (layout tabular)
    - `nosso_numero` em layouts multi-linha (label e valor separados por \n)
    - `nosso_numero` quando label está como imagem (fallback genérico)
- [x] Implementados padrões regex robustos com `re.DOTALL` e diferenciação de formatos
- [x] Documentação atualizada: `refactoring_history.md` (Fase 3 e 4 completas) e `extractors.md`
- [x] Criado guia completo de debug de PDFs em `docs/development/debugging_guide.md`
- [x] Criado script avançado de debug `scripts/debug_pdf.py` com:
    - Output colorido, análise de campos, comparação de PDFs
    - Biblioteca de padrões pré-testados, suporte a padrões customizados
    - Detecção automática de quando `re.DOTALL` é necessário

### 18/12/2025 - Dia 5

- [x] Conversar direito com a Melyssa, ou mesmo direto com o Paulo ou o Gustavo a respeito do redirecionamento de emails. Avaliar possíveis soluções e planejar como realmente as NFSE vai estar e em qual email.
- [x] Criado configuração do projeto pra rodar em container.
- [x] Criado módulo centralizado `core/diagnostics.py` para análise de qualidade
- [x] Criado `scripts/_init_env.py` para path resolution centralizado
- [x] Renomeado `test_rules_extractors.py` → `validate_extraction_rules.py` (clareza semântica)
- [x] Removidos comentários redundantes no código (mantendo docstrings importantes)
- [x] Implementado suporte completo para processamento de **Boletos Bancários**
- [x] Sistema identifica e separa automaticamente NFSe de Boletos
- [x] Extração de dados específicos de boletos (linha digitável, vencimento, CNPJ beneficiário, etc.)
- [x] Geração de relatórios separados: `relatorio_nfse.csv` e `relatorio_boletos.csv`
- [x] Criado extrator especializado `BoletoExtractor` com detecção inteligente
- [x] Implementada lógica de vinculação entre boletos e NFSe (por referência, número documento, ou cruzamento de dados)
- [x] Adicionada documentação completa em `docs/guide/boletos.md` e `docs/guide/quickstart_boletos.md`
- [x] Criados scripts de teste e análise (`test_boleto_extractor.py`, `analyze_boletos.py`)

### 17/12/2025 - Dia 4

- [x] Configurar o email para testes em ambiente real de scraping
- [x] **Nota**: Email `scrapper.nfse@gmail.com` configurado com autenticação em `rafael.ferreira@soumaster.com.br` e Google Authenticator

### 16/12/2025 - Dia 3

- [x] Estudar scraping de diferentes tipos de email
- [x] Terminar de organizar a documentação por completo

### 15/12/2025 - Dia 2

- [x] Montar site da documentação (MkDocs)
- [x] Organizar estrutura do projeto

### 11/12/2025 - Dia 1

- [x] Debugar PDFs para entender cada caso
- [x] Extração de dados para CSV baseados em PDFs de diferentes casos

## Instalação

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuração (.env)

Copie o modelo e preencha com suas credenciais IMAP:

```bash
copy .env.example .env  # Windows
# ou
cp .env.example .env    # Linux/macOS
```

Variáveis (ver [.env.example](.env.example)):

- `EMAIL_HOST`
- `EMAIL_USER`
- `EMAIL_PASS`
- `EMAIL_FOLDER`

## Uso (MVP)

### 1) Inspecionar um PDF

Use o script de inspeção para ver os campos extraídos:

```bash
python scripts/inspect_pdf.py "caminho/para/arquivo.pdf"
```

O script busca automaticamente em `failed_cases_pdf/` e `temp_email/`, então você pode passar só o nome:

```bash
python scripts/inspect_pdf.py exemplo.pdf
```

Para ver o texto bruto completo (útil para criar regex):

```bash
python scripts/inspect_pdf.py exemplo.pdf --raw
```

Para ver apenas campos específicos:

```bash
python scripts/inspect_pdf.py exemplo.pdf --fields fornecedor valor vencimento
```

### 2) Validar regras em lote

**Modo legado** (PDFs soltos em `failed_cases_pdf/`):

```bash
python scripts/validate_extraction_rules.py
```

**Modo batch** (lotes com `metadata.json` em `temp_email/`):

```bash
python scripts/validate_extraction_rules.py --batch-mode --apply-correlation
```

### 3) Ingestão via e-mail (gera CSVs)

Baixa anexos, cria lotes e processa com correlação:

```bash
python run_ingestion.py
```

**Flags disponíveis:**

```bash
python run_ingestion.py --reprocess           # Reprocessa lotes existentes
python run_ingestion.py --batch-folder <path> # Processa pasta específica
python run_ingestion.py --subject "NF-e"      # Filtro de assunto customizado
python run_ingestion.py --no-correlation      # Sem correlação (modo legado)
python run_ingestion.py --cleanup             # Remove lotes antigos
```

Saída em `data/output/`:

- `relatorio_nfse.csv`
- `relatorio_boletos.csv`
- `relatorio_danfe.csv`

## Dependências externas (OCR)

Quando o PDF não tem texto selecionável, o pipeline pode cair para OCR.
No Windows, os caminhos padrão são configurados em `config/settings.py` (`TESSERACT_CMD` e `POPPLER_PATH`).

## Estrutura do projeto (resumo)

```
config/          # settings (.env), parâmetros e caminhos
core/            # modelos, processor, batch_processor, correlation_service
  metadata.py    # EmailMetadata (contexto do e-mail)
  batch_processor.py  # Processador de lotes
  batch_result.py     # Resultado de lote
  correlation_service.py  # Correlação DANFE/Boleto
services/        # Serviços de alto nível
  ingestion_service.py  # Ingestão com lotes
extractors/      # extratores por tipo (NFSe/Boleto/DANFE)
strategies/      # estratégias (nativa/ocr/fallback)
ingestors/       # IMAP e utilitários de download
scripts/         # ferramentas utilitárias
  inspect_pdf.py           # Inspeção rápida de PDFs
  validate_extraction_rules.py  # Validação de regras
  example_batch_processing.py   # Exemplos de batch
  test_docker_setup.py     # Teste de setup
temp_email/      # Pastas de lotes (batch folders)
failed_cases_pdf/# PDFs para testes/validação de regras
data/
  output/        # CSVs gerados pela ingestão
  debug_output/  # relatórios de validação (sucesso/falha)
tests/           # suíte de testes (164 testes)
```

📖 Documentação técnica em [docs/](./docs/).
