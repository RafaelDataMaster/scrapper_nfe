"""
Script de validação de regras de extração para NFSe e Boletos.

Este script processa PDFs da pasta failed_cases_pdf e gera relatórios
detalhados separando sucessos e falhas, auxiliando no ajuste fino das regex.
"""
import os
import pandas as pd
from _init_env import setup_project_path

# Inicializa o ambiente do projeto
setup_project_path()

from core.processor import BaseInvoiceProcessor
from core.models import BoletoData, InvoiceData
from core.diagnostics import ExtractionDiagnostics
from config.settings import (
    DIR_DEBUG_INPUT,
    DIR_DEBUG_OUTPUT,
    DEBUG_CSV_NFSE_SUCESSO,
    DEBUG_CSV_NFSE_FALHA,
    DEBUG_CSV_BOLETO_SUCESSO,
    DEBUG_CSV_BOLETO_FALHA,
    DEBUG_RELATORIO_QUALIDADE
)

# As funções de classificação e relatório foram movidas para core.diagnostics
# Mantemos compatibilidade aqui para facilitar a transição
classificar_nfse = ExtractionDiagnostics.classificar_nfse
classificar_boleto = ExtractionDiagnostics.classificar_boleto

def main() -> None:
    """
    Testa as regras de extração nos PDFs da pasta failed_cases_pdf.
    
    Gera CSVs separados:
    - nfse_sucesso.csv / nfse_falha.csv (com coluna motivo_falha)
    - boletos_sucesso.csv / boletos_falha.csv (com coluna motivo_falha)
    - relatorio_qualidade.txt (estatísticas gerais)
    """
    # Cria pasta de saída se não existir
    DIR_DEBUG_OUTPUT.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("🧪 TESTE DE REGRAS - NFSe & BOLETOS")
    print("=" * 80)
    print(f"📂 Lendo: {DIR_DEBUG_INPUT}")
    print(f"💾 Salvando em: {DIR_DEBUG_OUTPUT}")
    print("=" * 80)

    processor = BaseInvoiceProcessor()
    
    # Listas separadas
    nfse_sucesso = []
    nfse_falha = []
    boletos_sucesso = []
    boletos_falha = []
    
    # Contadores
    count_nfse_ok = 0
    count_nfse_falha = 0
    count_boleto_ok = 0
    count_boleto_falha = 0
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
                eh_sucesso, motivos = classificar_boleto(result)
                
                if eh_sucesso:
                    count_boleto_ok += 1
                    boletos_sucesso.append(result.__dict__)
                    print(f"✅ BOLETO COMPLETO")
                    print(f"   • Valor: R$ {result.valor_documento:,.2f}")
                    print(f"   • Vencimento: {result.vencimento or 'N/A'}")
                    
                else:
                    count_boleto_falha += 1
                    result_dict = result.__dict__
                    result_dict['motivo_falha'] = '|'.join(motivos)
                    boletos_falha.append(result_dict)
                    print(f"⚠️ BOLETO INCOMPLETO: {result_dict['motivo_falha']}")
            
            # === NFSe ===
            elif isinstance(result, InvoiceData):
                eh_sucesso, motivos = classificar_nfse(result)
                
                if eh_sucesso:
                    count_nfse_ok += 1
                    nfse_sucesso.append(result.__dict__)
                    print(f"✅ NFSe COMPLETA")
                    print(f"   • Número: {result.numero_nota}")
                    print(f"   • Valor: R$ {result.valor_total:,.2f}")
                    
                else:
                    count_nfse_falha += 1
                    result_dict = result.__dict__
                    result_dict['motivo_falha'] = '|'.join(motivos)
                    nfse_falha.append(result_dict)
                    print(f"⚠️ NFSe INCOMPLETA: {result_dict['motivo_falha']}")
            
            else:
                count_erro += 1
                print(f"❓ TIPO DESCONHECIDO")

        except Exception as e:
            count_erro += 1
            print(f"❌ ERRO: {e}")

    # === GERAR CSVs ===
    print("\n" + "=" * 80)
    print("💾 GERANDO RELATÓRIOS")
    print("=" * 80)
    
    if nfse_sucesso:
        pd.DataFrame(nfse_sucesso).to_csv(DEBUG_CSV_NFSE_SUCESSO, index=False, encoding='utf-8-sig')
        print(f"✅ {DEBUG_CSV_NFSE_SUCESSO.name} ({len(nfse_sucesso)} registros)")
    
    if nfse_falha:
        pd.DataFrame(nfse_falha).to_csv(DEBUG_CSV_NFSE_FALHA, index=False, encoding='utf-8-sig')
        print(f"⚠️ {DEBUG_CSV_NFSE_FALHA.name} ({len(nfse_falha)} registros)")
    
    if boletos_sucesso:
        pd.DataFrame(boletos_sucesso).to_csv(DEBUG_CSV_BOLETO_SUCESSO, index=False, encoding='utf-8-sig')
        print(f"✅ {DEBUG_CSV_BOLETO_SUCESSO.name} ({len(boletos_sucesso)} registros)")
    
    if boletos_falha:
        pd.DataFrame(boletos_falha).to_csv(DEBUG_CSV_BOLETO_FALHA, index=False, encoding='utf-8-sig')
        print(f"⚠️ {DEBUG_CSV_BOLETO_FALHA.name} ({len(boletos_falha)} registros)")

    # === RELATÓRIO ===
    dados_relatorio = {
        'total': len(arquivos),
        'nfse_ok': count_nfse_ok,
        'nfse_falha': count_nfse_falha,
        'boleto_ok': count_boleto_ok,
        'boleto_falha': count_boleto_falha,
        'erros': count_erro,
        'nfse_falhas_detalhe': nfse_falha,
        'boleto_falhas_detalhe': boletos_falha
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
    print(f"❌ Erros: {count_erro}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()