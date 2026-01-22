"""
Teste do CarrierTelecomExtractor com texto real de PDF.

Este script testa a extração de valores de documentos da Carrier Telecom
que estavam sendo classificados incorretamente como "outros" com valor zero.

Uso:
    python test_carrier_telecom_extractor.py <caminho_do_pdf>

Exemplo:
    python test_carrier_telecom_extractor.py temp_email/email_20260121_080231_81f64f30/01_NFcom_114_CARRIER_TELECOM.pdf
"""

__test__ = False

import sys
import os
import re
import logging
import pdfplumber
from typing import Optional

# Adicionar diretório pai (scrapper) ao path para importações
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Texto de exemplo extraído do PDF "01_NFcom 114 CARRIER TELECOM.pdf"
TEXTO_EXEMPLO = """DOCUMENTO□AUXILIAR□DA□NOTA□FISCAL□FATURA□DE□SERVI□OS□DE□COMUNICA□□O□ELETR□NICA
NOME:□TELCABLES□BRASIL□LTDA□FILIAL□SAO□PAULO
ENDERE□O:□Rua□Irma□Gabriela,□N□□51,□Cidade□Moncoes
CEP:□04.571-130,□Sao□Paulo□-□SP
CPF/CNPJ:□20.609.743/0004-13
INSCRI□□O□ESTADUAL:□141.170.861.118
REFER□NCIA:□11/2025
NOTA FISCAL FATURA: 114
S□RIE: 1 VENCIMENTO:□23/12/2025
DATA DE EMISS□O:
TOTAL□A□PAGAR:□R$□29.250,00
10/11/2025
C□DIGO DO CLIENTE: 100288
N□ TELEFONE: 37999983900
PER□ODO: 01/01/0001 - 01/01/0001
QR□Code□para□pagamento□PIX
CONSULTE PELA CHAVE DE ACESSO EM:
https://dfe-portal.svrs.rs.gov.br/NFCom
CHAVE DE ACESSO:
3525 1120 6097 4300 0413 6200 1000 0001 1410 2827 2913
Protocolo de Autoriza□□o:
3352500028624395 - 10/11/2025 □s 16:34:41
N□□IDENTIFICADOR□DO□D□BITO□AUTOM□TICO
03399.90038□58400.000004□00447.201013□5□13040002925000
□REA□CONTRIBUINTE:
MENSAGENS□PRIORIT□RIAS□/□AVISOS□AO□CONSUMIDOR
ITENS□DA□FATURA UN QUANT PRE□O□UNIT VALOR□TOTAL PIS/COFINS BC□ICMS AL□Q VALOR□ICMS
CNTINT02□-□IP□Transit UN 1,00"""


def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """Extrai texto de um PDF usando pdfplumber."""
    try:
        logger.info(f"Extraindo texto do PDF: {pdf_path}")
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        logger.info(f"Texto extraído ({len(text)} caracteres)")
        return text
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF {pdf_path}: {e}")
        return None


def run_carrier_telecom_extractor_test(text: str) -> dict:
    """Testa o CarrierTelecomExtractor com o texto fornecido."""
    try:
        from extractors.carrier_telecom import CarrierTelecomExtractor

        logger.info("Testando CarrierTelecomExtractor...")
        extractor = CarrierTelecomExtractor()

        # Testar can_handle
        can_handle = extractor.can_handle(text)
        logger.info(f"can_handle: {can_handle}")

        if not can_handle:
            return {"error": "CarrierTelecomExtractor não reconheceu o documento"}

        # Extrair dados
        data = extractor.extract(text)

        # Verificar se valor foi extraído
        valor_total = data.get("valor_total", 0)
        if valor_total > 0:
            logger.info(f"✅ VALOR TOTAL EXTRAÍDO: R$ {valor_total:,.2f}")
        else:
            logger.warning("❌ Valor total não extraído ou zero")

        return {
            "success": valor_total > 0,
            "can_handle": can_handle,
            "data": data,
            "valor_total": valor_total,
        }

    except ImportError as e:
        logger.error(f"Erro ao importar CarrierTelecomExtractor: {e}")
        return {"error": f"Erro de importação: {e}"}
    except Exception as e:
        logger.error(f"Erro ao testar CarrierTelecomExtractor: {e}")
        return {"error": f"Erro: {e}"}


def run_other_extractors_test(text: str) -> dict:
    """Testa outros extratores para ver qual reconheceria o documento."""
    logger.info("Testando outros extratores...")

    results = {}
    extractors_to_test = [
        ("OutrosExtractor", "extractors.outros", "OutrosExtractor"),
        ("NfseGenericExtractor", "extractors.nfse_generic", "NfseGenericExtractor"),
        (
            "AdminDocumentExtractor",
            "extractors.admin_document",
            "AdminDocumentExtractor",
        ),
        ("DanfeExtractor", "extractors.danfe", "DanfeExtractor"),
        ("BoletoExtractor", "extractors.boleto", "BoletoExtractor"),
    ]

    for name, module, class_name in extractors_to_test:
        try:
            module_obj = __import__(module, fromlist=[class_name])
            extractor_class = getattr(module_obj, class_name)
            extractor = extractor_class()
            can_handle = extractor.can_handle(text)
            results[name] = can_handle
            logger.info(f"  {name}: {can_handle}")
        except Exception as e:
            logger.warning(f"  {name}: ERRO - {e}")
            results[name] = f"ERROR: {e}"

    return results


