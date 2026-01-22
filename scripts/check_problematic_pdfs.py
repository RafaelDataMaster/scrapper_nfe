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

# Adicionar caminho para importar módulos do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Importar extratores e matchers do projeto
try:
    from extractors.admin_document import AdminDocumentExtractor
    from extractors.nfse_generic import NfseGenericExtractor
    from extractors.boleto import BoletoExtractor
    from core.empresa_matcher import (
        infer_fornecedor_from_text,
        is_nome_nosso,
        pick_first_non_our_cnpj,
    )
    from core.empresa_matcher_email import find_empresa_in_email

    EXTRACTORS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Não foi possível importar módulos do projeto: {e}")
    EXTRACTORS_AVAILABLE = False
    AdminDocumentExtractor = None
    NfseGenericExtractor = None
    BoletoExtractor = None
    infer_fornecedor_from_text = None
    is_nome_nosso = None
    pick_first_non_our_cnpj = None
    find_empresa_in_email = None


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
                        "numero_nota": row.get("numero_nota", ""),
                        "vencimento": row.get("vencimento", ""),
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


def check_csv_extraction_quality(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifica a qualidade da extração diretamente dos dados do CSV.

    Args:
        case: Dicionário com dados do caso do CSV

    Returns:
        Dicionário com problemas detectados na extração
    """
    problems = {
        "fornecedor_issues": [],
        "valor_issues": [],
        "vencimento_issues": [],
        "numero_nota_issues": [],
        "extrator_identification_issues": [],
    }

    # 1. Verificar fornecedor
    fornecedor = case.get("fornecedor", "")
    if not fornecedor or fornecedor.strip() == "":
        problems["fornecedor_issues"].append("Fornecedor vazio")
    elif fornecedor.upper() in ["CNPJ FORNECEDOR", "FORNECEDOR", "NOME FORNECEDOR"]:
        problems["fornecedor_issues"].append(f"Fornecedor genérico: {fornecedor}")
    elif EXTRACTORS_AVAILABLE and is_nome_nosso:
        # Verificar se o fornecedor não é uma empresa nossa
        if is_nome_nosso(fornecedor):
            problems["fornecedor_issues"].append(
                f"Fornecedor é empresa nossa: {fornecedor}"
            )

    # 2. Verificar valor
    valor = case.get("valor_compra", 0)
    outros = case.get("outros", 0)
    nfses = case.get("nfses", 0)

    if valor == 0 and (outros > 0 or nfses > 0):
        # Documentos foram encontrados mas valor é zero
        problems["valor_issues"].append(
            f"Valor zero com {outros} outros e {nfses} NFSEs"
        )

    # 3. Verificar vencimento (para boletos)
    vencimento = case.get("vencimento", "")
    email_subject = case.get("email_subject", "").upper()

    # Se o assunto sugere boleto/fatura e vencimento está vazio
    is_boleto_subject = "BOLETO" in email_subject or "FATURA" in email_subject
    is_vencimento_subject = "VENCIMENTO" in email_subject or "VENCE" in email_subject

    # Não marcar problema de vencimento se for NFSE (documento classificada como NFSE)
    numero_nota = case.get("numero_nota", "")
    is_nfse = nfses > 0

    if outros > 0 and not vencimento and not is_nfse:
        # Poderia ser um boleto sem vencimento extraído
        message = "Vencimento não extraído"
        if is_boleto_subject or is_vencimento_subject:
            message += " (assunto sugere boleto/fatura)"
        else:
            message += " (pode ser boleto)"
        problems["vencimento_issues"].append(message)

    # 4. Verificar número da nota (para NFSEs)
    if nfses > 0 and not numero_nota:
        problems["numero_nota_issues"].append("Número da nota não extraído (para NFSE)")

    # 5. Tentar identificar o tipo de documento baseado no assunto/fornecedor
    email_subject = case.get("email_subject", "").upper()
    fornecedor_upper = fornecedor.upper() if fornecedor else ""

    # Padrões comuns para identificar tipo de documento
    if "BOLETO" in email_subject or "FATURA" in email_subject:
        problems["extrator_identification_issues"].append(
            "Assunto sugere boleto/fatura"
        )
    elif "NF" in email_subject or "NOTA" in email_subject:
        problems["extrator_identification_issues"].append("Assunto sugere nota fiscal")

    return problems


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
    # Primeiro verificar qualidade da extração do CSV
    csv_quality = check_csv_extraction_quality(case)
    case["csv_extraction_quality"] = csv_quality

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
            # Analisar qualidade da extração com extratores reais
            if EXTRACTORS_AVAILABLE and analysis.get("text_sample"):
                extraction_quality = check_extraction_quality(analysis["text_sample"])
                analysis["extraction_quality"] = extraction_quality
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


def check_extraction_quality(text: str) -> Dict[str, Any]:
    """
    Verifica a qualidade da extração usando os extratores reais do projeto.

    Args:
        text: Texto extraído do PDF

    Returns:
        Dicionário com informações sobre qualidade da extração
    """
    if not EXTRACTORS_AVAILABLE or not text:
        return {"available": False}

    quality_report = {
        "available": True,
        "extractors_tested": [],
        "missing_fields": [],
        "fornecedor_issues": [],
        "valor_issues": [],
        "vencimento_issues": [],
        "numero_nota_issues": [],
    }

    # Testar cada extrator relevante
    extractors_to_test = []

    if NfseGenericExtractor:
        nfse_extractor = NfseGenericExtractor()
        if nfse_extractor.can_handle(text):
            extractors_to_test.append(("NFSE", nfse_extractor))

    if BoletoExtractor:
        boleto_extractor = BoletoExtractor()
        if boleto_extractor.can_handle(text):
            extractors_to_test.append(("BOLETO", boleto_extractor))

    if AdminDocumentExtractor:
        admin_extractor = AdminDocumentExtractor()
        if admin_extractor.can_handle(text):
            extractors_to_test.append(("ADMIN", admin_extractor))

    for extractor_name, extractor in extractors_to_test:
        try:
            extracted_data = extractor.extract(text)
            quality_report["extractors_tested"].append(extractor_name)

            # Verificar campos críticos
            if extractor_name == "NFSE":
                # Para NFSE: verificar número da nota e fornecedor
                numero_nota = extracted_data.get("numero_nota")
                if not numero_nota or numero_nota.strip() == "":
                    quality_report["numero_nota_issues"].append(
                        f"{extractor_name}: Não extraiu número da nota"
                    )

                valor_total = extracted_data.get("valor_total")
                if not valor_total or valor_total == 0:
                    quality_report["valor_issues"].append(
                        f"{extractor_name}: Não extraiu valor total"
                    )

            elif extractor_name == "BOLETO":
                # Para Boleto: verificar vencimento e valor
                vencimento = extracted_data.get("vencimento")
                if not vencimento:
                    quality_report["vencimento_issues"].append(
                        f"{extractor_name}: Não extraiu vencimento"
                    )

                valor_documento = extracted_data.get("valor_documento")
                if not valor_documento or valor_documento == 0:
                    quality_report["valor_issues"].append(
                        f"{extractor_name}: Não extraiu valor do documento"
                    )

            # Verificar fornecedor para todos os extratores
            fornecedor_nome = extracted_data.get(
                "fornecedor_nome"
            ) or extracted_data.get("fornecedor")
            if fornecedor_nome:
                # Verificar se o fornecedor não é uma empresa nossa
                if is_nome_nosso and is_nome_nosso(fornecedor_nome):
                    quality_report["fornecedor_issues"].append(
                        f"{extractor_name}: Fornecedor é empresa nossa: {fornecedor_nome}"
                    )

                # Verificar se o fornecedor tem conteúdo significativo
                if fornecedor_nome.upper() in [
                    "CNPJ FORNECEDOR",
                    "FORNECEDOR",
                    "NOME FORNECEDOR",
                    "",
                ]:
                    quality_report["fornecedor_issues"].append(
                        f"{extractor_name}: Fornecedor genérico: {fornecedor_nome}"
                    )
            else:
                quality_report["fornecedor_issues"].append(
                    f"{extractor_name}: Não extraiu fornecedor"
                )

            # Tentar inferir fornecedor do texto usando empresa_matcher
            if infer_fornecedor_from_text and not fornecedor_nome:
                inferred_fornecedor = infer_fornecedor_from_text(text, None)
                if inferred_fornecedor:
                    quality_report["fornecedor_issues"].append(
                        f"{extractor_name}: Fornecedor inferível do texto: {inferred_fornecedor}"
                    )

        except Exception as e:
            quality_report["missing_fields"].append(
                f"{extractor_name}: Erro na extração: {e}"
            )

    # Se nenhum extrator foi testado, tentar análise genérica
    if not extractors_to_test:
        # Verificar valores no texto
        value_patterns = [r"R\$\s*[\d\.]+,\d{2}", r"VALOR.*TOTAL.*R\$\s*[\d\.]+,\d{2}"]
        has_values = any(re.search(pattern, text.upper()) for pattern in value_patterns)
        if has_values:
            quality_report["valor_issues"].append(
                "GENÉRICO: Valores detectados mas não extraídos"
            )

        # Verificar datas de vencimento
        vencimento_patterns = [
            r"VENCIMENTO.*\d{2}/\d{2}/\d{4}",
            r"DATA.*VENCIMENTO.*\d{2}/\d{2}/\d{4}",
        ]
        has_vencimento = any(
            re.search(pattern, text.upper()) for pattern in vencimento_patterns
        )
        if has_vencimento:
            quality_report["vencimento_issues"].append(
                "GENÉRICO: Vencimento detectado mas não extraído"
            )

        # Verificar números de nota
        nota_patterns = [
            r"N[º°o]\.?\s*[:.-]?\s*\d+",
            r"NOTA.*FISCAL.*N[º°o]\.?\s*[:.-]?\s*\d+",
        ]
        has_nota = any(re.search(pattern, text.upper()) for pattern in nota_patterns)
        if has_nota:
            quality_report["numero_nota_issues"].append(
                "GENÉRICO: Número de nota detectado mas não extraído"
            )

    return quality_report


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

    # Estatísticas de problemas de extração
    problem_counts = {
        "fornecedor_issues": 0,
        "valor_issues": 0,
        "vencimento_issues": 0,
        "numero_nota_issues": 0,
        "extrator_identification_issues": 0,
    }

    for case in cases:
        csv_quality = case.get("csv_extraction_quality", {})
        for problem_type in problem_counts.keys():
            issues = csv_quality.get(problem_type, [])
            if issues:
                problem_counts[problem_type] += 1

    report.append("\nPROBLEMAS DE EXTRAÇÃO DO CSV")
    report.append("-" * 50)
    for problem_type, count in sorted(problem_counts.items()):
        if count > 0:
            problem_name = problem_type.replace("_", " ").title()
            report.append(f"  {problem_name}: {count} casos")
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

        # Problemas de extração do CSV
        csv_quality = case.get("csv_extraction_quality", {})
        if csv_quality:
            problems_found = False
            for problem_type in [
                "fornecedor_issues",
                "valor_issues",
                "vencimento_issues",
                "numero_nota_issues",
                "extrator_identification_issues",
            ]:
                issues = csv_quality.get(problem_type, [])
                if issues:
                    if not problems_found:
                        report.append("  ⚠️  Problemas de extração do CSV:")
                        problems_found = True
                    for issue in issues[:2]:  # Limita a 2 problemas por tipo
                        report.append(f"    - {issue}")
                    if len(issues) > 2:
                        report.append(f"      ... (+{len(issues) - 2} mais)")

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

            # Qualidade da extração
            extraction_quality = pdf_analysis.get("extraction_quality")
            if extraction_quality and extraction_quality.get("available"):
                report.append(
                    f"      Extração testada com: {', '.join(extraction_quality.get('extractors_tested', []))}"
                )
                issues = []
                if extraction_quality.get("fornecedor_issues"):
                    issues.extend(extraction_quality["fornecedor_issues"])
                if extraction_quality.get("valor_issues"):
                    issues.extend(extraction_quality["valor_issues"])
                if extraction_quality.get("vencimento_issues"):
                    issues.extend(extraction_quality["vencimento_issues"])
                if extraction_quality.get("numero_nota_issues"):
                    issues.extend(extraction_quality["numero_nota_issues"])
                if extraction_quality.get("missing_fields"):
                    issues.extend(extraction_quality["missing_fields"])
                if issues:
                    report.append(f"      Problemas na extração:")
                    for issue in issues[:3]:  # Limita a 3 problemas
                        report.append(f"        - {issue}")
                    if len(issues) > 3:
                        report.append(f"        ... (+{len(issues) - 3} mais)")
                else:
                    report.append(f"      Extração OK (sem problemas detectados)")

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
    csv_path = base_dir.parent / "data" / "output" / "relatorio_lotes.csv"

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

    # Estatísticas de problemas de extração do CSV
    problem_counts = {
        "fornecedor_issues": 0,
        "valor_issues": 0,
        "vencimento_issues": 0,
        "numero_nota_issues": 0,
        "extrator_identification_issues": 0,
    }

    for case in analyzed_cases:
        csv_quality = case.get("csv_extraction_quality", {})
        for problem_type in problem_counts.keys():
            issues = csv_quality.get(problem_type, [])
            if issues:
                problem_counts[problem_type] += 1

    total_cases_with_problems = sum(problem_counts.values())
    if total_cases_with_problems > 0:
        print("\nProblemas de extração identificados:")
        print("-" * 50)
        for problem_type, count in sorted(problem_counts.items()):
            if count > 0:
                problem_name = problem_type.replace("_", " ").title()
                percentage = (count / len(analyzed_cases)) * 100
                print(f"  {problem_name}: {count} casos ({percentage:.1f}%)")

        # Resumo dos problemas mais comuns
        print("\nPrincipais problemas:")
        for problem_type, count in sorted(
            problem_counts.items(), key=lambda x: x[1], reverse=True
        ):
            if count > 0:
                if problem_type == "fornecedor_issues":
                    print(f"  • Fornecedor incorreto/genérico: {count} casos")
                elif problem_type == "valor_issues":
                    print(
                        f"  • Valor não extraído (zero com documentos): {count} casos"
                    )
                elif problem_type == "vencimento_issues":
                    print(f"  • Vencimento não extraído (boletos): {count} casos")
                elif problem_type == "numero_nota_issues":
                    print(f"  • Número da nota não extraído (NFSEs): {count} casos")
                elif problem_type == "extrator_identification_issues":
                    print(f"  • Tipo de documento mal identificado: {count} casos")
    else:
        print("\n✅ Nenhum problema de extração identificado no CSV")

    # Salvar relatório
    output_dir = base_dir.parent / "data" / "output"
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
