# Projeto de Scraping  de notas fiscais eletrônicas

# To Do
- [ ] Conseguir o acesso ao maior número de pdfs e a tabela de verdades já catalogada dos dados pra conferir se a extração do PDF está de fato funcionando.
- [ ] Verificar cada caso a fundo dos pdfs e avaliar possíveis estratégias para os casos onde o pdf em si não esta anexado no email (link de prefeitura ou redirecionador de terceiros).
- [ ] Conversar direito com a Melyssa, ou mesmo direto com o Paulo ou o Gustavo a respeito do redirecionamento de emails. Avaliar possíveis soluções e planejar como realmente as NFSE vai estar e em qual email.
- [ ] Modelar o projeto pra rodar em servidor, organizar a docker file e descobrir como subir isso em produção do jeito certo!




# Done

## 18/12/2025 - Refatoração e Organização Completa

### 🔄 Refatoração de Código
- [x] Criado módulo centralizado `core/diagnostics.py` para análise de qualidade
- [x] Eliminadas ~120 linhas de código duplicado entre scripts
- [x] Criado `scripts/_init_env.py` para path resolution centralizado
- [x] Refatorados 5 scripts para usar módulos centralizados
- [x] Renomeado `test_rules_extractors.py` → `validate_extraction_rules.py` (clareza semântica)
- [x] Removidos comentários redundantes no código (mantendo docstrings importantes)

### 🧪 Testes Unitários
- [x] Criada suite completa de testes em `tests/test_extractors.py`
- [x] Implementados 23 testes unitários (todos passando ✅)
- [x] Cobertura de: GenericExtractor, BoletoExtractor, roteamento, edge cases
- [x] Testes executam em ~0.13s

### 📚 Documentação Profissional
- [x] Refatorada estrutura de documentação em subpastas organizadas
- [x] Criada pasta `docs/api/` com 5 páginas especializadas:
  - `overview.md` - Visão geral + diagrama Mermaid do fluxo
  - `core.md` - Módulos centrais (Processor, Models, Interfaces, Exceções)
  - `extractors.md` - Extratores (Generic, Boleto) com exemplos
  - `strategies.md` - Estratégias (Native, OCR, Fallback) com benchmarks
  - `diagnostics.md` - Sistema de qualidade e validação
- [x] Criada seção "Desenvolvimento" em `docs/development/`
- [x] Movidos arquivos MD da raiz para `docs/` (organização)
- [x] Mantidos apenas `README.md` e `reuniao.md` na raiz
- [x] Atualizado `mkdocs.yml` com navegação hierárquica
- [x] Documentação com diagramas Mermaid, exemplos de código e tabelas comparativas

### 📊 Qualidade do Projeto
- [x] Zero erros de lint no código
- [x] Estrutura modular e extensível
- [x] Separação clara de responsabilidades
- [x] Documentação inline com docstrings completas
- [x] Site de documentação profissional (MkDocs)

