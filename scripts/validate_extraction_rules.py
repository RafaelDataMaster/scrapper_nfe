"""
Script de validação de regras de extração para NFSe, Boletos, DANFE e Outros.

Este script processa PDFs das pastas de lote (temp_email/) ou failed_cases_pdf (legado)
e gera relatórios detalhados separando sucessos e falhas.

MODOS DE OPERAÇÃO:
1. Modo Lote (RECOMENDADO - novo padrão):
   Processa batches de temp_email/ com metadata.json
   python scripts/validate_extraction_rules.py --batch-mode --temp-email

2. Modo Lote Específico:
   Processa apenas batches específicos (útil para validar correções)
   python scripts/validate_extraction_rules.py --batch-mode --temp-email --batches email_20260129_084433_c5c04540,email_20260129_084430_187f758c

3. Modo Legado: Processa PDFs soltos em failed_cases_pdf
   python scripts/validate_extraction_rules.py --input-dir failed_cases_pdf

FLAGS OPCIONAIS:
- --validar-prazo: Valida prazo de 4 dias úteis
- --exigir-nf: Exige número da NF na NFSe
- --apply-correlation: Aplica correlação entre documentos do mesmo lote (modo lote)
- --revalidar-processados: Reprocessa apenas PDFs já registrados no manifest

Princípios SOLID aplicados:
- SRP: Funções com responsabilidade única
- OCP: Extensível para novos tipos de documento sem modificar código existente
- DIP: Usa abstrações (BatchProcessor, ExtractionDiagnostics)
"""
import argparse

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

import pandas as pd
from _init_env import setup_project_path

# Inicializa o ambiente do projeto
setup_project_path()

from config.settings import (  # noqa: E402
    DEBUG_CSV_BOLETO_FALHA,
    DEBUG_CSV_BOLETO_SUCESSO,
    DEBUG_CSV_DANFE_FALHA,
    DEBUG_CSV_DANFE_SUCESSO,
    DEBUG_CSV_NFSE_FALHA,
    DEBUG_CSV_NFSE_SUCESSO,
    DEBUG_CSV_OUTROS_FALHA,
    DEBUG_CSV_OUTROS_SUCESSO,
    DEBUG_RELATORIO_QUALIDADE,
    DIR_DEBUG_INPUT,
    DIR_DEBUG_OUTPUT,
    DIR_TEMP,  # Adicionado: temp_email/
)
from core.batch_processor import BatchProcessor  # noqa: E402

from core.correlation_service import CorrelationService  # noqa: E402
from core.diagnostics import ExtractionDiagnostics  # noqa: E402
from core.models import BoletoData, DanfeData, InvoiceData, OtherDocumentData  # noqa: E402
from core.processor import BaseInvoiceProcessor  # noqa: E402

# Manifest para rastrear arquivos processados
MANIFEST_PROCESSADOS = DIR_DEBUG_OUTPUT / "processed_files.txt"


# === Funções Auxiliares ===

def _relpath_str(path: Path, base: Path = DIR_DEBUG_INPUT) -> str:
    """Converte path para string relativa ao diretório base."""
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return getattr(path, "name", str(path))


def _load_manifest_processados() -> Set[str]:
    """Carrega lista de arquivos já processados."""
    if not MANIFEST_PROCESSADOS.exists():
        return set()
    try:
        content = MANIFEST_PROCESSADOS.read_text(encoding="utf-8")
    except Exception:
        return set()
    items: Set[str] = set()
    for line in content.splitlines():
        s = (line or "").strip()
        if not s or s.startswith("#"):
            continue
        items.add(s)
    return items


def _save_manifest_processados(processados: Iterable[str]) -> None:
    """Salva lista de arquivos processados."""
    unique = sorted(
        {(p or "").strip() for p in processados if (p or "").strip()},
        key=lambda x: x.lower()
    )
    DIR_DEBUG_OUTPUT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PROCESSADOS.write_text(
        "\n".join(unique) + ("\n" if unique else ""),
        encoding="utf-8"
    )


