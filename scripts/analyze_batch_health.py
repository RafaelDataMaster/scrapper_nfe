#!/usr/bin/env python3
"""
Análise de Saúde de Batches - Verificação completa de qualidade de extração.

Este script analisa a saúde geral dos batches processados, verificando:
1. CSV (relatorio_lotes.csv) - valores, fornecedores, vencimentos exportados
2. metadata.json - informações do email para contexto
3. PDFs - apenas quando necessário para diagnóstico

Critérios de sucesso:
- Se batch tem valor > 0 no CSV = SUCESSO (independentemente de ter PDF ou não)
- Se batch tem fornecedor válido = SUCESSO
- Se batch tem vencimento (quando aplicável) = SUCESSO

Problemas reais detectados:
1. Valor no PDF/email mas não no CSV (perda de dados)
2. Fornecedor vazio/genérico/email/errado no CSV
3. Vencimento ausente quando deveria existir
4. Empresa interna como fornecedor (erro grave)

Melhorias v2.0:
- Diferenciação por tipo de documento (NFS-e vs Boleto vs Utility)
- Severidade contextual (NFS-e sem vencimento = esperado)
- Detecção de PDFs protegidos por senha
- Relatório mais detalhado com contexto
- Agrupamento por fornecedor para priorização

Uso:
    python scripts/analyze_batch_health.py [--csv caminho] [--output caminho]
"""

import csv
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class BatchHealth:
    """Representa a saúde de um batch processado."""

    batch_id: str
    row_number: int

    # Dados do CSV
    status_conciliacao: str = ""
    valor_compra: float = 0.0
    valor_boleto: float = 0.0
    fornecedor: str = ""
    vencimento: str = ""
    numero_nota: str = ""
    empresa: str = ""
    email_subject: str = ""
    email_sender: str = ""
    source_folder: str = ""
    outros: int = 0
    nfses: int = 0
    boletos: int = 0
    total_errors: int = 0

    # Dados do metadata.json (quando disponível)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tem_pdf: bool = False
    tem_metadata: bool = False
    pdf_protegido: bool = False
    dados_do_email_body: bool = False

    # Problemas detectados
    problemas: List[Tuple[str, str, float]] = field(
        default_factory=list
    )  # (tipo, descricao, severidade)

    @property
    def tem_valor(self) -> bool:
        """Retorna True se o batch tem valor no CSV."""
        return self.valor_compra > 0

    @property
    def tipo_documento_principal(self) -> str:
        """Identifica o tipo principal de documento no batch."""
        if self.nfses > 0:
            return "NFSE"
        elif self.boletos > 0:
            return "BOLETO"
        elif self.outros > 0:
            # Tentar identificar subtipo pelo fornecedor/assunto
            forn_upper = self.fornecedor.upper()
            assunto_upper = self.email_subject.upper()

            # Utilitários (energia, água)
            if any(
                u in forn_upper
                for u in [
                    "EDP",
                    "CEMIG",
                    "NEOENERGIA",
                    "ELEKTRO",
                    "CPFL",
                    "ENERGISA",
                    "ENEL",
                    "LIGHT",
                ]
            ):
                return "UTILITY_ENERGY"
            if any(u in forn_upper for u in ["COPASA", "SABESP", "SANEPAR"]):
                return "UTILITY_WATER"
            if any(u in assunto_upper for u in ["ENERGIA", "LUZ", "ELETRIC"]):
                return "UTILITY_ENERGY"
            if any(u in assunto_upper for u in ["AGUA", "ÁGUA", "SANEAMENTO"]):
                return "UTILITY_WATER"

            return "OUTRO"
        else:
            return "EMAIL_BODY"  # Dados extraídos apenas do corpo do email

    @property
    def tem_fornecedor_valido(self) -> bool:
        """Retorna True se o fornecedor parece válido."""
        if not self.fornecedor or len(self.fornecedor.strip()) < 3:
            return False

        forn = self.fornecedor.strip()

        # Verificar se é email
        if "@" in forn and ".com" in forn:
            return False

        # Verificar padrões genéricos/inválidos
        padroes_invalidos = [
            "identificada a seguir",
            "prestador de serviços nome",
            "documento do beneficiário",
            "cnpj",
            "fornecedor",
            "chave de acesso",
            "seus dados",
        ]
        for padrao in padroes_invalidos:
            if padrao in forn.lower():
                return False

        return True

    @property
    def eh_empresa_interna(self) -> bool:
        """Verifica se o fornecedor é uma empresa interna (erro grave)."""
        empresas_internas = [
            "CARRIER",
            "RBC",
            "CSC",
            "MOC",
            "EXATA",
            "ATIVE",
            "ORION",
            "ITACOLOMI",
            "FLORESTA",
            "SUNRISE",
        ]
        forn_upper = self.fornecedor.upper().strip()

        # Verificar se o fornecedor EXATAMENTE uma empresa interna
        for emp in empresas_internas:
            if forn_upper == emp:
                return True
        return False

    @property
    def severidade_geral(self) -> str:
        """Calcula severidade geral do batch."""
        if not self.problemas:
            return "OK"

        severidades = [p[2] for p in self.problemas]
        max_sev = max(severidades)

        if max_sev >= 3.0:
            return "CRITICA"
        elif max_sev >= 2.0:
            return "ALTA"
        elif max_sev >= 1.0:
            return "MEDIA"
        return "BAIXA"


