# Insights e Aprendizados do Projeto

Este documento serve como um "Diário de Bordo" técnico. Aqui registramos descobertas, problemas encontrados com bibliotecas específicas e a racional por trás de decisões técnicas que não são óbvias apenas olhando para o código.

---

## 1. Desafios com OCR e Tesseract

### O Problema da Instalação no Windows
Uma das maiores barreiras de entrada para este projeto foi a dependência do Tesseract OCR. Diferente de bibliotecas Python puras (`pip install`), o Tesseract é um binário externo.
*   **Sintoma:** Erro `TesseractNotFoundError` ou `Path not found`.
*   **Solução:** Foi necessário implementar uma configuração explícita em `config/settings.py` para apontar para o executável (`C:\Program Files\Tesseract-OCR\tesseract.exe`).
*   **Lição:** Para distribuição futura (Docker ou exe), o caminho do Tesseract não pode ser *hardcoded*. Precisamos verificar variáveis de ambiente primeiro.

### Qualidade vs. Velocidade
Testes iniciais mostraram que o Tesseract é lento. Processar um PDF de 1 página leva cerca de 2 a 4 segundos.
*   **Decisão:** O OCR deve ser sempre o **último recurso**. A estratégia `NativePdfStrategy` (usando `pdfplumber`) é instantânea (milissegundos). O sistema de fallback foi desenhado especificamente para priorizar velocidade e só pagar o custo de performance do OCR quando estritamente necessário (arquivos digitalizados).

---

## 2. Extração de Texto: PDFPlumber vs. PyPDF2

Durante a fase de pesquisa (Fase 1), avaliamos bibliotecas de leitura de PDF.
*   **PyPDF2:** Muito popular, mas foca em manipulação de arquivos (cortar, girar, unir). A extração de texto é pobre e perde o layout (espaços em branco).
*   **PDFPlumber:** Foca na extração de dados. Ele mantém a estrutura espacial (tabelas, colunas).
*   **Veredito:** Escolhemos `pdfplumber`. A precisão na detecção de quebras de linha e colunas é crucial para separar "Rótulo" de "Valor" (ex: "CNPJ:" e "12.345...").

---

## 3. Modelagem de Dados e Imutabilidade

Inicialmente, usávamos dicionários Python (`dict`) para passar dados entre funções.
*   **Problema:** Dicionários são frágeis. Não há garantia de que a chave `cnpj` existe, e erros de digitação (`cpnj`) passavam silenciosos até o momento de salvar o CSV.
*   **Solução:** Adoção de `dataclasses` (`core.models.InvoiceData`).
*   **Benefício:** Autocomplete na IDE, tipagem forte (sabemos que `valor` é `float`, não `str`) e garantia de estrutura. Se um campo for adicionado no futuro, a IDE avisa onde precisamos atualizar o código.

---

## 4. Estratégia de Regex (Expressões Regulares)

A extração de valores monetários brasileiros é traiçoeira.
*   Formatos encontrados: `1.234,56`, `1234,56`, `1 234,56`.
*   O ponto (`.`) pode ser separador de milhar ou decimal (em notas internacionais).
*   **Decisão:** Padronizamos uma função de limpeza que remove tudo que não é dígito ou vírgula final, e então converte para float padrão Python (ponto como decimal). Isso centraliza a lógica de conversão em um único lugar, evitando bugs dispersos.
