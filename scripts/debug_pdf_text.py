import sys
import os
import re
import logging
from typing import Dict, List, Optional, Tuple

# Adicionar diretório pai ao path para importações
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """Extrai texto do PDF usando a mesma estratégia do sistema."""
    try:
        from strategies.fallback import SmartExtractionStrategy

        reader = SmartExtractionStrategy()
        text = reader.extract(pdf_path)
        return text
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF {pdf_path}: {e}")
        return None


def analyze_text_for_values(text: str) -> Dict[str, any]:
    """Analisa o texto para encontrar valores monetários e padrões."""
    if not text:
        return {}

    analysis = {
        "text_length": len(text),
        "first_500_chars": text[:500],
        "value_patterns_found": [],
        "nfse_indicators": [],
        "danfe_indicators": [],
        "boleto_indicators": [],
        "other_indicators": [],
        "monetary_values": [],
    }

    text_upper = text.upper()

    # Procurar padrões de NFSE
    nfse_patterns = [
        "NFS-E",
        "NFSE",
        "NOTA FISCAL DE SERVIÇO",
        "NOTA FISCAL DE SERVICO",
        "DOCUMENTO AUXILIAR DA NOTA FISCAL",
        "DOCUMENTO AUXILIAR DA NFS-E",
        "PREFEITURA MUNICIPAL",
        "CÓDIGO DE VERIFICAÇÃO",
        "CODIGO DE VERIFICACAO",
    ]
    analysis["nfse_indicators"] = [p for p in nfse_patterns if p in text_upper]

    # Procurar padrões de DANFE
    danfe_patterns = [
        "DANFE",
        "CHAVE DE ACESSO",
        "NF-E",
        "NFE",
        "DOCUMENTO AUXILIAR DA NFE",
    ]
    analysis["danfe_indicators"] = [p for p in danfe_patterns if p in text_upper]

    # Procurar padrões de boleto
    boleto_patterns = [
        "LINHA DIGITÁVEL",
        "LINHA DIGITAVEL",
        "BENEFICIÁRIO",
        "BENEFICIARIO",
        "CÓDIGO DE BARRAS",
        "CODIGO DE BARRAS",
        "CEDENTE",
    ]
    analysis["boleto_indicators"] = [p for p in boleto_patterns if p in text_upper]

    # Procurar padrões de outros documentos
    other_patterns = [
        "DEMONSTRATIVO",
        "LOCAÇÃO",
        "LOCACAO",
        "FATURA",
        "CONTRATO",
        "LOCAWEB",
    ]
    analysis["other_indicators"] = [p for p in other_patterns if p in text_upper]

    # Procurar valores monetários
    # Padrões de valores monetários em R$
    value_patterns = [
        r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"VALOR\s+TOTAL\s*[:\s]*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"VALOR\s+DA\s+NOTA\s*[:\s]*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"TOTAL\s*[:\s]*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*REAIS",
        r"(\d{1,3}(?:\.\d{3})*,\d{2})",
    ]

    for pattern in value_patterns:
        matches = re.findall(pattern, text_upper)
        if matches:
            analysis["value_patterns_found"].append(
                {"pattern": pattern, "matches": matches}
            )

    # Extrair valores numéricos que podem ser monetários
    money_regex = r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b"
    matches = re.findall(money_regex, text)
    if matches:
        analysis["monetary_values"] = matches

    return analysis


