# Guia de Testes Automatizados

Este documento descreve como executar e expandir a suíte de testes do projeto.

## Visão Geral

Utilizamos o framework nativo `unittest` do Python. Os testes estão localizados na pasta `tests/` e cobrem:

1.  **Estratégias de Leitura (`test_strategies.py`):** Valida se o `pdfplumber` e o fallback para OCR estão funcionando.
2.  **Ingestão de E-mail (`test_ingestion.py`):** Simula a conexão IMAP e o download de anexos (usando Mocks).

## Executando os Testes

Para rodar todos os testes de uma vez:

```bash
python -m unittest discover tests
```

### Saída Esperada

Se tudo estiver correto, você verá uma saída similar a esta:

```text
......
----------------------------------------------------------------------
Ran 6 tests in 0.113s

OK
```

## Estrutura dos Testes

### 1. Testes de Estratégia (`test_strategies.py`)
Verifica se a lógica de extração de texto está resiliente.

*   `test_extract_success`: Garante que PDFs legíveis retornam texto.
*   `test_extract_fallback_empty_text`: Garante que PDFs vazios/imagens retornam string vazia (para acionar o OCR).
*   `test_extract_file_error`: Garante que o sistema não trava com arquivos corrompidos.

### 2. Testes de Ingestão (`test_ingestion.py`)
Verifica a integração com e-mail sem precisar de credenciais reais.

*   `test_connect`: Verifica se os parâmetros de host/user/pass são passados corretamente para o `imaplib`.
*   `test_fetch_attachments_success`: Simula uma resposta do servidor IMAP contendo um PDF e verifica se o parser extrai o anexo corretamente.
*   `test_save_bytes_to_disk_with_unique_name`: **Crítico.** Verifica se a lógica de salvar arquivos temporários gera nomes únicos (UUID) para evitar sobrescrita de arquivos com mesmo nome (ex: `invoice.pdf`).

## Criando Novos Testes

Ao adicionar uma nova funcionalidade, crie um arquivo `test_nova_funcionalidade.py` na pasta `tests/`.

Exemplo de teste unitário simples:

```python
import unittest
from minha_nova_feature import minha_funcao

class TestMinhaFeature(unittest.TestCase):
    def test_caso_sucesso(self):
        resultado = minha_funcao(10)
        self.assertEqual(resultado, 20)
```
