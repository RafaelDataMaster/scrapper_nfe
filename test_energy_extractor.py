"""
Teste do EnergyBillExtractor para faturas de energia elétrica.

Este script testa a extração de campos de faturas de energia
(EDP, CEMIG, etc.) que estavam sendo classificadas incorretamente.
"""

import sys
import os
import logging

# Adicionar diretório pai ao path para importações
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from extractors.energy_bill import EnergyBillExtractor


def test_edp_bill():
    """Testa extração de fatura EDP (caso real do problema)."""
    print("\n🔍 TESTANDO FATURA EDP")
    print("=" * 60)

    # Texto extraído do PDF real "01_BANDFATELBT11_0150403520_0000003479A.pdf"
    texto_edp = """EDP SP DISTRIB DE ENERGIA SA
RUA WERNER VON SIEMENS, 111 SALA 1 CJ 22 BL A LAPA DE BAIXO SAO PAULO CEP 05069-900
CNPJ 02302100000106 - INSCRIÇÃO ESTADUAL 115026474116
Classificação: B - B3-COMERCIAL Tensão Nominal: 220 / 127 V
Modalidade Tarifária: CONVENCIONAL Tipo de Fornecimento: BIFÁSICO
CARRIER TELECOM S A
RUA JOSE CLEMENTE PEREIRA 42 19/11/2025 19/12/2025 30 21/01/2026
ESTIVA / TAUBATE - SP 0150403520
CEP: 12050-530
CNPJ: 38323230000164 NOTA FISCAL N° 006.554.384
EMISSÃO: 20/12/2025 SÉRIE UNICA Série Única
DATA DE EMISSÃO: 20/12/2025
0351485237
Consulte pela Chave de Acesso em:
http://dfe-portal.svrs.rs.gov.br/NF3e/consulta
Chave de acesso:
35251202302100000106660000065543841048823644
DEZ/2025 22/01/2026 369,40 Protocolo de autorização: 335250005979620 - 20/12/2025 às 22:36:01
Débito automático
0605 TUSD - Consumo kWh 330,0 0 0 0 0,591212 1 2 195, 1 0 9,2 8 195,10 18, 0 0 0 35, 1 2 0,45667000 PIS 285,51 1 , 0 3 2,94
0601 TE - Consumo kWh 330,00 0 0 0,427272 7 3 141, 0 0 6,7 1 141,00 18,0 00 25, 3 8 0,33003000 COF I N S 285.51 4, 7 7 0 13.62
0698 Adicional Bandeira Amarela kWh 209,00 0 0 0,024401 9 1 5, 1 0 0,2 4 5,10 18,0 00 0, 92 0,01885000
0698 Adicional Bandeira Vermelha kWh 121,00 0 0 0,057768 6 0 6, 9 9 0,3 3 6,99 18,0 00 1, 2 6 0,04463000
0805 Multa Ref.: Out/25 6, 4 2 0,00000000
0807 Contribuição de Ilum. Pública - Lei Municipal 14, 7 9 0,00000000
TOTAL 369, 4 0 16,5 6 348,19 62, 6 8
AMARELA
01/12/2025 a 19/12/2025 19 dias
Vermelha PTM 1
20/11/2025 a 30/11/2025 1"""

    extractor = EnergyBillExtractor()

    # Testar can_handle
    can = extractor.can_handle(texto_edp)
    print(f"✅ can_handle: {can}")
    assert can == True, "Extrator deveria reconhecer fatura EDP como energia"

    # Extrair dados
    data = extractor.extract(texto_edp)

    # Verificar campos obrigatórios
    required_fields = [
        ("tipo_documento", "ENERGY_BILL"),
        ("fornecedor_nome", None),  # Não None
        ("valor_total", lambda x: x > 0),
        ("cnpj_prestador", None),  # Não None
        ("numero_nota", None),  # Não None
    ]

    for field, expected in required_fields:
        value = data.get(field)
        print(f"  {field}: {value}")

        if expected is None:
            assert value is not None, f"Campo {field} não deveria ser None"
        elif callable(expected):
            assert expected(value), f"Campo {field} não passou na validação: {value}"
        else:
            assert value == expected, (
                f"Campo {field} esperado {expected}, obtido {value}"
            )

    # Resultados esperados específicos para esta fatura
    print(f"\n📊 RESULTADOS EXTRAÍDOS:")
    print(f"   Fornecedor: {data.get('fornecedor_nome')}")
    print(f"   CNPJ: {data.get('cnpj_prestador')}")
    print(f"   Nota: {data.get('numero_nota')}")
    print(f"   Valor total: R$ {data.get('valor_total', 0):.2f}")
    print(f"   Vencimento: {data.get('vencimento')}")
    print(f"   Data emissão: {data.get('data_emissao')}")
    print(f"   Período: {data.get('periodo_referencia')}")
    print(f"   Instalação: {data.get('instalacao')}")

    # Validações específicas
    assert "EDP" in data.get("fornecedor_nome", "").upper(), (
        "Fornecedor deveria conter EDP"
    )
    assert data.get("valor_total") >= 300.0, (
        f"Valor parece baixo para uma fatura: {data.get('valor_total')}"
    )

    return data


