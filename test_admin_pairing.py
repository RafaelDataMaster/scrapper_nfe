# -*- coding: utf-8 -*-
"""
Teste da integração entre detecção de documentos administrativos e pareamento.

Este script testa se os avisos de documento administrativo gerados pelo
CorrelationService são corretamente propagados para os DocumentPair
gerados pelo DocumentPairingService.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from core.batch_result import BatchResult
from core.correlation_service import CorrelationService
from core.document_pairing import DocumentPairingService
from core.models import OtherDocumentData


def test_admin_detection_in_pairing():
    """
    Testa se documentos administrativos têm o aviso correto nos DocumentPair.
    """
    pairing_service = DocumentPairingService()
    correlation_service = CorrelationService()

    print('=' * 80)
    print('TESTE DE PROPAGAÇÃO DE DOCUMENTOS ADMINISTRATIVOS PARA DocumentPair')
    print('=' * 80)

    # Casos de teste: assuntos administrativos que DEVEM gerar aviso
    test_cases = [
        # (assunto, descrição esperada)
        ('Lembrete Gentil: Vencimento de Fatura', 'Lembrete administrativo'),
        ('Sua ordem Equinix n.º 1-255425159203 agendada com sucesso', 'Ordem de serviço/agendamento'),
        ('GUIA | Processo - Miralva Macedo Dias x CSC', 'Guia jurídica/fiscal'),
        ('Cobrança Indevida 11/2025 - 4security', 'Reclamação de cobrança'),
        ('December - 2025 Invoice for 6343 - ATIVE', 'Invoice internacional'),
        ('CONTRATO_SITE MASTER INTERNET', 'Documento de contrato'),
        ('Tarifas CSC - Acerto MOC - apuração até 31/12/2025', 'Documento de tarifas internas'),
    ]

    # Assuntos que NÃO devem gerar aviso (cobranças reais)
    normal_cases = [
        'CEMIG FATURA ONLINE - 214687921',
        'NFS-e + Boleto No 3494',
        'Boleto ACIV',
        'Sua fatura chegou',
        'Nota Fiscal Eletrônica Nº 103977',
    ]

    print('\n📋 TESTANDO ASSUNTOS ADMINISTRATIVOS:')
    print('-' * 80)

    admin_ok = 0
    admin_fail = 0

    for subject, expected_desc in test_cases:
        # Cria batch com documento fictício
        batch = BatchResult(batch_id=f"test_admin_{subject[:20]}")
        batch.email_subject = subject

        # Adiciona um documento "outro" com valor 0 (típico de documentos administrativos)
        doc = OtherDocumentData(
            arquivo_origem=f"doc_{subject[:10]}.pdf",
            valor_total=0.0
        )
        batch.add_document(doc)

        # Aplica correlação
        correlation_result = correlation_service.correlate(batch)
        batch.correlation_result = correlation_result

        # Gera pairs via DocumentPairingService
        pairs = pairing_service.pair_documents(batch)

        # Verifica se o pair contém o aviso
        if pairs:
            pair = pairs[0]
            has_admin_warning = pair.divergencia and "POSSÍVEL DOCUMENTO ADMINISTRATIVO" in pair.divergencia

            # Verifica também no correlation_result diretamente
            correlation_has_warning = correlation_result.divergencia and "POSSÍVEL DOCUMENTO ADMINISTRATIVO" in correlation_result.divergencia

            if has_admin_warning and correlation_has_warning:
                # Extrai descrição para verificar se é a esperada
                import re
                match = re.search(r'POSSÍVEL DOCUMENTO ADMINISTRATIVO - ([^\]]+)', pair.divergencia or "")
                actual_desc = match.group(1) if match else "N/A"

                if expected_desc in actual_desc:
                    status = f'✅ OK: {expected_desc}'
                    admin_ok += 1
                else:
                    status = f'⚠️ Descrição diferente: esperado "{expected_desc}", obtido "{actual_desc}"'
                    admin_fail += 1
            else:
                status = f'❌ SEM AVISO ADMIN'
                admin_fail += 1
        else:
            status = f'❌ SEM PAIRS'
            admin_fail += 1

        print(f'{status:60} | {subject[:40]}...')

    print('\n📄 TESTANDO ASSUNTOS NORMAIS (NÃO ADMINISTRATIVOS):')
    print('-' * 80)

    normal_ok = 0
    normal_fail = 0

    for subject in normal_cases:
        # Cria batch com documento normal
        batch = BatchResult(batch_id=f"test_normal_{subject[:20]}")
        batch.email_subject = subject

        # Adiciona um documento com valor (cobrança real)
        doc = OtherDocumentData(
            arquivo_origem=f"doc_{subject[:10]}.pdf",
            valor_total=150.75
        )
        batch.add_document(doc)

        # Aplica correlação
        correlation_result = correlation_service.correlate(batch)
        batch.correlation_result = correlation_result

        # Gera pairs
        pairs = pairing_service.pair_documents(batch)

        # Verifica se NÃO tem aviso administrativo
        has_admin_warning = False
        if pairs and pairs[0].divergencia:
            has_admin_warning = "POSSÍVEL DOCUMENTO ADMINISTRATIVO" in pairs[0].divergencia

        correlation_has_warning = correlation_result.divergencia and "POSSÍVEL DOCUMENTO ADMINISTRATIVO" in correlation_result.divergencia

        if not has_admin_warning and not correlation_has_warning:
            status = '✅ SEM AVISO (correto)'
            normal_ok += 1
        elif has_admin_warning:
            status = '⚠️ FALSO POSITIVO em pair'
            normal_fail += 1
        elif correlation_has_warning:
            status = '⚠️ FALSO POSITIVO em correlation'
            normal_fail += 1
        else:
            status = '❌ ERRO'
            normal_fail += 1

        print(f'{status:60} | {subject[:40]}...')

    print('\n' + '=' * 80)
    print('RESUMO:')
    print(f'  Administrativo: {admin_ok}/{len(test_cases)} com aviso correto')
    print(f'  Normal: {normal_ok}/{len(normal_cases)} sem aviso (correto)')
    if admin_fail > 0:
        print(f'  ⚠️ {admin_fail} assuntos admin SEM aviso ou com aviso incorreto!')
    if normal_fail > 0:
        print(f'  ⚠️ {normal_fail} falsos positivos!')

    # Teste adicional: verificar se aviso aparece no CSV final
    print('\n📊 TESTE DE FORMATAÇÃO DO AVISO NO DIVERGENCIA:')
    print('-' * 80)

    # Testa um caso específico
    batch = BatchResult(batch_id="test_format")
    batch.email_subject = "Lembrete Gentil: Vencimento de Fatura"
    batch.add_document(OtherDocumentData(arquivo_origem="lembrete.pdf", valor_total=0.0))

    correlation_result = correlation_service.correlate(batch)
    batch.correlation_result = correlation_result

    pairs = pairing_service.pair_documents(batch)

    if pairs:
        pair = pairs[0]
        print(f'Assunto: {batch.email_subject}')
        print(f'Correlation divergencia: {correlation_result.divergencia}')
        print(f'Pair divergencia: {pair.divergencia}')
        print(f'Pair status: {pair.status}')

        # Verifica se o formato está correto para exportação CSV
        summary = pair.to_summary()
        print(f'CSV divergencia: {summary.get("divergencia")}')

        if summary.get("divergencia") and "POSSÍVEL DOCUMENTO ADMINISTRATIVO" in summary.get("divergencia", ""):
            print('✅ Aviso presente no CSV summary')
        else:
            print('❌ Aviso NÃO presente no CSV summary')

    print('=' * 80)

    # Retorna resultado geral
    return admin_ok == len(test_cases) and normal_ok == len(normal_cases)

if __name__ == "__main__":
    success = test_admin_detection_in_pairing()
    sys.exit(0 if success else 1)
