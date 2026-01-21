#!/usr/bin/env python3
"""
Script para examinar PDFs de casos problemáticos onde documentos "outros" têm valor zero.

Objetivo: Analisar documentos classificados como administrativos (outros > 0) com valor zero
para determinar:
1. São realmente documentos administrativos ou são NFSEs mal classificadas?
2. Contêm valores que deveriam ter sido extraídos?
3. Como melhorar os extratores para evitar problemas futuros.

Funcionalidades:
- Extração de texto de PDFs usando pdfplumber
- Classificação baseada em padrões de conteúdo
- Identificação de valores presentes mas não extraídos
- Geração de relatório detalhado com recomendações
"""

import csv
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PDFAnalyzer:
    """Analisador de conteúdo de PDFs."""

    def __init__(self):
        self.nfse_patterns = [
            r"NFSE|NOTA.*SERVICO|SERVICO.*NOTA|NFS-E",
            r"PRESTAÇÃO.*SERVIÇOS|PRESTACAO.*SERVICOS",
            r"TOMADOR.*SERVIÇOS|TOMADOR.*SERVICOS",
            r"CNPJ.*PRESTADOR|CPF.*PRESTADOR",
            r"VALOR.*SERVIÇOS|VALOR.*SERVICOS",
            r"IMPOSTO.*SERVIÇOS|IMPOSTO.*SERVICOS",
            r"ISS|INSS|PIS|COFINS",
        ]

        self.admin_patterns = [
            r"LEMBRETE.*GENTIL|LEMBRE?TE.*GENTIL",
            r"NOTIFICAÇÃO.*AUTOMÁTICA|NOTIFICACAO.*AUTOMATICA",
            r"SOLICITAÇÃO.*ENCERRAMENTO|SOLICITACAO.*ENCERRAMENTO",
            r"AVISO.*IMPORTANTE|COMUNICADO.*IMPORTANTE",
            r"DISTRATO.*CONTRATO|RESCISÃO.*CONTRATUAL",
            r"ORDEM.*SERVIÇO|ORDEM.*SERVICO",
            r"CONTRATO.*RENOVAÇÃO|CONTRATO.*RENOVACAO",
            r"RELATÓRIO.*FATURAMENTO|RELATORIO.*FATURAMENTO",
            r"PLANILHA.*CONFERÊNCIA|PLANILHA.*CONFERENCIA",
        ]

        self.value_patterns = [
            r"R\$\s*[\d\.]+,\d{2}",
            r"VALOR.*TOTAL.*R\$\s*[\d\.]+,\d{2}",
            r"TOTAL.*R\$\s*[\d\.]+,\d{2}",
            r"VALOR.*DO.*CONTRATO.*R\$\s*[\d\.]+,\d{2}",
            r"VALOR.*PAGAR.*R\$\s*[\d\.]+,\d{2}",
        ]

    def extract_text(self, pdf_path: Path) -> Optional[str]:
        """
        Extrai texto de um arquivo PDF.

        Args:
            pdf_path: Caminho para o arquivo PDF

        Returns:
            Texto extraído ou None em caso de erro
        """
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"--- Página {i + 1} ---\n{page_text}\n\n"

                return text if text else None

        except ImportError:
            logger.error(
                "pdfplumber não está instalado. Instale com: pip install pdfplumber"
            )
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair texto de {pdf_path.name}: {e}")
            return None

    def classify_document(self, text: str) -> Dict[str, Any]:
        """
        Classifica um documento baseado em seu conteúdo.

        Args:
            text: Texto do documento

        Returns:
            Dicionário com classificação e características
        """
        text_upper = text.upper()

        classification = {
            "likely_nfse": False,
            "likely_admin": False,
            "likely_contract": False,
            "likely_report": False,
            "has_values": False,
            "values_found": [],
            "confidence": 0.0,
            "detected_patterns": [],
            "recommended_type": "DESCONHECIDO",
        }

        # Verificar padrões de NFSE
        nfse_score = 0
        for pattern in self.nfse_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                nfse_score += 1
                classification["detected_patterns"].append(f"NFSE: {pattern}")

        # Verificar padrões administrativos
        admin_score = 0
        for pattern in self.admin_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                admin_score += 1
                classification["detected_patterns"].append(f"ADMIN: {pattern}")

        # Verificar valores
        value_matches = []
        for pattern in self.value_patterns:
            matches = re.findall(pattern, text_upper)
            if matches:
                value_matches.extend(matches)

        if value_matches:
            classification["has_values"] = True
            classification["values_found"] = value_matches

        # Determinar classificação baseada em scores
        total_score = nfse_score + admin_score

        if total_score > 0:
            classification["confidence"] = max(nfse_score, admin_score) / total_score

            if nfse_score > admin_score:
                classification["likely_nfse"] = True
                classification["recommended_type"] = "NFSE"
            else:
                classification["likely_admin"] = True
                classification["recommended_type"] = "ADMINISTRATIVO"

                # Refinar tipo administrativo
                if any("CONTRATO" in p for p in classification["detected_patterns"]):
                    classification["likely_contract"] = True
                    classification["recommended_type"] = "CONTRATO"
                elif any(
                    "RELATÓRIO" in p or "PLANILHA" in p
                    for p in classification["detected_patterns"]
                ):
                    classification["likely_report"] = True
                    classification["recommended_type"] = "RELATÓRIO"

        return classification

    def analyze_pdf(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analisa um PDF completo.

        Args:
            pdf_path: Caminho para o arquivo PDF

        Returns:
            Dicionário com análise completa ou None em caso de erro
        """
        text = self.extract_text(pdf_path)
        if not text:
            return None

        classification = self.classify_document(text)

        # Informações básicas do PDF
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
        except:
            page_count = "DESCONHECIDO"

        analysis = {
            "pdf_name": pdf_path.name,
            "pdf_path": str(pdf_path),
            "page_count": page_count,
            "text_length": len(text),
            "text_sample": text[:500] + "..." if len(text) > 500 else text,
            **classification,
        }

        return analysis


def load_problematic_cases(csv_path: Path) -> List[Dict[str, Any]]:
    """
    Carrega casos problemáticos do relatório de lotes.

    Args:
        csv_path: Caminho para relatorio_lotes.csv

    Returns:
        Lista de casos problemáticos
    """
    cases = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for i, row in enumerate(reader, 1):
                outros = int(row.get("outros", "0") or "0")
                nfses = int(row.get("nfses", "0") or "0")

                # Converter valor brasileiro para float
                valor_str = row.get("valor_compra", "0")
                valor_str = valor_str.replace(".", "").replace(",", ".")
                try:
                    valor = float(valor_str) if valor_str else 0.0
                except ValueError:
                    valor = 0.0

                # Critério: outros > 0 e valor == 0
                if outros > 0 and valor == 0:
                    case = {
                        "row_number": i,
                        "batch_id": row.get("batch_id", ""),
                        "outros": outros,
                        "nfses": nfses,
                        "valor_compra": valor,
                        "status_conciliacao": row.get("status_conciliacao", ""),
                        "divergencia": row.get("divergencia", ""),
                        "fornecedor": row.get("fornecedor", ""),
                        "email_subject": row.get("email_subject", ""),
                        "email_sender": row.get("email_sender", ""),
                        "source_folder": row.get("source_folder", ""),
                        "empresa": row.get("empresa", ""),
                        "pdf_analysis": [],
                        "classification_summary": {},
                    }
                    cases.append(case)

        logger.info(f"Carregados {len(cases)} casos problemáticos")
        return cases

    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {csv_path}")
        return []
    except Exception as e:
        logger.error(f"Erro ao carregar CSV: {e}")
        return []


def analyze_pdfs_for_case(
    case: Dict[str, Any], analyzer: PDFAnalyzer
) -> Dict[str, Any]:
    """
    Analisa PDFs para um caso específico.

    Args:
        case: Caso problemático
        analyzer: Instância do PDFAnalyzer

    Returns:
        Caso atualizado com análise de PDFs
    """
    source_folder = case.get("source_folder", "")
    if not source_folder:
        logger.warning(f"Sem pasta fonte para caso: {case['batch_id']}")
        return case

    folder_path = Path(source_folder)
    if not folder_path.exists():
        logger.warning(f"Pasta não existe: {folder_path}")
        return case

    pdf_files = list(folder_path.glob("*.pdf"))
    if not pdf_files:
        logger.info(f"Sem PDFs na pasta: {folder_path}")
        return case

    logger.info(f"Analisando {len(pdf_files)} PDF(s) para {case['batch_id']}")

    pdf_analyses = []
    for pdf_path in pdf_files:
        analysis = analyzer.analyze_pdf(pdf_path)
        if analysis:
            pdf_analyses.append(analysis)

    case["pdf_analysis"] = pdf_analyses

    # Resumo da classificação
    if pdf_analyses:
        total_pdfs = len(pdf_analyses)
        nfse_count = sum(1 for a in pdf_analyses if a["likely_nfse"])
        admin_count = sum(1 for a in pdf_analyses if a["likely_admin"])
        has_values_count = sum(1 for a in pdf_analyses if a["has_values"])

        case["classification_summary"] = {
            "total_pdfs": total_pdfs,
            "nfse_count": nfse_count,
            "admin_count": admin_count,
            "has_values_count": has_values_count,
            "primary_classification": "MISTO"
            if nfse_count > 0 and admin_count > 0
            else "NFSE"
            if nfse_count > 0
            else "ADMIN"
            if admin_count > 0
            else "DESCONHECIDO",
            "has_missing_values": has_values_count > 0,
            "recommended_action": "REVISAR_CLASSIFICACAO"
            if nfse_count > 0 and case["outros"] > 0
            else "MELHORAR_EXTRACAO"
            if has_values_count > 0
            else "DOCUMENTO_ADMIN_OK"
            if admin_count > 0
            else "INVESTIGAR_MANUALMENTE",
        }

    return case


def generate_detailed_report(cases: List[Dict[str, Any]]) -> str:
    """
    Gera relatório detalhado da análise.

    Args:
        cases: Casos analisados

    Returns:
        Relatório formatado em string
    """
    report = []

    # Cabeçalho
    report.append("=" * 100)
    report.append("ANÁLISE DETALHADA DE PDFs PROBLEMÁTICOS")
    report.append("=" * 100)
    report.append("Documentos administrativos (outros > 0) com valor zero")
    report.append("")

    # Estatísticas gerais
    total_cases = len(cases)
    cases_with_pdfs = sum(1 for c in cases if c.get("pdf_analysis"))
    cases_classified = sum(1 for c in cases if c.get("classification_summary"))

    report.append("ESTATÍSTICAS GERAIS")
    report.append("-" * 50)
    report.append(f"Total de casos analisados: {total_cases}")
    report.append(f"Casos com PDFs disponíveis: {cases_with_pdfs}")
    report.append(f"Casos classificados automaticamente: {cases_classified}")
    report.append("")

    # Resumo por classificação
    if cases_classified > 0:
        classification_counts = {}
        action_counts = {}

        for case in cases:
            summary = case.get("classification_summary", {})
            primary = summary.get("primary_classification", "DESCONHECIDO")
            action = summary.get("recommended_action", "DESCONHECIDO")

            classification_counts[primary] = classification_counts.get(primary, 0) + 1
            action_counts[action] = action_counts.get(action, 0) + 1

        report.append("RESUMO POR CLASSIFICAÇÃO")
        report.append("-" * 50)
        for class_type, count in sorted(classification_counts.items()):
            report.append(f"  {class_type}: {count} casos")

        report.append("")
        report.append("AÇÕES RECOMENDADAS")
        report.append("-" * 50)
        for action, count in sorted(action_counts.items()):
            report.append(f"  {action}: {count} casos")
        report.append("")

    # Casos detalhados
    report.append("=" * 100)
    report.append("CASOS DETALHADOS")
    report.append("=" * 100)

    for i, case in enumerate(cases, 1):
        report.append(f"\nCaso {i}: {case['batch_id']}")
        report.append(f"  Assunto: {case['email_subject']}")
        report.append(f"  Remetente: {case['email_sender']}")
        report.append(
            f"  Fornecedor: {case['fornecedor'][:80]}..."
            if len(case["fornecedor"]) > 80
            else f"  Fornecedor: {case['fornecedor']}"
        )
        report.append(f"  Pasta fonte: {case['source_folder']}")
        report.append(f"  Status conciliação: {case['status_conciliacao']}")
        report.append(
            f"  Divergência: {case['divergencia'][:80]}..."
            if len(case["divergencia"]) > 80
            else f"  Divergência: {case['divergencia']}"
        )
        report.append(
            f"  Outros: {case['outros']}, NFSEs: {case['nfses']}, Valor: R$ {case['valor_compra']:.2f}"
        )

        # Análise de PDFs
        pdf_analyses = case.get("pdf_analysis", [])
        if not pdf_analyses:
            report.append("  ⚠️  Sem PDFs disponíveis para análise")
            continue

        report.append(f"  PDFs analisados: {len(pdf_analyses)}")

        summary = case.get("classification_summary", {})
        if summary:
            report.append(
                f"  Classificação principal: {summary.get('primary_classification', 'DESCONHECIDO')}"
            )
            report.append(
                f"  Ação recomendada: {summary.get('recommended_action', 'DESCONHECIDO')}"
            )
            report.append(
                f"  Valores encontrados: {'SIM' if summary.get('has_missing_values') else 'NÃO'}"
            )

        # Detalhes de cada PDF
        for j, pdf_analysis in enumerate(pdf_analyses, 1):
            report.append(f"\n    PDF {j}: {pdf_analysis['pdf_name']}")
            report.append(f"      Páginas: {pdf_analysis['page_count']}")
            report.append(f"      Tipo recomendado: {pdf_analysis['recommended_type']}")
            report.append(f"      Confiança: {pdf_analysis['confidence']:.2%}")
            report.append(
                f"      Tem valores: {'SIM' if pdf_analysis['has_values'] else 'NÃO'}"
            )

            if pdf_analysis["has_values"]:
                values = pdf_analysis["values_found"]
                if len(values) > 3:
                    report.append(
                        f"      Valores encontrados: {', '.join(values[:3])}... (+{len(values) - 3} mais)"
                    )
                else:
                    report.append(f"      Valores encontrados: {', '.join(values)}")

            # Padrões detectados (após primeiros 3)
            patterns = pdf_analysis.get("detected_patterns", [])
            if patterns:
                if len(patterns) > 3:
                    report.append(
                        f"      Padrões: {patterns[0][:50]}... (+{len(patterns) - 1} mais)"
                    )
                else:
                    report.append(
                        f"      Padrões: {patterns[0][:80]}..."
                        if len(patterns[0]) > 80
                        else f"      Padrões: {patterns[0]}"
                    )

        report.append("")

    # Recomendações gerais
    report.append("=" * 100)
    report.append("RECOMENDAÇÕES PARA MELHORIA")
    report.append("=" * 100)

    if cases_classified > 0:
        report.append("\n1. REVISÃO DE CLASSIFICAÇÃO")
        report.append(
            "   - Casos classificados como NFSE mas marcados como 'outros' podem indicar:"
        )
        report.append("     a) Falso positivo no AdminDocumentExtractor")
        report.append("     b) PDFs com múltiplos documentos (NFSE + administrativo)")
        report.append("     c) NFSEs que também contêm conteúdo administrativo")

        report.append("\n2. MELHORIA NA EXTRAÇÃO DE VALORES")
        report.append("   - Casos com valores detectados mas não extraídos sugerem:")
        report.append("     a) Padrões de valor não cobertos pelos extratores atuais")
        report.append("     b) Valores em formatos não padrão (ex: sem 'R$')")
        report.append("     c) Valores em tabelas que requerem extração estruturada")

        report.append("\n3. AJUSTES NO ADMIN DOCUMENT EXTRACTOR")
        report.append("   - Considerar:")
        report.append("     a) Adicionar mais padrões administrativos específicos")
        report.append("     b) Melhorar detecção de valores em contratos e relatórios")
        report.append("     c) Ajustar ordem de prioridade dos extratores")

        report.append("\n4. PRÓXIMOS PASSOS")
        report.append(
            "   - Revisar manualmente os casos marcados como 'INVESTIGAR_MANUALMENTE'"
        )
        report.append(
            "   - Testar ajustes no AdminDocumentExtractor com casos problemáticos"
        )
        report.append("   - Monitorar métricas após implementação das melhorias")
    else:
        report.append("\n⚠️  Não foi possível gerar recomendações específicas.")
        report.append("   - Verifique se os PDFs estão disponíveis nas pastas fonte")
        report.append("   - Certifique-se de que pdfplumber está instalado")
        report.append("   - Considere análise manual dos casos listados acima")

    report.append("\n" + "=" * 100)

    return "\n".join(report)


def main():
    """Função principal do script."""
    print("=" * 100)
    print("ANÁLISE DE PDFs PROBLEMÁTICOS")
    print("Documentos administrativos com valor zero")
    print("=" * 100)

    # Verificar dependências
    try:
        import pdfplumber

        print("✓ pdfplumber disponível")
    except ImportError:
        print("✗ pdfplumber não está instalado")
        print("  Instale com: pip install pdfplumber")
        sys.exit(1)

    # Configurar caminhos
    base_dir = Path(__file__).parent
    csv_path = base_dir / "data" / "output" / "relatorio_lotes.csv"

    print(f"\nLendo arquivo: {csv_path}")
    if not csv_path.exists():
        print(f"✗ Arquivo não encontrado: {csv_path}")
        sys.exit(1)

    # Carregar casos problemáticos
    cases = load_problematic_cases(csv_path)
    if not cases:
        print("✓ Nenhum caso problemático encontrado!")
        sys.exit(0)

    print(f"✓ Encontrados {len(cases)} casos problemáticos")

    # Analisar PDFs
    print("\nAnalisando PDFs...")
    analyzer = PDFAnalyzer()
    analyzed_cases = []

    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] Analisando {case['batch_id']}...", end=" ")
        analyzed_case = analyze_pdfs_for_case(case, analyzer)
        analyzed_cases.append(analyzed_case)

        summary = analyzed_case.get("classification_summary", {})
        if summary:
            action = summary.get("recommended_action", "")
            print(f"{action}")
        else:
            print("sem PDFs")

    # Gerar relatório
    print("\nGerando relatório...")
    report = generate_detailed_report(analyzed_cases)

    # Exibir resumo
    print("\n" + "=" * 100)
    print("RESUMO EXECUTIVO")
    print("=" * 100)

    analyzed_with_pdfs = [c for c in analyzed_cases if c.get("pdf_analysis")]
    if analyzed_with_pdfs:
        print(f"Casos analisados com PDFs: {len(analyzed_with_pdfs)}/{len(cases)}")

        classifications = {}
        for case in analyzed_with_pdfs:
            summary = case.get("classification_summary", {})
            primary = summary.get("primary_classification", "DESCONHECIDO")
            classifications[primary] = classifications.get(primary, 0) + 1

        print("\nDistribuição de classificações:")
        for class_type, count in sorted(classifications.items()):
            percentage = (count / len(analyzed_with_pdfs)) * 100
            print(f"  {class_type}: {count} casos ({percentage:.1f}%)")
    else:
        print("⚠️  Nenhum PDF foi analisado")

    # Salvar relatório
    output_dir = base_dir / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "analise_pdfs_detalhada.txt"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✓ Relatório salvo em: {output_path}")
    except Exception as e:
        print(f"\n✗ Erro ao salvar relatório: {e}")

    print("\n" + "=" * 100)
    print("ANÁLISE CONCLUÍDA")
    print("=" * 100)


if __name__ == "__main__":
    main()