def test_extractors_on_text(text: str) -> Dict[str, any]:
    """Testa todos os extratores no texto."""
    results = {}

    try:
        from extractors.boleto_repromaq import BoletoRepromaqExtractor

        extractor = BoletoRepromaqExtractor()
        results["BoletoRepromaqExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "BoletoRepromaqExtractor",
        }
    except Exception as e:
        results["BoletoRepromaqExtractor"] = {"error": str(e)}

    try:
        from extractors.emc_fatura import EmcFaturaExtractor

        extractor = EmcFaturaExtractor()
        results["EmcFaturaExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "EmcFaturaExtractor",
        }
    except Exception as e:
        results["EmcFaturaExtractor"] = {"error": str(e)}

    try:
        from extractors.net_center import NetCenterExtractor

        extractor = NetCenterExtractor()
        results["NetCenterExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "NetCenterExtractor",
        }
    except Exception as e:
        results["NetCenterExtractor"] = {"error": str(e)}

    try:
        from extractors.nfse_custom_montes_claros import NfseCustomMontesClarosExtractor

        extractor = NfseCustomMontesClarosExtractor()
        results["NfseCustomMontesClarosExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "NfseCustomMontesClarosExtractor",
        }
    except Exception as e:
        results["NfseCustomMontesClarosExtractor"] = {"error": str(e)}

    try:
        from extractors.nfse_custom_vila_velha import NfseCustomVilaVelhaExtractor

        extractor = NfseCustomVilaVelhaExtractor()
        results["NfseCustomVilaVelhaExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "NfseCustomVilaVelhaExtractor",
        }
    except Exception as e:
        results["NfseCustomVilaVelhaExtractor"] = {"error": str(e)}

    try:
        from extractors.sicoob import SicoobExtractor

        extractor = SicoobExtractor()
        results["SicoobExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "SicoobExtractor",
        }
    except Exception as e:
        results["SicoobExtractor"] = {"error": str(e)}

    try:
        from extractors.admin_document import AdminDocumentExtractor

        extractor = AdminDocumentExtractor()
        results["AdminDocumentExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "AdminDocumentExtractor",
        }
    except Exception as e:
        results["AdminDocumentExtractor"] = {"error": str(e)}

    try:
        from extractors.outros import OutrosExtractor

        extractor = OutrosExtractor()
        results["OutrosExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "OutrosExtractor",
        }
    except Exception as e:
        results["OutrosExtractor"] = {"error": str(e)}

    try:
        from extractors.nfse_generic import NfseGenericExtractor

        extractor = NfseGenericExtractor()
        results["NfseGenericExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "NfseGenericExtractor",
        }
    except Exception as e:
        results["NfseGenericExtractor"] = {"error": str(e)}

    try:
        from extractors.boleto import BoletoExtractor

        extractor = BoletoExtractor()
        results["BoletoExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "BoletoExtractor",
        }
    except Exception as e:
        results["BoletoExtractor"] = {"error": str(e)}

    try:
        from extractors.danfe import DanfeExtractor

        extractor = DanfeExtractor()
        results["DanfeExtractor"] = {
            "can_handle": extractor.can_handle(text),
            "class": "DanfeExtractor",
        }
    except Exception as e:
        results["DanfeExtractor"] = {"error": str(e)}

    return results