def analyze_text_for_values(text: str) -> dict:
    """Analisa o texto para encontrar padrões de valores."""
    logger.info("Analisando texto para valores...")

    analysis = {
        "text_length": len(text),
        "contains_total_a_pagar": False,
        "contains_valor_total": False,
        "money_patterns_found": [],
        "extracted_values": [],
    }

    # Verificar padrões específicos
    text_upper = text.upper()
    analysis["contains_total_a_pagar"] = (
        "TOTAL A PAGAR" in text_upper or "TOTAL□A□PAGAR" in text_upper
    )
    analysis["contains_valor_total"] = "VALOR TOTAL" in text_upper

    # Procurar padrões monetários
    money_patterns = [
        r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*REAIS",
        r"TOTAL\s*A\s*PAGAR.*?(\d{1,3}(?:\.\d{3})*,\d{2})",
    ]

    for pattern in money_patterns:
        matches = re.findall(pattern, text_upper, re.IGNORECASE)
        if matches:
            analysis["money_patterns_found"].append(
                {"pattern": pattern, "matches": matches}
            )

    # Extrair todos os valores no formato brasileiro
    br_money_regex = r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b"
    analysis["extracted_values"] = re.findall(br_money_regex, text)

    logger.info(f"  Tamanho do texto: {analysis['text_length']} caracteres")
    logger.info(f"  Contém 'TOTAL A PAGAR': {analysis['contains_total_a_pagar']}")
    logger.info(f"  Contém 'VALOR TOTAL': {analysis['contains_valor_total']}")
    logger.info(f"  Valores encontrados: {analysis['extracted_values']}")

    return analysis


def main():
    """Função principal."""
    if len(sys.argv) > 1:
        # Testar com arquivo PDF
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(f"❌ Arquivo não encontrado: {pdf_path}")
            sys.exit(1)

        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"❌ Falha ao extrair texto do PDF")
            sys.exit(1)

        print(f"📄 Testando arquivo: {pdf_path}")
    else:
        # Usar texto de exemplo
        text = TEXTO_EXEMPLO
        print("📄 Testando com texto de exemplo")

    print("=" * 80)

    # Analisar texto
    analysis = analyze_text_for_values(text)

    print("\n🧪 TESTE DO CARRIER TELECOM EXTRACTOR")
    print("-" * 40)

    # Testar CarrierTelecomExtractor
    carrier_result = run_carrier_telecom_extractor_test(text)

    print("\n🔍 TESTE DE OUTROS EXTRATORES")
    print("-" * 40)

    # Testar outros extratores
    other_results = run_other_extractors_test(text)

    print("\n📊 RESUMO")
    print("=" * 80)

    # Imprimir resumo
    if "error" in carrier_result:
        print(f"❌ ERRO: {carrier_result['error']}")
    else:
        if carrier_result["success"]:
            print(
                f"✅ SUCESSO: Valor total extraído = R$ {carrier_result['valor_total']:,.2f}"
            )
        else:
            print(
                f"❌ FALHA: Valor total não foi extraído (valor = R$ {carrier_result['valor_total']:,.2f})"
            )

    # Imprimir resultados dos outros extratores
    print(f"\n📋 Outros extratores que reconheceriam este documento:")
    for name, result in other_results.items():
        if result is True:
            print(f"  ⚠️  {name}: SIM (risco de classificação incorreta)")
        elif isinstance(result, str) and "ERROR" in result:
            print(f"  🔧 {name}: ERRO")
        else:
            print(f"  ✅ {name}: NÃO")

    # Imprimir análise detalhada
    print(f"\n📈 ANÁLISE DO TEXTO:")
    print(f"  Tamanho: {analysis['text_length']} caracteres")
    print(f"  Contém 'TOTAL A PAGAR': {analysis['contains_total_a_pagar']}")

    if analysis["extracted_values"]:
        print(f"  Valores encontrados no texto:")
        for i, value in enumerate(analysis["extracted_values"][:5]):
            print(f"    {i + 1}. {value}")
        if len(analysis["extracted_values"]) > 5:
            print(f"    ... e mais {len(analysis['extracted_values']) - 5} valores")
    else:
        print(f"  ❌ Nenhum valor encontrado no texto!")

    # Imprimir amostra do texto (primeiros 500 caracteres)
    print(f"\n📝 AMOSTRA DO TEXTO (primeiros 500 caracteres):")
    print("-" * 40)
    print(text[:500])
    if len(text) > 500:
        print("...")

    print("=" * 80)

    # Salvar resultados em arquivo
    output_file = "test_carrier_results.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            f"TESTE DE EXTRAÇÃO - {pdf_path if len(sys.argv) > 1 else 'Texto de exemplo'}\n"
        )
        f.write("=" * 80 + "\n")
        f.write(
            f"\nResultado CarrierTelecomExtractor: {'SUCESSO' if carrier_result.get('success') else 'FALHA'}\n"
        )
        if carrier_result.get("valor_total"):
            f.write(f"Valor total extraído: R$ {carrier_result['valor_total']:,.2f}\n")

        f.write("\nDados completos extraídos:\n")
        if carrier_result.get("data"):
            for key, value in carrier_result["data"].items():
                if value:
                    f.write(f"  {key}: {value}\n")

    print(f"\n📁 Relatório salvo em: {output_file}")


if __name__ == "__main__":
    main()