def _configure_stdout_utf8() -> None:
    """Configura stdout/stderr para UTF-8 (evita erros com emojis no Windows)."""
    for stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


# === Classes de Resultado ===

class ValidationResult:
    """Armazena resultados da validação por tipo de documento."""

    def __init__(self):
        self.nfse_sucesso: List[Dict[str, Any]] = []
        self.nfse_falha: List[Dict[str, Any]] = []
        self.boletos_sucesso: List[Dict[str, Any]] = []
        self.boletos_falha: List[Dict[str, Any]] = []
        self.danfe_sucesso: List[Dict[str, Any]] = []
        self.danfe_falha: List[Dict[str, Any]] = []
        self.outros_sucesso: List[Dict[str, Any]] = []
        self.outros_falha: List[Dict[str, Any]] = []
        self.count_erro: int = 0
        self.processed_files: Set[str] = set()

    @property
    def count_nfse_ok(self) -> int:
        return len(self.nfse_sucesso)

    @property
    def count_nfse_falha(self) -> int:
        return len(self.nfse_falha)

    @property
    def count_boleto_ok(self) -> int:
        return len(self.boletos_sucesso)

    @property
    def count_boleto_falha(self) -> int:
        return len(self.boletos_falha)

    @property
    def count_danfe_ok(self) -> int:
        return len(self.danfe_sucesso)

    @property
    def count_danfe_falha(self) -> int:
        return len(self.danfe_falha)

    @property
    def count_outros_ok(self) -> int:
        return len(self.outros_sucesso)

    @property
    def count_outros_falha(self) -> int:
        return len(self.outros_falha)


# === Classificadores de Documentos ===

def classify_boleto(
    result: BoletoData,
    relpath: str,
    validar_prazo: bool
) -> Tuple[bool, Dict[str, Any]]:
    """
    Classifica resultado de extração de boleto.

    Returns:
        Tupla (eh_sucesso, dict_resultado)
    """
    eh_sucesso, motivos = ExtractionDiagnostics.classificar_boleto(
        result, validar_prazo=validar_prazo
    )

    result_dict = {
        'arquivo_relativo': relpath,
        **result.__dict__,
    }

    if not eh_sucesso:
        result_dict['motivo_falha'] = '|'.join(motivos)

    return eh_sucesso, result_dict


def classify_nfse(
    result: InvoiceData,
    relpath: str,
    validar_prazo: bool,
    exigir_nf: bool
) -> Tuple[bool, Dict[str, Any]]:
    """
    Classifica resultado de extração de NFSe.

    Returns:
        Tupla (eh_sucesso, dict_resultado)
    """
    eh_sucesso, motivos = ExtractionDiagnostics.classificar_nfse(
        result,
        validar_prazo=validar_prazo,
        exigir_numero_nf=exigir_nf,
    )

    result_dict = {
        'arquivo_relativo': relpath,
        **result.__dict__,
    }

    if not eh_sucesso:
        result_dict['motivo_falha'] = '|'.join(motivos)

    return eh_sucesso, result_dict