def run_extraction_and_analyze(pdf_path: str) -> Dict[str, any]:
    """Executa extração completa e análise do PDF."""
    if not os.path.exists(pdf_path):
        logger.error(f"Arquivo não encontrado: {pdf_path}")
        return {"error": "Arquivo não encontrado"}

    logger.info(f"Analisando PDF: {pdf_path}")

    # 1. Extrair texto
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return {"error": "Falha na extração de texto"}

    # 2. Analisar texto
    text_analysis = analyze_text_for_values(text)

    # 3. Testar extratores
    extractor_results = test_extractors_on_text(text)

    # 4. Executar extrator selecionado
    selected_extractor = None
    extraction_data = None

    # Ordem de prioridade dos extratores
    extractor_order = [
        "BoletoRepromaqExtractor",
        "EmcFaturaExtractor",
        "NetCenterExtractor",
        "NfseCustomMontesClarosExtractor",
        "NfseCustomVilaVelhaExtractor",
        "SicoobExtractor",
        "AdminDocumentExtractor",
        "OutrosExtractor",
        "NfseGenericExtractor",
        "BoletoExtractor",
        "DanfeExtractor",
    ]

    for extractor_name in extractor_order:
        if extractor_name in extractor_results:
            result = extractor_results[extractor_name]
            if result.get("can_handle", False):
                try:
                    # Importar e instanciar extrator
                    module_name = extractor_name.lower()
                    class_name = extractor_name

                    if extractor_name == "BoletoRepromaqExtractor":
                        from extractors.boleto_repromaq import BoletoRepromaqExtractor

                        extractor = BoletoRepromaqExtractor()
                    elif extractor_name == "EmcFaturaExtractor":
                        from extractors.emc_fatura import EmcFaturaExtractor

                        extractor = EmcFaturaExtractor()
                    elif extractor_name == "NetCenterExtractor":
                        from extractors.net_center import NetCenterExtractor

                        extractor = NetCenterExtractor()
                    elif extractor_name == "NfseCustomMontesClarosExtractor":
                        from extractors.nfse_custom_montes_claros import (
                            NfseCustomMontesClarosExtractor,
                        )

                        extractor = NfseCustomMontesClarosExtractor()
                    elif extractor_name == "NfseCustomVilaVelhaExtractor":
                        from extractors.nfse_custom_vila_velha import (
                            NfseCustomVilaVelhaExtractor,
                        )

                        extractor = NfseCustomVilaVelhaExtractor()
                    elif extractor_name == "SicoobExtractor":
                        from extractors.sicoob import SicoobExtractor

                        extractor = SicoobExtractor()
                    elif extractor_name == "AdminDocumentExtractor":
                        from extractors.admin_document import AdminDocumentExtractor

                        extractor = AdminDocumentExtractor()
                    elif extractor_name == "OutrosExtractor":
                        from extractors.outros import OutrosExtractor

                        extractor = OutrosExtractor()
                    elif extractor_name == "NfseGenericExtractor":
                        from extractors.nfse_generic import NfseGenericExtractor

                        extractor = NfseGenericExtractor()
                    elif extractor_name == "BoletoExtractor":
                        from extractors.boleto import BoletoExtractor

                        extractor = BoletoExtractor()
                    elif extractor_name == "DanfeExtractor":
                        from extractors.danfe import DanfeExtractor

                        extractor = DanfeExtractor()
                    else:
                        continue

                    selected_extractor = extractor_name
                    extraction_data = extractor.extract(text)
                    break
                except Exception as e:
                    logger.error(f"Erro ao extrair dados com {extractor_name}: {e}")

    return {
        "pdf_path": pdf_path,
        "text_sample": text[:1000],
        "text_analysis": text_analysis,
        "extractor_results": extractor_results,
        "selected_extractor": selected_extractor,
        "extraction_data": extraction_data,
        "text_length": len(text),
    }


