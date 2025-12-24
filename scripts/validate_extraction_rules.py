"""
Script de validação de regras de extração para NFSe e Boletos.

Este script processa PDFs da pasta failed_cases_pdf e gera relatórios
detalhados separando sucessos e falhas, auxiliando no ajuste fino das regex.

⚠️ MODOS IMPORTANTES (MVP):
- Por padrão, IGNORA a validação de prazo de 4 dias úteis (útil para documentos antigos)
    Para validar prazo: python scripts/validate_extraction_rules.py --validar-prazo
- Por padrão, NÃO exige o número da NF (coluna NF fica vazia e será preenchida via API da OpenAI)
    Para exigir NF: python scripts/validate_extraction_rules.py --exigir-nf
"""
import os
import argparse
import pandas as pd
import re
import sys
from _init_env import setup_project_path

# Inicializa o ambiente do projeto
setup_project_path()

from core.processor import BaseInvoiceProcessor
from core.models import BoletoData, InvoiceData, DanfeData, OtherDocumentData
from core.diagnostics import ExtractionDiagnostics
from config.settings import (
    DIR_DEBUG_INPUT,
    DIR_DEBUG_OUTPUT,
    DEBUG_CSV_NFSE_SUCESSO,
    DEBUG_CSV_NFSE_FALHA,
    DEBUG_CSV_BOLETO_SUCESSO,
    DEBUG_CSV_BOLETO_FALHA,
    DEBUG_CSV_DANFE_SUCESSO,
    DEBUG_CSV_DANFE_FALHA,
    DEBUG_CSV_OUTROS_SUCESSO,
    DEBUG_CSV_OUTROS_FALHA,
    DEBUG_RELATORIO_QUALIDADE
)


def _nf_candidate_fields_from_obs(obs_interna: str) -> dict:
    """Extrai NF candidata do campo obs_interna (se existir).

    Formato esperado (gerado no pipeline):
        NF_CANDIDATE=12345 (conf=0.82, label=nfse)
    """
    obs = obs_interna or ""
    m = re.search(r"\bNF_CANDIDATE=([0-9]{3,12})\b\s*\(conf=([0-9.]+),\s*([^\)]+)\)", obs)
    if not m:
        return {
            'nf_candidate': "",
            'nf_candidate_confidence': "",
            'nf_candidate_reason': "",
        }
    return {
        'nf_candidate': m.group(1),
        'nf_candidate_confidence': m.group(2),
        'nf_candidate_reason': m.group(3),
    }