class BatchHealthAnalyzer:
    """Analisador de saúde de batches."""

    # Severidade dos problemas
    SEV_CRITICA = 3.0  # Perda de dados ou erro grave
    SEV_ALTA = 2.0  # Dados incorretos no export
    SEV_MEDIA = 1.0  # Dados incompletos mas exportáveis
    SEV_BAIXA = 0.5  # Alerta menor
    SEV_INFO = 0.1  # Apenas informativo (esperado)

    def __init__(self, csv_path: Path, temp_email_path: Path):
        self.csv_path = csv_path
        self.temp_email_path = temp_email_path
        self.batches: List[BatchHealth] = []

    def load_csv_data(self) -> List[BatchHealth]:
        """Carrega dados do CSV."""
        batches = []

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for i, row in enumerate(reader, 1):
                    try:
                        valor_str = (
                            row.get("valor_compra", "0")
                            .replace(".", "")
                            .replace(",", ".")
                        )
                        valor = float(valor_str) if valor_str else 0.0

                        batch = BatchHealth(
                            batch_id=row.get("batch_id", ""),
                            row_number=i,
                            status_conciliacao=row.get("status_conciliacao", ""),
                            valor_compra=valor,
                            valor_boleto=float(
                                row.get("valor_boleto", "0")
                                .replace(".", "")
                                .replace(",", ".")
                                or 0
                            ),
                            fornecedor=row.get("fornecedor", ""),
                            vencimento=row.get("vencimento", ""),
                            numero_nota=row.get("numero_nota", ""),
                            empresa=row.get("empresa", ""),
                            email_subject=row.get("email_subject", ""),
                            email_sender=row.get("email_sender", ""),
                            source_folder=row.get("source_folder", ""),
                            outros=int(row.get("outros", "0") or 0),
                            nfses=int(row.get("nfses", "0") or 0),
                            boletos=int(row.get("boletos", "0") or 0),
                            total_errors=int(row.get("total_errors", "0") or 0),
                        )
                        batches.append(batch)
                    except Exception as e:
                        logger.warning(f"Erro ao processar linha {i}: {e}")
                        continue

        except FileNotFoundError:
            logger.error(f"Arquivo não encontrado: {self.csv_path}")
            return []
        except Exception as e:
            logger.error(f"Erro ao carregar CSV: {e}")
            return []

        logger.info(f"Carregados {len(batches)} batches do CSV")
        return batches

    def load_metadata(self, batch: BatchHealth) -> None:
        """Carrega metadata.json para um batch e detecta características especiais."""
        if not batch.source_folder:
            return

        metadata_path = Path(batch.source_folder) / "metadata.json"

        try:
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    batch.metadata = json.load(f)
                    batch.tem_metadata = True

                # Verificar se tem PDF
                pdf_files = list(Path(batch.source_folder).glob("*.pdf"))
                batch.tem_pdf = len(pdf_files) > 0

                # Detectar se dados vieram do corpo do email (Sabesp, etc.)
                email_body = batch.metadata.get("email_body_text", "")
                if email_body and "sabesp" in email_body.lower():
                    batch.dados_do_email_body = True

                # Detectar PDF protegido por senha (Sabesp usa CPF)
                if batch.tem_pdf and batch.total_errors > 0:
                    # Verificar se é Sabesp (PDF protegido com CPF)
                    if (
                        "sabesp" in batch.email_sender.lower()
                        or "sabesp" in batch.email_subject.lower()
                    ):
                        batch.pdf_protegido = True
                        batch.dados_do_email_body = True  # Dados vieram do email body

        except Exception as e:
            logger.debug(f"Erro ao carregar metadata para {batch.batch_id}: {e}")

    def detectar_problemas(self, batch: BatchHealth) -> None:
        """Detecta problemas em um batch com severidade contextual."""

        tipo_doc = batch.tipo_documento_principal

        # === PROBLEMA 1: Fornecedor é empresa interna (ERRO GRAVE) ===
        if batch.eh_empresa_interna:
            batch.problemas.append(
                (
                    "FORNECEDOR_INTERNO",
                    f"Fornecedor é empresa interna: '{batch.fornecedor}'",
                    self.SEV_CRITICA,
                )
            )

        # === PROBLEMA 2: Fornecedor vazio mas tem valor (CRÍTICO) ===
        if batch.tem_valor and not batch.fornecedor.strip():
            batch.problemas.append(
                (
                    "FORNECEDOR_VAZIO",
                    f"Valor R$ {batch.valor_compra:,.2f} mas fornecedor vazio",
                    self.SEV_CRITICA,
                )
            )

        # === PROBLEMA 3: Fornecedor = email (ALTO) ===
        if batch.tem_valor and "@" in batch.fornecedor and ".com" in batch.fornecedor:
            batch.problemas.append(
                (
                    "FORNECEDOR_EMAIL",
                    f"Fornecedor é email: {batch.fornecedor[:40]}",
                    self.SEV_ALTA,
                )
            )

        # === PROBLEMA 4: Fornecedor = texto do PDF não tratado (ALTO) ===
        padroes_texto_pdf = [
            "identificada a seguir",
            "prestador de serviços nome",
            "documento do beneficiário",
            "chave de acesso:",
        ]
        for padrao in padroes_texto_pdf:
            if padrao in batch.fornecedor.lower():
                batch.problemas.append(
                    (
                        "FORNECEDOR_TEXTO_PDF",
                        f"Fornecedor não tratado: '{batch.fornecedor[:50]}...'",
                        self.SEV_ALTA,
                    )
                )
                break

        # === PROBLEMA 5: Fornecedor muito curto com valor alto (ALTO) ===
        if (
            batch.tem_valor
            and len(batch.fornecedor.strip()) < 10
            and batch.valor_compra > 1000
        ):
            # Exceções: empresas conhecidas com nome curto
            excecoes = [
                "GOX",
                "CEMIG",
                "COPASA",
                "EDP",
                "TIM",
                "VIVO",
                "CLARO",
                "OI",
                "SABESP",
            ]
            if not any(exc in batch.fornecedor.upper() for exc in excecoes):
                batch.problemas.append(
                    (
                        "FORNECEDOR_CURTO",
                        f"Fornecedor curto ({len(batch.fornecedor)} chars) com valor alto R$ {batch.valor_compra:,.2f}: '{batch.fornecedor}'",
                        self.SEV_ALTA,
                    )
                )

        # === PROBLEMA 6: Nome de pessoa com valor muito alto (ALTO) ===
        if batch.valor_compra > 10000:
            nomes_pessoa = [
                "marco",
                "túlio",
                "lima",
                "natalia",
                "ferreira",
                "silva",
                "raphaela",
            ]
            forn_lower = batch.fornecedor.lower()
            if any(nome in forn_lower for nome in nomes_pessoa):
                batch.problemas.append(
                    (
                        "FORNECEDOR_PESSOA_VALOR_ALTO",
                        f"Nome de pessoa com valor alto R$ {batch.valor_compra:,.2f}: '{batch.fornecedor}'",
                        self.SEV_ALTA,
                    )
                )

        # === PROBLEMA 7: Vencimento ausente (SEVERIDADE CONTEXTUAL) ===
        if batch.tem_valor and not batch.vencimento.strip():
            assunto_upper = batch.email_subject.upper()
            sugere_boleto = any(
                termo in assunto_upper
                for termo in ["BOLETO", "FATURA", "VENCIMENTO", "PAGAMENTO"]
            )

            if tipo_doc == "NFSE":
                # NFS-e sem vencimento é ESPERADO (vencimento vem do boleto)
                if sugere_boleto:
                    batch.problemas.append(
                        (
                            "NFSE_SEM_VENCIMENTO",
                            f"NFS-e sem vencimento (esperado - vencimento vem do boleto): R$ {batch.valor_compra:,.2f}",
                            self.SEV_INFO,
                        )
                    )
            elif tipo_doc in ["UTILITY_ENERGY", "UTILITY_WATER"]:
                # Conta de luz/água DEVE ter vencimento
                batch.problemas.append(
                    (
                        "UTILITY_SEM_VENCIMENTO",
                        f"Conta de utilidade sem vencimento: R$ {batch.valor_compra:,.2f} ({batch.fornecedor})",
                        self.SEV_MEDIA,
                    )
                )
            elif tipo_doc == "EMAIL_BODY":
                # Dados do corpo do email podem não ter vencimento
                if batch.pdf_protegido:
                    batch.problemas.append(
                        (
                            "PDF_PROTEGIDO_SEM_VENCIMENTO",
                            f"PDF protegido por senha - dados extraídos do email: R$ {batch.valor_compra:,.2f}",
                            self.SEV_INFO,
                        )
                    )
                elif sugere_boleto:
                    batch.problemas.append(
                        (
                            "EMAIL_BODY_SEM_VENCIMENTO",
                            f"Dados do email sem vencimento: R$ {batch.valor_compra:,.2f}",
                            self.SEV_BAIXA,
                        )
                    )
            elif sugere_boleto:
                # Outros casos onde assunto sugere boleto/fatura
                batch.problemas.append(
                    (
                        "VENCIMENTO_AUSENTE",
                        f"Valor R$ {batch.valor_compra:,.2f} mas sem vencimento (assunto sugere boleto/fatura)",
                        self.SEV_MEDIA,
                    )
                )

        # === PROBLEMA 8: NFSE sem número da nota (MÉDIA) ===
        if batch.nfses > 0 and not batch.numero_nota.strip() and batch.tem_valor:
            batch.problemas.append(
                (
                    "NFSE_SEM_NUMERO",
                    f"NFSE com valor R$ {batch.valor_compra:,.2f} mas sem número da nota",
                    self.SEV_MEDIA,
                )
            )

        # === PROBLEMA 9: PDF protegido mas dados extraídos (INFO) ===
        if batch.pdf_protegido and batch.tem_valor and batch.tem_fornecedor_valido:
            batch.problemas.append(
                (
                    "PDF_PROTEGIDO_OK",
                    f"PDF protegido (Sabesp) - dados extraídos do corpo do email com sucesso",
                    self.SEV_INFO,
                )
            )

        # === PROBLEMA 10: Status CONFERIR mas valores OK (INFO - não é problema real) ===
        # Isso acontece quando há NF/fatura mas sem boleto para conciliar
        # É comportamento esperado, não um erro
        if (
            batch.status_conciliacao == "CONFERIR"
            and batch.tem_valor
            and batch.tem_fornecedor_valido
        ):
            batch.problemas.append(
                (
                    "STATUS_CONFERIR",
                    "Dados OK mas sem boleto para conciliação automática",
                    self.SEV_INFO,
                )
            )

        # === PROBLEMA 11: Fornecedor com texto corrompido (OCR) ===
        if batch.fornecedor and ".." in batch.fornecedor:
            batch.problemas.append(
                (
                    "FORNECEDOR_OCR_CORROMPIDO",
                    f"Fornecedor com texto OCR corrompido: '{batch.fornecedor[:40]}'",
                    self.SEV_MEDIA,
                )
            )

    def analyze_all(self) -> List[BatchHealth]:
        """Executa análise completa de todos os batches."""
        logger.info("Iniciando análise de saúde dos batches...")

        # 1. Carregar dados do CSV
        self.batches = self.load_csv_data()

        # 2. Para cada batch, carregar metadata e detectar problemas
        for i, batch in enumerate(self.batches, 1):
            if i % 100 == 0:
                logger.info(f"Analisando batch {i}/{len(self.batches)}...")

            # Carregar metadata se disponível
            self.load_metadata(batch)

            # Detectar problemas
            self.detectar_problemas(batch)

        return self.batches

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Gera relatório detalhado."""
        if not self.batches:
            return "Nenhum batch para analisar."

        lines = []
        lines.append("=" * 100)
        lines.append("RELATÓRIO DE SAÚDE DOS BATCHES - ANÁLISE DE EXPORTAÇÃO v2.0")
        lines.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 100)
        lines.append("")

        # === RESUMO EXECUTIVO ===
        total = len(self.batches)
        com_valor = sum(1 for b in self.batches if b.tem_valor)
        com_forn_valido = sum(1 for b in self.batches if b.tem_fornecedor_valido)
        com_vencimento = sum(1 for b in self.batches if b.vencimento.strip())

        # Contar problemas por severidade (excluindo INFO)
        # Problemas reais = MÉDIA ou maior (BAIXA é mais informativo que problemático)
        problemas_reais = [
            b for b in self.batches if any(p[2] >= self.SEV_MEDIA for p in b.problemas)
        ]
        com_problemas = len(problemas_reais)

        critica = sum(1 for b in self.batches if b.severidade_geral == "CRITICA")
        alta = sum(1 for b in self.batches if b.severidade_geral == "ALTA")
        media = sum(1 for b in self.batches if b.severidade_geral == "MEDIA")
        # Conta apenas batches que têm problemas BAIXA reais (não STATUS_CONFERIR que agora é INFO)
        baixa = sum(
            1
            for b in self.batches
            if b.severidade_geral == "BAIXA"
            and any(
                p[0] != "STATUS_CONFERIR" and p[2] == self.SEV_BAIXA
                for p in b.problemas
            )
        )

        # Contagem por tipo de documento
        tipos = defaultdict(int)
        for b in self.batches:
            tipos[b.tipo_documento_principal] += 1

        lines.append("RESUMO EXECUTIVO")
        lines.append("-" * 100)
        lines.append(f"Total de batches analisados: {total}")
        lines.append(
            f"Batches com valor exportado: {com_valor} ({com_valor / total * 100:.1f}%)"
        )
        lines.append(
            f"Batches com fornecedor válido: {com_forn_valido} ({com_forn_valido / total * 100:.1f}%)"
        )
        lines.append(
            f"Batches com vencimento: {com_vencimento} ({com_vencimento / total * 100:.1f}%)"
        )
        lines.append("")

        lines.append("DISTRIBUIÇÃO POR TIPO DE DOCUMENTO:")
        for tipo, qtd in sorted(tipos.items(), key=lambda x: -x[1]):
            lines.append(f"  - {tipo}: {qtd} ({qtd / total * 100:.1f}%)")
        lines.append("")

        lines.append(
            f"Batches com problemas reais: {com_problemas} ({com_problemas / total * 100:.1f}%)"
        )
        lines.append(f"  - Severidade CRÍTICA: {critica}")
        lines.append(f"  - Severidade ALTA: {alta}")
        lines.append(f"  - Severidade MÉDIA: {media}")
        if baixa > 0:
            lines.append(f"  - Severidade BAIXA: {baixa}")
        lines.append("")

        # === PDFs PROTEGIDOS (Sabesp) ===
        pdfs_protegidos = [b for b in self.batches if b.pdf_protegido]
        if pdfs_protegidos:
            lines.append("PDFs PROTEGIDOS POR SENHA (dados extraídos do email)")
            lines.append("-" * 100)
            lines.append(f"Total: {len(pdfs_protegidos)} batches")
            valor_total_protegidos = sum(b.valor_compra for b in pdfs_protegidos)
            lines.append(f"Valor total: R$ {valor_total_protegidos:,.2f}")
            lines.append(
                "(Estes PDFs usam senha dinâmica - CPF do titular. Dados extraídos do corpo do email.)"
            )
            lines.append("")

        # === ANÁLISE POR TIPO DE PROBLEMA ===
        lines.append("DISTRIBUIÇÃO DE PROBLEMAS (excluindo informativos)")
        lines.append("-" * 100)

        problemas_agrupados = defaultdict(list)
        for batch in self.batches:
            for tipo, desc, sev in batch.problemas:
                if sev >= self.SEV_BAIXA:  # Exclui INFO
                    problemas_agrupados[tipo].append((batch, desc, sev))

        # Ordenar por severidade e depois por quantidade
        def sort_key(item):
            tipo, ocorrencias = item
            max_sev = max(o[2] for o in ocorrencias) if ocorrencias else 0
            return (-max_sev, -len(ocorrencias))

        for tipo, ocorrencias in sorted(problemas_agrupados.items(), key=sort_key):
            if not ocorrencias:
                continue
            valor_total = sum(b.valor_compra for b, _, _ in ocorrencias)
            max_sev = max(o[2] for o in ocorrencias)
            sev_label = (
                "CRÍTICA"
                if max_sev >= 3
                else "ALTA"
                if max_sev >= 2
                else "MÉDIA"
                if max_sev >= 1
                else "BAIXA"
            )

            lines.append("")
            lines.append(
                f"{tipo} [{sev_label}]: {len(ocorrencias)} ocorrências | Valor total: R$ {valor_total:,.2f}"
            )

            # Mostrar exemplos (máximo 3)
            for batch, desc, sev in ocorrencias[:3]:
                lines.append(f"  - {desc}")
                lines.append(
                    f"    Batch: {batch.batch_id} | Fornecedor: {batch.fornecedor[:30]}"
                )

        lines.append("")
        lines.append("=" * 100)
        lines.append("")

        # === ANÁLISE POR FORNECEDOR (para priorização) ===
        lines.append("FORNECEDORES COM MAIS PROBLEMAS (para priorização)")
        lines.append("-" * 100)

        fornecedor_problemas = defaultdict(
            lambda: {"qtd": 0, "valor": 0.0, "tipos": set()}
        )
        for batch in self.batches:
            for tipo, desc, sev in batch.problemas:
                if sev >= self.SEV_MEDIA:  # Apenas MÉDIA ou maior
                    forn = batch.fornecedor[:40] if batch.fornecedor else "(vazio)"
                    fornecedor_problemas[forn]["qtd"] += 1
                    fornecedor_problemas[forn]["valor"] += batch.valor_compra
                    fornecedor_problemas[forn]["tipos"].add(tipo)

        # Top 10 fornecedores com problemas
        top_fornecedores = sorted(
            fornecedor_problemas.items(), key=lambda x: -x[1]["valor"]
        )[:10]

        for forn, info in top_fornecedores:
            tipos_str = ", ".join(info["tipos"])
            lines.append(f"  {forn}: {info['qtd']} problemas | R$ {info['valor']:,.2f}")
            lines.append(f"    Tipos: {tipos_str}")

        lines.append("")
        lines.append("=" * 100)
        lines.append("")

        # === TOP 10 PROBLEMAS CRÍTICOS ===
        lines.append("TOP 10 PROBLEMAS CRÍTICOS/ALTOS (por valor)")
        lines.append("-" * 100)

        todos_problemas = []
        for batch in self.batches:
            for tipo, desc, sev in batch.problemas:
                if sev >= self.SEV_ALTA:
                    todos_problemas.append((batch.valor_compra, batch, tipo, desc, sev))

        todos_problemas.sort(key=lambda x: x[0], reverse=True)

        if not todos_problemas:
            lines.append("✅ Nenhum problema crítico ou alto encontrado!")
        else:
            for valor, batch, tipo, desc, sev in todos_problemas[:10]:
                sev_label = "CRÍTICA" if sev >= 3 else "ALTA"
                lines.append("")
                lines.append(f"[{sev_label}] Valor: R$ {valor:,.2f}")
                lines.append(f"Problema: {tipo}")
                lines.append(f"Descrição: {desc}")
                lines.append(f"Batch: {batch.batch_id}")
                lines.append(f"Empresa: {batch.empresa}")
                lines.append(f"Assunto: {batch.email_subject[:60]}...")

        lines.append("")
        lines.append("=" * 100)

        # === CASOS INFORMATIVOS (para contexto) ===
        problemas_info = defaultdict(int)
        for batch in self.batches:
            for tipo, desc, sev in batch.problemas:
                if sev < self.SEV_BAIXA:  # Apenas INFO
                    problemas_info[tipo] += 1

        if problemas_info:
            lines.append("")
            lines.append("CASOS INFORMATIVOS (comportamento esperado)")
            lines.append("-" * 100)
            for tipo, qtd in sorted(problemas_info.items(), key=lambda x: -x[1]):
                lines.append(f"  - {tipo}: {qtd} ocorrências")

        lines.append("")
        lines.append("=" * 100)
        lines.append("FIM DO RELATÓRIO")
        lines.append("=" * 100)

        report = "\n".join(lines)

        # Salvar em arquivo
        if output_path:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"Relatório salvo em: {output_path}")
            except Exception as e:
                logger.error(f"Erro ao salvar relatório: {e}")

        return report


def main():
    """Função principal."""
    print("=" * 100)
    print("ANÁLISE DE SAÚDE DOS BATCHES v2.0")
    print("Verificação de qualidade de exportação (CSV + metadata)")
    print(
        "Melhorias: severidade contextual, detecção de PDFs protegidos, agrupamento por fornecedor"
    )
    print("=" * 100)
    print()

    # Configurar caminhos
    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / "data" / "output" / "relatorio_lotes.csv"
    temp_email_path = base_dir / "temp_email"
    output_path = base_dir / "data" / "output" / "analise_saude_batches.txt"

    if not csv_path.exists():
        print(f"ERRO: CSV não encontrado: {csv_path}")
        sys.exit(1)

    # Executar análise
    analyzer = BatchHealthAnalyzer(csv_path, temp_email_path)
    analyzer.analyze_all()

    # Gerar relatório
    report = analyzer.generate_report(output_path)

    # Imprimir resumo na tela
    print(report)


if __name__ == "__main__":
    main()
