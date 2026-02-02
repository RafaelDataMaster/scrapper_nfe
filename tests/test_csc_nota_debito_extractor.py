"""
Testes para o extrator CscNotaDebitoExtractor.

Este módulo testa a extração de documentos do tipo "NOTA DÉBITO / RECIBO FATURA"
emitidos pela CSC GESTAO INTEGRADA S/A.
"""

import pytest

from extractors.csc_nota_debito import CscNotaDebitoExtractor


class TestCscNotaDebitoCanHandle:
    """Testes para o método can_handle."""

    def test_can_handle_nota_debito_recibo_fatura(self):
        """Deve aceitar documento com 'NOTA DÉBITO / RECIBO FATURA'."""
        texto = """
        Página: 1 de 1
        NOTA DÉBITO / RECIBO FATURA (AR)
        Numero: 347
        38.323.227/0001-40
        CSC GESTAO INTEGRADA S/A
        """
        assert CscNotaDebitoExtractor.can_handle(texto) is True

    def test_can_handle_nota_debito_simples(self):
        """Deve aceitar documento com apenas 'NOTA DÉBITO'."""
        texto = """
        NOTA DÉBITO
        Numero: 123
        38.323.227/0001-40
        CSC GESTAO INTEGRADA S/A
        """
        assert CscNotaDebitoExtractor.can_handle(texto) is True

    def test_can_handle_com_cnpj_csc(self):
        """Deve aceitar documento com CNPJ da CSC."""
        texto = """
        NOTA DÉBITO / RECIBO FATURA
        38.323.227/0001-40
        Emissão: 07/01/2026
        """
        assert CscNotaDebitoExtractor.can_handle(texto) is True

    def test_reject_sem_identificador(self):
        """Deve rejeitar documento sem identificador de nota débito."""
        texto = """
        38.323.227/0001-40
        CSC GESTAO INTEGRADA S/A
        Valor: R$ 1.000,00
        """
        assert CscNotaDebitoExtractor.can_handle(texto) is False

    def test_reject_sem_csc(self):
        """Deve rejeitar documento sem referência à CSC."""
        texto = """
        NOTA DÉBITO / RECIBO FATURA
        Numero: 347
        Outra Empresa LTDA
        """
        assert CscNotaDebitoExtractor.can_handle(texto) is False

    def test_reject_nfse(self):
        """Deve rejeitar NFS-e mesmo com NOTA DÉBITO no texto."""
        texto = """
        NOTA DÉBITO / RECIBO FATURA
        38.323.227/0001-40
        NFS-E Nº 12345
        NOTA FISCAL DE SERVIÇO ELETRÔNICA
        CHAVE DE ACESSO: 12345678901234567890123456789012345678901234
        """
        assert CscNotaDebitoExtractor.can_handle(texto) is False

    def test_reject_danfe(self):
        """Deve rejeitar DANFE."""
        texto = """
        NOTA DÉBITO
        38.323.227/0001-40
        DANFE
        DOCUMENTO AUXILIAR DA NF-E
        """
        assert CscNotaDebitoExtractor.can_handle(texto) is False

    def test_reject_boleto(self):
        """Deve rejeitar boleto bancário."""
        texto = """
        NOTA DÉBITO
        38.323.227/0001-40
        RECIBO DO SACADO
        LINHA DIGITÁVEL
        """
        assert CscNotaDebitoExtractor.can_handle(texto) is False

    def test_can_handle_empty_text(self):
        """Deve rejeitar texto vazio."""
        assert CscNotaDebitoExtractor.can_handle("") is False
        assert CscNotaDebitoExtractor.can_handle(None) is False


