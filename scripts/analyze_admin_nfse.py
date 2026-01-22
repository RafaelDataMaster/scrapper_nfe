#!/usr/bin/env python3
"""
Script para analisar casos de NFSEs classificadas como administrativas com valor zero.

Objetivo: Investigar os 19 casos identificados de NFSEs que foram classificadas
como documentos administrativos mas têm valor zero, para entender:
1. São realmente NFSEs ou documentos administrativos?
2. Por que foram classificadas incorretamente?
3. Como melhorar os extratores para evitar falsos positivos.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_relatorio_lotes(csv_path: Path) -> List[Dict[str, str]]:
    """
    Carrega o arquivo relatorio_lotes.csv.

    Args:
        csv_path: Caminho para o arquivo CSV

    Returns:
        Lista de dicionários com os dados das linhas
    """
    rows = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            # Detectar delimitador (pode ser ; ou ,)
            sample = f.readline()
            f.seek(0)

            if ";" in sample:
                delimiter = ";"
            else:
                delimiter = ","

            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                # Normalizar nomes de colunas (remover espaços)
                normalized_row = {k.strip(): v for k, v in row.items()}
                rows.append(normalized_row)

        logger.info(f"Carregadas {len(rows)} linhas de {csv_path}")

    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {csv_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro ao carregar CSV: {e}")
        sys.exit(1)

    return rows


def identify_admin_nfse_cases(
    rows: List[Dict[str, str]],
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Identifica casos de NFSEs classificadas como administrativas com valor zero.

    Args:
        rows: Dados do relatório de lotes

    Returns:
        Tuple: (lista de casos problemáticos, estatísticas)
    """
    problematic_cases = []
    stats = {
        "total_cases": 0,
        "admin_nfse_zero": 0,
        "admin_with_value": 0,
        "nfse_total": 0,
        "outro_total": 0,
    }

    for i, row in enumerate(rows, 1):
        # Contagens básicas
        stats["total_cases"] += 1

        # Extrair valores numéricos (tratando separadores brasileiros)
        nfses = 0
        outros = 0
        valor_compra = 0.0

        try:
            # Contagem de NFSEs
            nfses_str = row.get("nfses", "0")
            nfses = int(nfses_str) if nfses_str.strip() else 0

            # Contagem de "outros" (documentos administrativos)
            outros_str = row.get("outros", "0")
            outros = int(outros_str) if outros_str.strip() else 0

            # Valor da compra
            valor_str = row.get("valor_compra", "0")
            # Converter formato brasileiro: 1.234,56 -> 1234.56
            valor_str = valor_str.replace(".", "").replace(",", ".")
            valor_compra = float(valor_str) if valor_str else 0.0

        except (ValueError, AttributeError) as e:
            logger.debug(f"Erro ao converter valores na linha {i}: {e}")
            continue

        stats["nfse_total"] += nfses
        stats["outro_total"] += outros

        # Caso 1: Tem NFSE E "outros" (administrativo) E valor zero
        if nfses > 0 and outros > 0 and valor_compra == 0:
            case = {
                "batch_id": row.get("batch_id", ""),
                "nfses": nfses,
                "outros": outros,
                "valor_compra": valor_compra,
                "status_conciliacao": row.get("status_conciliacao", ""),
                "divergencia": row.get("divergencia", ""),
                "fornecedor": row.get("fornecedor", ""),
                "email_subject": row.get("email_subject", ""),
                "email_sender": row.get("email_sender", ""),
                "source_folder": row.get("source_folder", ""),
                "row_number": i,
            }
            problematic_cases.append(case)
            stats["admin_nfse_zero"] += 1

        # Caso 2: Tem "outros" (administrativo) com valor > 0
        elif outros > 0 and valor_compra > 0:
            stats["admin_with_value"] += 1

    return problematic_cases, stats


