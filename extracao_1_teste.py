import pdfplumber
import pandas as pd

# Nome do arquivo PDF de entrada
arquivo_pdf = "nfs/nfse_456392017301641.pdf"
lista_dados = []

with pdfplumber.open(arquivo_pdf) as pdf:
    # Itera sobre todas as páginas
    for page in pdf.pages:
        # Tenta extrair a tabela da página
        # O método extract_table() retorna uma lista de listas
        tabela = page.extract_table()
        
        if tabela:
            # Adiciona as linhas extraídas na nossa lista geral
            for linha in tabela:
                lista_dados.append(linha)

# Se encontrou dados
if lista_dados:
    # Cria o DataFrame. Assume que a primeira linha é o cabeçalho.
    # Se o cabeçalho se repete em toda página, precisaremos tratar isso depois.
    df = pd.DataFrame(lista_dados[1:], columns=lista_dados[0])
    
    # Salva em CSV
    df.to_csv("dados_extraidos.csv", index=False, encoding="utf-8-sig") # utf-8-sig para abrir certo no Excel
    print("Sucesso! CSV criado.")
else:
    print("Nenhuma tabela encontrada automaticamente.")