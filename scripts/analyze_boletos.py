"""
Script de Análise: Vinculação de Boletos e NFSe

Este script analisa os relatórios gerados e tenta vincular boletos às suas NFSe correspondentes.
"""

from _init_env import setup_project_path
setup_project_path()

import pandas as pd
from datetime import datetime, timedelta
from config import settings

def main():
    print("=" * 80)
    print("ANÁLISE DE VINCULAÇÃO: BOLETOS x NFSe")
    print("=" * 80)
    
    # Carregar dados
    try:
        nfse_path = settings.DIR_SAIDA / "relatorio_nfse.csv"
        boleto_path = settings.DIR_SAIDA / "relatorio_boletos.csv"
        
        if not nfse_path.exists():
            print(f"❌ Arquivo não encontrado: {nfse_path}")
            return
        
        if not boleto_path.exists():
            print(f"❌ Arquivo não encontrado: {boleto_path}")
            return
        
        df_nfse = pd.read_csv(nfse_path)
        df_boleto = pd.read_csv(boleto_path)
        
        print(f"\n📊 Dados carregados:")
        print(f"  - NFSe: {len(df_nfse)} registros")
        print(f"  - Boletos: {len(df_boleto)} registros")
        
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return
    
    # Estatísticas Gerais
    print("\n" + "=" * 80)
    print("ESTATÍSTICAS GERAIS")
    print("=" * 80)
    
    print(f"\n💰 Valores Totais:")
    print(f"  - NFSe: R$ {df_nfse['valor_total'].sum():,.2f}")
    print(f"  - Boletos: R$ {df_boleto['valor_documento'].sum():,.2f}")
    
    print(f"\n📈 Valores Médios:")
    print(f"  - NFSe: R$ {df_nfse['valor_total'].mean():,.2f}")
    print(f"  - Boletos: R$ {df_boleto['valor_documento'].mean():,.2f}")
    
    # Análise de Vinculação
    print("\n" + "=" * 80)
    print("ANÁLISE DE VINCULAÇÃO")
    print("=" * 80)
    
    # Método 1: Referência Explícita
    print("\n[Método 1] Vinculação por Referência Explícita:")
    boletos_com_ref = df_boleto[df_boleto['referencia_nfse'].notna()]
    print(f"  - Boletos com referência à NF: {len(boletos_com_ref)} de {len(df_boleto)}")
    
    if len(boletos_com_ref) > 0:
        merged_ref = pd.merge(
            boletos_com_ref,
            df_nfse,
            left_on='referencia_nfse',
            right_on='numero_nota',
            how='left',
            suffixes=('_boleto', '_nfse')
        )
        vinculados_ref = merged_ref[merged_ref['numero_nota'].notna()]
        print(f"  - Vinculações bem-sucedidas: {len(vinculados_ref)}")
        
        if len(vinculados_ref) > 0:
            print(f"\n  Exemplos de vinculação:")
            for idx, row in vinculados_ref.head(3).iterrows():
                print(f"    • Boleto (Doc: {row['numero_documento']}) ↔ NF {row['numero_nota']}")
                print(f"      Valor Boleto: R$ {row['valor_documento']:,.2f} | Valor NF: R$ {row['valor_total']:,.2f}")
    
    # Método 2: Número do Documento
    print("\n[Método 2] Vinculação por Número do Documento:")
    boletos_com_doc = df_boleto[df_boleto['numero_documento'].notna()]
    print(f"  - Boletos com nº documento: {len(boletos_com_doc)} de {len(df_boleto)}")
    
    if len(boletos_com_doc) > 0:
        merged_doc = pd.merge(
            boletos_com_doc,
            df_nfse,
            left_on='numero_documento',
            right_on='numero_nota',
            how='left',
            suffixes=('_boleto', '_nfse')
        )
        vinculados_doc = merged_doc[merged_doc['numero_nota'].notna()]
        print(f"  - Vinculações bem-sucedidas: {len(vinculados_doc)}")
    
    # Método 3: CNPJ + Valor
    print("\n[Método 3] Vinculação por CNPJ + Valor:")
    df_boleto_norm = df_boleto.copy()
    df_nfse_norm = df_nfse.copy()
    
    df_boleto_norm['valor_normalizado'] = df_boleto_norm['valor_documento'].round(2)
    df_nfse_norm['valor_normalizado'] = df_nfse_norm['valor_total'].round(2)
    
    merged_cnpj_valor = pd.merge(
        df_boleto_norm,
        df_nfse_norm,
        left_on=['cnpj_beneficiario', 'valor_normalizado'],
        right_on=['cnpj_prestador', 'valor_normalizado'],
        how='left',
        suffixes=('_boleto', '_nfse')
    )
    vinculados_cnpj = merged_cnpj_valor[merged_cnpj_valor['numero_nota'].notna()]
    print(f"  - Vinculações bem-sucedidas: {len(vinculados_cnpj)}")
    
    # Resumo de Vinculação
    print("\n" + "=" * 80)
    print("RESUMO DE VINCULAÇÃO")
    print("=" * 80)
    
    total_vinculados = len(set(
        list(vinculados_ref['arquivo_origem_boleto'].values if len(boletos_com_ref) > 0 and len(vinculados_ref) > 0 else []) +
        list(vinculados_doc['arquivo_origem_boleto'].values if len(boletos_com_doc) > 0 and len(vinculados_doc) > 0 else []) +
        list(vinculados_cnpj['arquivo_origem_boleto'].values if len(vinculados_cnpj) > 0 else [])
    ))
    
    print(f"\nTotal de boletos vinculados (qualquer método): {total_vinculados} de {len(df_boleto)}")
    print(f"Percentual de vinculação: {total_vinculados/len(df_boleto)*100:.1f}%")
    
    boletos_sem_vinculo = len(df_boleto) - total_vinculados
    if boletos_sem_vinculo > 0:
        print(f"\n⚠️ {boletos_sem_vinculo} boletos sem NFSe correspondente encontrada")
    
    # Alertas de Vencimento
    print("\n" + "=" * 80)
    print("ALERTAS DE VENCIMENTO")
    print("=" * 80)
    
    df_boleto['vencimento_dt'] = pd.to_datetime(df_boleto['vencimento'], errors='coerce')
    hoje = datetime.now()
    limite_7dias = hoje + timedelta(days=7)
    limite_30dias = hoje + timedelta(days=30)
    
    vencidos = df_boleto[df_boleto['vencimento_dt'] < hoje]
    proximos_7 = df_boleto[(df_boleto['vencimento_dt'] >= hoje) & (df_boleto['vencimento_dt'] <= limite_7dias)]
    proximos_30 = df_boleto[(df_boleto['vencimento_dt'] > limite_7dias) & (df_boleto['vencimento_dt'] <= limite_30dias)]
    
    if len(vencidos) > 0:
        print(f"\n🔴 {len(vencidos)} boletos VENCIDOS:")
        for idx, row in vencidos.iterrows():
            print(f"  • {row['arquivo_origem']} - R$ {row['valor_documento']:,.2f} - Vencimento: {row['vencimento']}")
    
    if len(proximos_7) > 0:
        print(f"\n🟡 {len(proximos_7)} boletos vencem nos próximos 7 dias:")
        for idx, row in proximos_7.iterrows():
            print(f"  • {row['arquivo_origem']} - R$ {row['valor_documento']:,.2f} - Vencimento: {row['vencimento']}")
    
    if len(proximos_30) > 0:
        print(f"\n🟢 {len(proximos_30)} boletos vencem entre 7-30 dias")
    
    # Fornecedores
    print("\n" + "=" * 80)
    print("ANÁLISE POR FORNECEDOR")
    print("=" * 80)
    
    print("\n📊 Top 5 Fornecedores (por valor de boletos):")
    top_fornecedores = df_boleto.groupby('cnpj_beneficiario').agg({
        'valor_documento': 'sum',
        'arquivo_origem': 'count'
    }).sort_values('valor_documento', ascending=False).head(5)
    
    for cnpj, row in top_fornecedores.iterrows():
        print(f"  • CNPJ: {cnpj}")
        print(f"    - Valor total: R$ {row['valor_documento']:,.2f}")
        print(f"    - Quantidade: {row['arquivo_origem']} boletos")
    
    print("\n" + "=" * 80)
    print("ANÁLISE CONCLUÍDA")
    print("=" * 80)

if __name__ == "__main__":
    main()
