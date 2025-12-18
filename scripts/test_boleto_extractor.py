"""
Script de Teste para Extração de Boletos

Testa o novo BoletoExtractor com exemplos de texto simulado.
"""

from _init_env import setup_project_path
setup_project_path()

from extractors.boleto import BoletoExtractor
from extractors.generic import GenericExtractor

# Exemplo de texto de um boleto
texto_boleto = """
BANCO DO BRASIL S.A.

Beneficiário: EMPRESA EXEMPLO LTDA
CNPJ: 12.345.678/0001-90

Linha Digitável: 00190.00009 02828.282828 28282.828282 8 99990000012345

Vencimento: 31/12/2025
Valor do Documento: R$ 1.500,00

Número do Documento: 98765
Nosso Número: 12345678-9

Observações: Ref. NF 54321
"""

# Exemplo de texto de NFSe
texto_nfse = """
PREFEITURA MUNICIPAL DE SÃO PAULO
NOTA FISCAL DE SERVIÇO ELETRÔNICA - NFS-e

Número da Nota: 12345
CNPJ Prestador: 98.765.432/0001-10
Data de Emissão: 15/12/2025
Valor Total: R$ 2.000,00
"""

print("=" * 60)
print("TESTE DE IDENTIFICAÇÃO DE DOCUMENTOS")
print("=" * 60)

# Teste 1: Verificar se identifica boleto corretamente
print("\n[Teste 1] Identificando Boleto...")
if BoletoExtractor.can_handle(texto_boleto):
    print("✅ BoletoExtractor reconheceu o boleto")
    extractor = BoletoExtractor()
    dados = extractor.extract(texto_boleto)
    print(f"  - Tipo: {dados.get('tipo_documento')}")
    print(f"  - CNPJ Beneficiário: {dados.get('cnpj_beneficiario')}")
    print(f"  - Valor: R$ {dados.get('valor_documento'):.2f}")
    print(f"  - Vencimento: {dados.get('vencimento')}")
    print(f"  - Nº Documento: {dados.get('numero_documento')}")
    print(f"  - Linha Digitável: {dados.get('linha_digitavel')}")
    print(f"  - Referência NFSe: {dados.get('referencia_nfse')}")
else:
    print("❌ BoletoExtractor NÃO reconheceu o boleto")

# Teste 2: Verificar se não identifica NFSe como boleto
print("\n[Teste 2] Diferenciando NFSe de Boleto...")
if BoletoExtractor.can_handle(texto_nfse):
    print("❌ BoletoExtractor identificou NFSe como boleto (ERRO)")
else:
    print("✅ BoletoExtractor corretamente rejeitou a NFSe")

if GenericExtractor.can_handle(texto_nfse):
    print("✅ GenericExtractor reconheceu a NFSe")
    extractor = GenericExtractor()
    dados = extractor.extract(texto_nfse)
    print(f"  - CNPJ Prestador: {dados.get('cnpj_prestador')}")
    print(f"  - Número Nota: {dados.get('numero_nota')}")
    print(f"  - Valor: R$ {dados.get('valor_total'):.2f}")

print("\n" + "=" * 60)
print("TESTES CONCLUÍDOS")
print("=" * 60)