class TestCscNotaDebitoExtract:
    """Testes para o método extract."""

    @pytest.fixture
    def texto_completo(self):
        """Texto completo de exemplo de NOTA DÉBITO / RECIBO FATURA."""
        return """
        Página: 1 de 1
        NOTA DÉBITO / RECIBO FATURA (AR)
        Numero: 347
        38.323.227/0001-40
        CSC GESTAO INTEGRADA S/A Emissão: 07/01/2026
        Av Vinte E Um De Abril Número: 505
        Competência: dezembro-25
        Complemento: SALA 201
        CEP: 35.500-010 Bairro: Centro Divinopolis - MG
        Tomador:
        ATIVE TELECOMUNICAÇÕES S.A.
        33.960.847/0001-77
        Preço (R$)
        Item Descrição
        Quant. Unit. Total
        1 Boletos Impressos 384 3,00 1.152,00
        3 Boletos online 1600 0,60 960,00
        3 4 Boletos online/baixas por decurso de prazo 258 0,20 51,60
        VALOR TOTAL R$ 2.163,60
        Observações:
        """

    def test_extract_tipo_documento(self, texto_completo):
        """Deve extrair tipo_documento como OUTRO e subtipo como NOTA_DEBITO."""
        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto_completo)

        assert data["tipo_documento"] == "OUTRO"
        assert data["subtipo"] == "NOTA_DEBITO"

    def test_extract_fornecedor(self, texto_completo):
        """Deve extrair dados do fornecedor (CSC)."""
        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto_completo)

        assert data["fornecedor_nome"] == "CSC GESTAO INTEGRADA S/A"
        assert data["cnpj_fornecedor"] == "38.323.227/0001-40"

    def test_extract_numero_documento(self, texto_completo):
        """Deve extrair número do documento."""
        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto_completo)

        assert data["numero_documento"] == "347"
        assert data["numero_nota"] == "347"

    def test_extract_data_emissao(self, texto_completo):
        """Deve extrair e formatar data de emissão."""
        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto_completo)

        assert data["data_emissao"] == "2026-01-07"

    def test_extract_competencia(self, texto_completo):
        """Deve extrair competência."""
        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto_completo)

        assert data["competencia"] == "dezembro-25"

    def test_extract_tomador(self, texto_completo):
        """Deve extrair dados do tomador."""
        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto_completo)

        assert "ATIVE" in data["tomador_nome"].upper()
        assert data["cnpj_tomador"] == "33.960.847/0001-77"

    def test_extract_valor_total(self, texto_completo):
        """Deve extrair valor total."""
        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto_completo)

        assert data["valor_total"] == 2163.60
        assert data["valor_documento"] == 2163.60

    def test_extract_itens_como_observacoes(self, texto_completo):
        """Deve extrair itens como observações."""
        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto_completo)

        # Verifica se observações contêm descrições dos itens
        obs = data.get("observacoes", "")
        assert "Boletos Impressos" in obs or "Boletos online" in obs

    def test_extract_numero_diferentes_formatos(self):
        """Deve extrair número em diferentes formatos."""
        extractor = CscNotaDebitoExtractor()

        # Formato "Numero: 347"
        texto1 = """
        NOTA DÉBITO / RECIBO FATURA
        Numero: 347
        38.323.227/0001-40
        VALOR TOTAL R$ 100,00
        """
        data1 = extractor.extract(texto1)
        assert data1["numero_documento"] == "347"

        # Formato "Número: 348"
        texto2 = """
        NOTA DÉBITO / RECIBO FATURA
        Número: 348
        38.323.227/0001-40
        VALOR TOTAL R$ 100,00
        """
        data2 = extractor.extract(texto2)
        assert data2["numero_documento"] == "348"

    def test_extract_valor_diferentes_formatos(self):
        """Deve extrair valor em diferentes formatos."""
        extractor = CscNotaDebitoExtractor()

        # Formato "VALOR TOTAL R$ 2.163,60"
        texto1 = """
        NOTA DÉBITO / RECIBO FATURA
        38.323.227/0001-40
        VALOR TOTAL R$ 2.163,60
        """
        data1 = extractor.extract(texto1)
        assert data1["valor_total"] == 2163.60

        # Formato "VALOR TOTAL: R$ 500,00"
        texto2 = """
        NOTA DÉBITO / RECIBO FATURA
        38.323.227/0001-40
        VALOR TOTAL: R$ 500,00
        """
        data2 = extractor.extract(texto2)
        assert data2["valor_total"] == 500.00

    def test_extract_competencia_diferentes_formatos(self):
        """Deve extrair competência em diferentes formatos."""
        extractor = CscNotaDebitoExtractor()

        # Formato "dezembro-25"
        texto1 = """
        NOTA DÉBITO / RECIBO FATURA
        38.323.227/0001-40
        Competência: dezembro-25
        VALOR TOTAL R$ 100,00
        """
        data1 = extractor.extract(texto1)
        assert data1["competencia"] == "dezembro-25"

        # Formato "janeiro-26"
        texto2 = """
        NOTA DÉBITO / RECIBO FATURA
        38.323.227/0001-40
        Competência: janeiro-26
        VALOR TOTAL R$ 100,00
        """
        data2 = extractor.extract(texto2)
        assert data2["competencia"] == "janeiro-26"