def classify_danfe(
    result: DanfeData,
    relpath: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Classifica resultado de extração de DANFE.

    Returns:
        Tupla (eh_sucesso, dict_resultado)
    """
    motivos = []
    if (result.valor_total or 0) <= 0:
        motivos.append('VALOR_ZERO')
    if not (result.fornecedor_nome and result.fornecedor_nome.strip()):
        motivos.append('SEM_RAZAO_SOCIAL')
    if not result.cnpj_emitente:
        motivos.append('SEM_CNPJ')

    eh_sucesso = len(motivos) == 0

    result_dict = {
        'arquivo_relativo': relpath,
        **result.__dict__,
    }

    if not eh_sucesso:
        result_dict['motivo_falha'] = '|'.join(motivos)

    return eh_sucesso, result_dict


def classify_outros(
    result: OtherDocumentData,
    relpath: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Classifica resultado de extração de outros documentos.

    Returns:
        Tupla (eh_sucesso, dict_resultado)
    """
    motivos = []
    # Outros documentos são mais flexíveis - podem não ter valor
    if not (result.fornecedor_nome and result.fornecedor_nome.strip()):
        motivos.append('SEM_FORNECEDOR')

    eh_sucesso = len(motivos) == 0

    result_dict = {
        'arquivo_relativo': relpath,
        **result.__dict__,
    }

    if not eh_sucesso:
        result_dict['motivo_falha'] = '|'.join(motivos)

    return eh_sucesso, result_dict


def _classify_and_store(
    result: Any,
    relpath: str,
    validar_prazo: bool,
    exigir_nf: bool,
    validation_result: ValidationResult
) -> None:
    """Classifica e armazena o resultado no objeto de validação."""
    doc_type = getattr(result, 'doc_type', 'UNKNOWN')

    if doc_type == 'NFSE' and isinstance(result, InvoiceData):
        eh_ok, data = classify_nfse(result, relpath, validar_prazo, exigir_nf)
        if eh_ok:
            validation_result.nfse_sucesso.append(data)
        else:
            validation_result.nfse_falha.append(data)

    elif doc_type == 'BOLETO' and isinstance(result, BoletoData):
        eh_ok, data = classify_boleto(result, relpath, validar_prazo)
        if eh_ok:
            validation_result.boletos_sucesso.append(data)
        else:
            validation_result.boletos_falha.append(data)

    elif doc_type == 'DANFE' and isinstance(result, DanfeData):
        eh_ok, data = classify_danfe(result, relpath)
        if eh_ok:
            validation_result.danfe_sucesso.append(data)
        else:
            validation_result.danfe_falha.append(data)

    elif doc_type == 'OUTRO' and isinstance(result, OtherDocumentData):
        eh_ok, data = classify_outros(result, relpath)
        if eh_ok:
            validation_result.outros_sucesso.append(data)
        else:
            validation_result.outros_falha.append(data)
    else:
        # Tipo desconhecido - tenta inferir
        validation_result.count_erro += 1


# === Exportadores ===

def export_results(validation_result: ValidationResult) -> None:
    """Exporta resultados para CSVs separados por tipo e status."""
    def _export_csv(data: List[Dict], path: Path) -> None:
        if not data:
            # Cria CSV vazio com headers padrão
            pd.DataFrame().to_csv(path, index=False, sep=';', encoding='utf-8-sig')
            return
        try:
            df = pd.DataFrame(data)
            df.to_csv(path, index=False, sep=';', encoding='utf-8-sig')
        except Exception as e:
            print(f"⚠️ Erro ao exportar {path}: {e}")

    DIR_DEBUG_OUTPUT.mkdir(parents=True, exist_ok=True)

    # NFSe
    _export_csv(validation_result.nfse_sucesso, DEBUG_CSV_NFSE_SUCESSO)
    _export_csv(validation_result.nfse_falha, DEBUG_CSV_NFSE_FALHA)

    # Boletos
    _export_csv(validation_result.boletos_sucesso, DEBUG_CSV_BOLETO_SUCESSO)
    _export_csv(validation_result.boletos_falha, DEBUG_CSV_BOLETO_FALHA)

    # DANFE
    _export_csv(validation_result.danfe_sucesso, DEBUG_CSV_DANFE_SUCESSO)
    _export_csv(validation_result.danfe_falha, DEBUG_CSV_DANFE_FALHA)

    # Outros
    _export_csv(validation_result.outros_sucesso, DEBUG_CSV_OUTROS_SUCESSO)
    _export_csv(validation_result.outros_falha, DEBUG_CSV_OUTROS_FALHA)

    print(f"📊 CSVs exportados em: {DIR_DEBUG_OUTPUT}")


def export_quality_report(
    validation_result: ValidationResult,
    total_arquivos: int,
    processados: int
) -> None:
    """Gera relatório de qualidade consolidado."""
    lines = []
    lines.append("# Relatório de Qualidade - Validação de Extração\n")
    lines.append(f"Total de arquivos: {total_arquivos}")
    lines.append(f"Processados: {processados}")
    lines.append(f"Erros: {validation_result.count_erro}\n")

    lines.append("## NFSe")
    lines.append(f"- Sucesso: {validation_result.count_nfse_ok}")
    lines.append(f"- Falha: {validation_result.count_nfse_falha}\n")

    lines.append("## Boletos")
    lines.append(f"- Sucesso: {validation_result.count_boleto_ok}")
    lines.append(f"- Falha: {validation_result.count_boleto_falha}\n")

    lines.append("## DANFE")
    lines.append(f"- Sucesso: {validation_result.count_danfe_ok}")
    lines.append(f"- Falha: {validation_result.count_danfe_falha}\n")

    lines.append("## Outros")
    lines.append(f"- Sucesso: {validation_result.count_outros_ok}")
    lines.append(f"- Falha: {validation_result.count_outros_falha}\n")

    content = "\n".join(lines)
    DEBUG_RELATORIO_QUALIDADE.write_text(content, encoding="utf-8")


def print_summary(validation_result: ValidationResult) -> None:
    """Imprime resumo dos resultados."""
    print("\n" + "=" * 80)
    print("📊 RESUMO DA VALIDAÇÃO")
    print("=" * 80)

    total_ok = (
        validation_result.count_nfse_ok +
        validation_result.count_boleto_ok +
        validation_result.count_danfe_ok +
        validation_result.count_outros_ok
    )
    total_falha = (
        validation_result.count_nfse_falha +
        validation_result.count_boleto_falha +
        validation_result.count_danfe_falha +
        validation_result.count_outros_falha
    )

    print(f"✅ Sucessos: {total_ok}")
    print(f"❌ Falhas: {total_falha}")
    print(f"💥 Erros: {validation_result.count_erro}")
    print("-" * 80)
    print(f"NFSe: {validation_result.count_nfse_ok} ok, {validation_result.count_nfse_falha} falha")
    print(f"Boletos: {validation_result.count_boleto_ok} ok, {validation_result.count_boleto_falha} falha")
    print(f"DANFE: {validation_result.count_danfe_ok} ok, {validation_result.count_danfe_falha} falha")
    print(f"Outros: {validation_result.count_outros_ok} ok, {validation_result.count_outros_falha} falha")
    print("=" * 80)


# === Processadores ===

def process_legacy_files(
    arquivos: List[Path],
    validar_prazo: bool,
    exigir_nf: bool,
    validation_result: ValidationResult
) -> int:
    """
    Processa arquivos no modo legado (PDFs soltos).

    Args:
        arquivos: Lista de caminhos de arquivos
        validar_prazo: Se True, valida prazo de vencimento
        exigir_nf: Se True, exige número da NF
        validation_result: Objeto para armazenar resultados

    Returns:
        Número de arquivos processados
    """
    processor = BaseInvoiceProcessor()
    total = len(arquivos)
    processados = 0
    _interrompido = False

    try:
        for i, caminho in enumerate(arquivos, start=1):
            processados = i
            sys.stdout.write(f"\r📄 Processados: {i}/{total}")
            sys.stdout.flush()

            relpath = _relpath_str(caminho)
            validation_result.processed_files.add(relpath)

            try:
                result = processor.process(str(caminho))
                _classify_and_store(
                    result, relpath, validar_prazo, exigir_nf, validation_result
                )
            except Exception:
                validation_result.count_erro += 1

    except KeyboardInterrupt:
        _interrompido = True
        print("\n🛑 Interrompido com Ctrl+C.")

    sys.stdout.write("\n")
    sys.stdout.flush()

    return processados


def process_batch_mode(
    batch_folders: List[Path],
    validar_prazo: bool,
    exigir_nf: bool,
    apply_correlation: bool,
    validation_result: ValidationResult
) -> int:
    """
    Processa pastas de lote (nova estrutura com metadata.json).

    Args:
        batch_folders: Lista de pastas de lote
        validar_prazo: Se True, valida prazo de vencimento
        exigir_nf: Se True, exige número da NF
        apply_correlation: Se True, aplica correlação entre documentos
        validation_result: Objeto para armazenar resultados

    Returns:
        Número total de documentos processados
    """
    batch_processor = BatchProcessor()
    _correlation_service = CorrelationService() if apply_correlation else None

    total_batches = len(batch_folders)
    total_docs = 0

    try:
        for i, folder in enumerate(batch_folders, start=1):
            sys.stdout.write(f"\r📁 Lotes: {i}/{total_batches}")
            sys.stdout.flush()

            # Processa o lote
            batch_result = batch_processor.process_batch(
                folder, apply_correlation=apply_correlation
            )

            # Classifica cada documento do lote
            for doc in batch_result.documents:
                total_docs += 1
                relpath = f"{batch_result.batch_id}/{doc.arquivo_origem}"
                validation_result.processed_files.add(relpath)

                _classify_and_store(
                    doc, relpath, validar_prazo, exigir_nf, validation_result
                )

            # Registra erros do lote
            validation_result.count_erro += batch_result.total_errors

    except KeyboardInterrupt:
        print("\n🛑 Interrompido com Ctrl+C.")

    sys.stdout.write("\n")
    sys.stdout.flush()

    return total_docs


def main() -> None:
    """Função principal do script de validação."""
    _configure_stdout_utf8()

    # Parse argumentos
    parser = argparse.ArgumentParser(
        description='Valida regras de extração de PDFs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLOS DE USO:

# Modo Lote - Processa TODOS os batches de temp_email/ (RECOMENDADO)
  python scripts/validate_extraction_rules.py --batch-mode --temp-email

# Modo Lote Específico - Apenas batches específicos (útil para validar correções)
  python scripts/validate_extraction_rules.py --batch-mode --temp-email \\
      --batches email_20260129_084433_c5c04540,email_20260129_084430_187f758c

# Modo Legado - PDFs soltos em failed_cases_pdf/
  python scripts/validate_extraction_rules.py --input-dir failed_cases_pdf

# Validação completa com prazo e NF
  python scripts/validate_extraction_rules.py --batch-mode --temp-email \\
      --validar-prazo --exigir-nf --apply-correlation
        """
    )
    parser.add_argument(
        '--validar-prazo',
        action='store_true',
        help='Valida prazo de 4 dias úteis (ignora por padrão para docs antigos)'
    )
    parser.add_argument(
        '--exigir-nf',
        action='store_true',
        help='Exige numero_nota na NFSe (por padrão não exige no MVP)'
    )
    parser.add_argument(
        '--revalidar-processados',
        action='store_true',
        help='Reprocessa apenas PDFs já registrados no manifest'
    )
    parser.add_argument(
        '--batch-mode',
        action='store_true',
        help='Processa pastas de lote (com metadata.json) ao invés de PDFs soltos'
    )
    parser.add_argument(
        '--temp-email',
        action='store_true',
        help='Usa temp_email/ como diretório de entrada (padrão para modo batch)'
    )
    parser.add_argument(
        '--batches',
        type=str,
        default=None,
        help='Lista de batches específicos para processar (ex: batch1,batch2,batch3)'
    )
    parser.add_argument(
        '--apply-correlation',
        action='store_true',
        help='Aplica correlação entre documentos do mesmo lote (apenas modo lote)'
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        default=None,
        help='Diretório de entrada customizado (padrão: failed_cases_pdf ou temp_email)'
    )

    args = parser.parse_args()

    # Configurações
    validar_prazo = args.validar_prazo
    exigir_nf = args.exigir_nf
    revalidar_processados = args.revalidar_processados
    batch_mode = args.batch_mode
    apply_correlation = args.apply_correlation
    use_temp_email = args.temp_email
    batches_especificos = args.batches.split(',') if args.batches else None

    # Determina diretório de entrada
    if args.input_dir:
        input_dir = Path(args.input_dir)
    elif batch_mode and use_temp_email:
        input_dir = DIR_TEMP  # temp_email/
    else:
        input_dir = DIR_DEBUG_INPUT  # failed_cases_pdf/ (legado)

    # Se modo batch e --temp-email não foi passado, sugere usar
    if batch_mode and not use_temp_email and not args.input_dir:
        print("💡 Dica: Use --temp-email para processar batches de temp_email/")
        print("   Ou especifique --input-dir para outro diretório\n")

    # Cria pasta de saída
    DIR_DEBUG_OUTPUT.mkdir(parents=True, exist_ok=True)

    # Cabeçalho
    print("=" * 80)
    print("🧪 TESTE DE REGRAS - NFSe, BOLETOS, DANFE & OUTROS")
    print("=" * 80)
    print(f"📂 Lendo: {input_dir}")
    print(f"💾 Salvando em: {DIR_DEBUG_OUTPUT}")
    if batch_mode:
        print("🔄 Modo: LOTE (batches)")
        if batches_especificos:
            print(f"📋 Batches específicos: {len(batches_especificos)}")
    else:
        print("🔄 Modo: LEGADO (arquivos soltos)")
    if validar_prazo:
        print("⏰ Validação de prazo: ATIVA")
    else:
        print("⏰ Validação de prazo: DESATIVADA")
    if exigir_nf:
        print("🧾 NF (numero_nota): EXIGIDA")
    else:
        print("🧾 NF (numero_nota): NÃO exigida")
    if batch_mode and apply_correlation:
        print("🔗 Correlação entre documentos: ATIVA")
    print("=" * 80)

    # Verifica diretório de entrada
    if not input_dir.exists():
        print(f"❌ Pasta não existe: {input_dir}")
        return

    # Inicializa resultado
    validation_result = ValidationResult()
    processed_prev = _load_manifest_processados()

    # Modo Lote
    if batch_mode:
        # Lista pastas de lote
        if batches_especificos:
            # Processa apenas batches específicos
            batch_folders = []
            for batch_name in batches_especificos:
                batch_path = input_dir / batch_name.strip()
                if batch_path.exists() and batch_path.is_dir():
                    batch_folders.append(batch_path)
                else:
                    print(f"⚠️ Batch não encontrado: {batch_name}")
        else:
            # Lista todos os batches
            batch_folders = []
            for item in sorted(input_dir.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    # Verifica se tem PDFs ou metadata.json
                    has_pdfs = any(f.suffix.lower() == '.pdf' for f in item.iterdir() if f.is_file())
                    has_metadata = (item / "metadata.json").exists()
                    if has_pdfs or has_metadata:
                        batch_folders.append(item)

        if not batch_folders:
            print("⚠️ Nenhuma pasta de lote encontrada.")
            return

        print(f"\n📦 {len(batch_folders)} lote(s) encontrado(s)\n")

        processados = process_batch_mode(
            batch_folders,
            validar_prazo,
            exigir_nf,
            apply_correlation,
            validation_result
        )

        total_arquivos = processados

    # Modo Legado
    else:
        if revalidar_processados:
            manifest = _load_manifest_processados()
            arquivos = []
            for rel in sorted(manifest, key=lambda x: x.lower()):
                p = input_dir / rel
                if p.exists() and p.is_file() and p.suffix.lower() == '.pdf':
                    arquivos.append(p)
            print(f"🔁 Revalidação: {len(arquivos)} arquivo(s) do manifest")
        else:
            # Busca recursiva de PDFs
            arquivos = sorted(
                [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"],
                key=lambda p: str(p).lower(),
            )

        if not arquivos:
            print("⚠️ Nenhum PDF encontrado.")
            return

        print(f"\n📦 {len(arquivos)} arquivo(s) encontrado(s)\n")

        total_arquivos = len(arquivos)
        processados = process_legacy_files(
            arquivos,
            validar_prazo,
            exigir_nf,
            validation_result
        )

    # Atualiza manifest
    merged = processed_prev | validation_result.processed_files
    try:
        _save_manifest_processados(merged)
        print(f"🧾 Manifest atualizado: {MANIFEST_PROCESSADOS.name} ({len(merged)} itens)")
    except Exception as e:
        print(f"⚠️ Falha ao salvar manifest: {e}")

    # Exporta resultados
    export_results(validation_result)
    export_quality_report(validation_result, total_arquivos, processados)
    print_summary(validation_result)


if __name__ == "__main__":
    main()