def test_cemig_bill():
    """Testa extração de fatura CEMIG (exemplo genérico)."""
    print("\n🔍 TESTANDO FATURA CEMIG")
    print("=" * 60)

    texto_cemig = """CEMIG DISTRIBUIÇÃO S.A.
CNPJ: 06.981.180/0001-16
NOTA FISCAL N° 342654282
EMISSÃO: 15/01/2026
VENCIMENTO: 22/01/2026
CONSUMO: 734.97 kWh
TOTAL: R$ 734,97
MÊS REFERÊNCIA: JAN/2026
INSTALAÇÃO: 213779192
BANDEIRA TARIFÁRIA: VERMELHA PATAMAR 1"""

    extractor = EnergyBillExtractor()

    can = extractor.can_handle(texto_cemig)
    print(f"✅ can_handle: {can}")
    assert can == True, "Extrator deveria reconhecer fatura CEMIG como energia"

    data = extractor.extract(texto_cemig)

    print(f"\n📊 RESULTADOS EXTRAÍDOS:")
    print(f"   Fornecedor: {data.get('fornecedor_nome')}")
    print(f"   CNPJ: {data.get('cnpj_prestador')}")
    print(f"   Nota: {data.get('numero_nota')}")
    print(f"   Valor total: R$ {data.get('valor_total', 0):.2f}")
    print(f"   Vencimento: {data.get('vencimento')}")

    return data


def test_negative_cases():
    """Testa documentos que NÃO devem ser reconhecidos como energia."""
    print("\n🔍 TESTANDO CASOS NEGATIVOS")
    print("=" * 60)

    extractor = EnergyBillExtractor()

    # Documento administrativo (não é energia)
    texto_admin = """DOCUMENTO ADMINISTRATIVO
MEMORANDO INTERNO
REFERÊNCIA: 2025-0456
DATA: 20/12/2025
ASSUNTO: Reunião de planejamento"""

    can = extractor.can_handle(texto_admin)
    print(f"✅ Documento administrativo - can_handle: {can} (esperado: False)")
    assert can == False, (
        "Documento administrativo não deveria ser reconhecido como energia"
    )

    # Boleto bancário
    texto_boleto = """BOLETO BANCÁRIO
BANCO DO BRASIL
LINHA DIGITÁVEL: 00190.00009 01234.567890 12345.678901 2 12345678901234
VALOR: R$ 1.234,56
VENCIMENTO: 30/12/2025"""

    can = extractor.can_handle(texto_boleto)
    print(f"✅ Boleto bancário - can_handle: {can} (esperado: False)")
    assert can == False, "Boleto não deveria ser reconhecido como energia"

    print("✅ Todos os casos negativos passaram!")


def test_extractor_priority():
    """Testa se o extrator tem prioridade correta no sistema."""
    print("\n🔍 TESTANDO PRIORIDADE DO EXTRATOR")
    print("=" * 60)

    from core.extractors import EXTRACTOR_REGISTRY

    # Encontrar a posição do EnergyBillExtractor no registro
    extractor_classes = [cls.__name__ for cls in EXTRACTOR_REGISTRY]
    energy_index = (
        extractor_classes.index("EnergyBillExtractor")
        if "EnergyBillExtractor" in extractor_classes
        else -1
    )

    print(f"Extratores no registro: {extractor_classes}")
    print(f"Posição do EnergyBillExtractor: {energy_index}")

    # EnergyBillExtractor deve estar antes de extratores genéricos como OutrosExtractor e NfseGenericExtractor
    if "OutrosExtractor" in extractor_classes:
        outros_index = extractor_classes.index("OutrosExtractor")
        assert energy_index < outros_index, (
            "EnergyBillExtractor deve ter prioridade sobre OutrosExtractor"
        )
        print(
            f"✅ Prioridade correta: EnergyBillExtractor[{energy_index}] antes de OutrosExtractor[{outros_index}]"
        )

    if "NfseGenericExtractor" in extractor_classes:
        nfse_index = extractor_classes.index("NfseGenericExtractor")
        assert energy_index < nfse_index, (
            "EnergyBillExtractor deve ter prioridade sobre NfseGenericExtractor"
        )
        print(
            f"✅ Prioridade correta: EnergyBillExtractor[{energy_index}] antes de NfseGenericExtractor[{nfse_index}]"
        )

    print("✅ Prioridade do extrator está correta!")


def main():
    """Executa todos os testes."""
    print("🧪 TESTE DO ENERGYBILLEXTRACTOR")
    print("=" * 60)

    try:
        # Testar casos positivos
        edp_data = test_edp_bill()
        cemig_data = test_cemig_bill()

        # Testar casos negativos
        test_negative_cases()

        # Testar prioridade
        test_extractor_priority()

        print("\n" + "=" * 60)
        print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
        print("=" * 60)

        # Resumo dos resultados
        print("\n📈 RESUMO DA EXTRAÇÃO EDP:")
        print(f"   • Fornecedor: {edp_data.get('fornecedor_nome')}")
        print(f"   • Valor extraído: R$ {edp_data.get('valor_total', 0):.2f}")
        print(f"   • Vencimento: {edp_data.get('vencimento')}")
        print(
            f"   • Problema resolvido: Fatura não será mais classificada como 'outros' com valor zero"
        )

        return 0

    except AssertionError as e:
        print(f"\n❌ FALHA NO TESTE: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
