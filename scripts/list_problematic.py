#!/usr/bin/env python3
"""
Script para listar lotes problemáticos identificados na análise.

Identifica casos onde:
- outros > 0 (documentos classificados como administrativos)
- valor_compra = 0 (nenhum valor extraído)
- Mas o documento pode ser uma NFSE/DANFE mal classificada

Este script gera uma lista formatada para reprocessamento manual ou automático.
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def load_problematic_cases(csv_path: Path) -> List[Dict]:
    """
    Carrega casos problemáticos do relatório de lotes.

    Args:
        csv_path: Caminho para o arquivo relatorio_lotes.csv

    Returns:
        Lista de dicionários com informações dos casos problemáticos
    """
    cases = []

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
            for i, row in enumerate(reader, 1):
                # Normalizar nomes de colunas
                row = {k.strip(): v for k, v in row.items()}

                # Contar documentos
                outros_str = row.get("outros", "0")
                outros = int(outros_str) if outros_str.strip() else 0

                nfses_str = row.get("nfses", "0")
                nfses = int(nfses_str) if nfses_str.strip() else 0

                # Converter valor brasileiro para float
                valor_str = row.get("valor_compra", "0")
                if valor_str:
                    valor_str = valor_str.replace(".", "").replace(",", ".")
                    try:
                        valor = float(valor_str)
                    except ValueError:
                        valor = 0.0
                else:
                    valor = 0.0

                # Critério: outros > 0 e valor == 0
                if outros > 0 and valor == 0:
                    # Extrair batch_id do source_folder
                    source = row.get("source_folder", "")
                    if source:
                        # Normalizar separadores de caminho
                        parts = source.replace("\\", "/").split("/")
                        batch_id = parts[-1] if parts else "DESCONHECIDO"
                    else:
                        batch_id = "DESCONHECIDO"

                    case = {
                        "row_number": i,
                        "batch_id": batch_id,
                        "source_folder": source,
                        "outros": outros,
                        "nfses": nfses,
                        "valor_compra": valor,
                        "status_conciliacao": row.get("status_conciliacao", ""),
                        "divergencia": row.get("divergencia", ""),
                        "fornecedor": row.get("fornecedor", ""),
                        "email_subject": row.get("email_subject", ""),
                        "email_sender": row.get("email_sender", ""),
                        "empresa": row.get("empresa", ""),
                    }
                    cases.append(case)

        return cases

    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado: {csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao processar CSV: {e}")
        sys.exit(1)


def classify_problem_type(case: Dict) -> str:
    """
    Classifica o tipo de problema baseado no conteúdo.

    Args:
        case: Informações do caso problemático

    Returns:
        String com a classificação
    """
    subject = (case.get("email_subject") or "").upper()
    divergencia = (case.get("divergencia") or "").upper()

    # Padrões identificados na análise
    if "LEMBRETE GENTIL" in subject and "NOTA FISCAL" in divergencia:
        return "NFSE_MAL_CLASSIFICADA"
    elif "NOTA FISCAL FAT/" in subject or "DANFE" in subject:
        return "DANFE_COMO_ADMIN"
    elif "TCF TELECOM" in subject:
        return "TCF_TELECOM_PROBLEM"
    elif "BOX BRAZIL" in subject:
        return "BOX_BRAZIL_PROBLEM"
    elif "NOTIFICAÇÃO AUTOMÁTICA" in subject:
        return "NOTIFICACAO_AUTOMATICA"
    elif "RELATÓRIO" in subject:
        return "RELATORIO_ADMIN"
    elif "CEMIG" in subject:
        return "CEMIG_FATURA"
    elif "FATURAMENTO" in subject:
        return "FATURAMENTO_ADMIN"
    else:
        return "OUTROS"


def generate_commands(cases: List[Dict]) -> Tuple[List[str], List[str]]:
    """
    Gera comandos para reprocessamento.

    Args:
        cases: Lista de casos problemáticos

    Returns:
        Tupla (comandos_individual, comandos_lote)
    """
    individual_commands = []
    batch_commands = []

    # Comandos individuais (um por lote)
    for case in cases:
        batch_id = case["batch_id"]
        if batch_id and batch_id != "DESCONHECIDO":
            cmd = f"python run_ingestion.py --folder temp_email/{batch_id}"
            individual_commands.append(cmd)

    # Comando para processar todos de uma vez
    if cases:
        batch_ids = [
            case["batch_id"] for case in cases if case["batch_id"] != "DESCONHECIDO"
        ]
        if batch_ids:
            # Agrupar em lotes de 5 para não sobrecarregar
            for i in range(0, len(batch_ids), 5):
                group = batch_ids[i : i + 5]
                folders = " ".join([f"temp_email/{bid}" for bid in group])
                cmd = f"python run_ingestion.py --folder {folders}"
                batch_commands.append(cmd)

    return individual_commands, batch_commands


def main():
    """Função principal do script."""
    print("=" * 80)
    print("LISTA DE LOTES PROBLEMÁTICOS PARA REPROCESSAR")
    print("=" * 80)

    # Configurar caminhos
    base_dir = Path(__file__).parent
    csv_path = base_dir.parent / "data" / "output" / "relatorio_lotes.csv"

    print(f"Lendo arquivo: {csv_path}")
    if not csv_path.exists():
        print(f"Erro: Arquivo não encontrado: {csv_path}")
        sys.exit(1)

    # Carregar casos problemáticos
    cases = load_problematic_cases(csv_path)
    if not cases:
        print("✅ Nenhum caso problemático encontrado!")
        sys.exit(0)

    print(f"✅ Encontrados {len(cases)} casos problemáticos")
    print()

    # Estatísticas por tipo
    type_counts = {}
    for case in cases:
        prob_type = classify_problem_type(case)
        type_counts[prob_type] = type_counts.get(prob_type, 0) + 1

    print("ESTATÍSTICAS POR TIPO DE PROBLEMA")
    print("-" * 40)
    for prob_type, count in sorted(
        type_counts.items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (count / len(cases)) * 100
        print(f"  {prob_type}: {count} casos ({percentage:.1f}%)")
    print()

    # Lista detalhada
    print("LISTA DETALHADA DE LOTES")
    print("-" * 80)

    for i, case in enumerate(cases, 1):
        print(f"\n{i:2d}. BATCH ID: {case['batch_id']}")
        print(f"    Pasta: {case['source_folder']}")
        print(f"    Assunto: {case['email_subject'][:80]}...")
        print(f"    Remetente: {case['email_sender']}")
        print(f"    Fornecedor: {case['fornecedor'][:60]}...")
        print(f"    Status: {case['status_conciliacao']}")
        print(f"    Divergência: {case['divergencia'][:80]}...")
        print(
            f"    Outros: {case['outros']}, NFSEs: {case['nfses']}, Valor: R$ {case['valor_compra']:.2f}"
        )
        print(f"    Tipo: {classify_problem_type(case)}")

    # Gerar comandos
    individual_cmds, batch_cmds = generate_commands(cases)

    print("\n" + "=" * 80)
    print("COMANDOS PARA REPROCESSAMENTO")
    print("=" * 80)

    print("\n1. REPROCESSAR INDIVIDUALMENTE (recomendado para testes):")
    print("-" * 40)
    for cmd in individual_cmds[:10]:  # Mostrar só os primeiros 10
        print(f"  {cmd}")
    if len(individual_cmds) > 10:
        print(f"  ... e mais {len(individual_cmds) - 10} comandos")

    if batch_cmds:
        print("\n2. REPROCESSAR EM LOTE:")
        print("-" * 40)
        for cmd in batch_cmds:
            print(f"  {cmd}")

    print("\n3. REPROCESSAR TODOS DE UMA VEZ:")
    print("-" * 40)
    if individual_cmds:
        all_folders = " ".join(
            [
                f"temp_email/{case['batch_id']}"
                for case in cases
                if case["batch_id"] != "DESCONHECIDO"
            ]
        )
        print(f"  python run_ingestion.py --folder {all_folders}")
        print(f"  (Total: {len(individual_cmds)} lotes)")

    print("\n" + "=" * 80)
    print("INSTRUÇÕES")
    print("=" * 80)

    print("""