### 🎯 Melhorias de Arquitetura
- [x] Redundâncias estratégicas mantidas (Strategy Pattern, validação em camadas)
- [x] Lógica de negócio centralizada em módulos reutilizáveis
- [x] Scripts simplificados e DRY (Don't Repeat Yourself)
- [x] Facilidade para adicionar novos extratores e estratégias

### 🎉 Processamento de Boletos
- [x] Implementado suporte completo para processamento de **Boletos Bancários**
- [x] Sistema identifica e separa automaticamente NFSe de Boletos
- [x] Extração de dados específicos de boletos (linha digitável, vencimento, CNPJ beneficiário, etc.)
- [x] Geração de relatórios separados: `relatorio_nfse.csv` e `relatorio_boletos.csv`
- [x] Criado extrator especializado `BoletoExtractor` com detecção inteligente
- [x] Implementada lógica de vinculação entre boletos e NFSe (por referência, número documento, ou cruzamento de dados)
- [x] Adicionada documentação completa em `docs/guide/boletos.md` e `docs/guide/quickstart_boletos.md`
- [x] Criados scripts de teste e análise (`test_boleto_extractor.py`, `analyze_boletos.py`)

## 17/12/2025
- [x] Configurar o email para testes em ambiente real de scraping
- [x] **Nota**: Email `scrapper.nfse@gmail.com` configurado com autenticação em `rafael.ferreira@soumaster.com.br` e Google Authenticator

## 16/12/2025
- [x] Estudar scraping de diferentes tipos de email
- [x] Terminar de organizar a documentação por completo

## 15/12/2025
- [x] Montar site da documentação (MkDocs)
- [x] Organizar estrutura do projeto

## 11/12/2025
- [x] Debugar PDFs para entender cada caso
- [x] Extração de dados para CSV baseados em PDFs de diferentes casos


# Oque eu to focando em pesquisar por agora
- Validar a extração de dados do pdf. 
- Identificar adição de abordagem de extração de xml. 
- Configuração dos imaps e testar o scrapping em um email real.

# Dificuldades até o momento
Boa parte dos erros foram relacionados ao Regex, estudar mais a fundo e procurar fazer testes com casos mais complexos para ir adicionando mais palavras ao dicionário de Regex.
Durante o planejamento do projeto avaliar a necessidade de separar uma fila de processamentos de pdfs que são imagens do OCR e tesseract por conta do alto tempo de execução, pra um caso já esta demorando 30 segundos na versão atual do código.

# Informações gerais do projeto e requisitos

## Tipos de Documentos Suportados

O sistema processa automaticamente dois tipos de documentos:

### 1. NFSe (Nota Fiscal de Serviço Eletrônica)
**Dados extraídos:**
- `arquivo_origem` - Nome do arquivo PDF
- `cnpj_prestador` - CNPJ do prestador de serviço
- `numero_nota` - Número da nota fiscal
- `data_emissao` - Data de emissão (YYYY-MM-DD)
- `valor_total` - Valor total da nota
- `texto_bruto` - Snippet do texto extraído

**Saída:** `data/output/relatorio_nfse.csv`

### 2. Boletos Bancários
**Dados extraídos:**
- `arquivo_origem` - Nome do arquivo PDF
- `cnpj_beneficiario` - CNPJ do beneficiário (quem recebe)
- `valor_documento` - Valor nominal do boleto
- `vencimento` - Data de vencimento (YYYY-MM-DD)
- `numero_documento` - Número do documento/fatura
- `linha_digitavel` - Código de barras do boleto
- `nosso_numero` - Identificação interna do banco
- `referencia_nfse` - Número da NFSe (se mencionado no boleto)
- `texto_bruto` - Snippet do texto extraído

**Saída:** `data/output/relatorio_boletos.csv`

### Vinculação de Boletos e NFSe

O sistema pode vincular boletos às suas notas fiscais através de:
1. **Referência explícita** - Campo `referencia_nfse` no boleto
2. **Número do documento** - Muitos fornecedores usam o nº da NF
3. **Cruzamento de dados** - CNPJ + Valor + Data aproximada

Consulte [docs/guide/boletos.md](docs/guide/boletos.md) para exemplos detalhados.

## Estrutura do projeto

```
scrapper/
│
├── config/                     # Configurações (settings.py + .env)
├── core/                       # Módulos centrais
│   ├── processor.py            # Orquestrador principal
│   ├── models.py               # InvoiceData, BoletoData
│   ├── extractors.py           # Classe base para extratores
│   ├── diagnostics.py          # Sistema de análise de qualidade ✨ NOVO
│   ├── interfaces.py           # Contratos e interfaces
│   └── exceptions.py           # Exceções customizadas
│
├── extractors/                 # Extratores especializados
│   ├── generic.py              # NFSe genéricas (regex)
│   └── boleto.py               # Boletos bancários
│
├── strategies/                 # Estratégias de extração de texto
│   ├── native.py               # PDFPlumber (rápido)
│   ├── ocr.py                  # Tesseract OCR
│   └── fallback.py             # Fallback automático
│
├── ingestors/                  # Conectores de entrada
│   └── imap.py                 # Ingestão via e-mail IMAP
│
├── scripts/                    # Scripts utilitários
│   ├── _init_env.py            # Path resolution centralizado ✨ NOVO
│   ├── validate_extraction_rules.py  # Validação de regras (renomeado)
│   ├── diagnose_failures.py    # Análise de falhas (refatorado)
│   ├── analyze_boletos.py      # Análise estatística de boletos
│   ├── move_failed_files.py    # Move PDFs com falha
│   └── test_boleto_extractor.py # Teste do extrator de boletos
│
├── tests/                      # Testes unitários ✨ NOVO
│   └── test_extractors.py      # 23 testes (GenericExtractor, BoletoExtractor)
│
├── docs/                       # Documentação MkDocs ✨ REORGANIZADA
│   ├── index.md                # Home
│   ├── api/                    # Referência técnica (5 páginas)
│   │   ├── overview.md         # Visão geral + diagrama
│   │   ├── core.md             # Módulos centrais
│   │   ├── extractors.md       # Extratores
│   │   ├── strategies.md       # Estratégias
│   │   └── diagnostics.md      # Sistema de qualidade
│   ├── guide/                  # Guias de uso
│   ├── research/               # Arquitetura e pesquisa
│   └── development/            # Histórico de desenvolvimento
│
├── data/                       # Dados
│   ├── debug_output/           # CSVs de validação (sucesso/falha)
│   └── output/                 # Relatórios finais (NFSe + Boletos)
│
├── nfs/                        # PDFs para análise manual
├── temp_email/                 # Buffer temporário de downloads
├── failed_cases_pdf/           # Casos de teste para validação
│
├── main.py                     # Script de processamento local
├── run_ingestion.py            # Script de ingestão de e-mail
├── mkdocs.yml                  # Configuração da documentação
└── requirements.txt            # Dependências Python
```

# Guia Rápido

## Instalação

1.  Clone o repositório e crie o ambiente virtual:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    .venv\Scripts\activate     # Windows
    ```

2.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure a segurança:
    *   Copie `.env.example` para `.env`.
    *   Preencha suas credenciais de e-mail no `.env`.

## Como Usar

*   **Ingestão de E-mail:** `python run_ingestion.py` (Baixa e processa notas do e-mail).
*   **Processamento Local:** `python main.py` (Processa arquivos da pasta `nfs/`).
*   **Documentação:** `mkdocs serve` (Abre o site da documentação localmente).

## 1. Automação de Entradas de NFe

### ORQUESTRAÇÃO
- Programar rotinas de varredura do email e integrar com fonte de contratos
- ELT

### Requisitos
- [ ] Ler e-mails com NF
- [ ] Categorizar e digitalizar informações
- [ ] Ler tabela verdade de Contratos e Pedidos
- [ ] Comparar informações de NF de entrada e informações da tabela
- [ ] Criar tabela de input de dados