def print_analysis_report(analysis: Dict[str, any]):
    """Imprime relatório detalhado da análise."""
    print("=" * 80)
    print(f"ANÁLISE DO PDF: {analysis.get('pdf_path', 'N/A')}")
    print("=" * 80)

    print(f"\n📄 INFORMAÇÕES DO TEXTO:")
    print(f"   Tamanho do texto: {analysis.get('text_length', 0)} caracteres")

    text_sample = analysis.get("text_sample", "")
    if text_sample:
        print(f"\n   Amostra do texto (primeiros 1000 caracteres):")
        print(f"   {'-' * 40}")
        print(f"   {text_sample[:500]}")
        if len(text_sample) > 500:
            print(f"   ...")
            print(f"   {text_sample[500:1000]}")

    # Análise de texto
    text_analysis = analysis.get("text_analysis", {})
    if text_analysis:
        print(f"\n🔍 INDICADORES ENCONTRADOS:")

        if text_analysis.get("nfse_indicators"):
            print(f"   ✅ NFSE: {', '.join(text_analysis['nfse_indicators'])}")
        else:
            print(f"   ❌ NFSE: Nenhum indicador encontrado")

        if text_analysis.get("danfe_indicators"):
            print(f"   ✅ DANFE: {', '.join(text_analysis['danfe_indicators'])}")
        else:
            print(f"   ❌ DANFE: Nenhum indicador encontrado")

        if text_analysis.get("boleto_indicators"):
            print(f"   ✅ Boleto: {', '.join(text_analysis['boleto_indicators'])}")
        else:
            print(f"   ❌ Boleto: Nenhum indicador encontrado")

        if text_analysis.get("other_indicators"):
            print(f"   ✅ Outros: {', '.join(text_analysis['other_indicators'])}")
        else:
            print(f"   ❌ Outros: Nenhum indicador encontrado")

        # Valores monetários
        monetary_values = text_analysis.get("monetary_values", [])
        if monetary_values:
            print(f"\n💰 VALORES MONETÁRIOS ENCONTRADOS:")
            for value in monetary_values[:10]:  # Mostrar apenas os primeiros 10
                print(f"   - {value}")
            if len(monetary_values) > 10:
                print(f"   ... e mais {len(monetary_values) - 10} valores")
        else:
            print(f"\n💰 VALORES MONETÁRIOS: Nenhum valor encontrado")

    # Resultados dos extratores
    print(f"\n🧪 RESULTADOS DOS EXTRATORES:")
    extractor_results = analysis.get("extractor_results", {})

    extractor_order = [
        "BoletoRepromaqExtractor",
        "EmcFaturaExtractor",
        "NetCenterExtractor",
        "NfseCustomMontesClarosExtractor",
        "NfseCustomVilaVelhaExtractor",
        "SicoobExtractor",
        "AdminDocumentExtractor",
        "OutrosExtractor",
        "NfseGenericExtractor",
        "BoletoExtractor",
        "DanfeExtractor",
    ]

    for extractor_name in extractor_order:
        if extractor_name in extractor_results:
            result = extractor_results[extractor_name]
            status = "✅ SIM" if result.get("can_handle", False) else "❌ NÃO"

            if "error" in result:
                print(f"   {extractor_name}: ERRO - {result['error']}")
            else:
                print(f"   {extractor_name}: {status}")

    # Extrator selecionado
    selected_extractor = analysis.get("selected_extractor")
    extraction_data = analysis.get("extraction_data")

    print(f"\n🎯 EXTRATOR SELECIONADO: {selected_extractor or 'NENHUM'}")

    if extraction_data:
        print(f"\n📊 DADOS EXTRAÍDOS:")
        for key, value in extraction_data.items():
            if value:  # Mostrar apenas valores não vazios
                print(f"   {key}: {value}")

        # Verificar se valor total foi extraído
        valor_total = extraction_data.get(
            "valor_total", extraction_data.get("valor_documento", 0)
        )
        if valor_total and valor_total > 0:
            print(f"\n✅ VALOR TOTAL EXTRAÍDO: R$ {valor_total:,.2f}")
        else:
            print(f"\n❌ VALOR TOTAL: NÃO EXTRAÍDO OU ZERO")
    else:
        print(f"\n❌ NENHUM DADO EXTRAÍDO")

    print("\n" + "=" * 80)


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print("Uso: python debug_pdf_text.py <caminho_do_pdf>")
        print(
            "Exemplo: python debug_pdf_text.py temp_email/email_20260121_080231_81f64f30/01_NFcom_114_CARRIER_TELECOM.pdf"
        )
        return

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Erro: Arquivo não encontrado: {pdf_path}")
        return

    # Executar análise
    analysis = run_extraction_and_analyze(pdf_path)

    if "error" in analysis:
        print(f"Erro: {analysis['error']}")
        return

    # Imprimir relatório
    print_analysis_report(analysis)

    # Salvar relatório em arquivo
    output_file = f"debug_{os.path.basename(pdf_path).replace('.pdf', '')}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"ANÁLISE DO PDF: {pdf_path}\n")
        f.write("=" * 80 + "\n")

        f.write(f"\nTEXTO EXTRAÍDO (primeiros 2000 caracteres):\n")
        f.write("=" * 80 + "\n")
        f.write(analysis.get("text_sample", "")[:2000])
        f.write("\n" + "=" * 80 + "\n")

        f.write(f"\nRESUMO DA ANÁLISE:\n")
        f.write(
            f"Extrator selecionado: {analysis.get('selected_extractor', 'NENHUM')}\n"
        )

        extraction_data = analysis.get("extraction_data", {})
        if extraction_data:
            f.write("\nDADOS EXTRAÍDOS:\n")
            for key, value in extraction_data.items():
                if value:
                    f.write(f"  {key}: {value}\n")

    print(f"\n📁 Relatório salvo em: {output_file}")


if __name__ == "__main__":
    main()