class TestCscNotaDebitoExtractorPriority:
    """Testes de prioridade do extrator no registro."""

    def test_extractor_registered(self):
        """Verifica se o extrator está registrado."""
        from core.extractors import EXTRACTOR_REGISTRY

        extractor_names = [cls.__name__ for cls in EXTRACTOR_REGISTRY]
        assert "CscNotaDebitoExtractor" in extractor_names

    def test_extractor_before_generic(self):
        """Verifica se o extrator vem antes dos genéricos."""
        from core.extractors import EXTRACTOR_REGISTRY

        extractor_names = [cls.__name__ for cls in EXTRACTOR_REGISTRY]

        csc_idx = extractor_names.index("CscNotaDebitoExtractor")

        # Deve vir antes de OutrosExtractor e NfseGenericExtractor
        if "OutrosExtractor" in extractor_names:
            outros_idx = extractor_names.index("OutrosExtractor")
            assert csc_idx < outros_idx, (
                "CscNotaDebitoExtractor deve vir antes de OutrosExtractor"
            )

        if "NfseGenericExtractor" in extractor_names:
            nfse_idx = extractor_names.index("NfseGenericExtractor")
            assert csc_idx < nfse_idx, (
                "CscNotaDebitoExtractor deve vir antes de NfseGenericExtractor"
            )


class TestCscNotaDebitoRealCases:
    """Testes com casos reais (se disponíveis)."""

    def test_caso_tarifa_bradesco_ative(self):
        """Testa extração de caso real: Tarifa Bradesco ATIVE."""
        texto = """
        Página: 1 de 1
        NOTA DÉBITO / RECIBO FATURA (AR)
        Numero: 347
        38.323.227/0001-40
        CSC GESTAO INTEGRADA S/A Emissão: 07/01/2026
        Av Vinte E Um De Abril Número: 505
        Competência: dezembro-25
        Complemento: SALA 201
        CEP: 35.500-010 Bairro: Centro Divinopolis - MG
        Tomador:
        ATIVE TELECOMUNICAÇÕES S.A.
        33.960.847/0001-77
        Preço (R$)
        Item Descrição
        Quant. Unit. Total
        1 Boletos Impressos 384 3,00 1.152,00
        3 Boletos online 1600 0,60 960,00
        3 4 Boletos online/baixas por decurso de prazo 258 0,20 51,60
        VALOR TOTAL R$ 2.163,60
        Observações:
        """

        assert CscNotaDebitoExtractor.can_handle(texto) is True

        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto)

        assert data["numero_documento"] == "347"
        assert data["valor_total"] == 2163.60
        assert data["data_emissao"] == "2026-01-07"
        assert data["competencia"] == "dezembro-25"
        assert "ATIVE" in data["tomador_nome"].upper()
        assert data["cnpj_tomador"] == "33.960.847/0001-77"

    def test_caso_tarifa_itau_ative(self):
        """Testa extração de caso real: Tarifa Itaú ATIVE."""
        texto = """
        Página: 1 de 1
        NOTA DÉBITO / RECIBO FATURA (AR)
        Numero: 348
        38.323.227/0001-40
        CSC GESTAO INTEGRADA S/A Emissão: 07/01/2026
        Av Vinte E Um De Abril Número: 505
        Competência: dezembro-25
        Complemento: SALA 201
        CEP: 35.500-010 Bairro: Centro Divinopolis - MG
        Tomador:
        ATIVE TELECOMUNICAÇÕES S.A.
        33.960.847/0001-77
        Preço (R$)
        Item Descrição
        Quant. Unit. Total
        1 Boletos Online 0 1,26 -
        2 Boletos online/baixas por decurso de prazo 0 0,34 -
        3 Boletos Online 1650 1,25 2.062,50
        4 Manutenção de Tit. Vencidos 0 - -
        VALOR TOTAL R$ 2.062,50
        """

        assert CscNotaDebitoExtractor.can_handle(texto) is True

        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto)

        assert data["numero_documento"] == "348"
        assert data["valor_total"] == 2062.50
        assert data["data_emissao"] == "2026-01-07"

    def test_caso_ocr_com_espacos_entre_letras(self):
        """Testa extração quando OCR gera espaços entre letras."""
        texto = """
        Página: 1 de 1
        38.323.227/0001-40 N O T A D É B I T O / R E C I B O FATURA (AR)
        CSC GESTAO INTEGRADA S/A
        Numero: 350
        Av Vinte E Um De Abril Número: 505
        Complemento: SALA 201
        Emissão: 07/01/2026
        CEP: 35.500-010 Bairro: Centro Divinopolis -
        MG Competênci dezembro-25
        a:
        Tomador:
        ATIVE TELECOMUNICAÇÕES S.A.
        33.960.847/0001-77
        Preço (R$)
        Item Descrição
        Quan Unit. Total
        1 Liquidação t. 955 0,70 668,50
        2 Baixa 0 0,25 -
        VALOR TOTAL R$ 668,50
        Observações:
        """

        assert CscNotaDebitoExtractor.can_handle(texto) is True

        extractor = CscNotaDebitoExtractor()
        data = extractor.extract(texto)

        assert data["numero_documento"] == "350"
        assert data["valor_total"] == 668.50
        assert data["data_emissao"] == "2026-01-07"