def analyze_email_subjects(cases: List[Dict]) -> Dict[str, int]:
    """
    Analisa padrões nos assuntos dos emails.

    Args:
        cases: Casos problemáticos

    Returns:
        Dicionário com contagem de padrões encontrados
    """
    patterns = {
        "nfse": r"NFSE|NOTA.*SERVICO|SERVICO.*NOTA",
        "boleto": r"BOLETO|FATURA|COBRAN[ÇC]A",
        "admin": r"LEMBRETE|NOTIFICACA[OÇ]|SOLICITACA[OÇ]|AVISO|COMUNICADO",
        "contrato": r"CONTRATO|ADITIVO|RENOVACA[OÇ]",
        "encerramento": r"ENCERRAMENTO|DISTRATO|RESCIS[AÃ]O",
    }

    pattern_counts = {key: 0 for key in patterns}

    for case in cases:
        subject = case.get("email_subject", "").upper()
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, subject, re.IGNORECASE):
                pattern_counts[pattern_name] += 1

    return pattern_counts


def check_pdf_content(source_folder: str) -> Optional[Dict[str, str]]:
    """
    Verifica conteúdo dos PDFs no diretório fonte.

    Args:
        source_folder: Caminho do diretório fonte

    Returns:
        Informações sobre os PDFs encontrados ou None
    """
    try:
        folder = Path(source_folder)
        if not folder.exists():
            return None

        pdf_files = list(folder.glob("*.pdf"))
        if not pdf_files:
            return {"pdf_count": 0, "pdf_names": []}

        # Extrair texto do primeiro PDF para análise
        pdf_info = {
            "pdf_count": len(pdf_files),
            "pdf_names": [f.name for f in pdf_files],
            "sample_text": "",
        }

        # Tentar extrair texto do primeiro PDF
        try:
            import pdfplumber

            with pdfplumber.open(pdf_files[0]) as pdf:
                text = ""
                for page in pdf.pages[:3]:  # Limitar às 3 primeiras páginas
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                # Limitar tamanho do texto
                pdf_info["sample_text"] = (
                    text[:1000] + "..." if len(text) > 1000 else text
                )

                # Verificar se parece NFSE
                nfse_keywords = [
                    "NFSE",
                    "NOTA DE SERVIÇO",
                    "NFS-E",
                    "PRESTAÇÃO DE SERVIÇOS",
                ]
                admin_keywords = [
                    "LEMBRETE",
                    "NOTIFICAÇÃO",
                    "SOLICITAÇÃO",
                    "AVISO",
                    "COMUNICADO",
                ]

                text_upper = text.upper()
                has_nfse = any(kw in text_upper for kw in nfse_keywords)
                has_admin = any(kw in text_upper for kw in admin_keywords)

                pdf_info["likely_nfse"] = has_nfse
                pdf_info["likely_admin"] = has_admin
                pdf_info["classification"] = (
                    "NFSE" if has_nfse else ("ADMIN" if has_admin else "DESCONHECIDO")
                )

        except ImportError:
            pdf_info["pdfplumber_error"] = "pdfplumber não instalado"
        except Exception as e:
            pdf_info["extraction_error"] = str(e)

        return pdf_info

    except Exception as e:
        logger.error(f"Erro ao verificar PDFs em {source_folder}: {e}")
        return None