def main() -> None:
    """
    Testa as regras de extração nos PDFs da pasta failed_cases_pdf.
    
    Gera CSVs separados:
    - nfse_sucesso.csv / nfse_falha.csv (com coluna motivo_falha)
    - boletos_sucesso.csv / boletos_falha.csv (com coluna motivo_falha)
    - relatorio_qualidade.txt (estatísticas gerais)
    """
    # Garantia de UTF-8 no Windows (evita UnicodeEncodeError com emojis no print)
    for stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    # Parse argumentos
    parser = argparse.ArgumentParser(description='Valida regras de extração de PDFs')
    parser.add_argument('--validar-prazo', action='store_true',
                       help='Valida prazo de 4 dias úteis (ignora por padrão para docs antigos)')
    parser.add_argument('--exigir-nf', action='store_true',
                        help='Exige numero_nota na NFSe (por padrão não exige no MVP)')
    args = parser.parse_args()
    
    validar_prazo = args.validar_prazo
    exigir_nf = args.exigir_nf
    
    # Cria pasta de saída se não existir
    DIR_DEBUG_OUTPUT.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("🧪 TESTE DE REGRAS - NFSe & BOLETOS")
    print("=" * 80)
    print(f"📂 Lendo: {DIR_DEBUG_INPUT}")
    print(f"💾 Salvando em: {DIR_DEBUG_OUTPUT}")
    if validar_prazo:
        print("⏰ Validação de prazo: ATIVA (requer 4 dias úteis)")
    else:
        print("⏰ Validação de prazo: DESATIVADA (documentos antigos)")
    if exigir_nf:
        print("🧾 NF (numero_nota): EXIGIDA")
    else:
        print("🧾 NF (numero_nota): NÃO exigida (será preenchida via API da OpenAI)")
    print("=" * 80)

    processor = BaseInvoiceProcessor()
    
    # Listas separadas
    nfse_sucesso = []
    nfse_falha = []
    boletos_sucesso = []
    boletos_falha = []
    danfe_sucesso = []
    danfe_falha = []
    outros_sucesso = []
    outros_falha = []
    
    # Contadores
    count_nfse_ok = 0
    count_nfse_falha = 0
    count_boleto_ok = 0
    count_boleto_falha = 0
    count_danfe_ok = 0
    count_danfe_falha = 0
    count_outros_ok = 0
    count_outros_falha = 0
    count_erro = 0

    if not DIR_DEBUG_INPUT.exists():
        print(f"❌ Pasta não existe: {DIR_DEBUG_INPUT}")
        return

    arquivos = [f for f in os.listdir(DIR_DEBUG_INPUT) if f.lower().endswith('.pdf')]
    
    if not arquivos:
        print("⚠️ Nenhum PDF encontrado.")
        return

    print(f"\n📦 {len(arquivos)} arquivo(s) encontrado(s)\n")

    for file in arquivos:
        caminho = DIR_DEBUG_INPUT / file
        print(f"{'=' * 80}")
        print(f"⚙️ Processando: {file}")
        
        try:
            result = processor.process(str(caminho))
            
            # === BOLETOS ===
            if isinstance(result, BoletoData):
                eh_sucesso, motivos = ExtractionDiagnostics.classificar_boleto(result, validar_prazo=validar_prazo)
                
                if eh_sucesso:
                    count_boleto_ok += 1
                    # Armazena objeto e dados para uso posterior
                    boletos_sucesso.append({'object': result, **result.__dict__, **_nf_candidate_fields_from_obs(result.obs_interna)})
                    print(f"✅ BOLETO COMPLETO")
                    print(f"   • Valor: R$ {result.valor_documento:,.2f}")
                    print(f"   • Vencimento: {result.vencimento or 'N/A'}")
                    
                else:
                    count_boleto_falha += 1
                    result_dict = result.__dict__
                    result_dict['motivo_falha'] = '|'.join(motivos)
                    result_dict.update(_nf_candidate_fields_from_obs(result_dict.get('obs_interna')))
                    boletos_falha.append(result_dict)
                    print(f"⚠️ BOLETO INCOMPLETO: {result_dict['motivo_falha']}")
            
            # === NFSe ===
            elif isinstance(result, InvoiceData):
                eh_sucesso, motivos = ExtractionDiagnostics.classificar_nfse(
                    result,
                    validar_prazo=validar_prazo,
                    exigir_numero_nf=exigir_nf,
                )
                
                if eh_sucesso:
                    count_nfse_ok += 1
                    # Armazena objeto e dados para uso posterior
                    nfse_sucesso.append({'object': result, **result.__dict__, **_nf_candidate_fields_from_obs(result.obs_interna)})
                    print(f"✅ NFSe COMPLETA")
                    print(f"   • Número: {result.numero_nota}")
                    print(f"   • Valor: R$ {result.valor_total:,.2f}")
                    
                else:
                    count_nfse_falha += 1
                    result_dict = result.__dict__
                    result_dict['motivo_falha'] = '|'.join(motivos)
                    result_dict.update(_nf_candidate_fields_from_obs(result_dict.get('obs_interna')))
                    nfse_falha.append(result_dict)
                    print(f"⚠️ NFSe INCOMPLETA: {result_dict['motivo_falha']}")

            # === DANFE ===
            elif isinstance(result, DanfeData):
                # Critério mínimo (sem criar uma regra PAF rígida ainda): valor>0 e fornecedor
                motivos = []
                if (result.valor_total or 0) <= 0:
                    motivos.append('VALOR_ZERO')
                if not (result.fornecedor_nome and result.fornecedor_nome.strip()):
                    motivos.append('SEM_RAZAO_SOCIAL')
                if not result.cnpj_emitente:
                    motivos.append('SEM_CNPJ')

                eh_sucesso = len(motivos) == 0

                if eh_sucesso:
                    count_danfe_ok += 1
                    danfe_sucesso.append({'object': result, **result.__dict__, **_nf_candidate_fields_from_obs(result.obs_interna)})
                    print(f"✅ DANFE COMPLETO")
                    print(f"   • Número: {result.numero_nota}")
                    print(f"   • Valor: R$ {result.valor_total:,.2f}")
                else:
                    count_danfe_falha += 1
                    result_dict = result.__dict__
                    result_dict['motivo_falha'] = '|'.join(motivos)
                    result_dict.update(_nf_candidate_fields_from_obs(result_dict.get('obs_interna')))
                    danfe_falha.append(result_dict)
                    print(f"⚠️ DANFE INCOMPLETO: {result_dict['motivo_falha']}")

            # === OUTROS ===
            elif isinstance(result, OtherDocumentData):
                motivos = []
                if (result.valor_total or 0) <= 0:
                    motivos.append('VALOR_ZERO')
                if not (result.fornecedor_nome and result.fornecedor_nome.strip()):
                    motivos.append('SEM_RAZAO_SOCIAL')

                eh_sucesso = len(motivos) == 0

                if eh_sucesso:
                    count_outros_ok += 1
                    outros_sucesso.append({'object': result, **result.__dict__, **_nf_candidate_fields_from_obs(result.obs_interna)})
                    print(f"✅ OUTRO COMPLETO")
                    print(f"   • Subtipo: {result.subtipo or 'N/A'}")
                    print(f"   • Valor: R$ {result.valor_total:,.2f}")
                else:
                    count_outros_falha += 1
                    result_dict = result.__dict__
                    result_dict['motivo_falha'] = '|'.join(motivos)
                    result_dict.update(_nf_candidate_fields_from_obs(result_dict.get('obs_interna')))
                    outros_falha.append(result_dict)
                    print(f"⚠️ OUTRO INCOMPLETO: {result_dict['motivo_falha']}")
            
            else:
                count_erro += 1
                print(f"❓ TIPO DESCONHECIDO")

        except Exception as e:
            count_erro += 1
            print(f"❌ ERRO: {e}")

    # === GERAR CSVs NO FORMATO PAF (18 colunas) ===
    print("\n" + "=" * 80)
    print("💾 GERANDO RELATÓRIOS (Formato PAF - 18 colunas)")
    print("=" * 80)
    
    # Colunas PAF padrão (18 colunas conforme POP 4.10)
    COLUNAS_PAF = [
        "DATA", "SETOR", "EMPRESA", "FORNECEDOR", "NF", "EMISSÃO",
        "VALOR", "Nº PEDIDO", "VENCIMENTO", "FORMA PAGTO", "INDEX",
        "DT CLASS", "Nº FAT", "TP DOC", "TRAT PAF", "LANC SISTEMA",
        "OBSERVAÇÕES", "OBS INTERNA"
    ]
    
    if nfse_sucesso:
        # Converte usando o método to_sheets_row() para formato PAF
        rows_paf = [item['object'].to_sheets_row() for item in nfse_sucesso]
        df_paf = pd.DataFrame(rows_paf, columns=COLUNAS_PAF)
        df_paf.to_csv(DEBUG_CSV_NFSE_SUCESSO, index=False, encoding='utf-8-sig')
        print(f"✅ {DEBUG_CSV_NFSE_SUCESSO.name} ({len(nfse_sucesso)} registros) - Formato PAF")

        # Export adicional (debug completo, inclui NF candidata)
        df_ok_debug = pd.DataFrame([{k: v for k, v in item.items() if k != 'object'} for item in nfse_sucesso])
        debug_ok_path = DIR_DEBUG_OUTPUT / "nfse_sucesso_debug.csv"
        df_ok_debug.to_csv(debug_ok_path, index=False, encoding='utf-8-sig')
        print(f"ℹ️ {debug_ok_path.name} ({len(nfse_sucesso)} registros) - Debug completo (inclui nf_candidate)")
    
    if nfse_falha:
        # Para falhas, mantém dados completos + motivo_falha para debug
        df_falha = pd.DataFrame(nfse_falha)
        df_falha.to_csv(DEBUG_CSV_NFSE_FALHA, index=False, encoding='utf-8-sig')
        print(f"⚠️ {DEBUG_CSV_NFSE_FALHA.name} ({len(nfse_falha)} registros) - Debug completo")
    
    if boletos_sucesso:
        # Converte usando o método to_sheets_row() para formato PAF
        rows_paf = [item['object'].to_sheets_row() for item in boletos_sucesso]
        df_paf = pd.DataFrame(rows_paf, columns=COLUNAS_PAF)
        df_paf.to_csv(DEBUG_CSV_BOLETO_SUCESSO, index=False, encoding='utf-8-sig')
        print(f"✅ {DEBUG_CSV_BOLETO_SUCESSO.name} ({len(boletos_sucesso)} registros) - Formato PAF")

        # Export adicional (debug completo, inclui NF candidata)
        df_ok_debug = pd.DataFrame([{k: v for k, v in item.items() if k != 'object'} for item in boletos_sucesso])
        debug_ok_path = DIR_DEBUG_OUTPUT / "boletos_sucesso_debug.csv"
        df_ok_debug.to_csv(debug_ok_path, index=False, encoding='utf-8-sig')
        print(f"ℹ️ {debug_ok_path.name} ({len(boletos_sucesso)} registros) - Debug completo (inclui nf_candidate)")
    
    if boletos_falha:
        # Para falhas, mantém dados completos + motivo_falha para debug
        df_falha = pd.DataFrame(boletos_falha)
        df_falha.to_csv(DEBUG_CSV_BOLETO_FALHA, index=False, encoding='utf-8-sig')
        print(f"⚠️ {DEBUG_CSV_BOLETO_FALHA.name} ({len(boletos_falha)} registros) - Debug completo")

    if danfe_sucesso:
        rows_paf = [item['object'].to_sheets_row() for item in danfe_sucesso]
        df_paf = pd.DataFrame(rows_paf, columns=COLUNAS_PAF)
        df_paf.to_csv(DEBUG_CSV_DANFE_SUCESSO, index=False, encoding='utf-8-sig')
        print(f"✅ {DEBUG_CSV_DANFE_SUCESSO.name} ({len(danfe_sucesso)} registros) - Formato PAF")

        df_ok_debug = pd.DataFrame([{k: v for k, v in item.items() if k != 'object'} for item in danfe_sucesso])
        debug_ok_path = DIR_DEBUG_OUTPUT / "danfe_sucesso_debug.csv"
        df_ok_debug.to_csv(debug_ok_path, index=False, encoding='utf-8-sig')
        print(f"ℹ️ {debug_ok_path.name} ({len(danfe_sucesso)} registros) - Debug completo (inclui nf_candidate)")

    if danfe_falha:
        df_falha = pd.DataFrame(danfe_falha)
        df_falha.to_csv(DEBUG_CSV_DANFE_FALHA, index=False, encoding='utf-8-sig')
        print(f"⚠️ {DEBUG_CSV_DANFE_FALHA.name} ({len(danfe_falha)} registros) - Debug completo")

    if outros_sucesso:
        rows_paf = [item['object'].to_sheets_row() for item in outros_sucesso]
        df_paf = pd.DataFrame(rows_paf, columns=COLUNAS_PAF)
        df_paf.to_csv(DEBUG_CSV_OUTROS_SUCESSO, index=False, encoding='utf-8-sig')
        print(f"✅ {DEBUG_CSV_OUTROS_SUCESSO.name} ({len(outros_sucesso)} registros) - Formato PAF")

        df_ok_debug = pd.DataFrame([{k: v for k, v in item.items() if k != 'object'} for item in outros_sucesso])
        debug_ok_path = DIR_DEBUG_OUTPUT / "outros_sucesso_debug.csv"
        df_ok_debug.to_csv(debug_ok_path, index=False, encoding='utf-8-sig')
        print(f"ℹ️ {debug_ok_path.name} ({len(outros_sucesso)} registros) - Debug completo (inclui nf_candidate)")

    if outros_falha:
        df_falha = pd.DataFrame(outros_falha)
        df_falha.to_csv(DEBUG_CSV_OUTROS_FALHA, index=False, encoding='utf-8-sig')
        print(f"⚠️ {DEBUG_CSV_OUTROS_FALHA.name} ({len(outros_falha)} registros) - Debug completo")

    # === RELATÓRIO ===
    dados_relatorio = {
        'total': len(arquivos),
        'nfse_ok': count_nfse_ok,
        'nfse_falha': count_nfse_falha,
        'boleto_ok': count_boleto_ok,
        'boleto_falha': count_boleto_falha,
        'danfe_ok': count_danfe_ok,
        'danfe_falha': count_danfe_falha,
        'outros_ok': count_outros_ok,
        'outros_falha': count_outros_falha,
        'erros': count_erro,
        'nfse_falhas_detalhe': nfse_falha,
        'boleto_falhas_detalhe': boletos_falha,
        'danfe_falhas_detalhe': danfe_falha,
        'outros_falhas_detalhe': outros_falha,
    }
    
    # Usa o módulo centralizado de diagnósticos
    ExtractionDiagnostics.salvar_relatorio(dados_relatorio, DEBUG_RELATORIO_QUALIDADE)
    print(f"📊 {DEBUG_RELATORIO_QUALIDADE.name}")
    
    # === RESUMO ===
    print("\n" + "=" * 80)
    print("📊 RESUMO FINAL")
    print("=" * 80)
    print(f"\n📈 NFSe: {count_nfse_ok} OK / {count_nfse_falha} Falhas")
    print(f"📈 Boletos: {count_boleto_ok} OK / {count_boleto_falha} Falhas")
    print(f"📈 DANFE: {count_danfe_ok} OK / {count_danfe_falha} Falhas")
    print(f"📈 Outros: {count_outros_ok} OK / {count_outros_falha} Falhas")
    print(f"❌ Erros: {count_erro}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()