1. REPROCESSAMENTO RECOMENDADO:
   - Execute os comandos individualmente para validar as correções
   - Verifique se os valores são extraídos corretamente agora
   - Compare com os resultados anteriores no relatorio_lotes.csv

2. O QUE ESPERAR APÓS CORREÇÕES:
   - NFSEs/DANFEs classificadas corretamente (nfses > 0)
   - Valores extraídos (valor_compra > 0)
   - Status "CONCILIADO" ou "OK" em vez de "CONFERIR"
   - Redução de avisos sobre documentos administrativos

3. MONITORAMENTO:
   - Verifique se houve redução em: outros > 0 AND valor_compra = 0
   - Confirme extração de valores em contratos/documentos administrativos legítimos
   - Valide classificação correta de documentos fiscais
    """)

    # Salvar lista em arquivo
    output_dir = base_dir / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "lotes_problematicos.txt"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"Total de lotes problemáticos: {len(cases)}\n")
            f.write("=" * 60 + "\n")
            for case in cases:
                f.write(f"\n{case['batch_id']}\n")
                f.write(f"  Assunto: {case['email_subject']}\n")
                f.write(f"  Fornecedor: {case['fornecedor']}\n")
                f.write(f"  Status: {case['status_conciliacao']}\n")
                f.write(f"  Tipo: {classify_problem_type(case)}\n")
        print(f"\n✅ Lista salva em: {output_path}")
    except Exception as e:
        print(f"\n⚠️  Não foi possível salvar a lista: {e}")

    print("\n" + "=" * 80)
    print(f"ANÁLISE CONCLUÍDA - {len(cases)} LOTES IDENTIFICADOS")
    print("=" * 80)


if __name__ == "__main__":
    main()