def generate_report(
    problematic_cases: List[Dict], stats: Dict[str, int], pattern_counts: Dict[str, int]
) -> str:
    """
    Gera relatório em formato texto.

    Args:
        problematic_cases: Casos problemáticos
        stats: Estatísticas
        pattern_counts: Contagem de padrões

    Returns:
        String com relatório formatado
    """
    report_lines = []

    # Cabeçalho
    report_lines.append("=" * 80)
    report_lines.append("ANÁLISE DE NFSEs ADMINISTRATIVAS COM VALOR ZERO")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Estatísticas gerais
    report_lines.append("ESTATÍSTICAS GERAIS")
    report_lines.append("-" * 40)
    report_lines.append(f"Total de lotes analisados: {stats['total_cases']}")
    report_lines.append(f"Total de NFSEs encontradas: {stats['nfse_total']}")
    report_lines.append(
        f"Total de documentos 'outros' (administrativos): {stats['outro_total']}"
    )
    report_lines.append(
        f"Documentos administrativos COM valor: {stats['admin_with_value']}"
    )
    report_lines.append(
        f"NFSEs administrativas com valor ZERO: {stats['admin_nfse_zero']}"
    )
    report_lines.append("")

    # Análise de padrões
    report_lines.append("PADRÕES NOS ASSUNTOS DE EMAIL")
    report_lines.append("-" * 40)
    for pattern, count in pattern_counts.items():
        if count > 0:
            report_lines.append(f"{pattern.upper()}: {count} casos")
    report_lines.append("")

    # Casos problemáticos detalhados
    report_lines.append("CASOS PROBLEMÁTICOS DETALHADOS")
    report_lines.append("-" * 40)

    if not problematic_cases:
        report_lines.append("Nenhum caso problemático encontrado!")
    else:
        report_lines.append(
            f"Encontrados {len(problematic_cases)} casos problemáticos:"
        )
        report_lines.append("")

        for i, case in enumerate(problematic_cases, 1):
            report_lines.append(f"Caso {i}:")
            report_lines.append(f"  Batch ID: {case['batch_id']}")
            report_lines.append(f"  NFSEs: {case['nfses']}, Outros: {case['outros']}")
            report_lines.append(f"  Valor: R$ {case['valor_compra']:.2f}")
            report_lines.append(f"  Status: {case['status_conciliacao']}")
            report_lines.append(
                f"  Fornecedor: {case['fornecedor'][:50]}..."
                if len(case["fornecedor"]) > 50
                else f"  Fornecedor: {case['fornecedor']}"
            )
            report_lines.append(
                f"  Assunto: {case['email_subject'][:60]}..."
                if len(case["email_subject"]) > 60
                else f"  Assunto: {case['email_subject']}"
            )
            report_lines.append(f"  Remetente: {case['email_sender']}")
            report_lines.append(f"  Pasta fonte: {case['source_folder']}")

            # Verificar conteúdo dos PDFs
            pdf_info = check_pdf_content(case["source_folder"])
            if pdf_info:
                report_lines.append(f"  PDFs encontrados: {pdf_info['pdf_count']}")
                if pdf_info.get("classification"):
                    report_lines.append(
                        f"  Classificação provável: {pdf_info['classification']}"
                    )
                if pdf_info.get("pdf_names"):
                    report_lines.append(
                        f"  Nomes: {', '.join(pdf_info['pdf_names'][:2])}"
                    )
                    if len(pdf_info["pdf_names"]) > 2:
                        report_lines.append(
                            f"    ... e mais {len(pdf_info['pdf_names']) - 2}"
                        )

            report_lines.append("")

    # Recomendações
    report_lines.append("RECOMENDAÇÕES")
    report_lines.append("-" * 40)

    if problematic_cases:
        report_lines.append("1. Investigar manualmente os casos listados acima")
        report_lines.append(
            "2. Verificar se são realmente NFSEs ou documentos administrativos"
        )
        report_lines.append("3. Melhorar padrões de detecção no AdminDocumentExtractor")
        report_lines.append("4. Ajustar ordem dos extratores se necessário")
        report_lines.append(
            "5. Considerar adicionar novos padrões baseados nos assuntos identificados"
        )
    else:
        report_lines.append("✅ Nenhuma ação necessária - não há casos problemáticos!")

    report_lines.append("")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def main():
    """Função principal."""
    print("=" * 80)
    print("ANÁLISE DE NFSEs ADMINISTRATIVAS COM VALOR ZERO")
    print("=" * 80)

    # Configurar caminhos
    base_dir = Path(__file__).parent
    csv_path = base_dir.parent / "data" / "output" / "relatorio_lotes.csv"

    print(f"Lendo arquivo: {csv_path}")

    # Carregar dados
    rows = load_relatorio_lotes(csv_path)
    if not rows:
        print("Nenhum dado encontrado!")
        return

    # Identificar casos problemáticos
    print("Identificando casos de NFSEs administrativas com valor zero...")
    problematic_cases, stats = identify_admin_nfse_cases(rows)

    # Analisar padrões
    pattern_counts = analyze_email_subjects(problematic_cases)

    # Gerar relatório
    report = generate_report(problematic_cases, stats, pattern_counts)

    # Exibir relatório
    print("\n" + report)

    # Salvar relatório em arquivo
    output_path = base_dir.parent / "data" / "output" / "analise_admin_nfse.txt"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nRelatório salvo em: {output_path}")
    except Exception as e:
        print(f"\n⚠️  Não foi possível salvar o relatório: {e}")

    # Status final
    if problematic_cases:
        print(
            f"\n⚠️  ATENÇÃO: {len(problematic_cases)} casos problemáticos encontrados!"
        )
        print("   Recomenda-se investigação manual.")
    else:
        print("\n✅ Nenhum caso problemático encontrado!")


if __name__ == "__main__":
    main()
