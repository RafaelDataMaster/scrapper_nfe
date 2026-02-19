"""
Testes para o extrator de NFCom (Nota Fiscal de Comunicação Eletrônica).

Verifica que:
1. O cabeçalho "DOCUMENTO AUXILIAR DA NOTA FISCAL..." não é capturado como fornecedor
2. O nome do fornecedor é extraído corretamente da segunda linha
3. Outros campos (CNPJ, valor, número da nota) são extraídos corretamente
"""

import pytest

from extractors.nfcom import NFComExtractor


class TestNFComExtractor:
    """Testes para NFComExtractor."""

    @pytest.fixture
    def extractor(self):
        """Fixture que retorna uma instância do extrator."""
        return NFComExtractor()

    def test_can_handle_nfcom_document(self, extractor):
        """Verifica que o extrator reconhece documentos NFCom."""
        text = """
        DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
        AGYONET LTDA
        RUA CAPITAO MENEZES, 68 - CENTRO
        10.652.926/0001-15
        NOTA FISCAL FATURA Nº: 000002001
        SÉRIE: 001
        CHAVE DE ACESSO:
        31251210652926000115620010000020011012150983
        """
        assert NFComExtractor.can_handle(text) is True

    def test_fornecedor_not_captures_header(self, extractor):
        """Verifica que 'DOCUMENTO AUXILIAR...' NÃO é capturado como fornecedor."""
        text = """
DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
AGYONET LTDA
RUA CAPITAO MENEZES, 68 - CENTRO (NEPOMUCENO/MG)
10.652.926/0001-15
0011102760021
NOTA FISCAL FATURA Nº: 000002001
SÉRIE: 001
DATA DE EMISSÃO: 25/12/2025
CHAVE DE ACESSO:
31251210652926000115620010000020011012150983
        """
        result = extractor.extract(text)

        # O fornecedor deve ser AGYONET LTDA, não o cabeçalho
        fornecedor = result.get("fornecedor_nome", "")
        assert "DOCUMENTO AUXILIAR" not in fornecedor
        assert "NOTA FISCAL FATURA" not in fornecedor
        assert "COMUNICAÇÃO ELETRÔNICA" not in fornecedor.upper().replace("Ã", "A")
        assert "AGYONET" in fornecedor.upper()

    def test_fornecedor_extracts_second_line(self, extractor):
        """Verifica que o fornecedor é extraído da segunda linha após cabeçalho."""
        text = """
DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
Shield Telecom LTDA
CNPJ: 45.585.923/0001-90
IE: 0042889660010
RUA NAIR MIRANDA CIZALPINO, 749
NOTA FISCAL FATURA Nº: 000005619
CHAVE DE ACESSO:
31260145585923000190620010000056191060594678
        """
        result = extractor.extract(text)
        fornecedor = result.get("fornecedor_nome", "")

        assert "Shield Telecom" in fornecedor or "SHIELD TELECOM" in fornecedor.upper()
        assert "DOCUMENTO" not in fornecedor.upper()

    def test_fornecedor_extracts_from_razao_social(self, extractor):
        """Verifica extração via padrão RAZÃO SOCIAL."""
        text = """
NOTA FISCAL DE COMUNICAÇÃO
RAZÃO SOCIAL: WN TELECOM LTDA
CNPJ: 12.345.678/0001-99
ENDEREÇO: Rua das Flores, 123
CHAVE DE ACESSO: 31260112345678000199620010000012341060594678
        """
        result = extractor.extract(text)
        fornecedor = result.get("fornecedor_nome", "")

        assert "WN TELECOM" in fornecedor.upper()

    def test_extract_cnpj_prestador(self, extractor):
        """Verifica extração do CNPJ do prestador."""
        text = """
DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
EMPRESA TELECOM LTDA
CNPJ: 10.652.926/0001-15
IE: 001234567
CHAVE DE ACESSO: 31251210652926000115620010000020011012150983
        """
        result = extractor.extract(text)

        assert result.get("cnpj_prestador") == "10.652.926/0001-15"

    def test_extract_numero_nota(self, extractor):
        """Verifica extração do número da nota."""
        text = """
DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
EMPRESA LTDA
NOTA FISCAL FATURA Nº: 000002001
SÉRIE: 001
CHAVE DE ACESSO: 31251210652926000115620010000020011012150983
        """
        result = extractor.extract(text)

        assert result.get("numero_nota") == "2001"

    def test_extract_valor_total(self, extractor):
        """Verifica extração do valor total."""
        text = """
DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
EMPRESA LTDA
CNPJ: 10.652.926/0001-15
TOTAL A PAGAR: R$ 750,00
CHAVE DE ACESSO: 31251210652926000115620010000020011012150983
        """
        result = extractor.extract(text)

        assert result.get("valor_total") == 750.0

    def test_extract_vencimento(self, extractor):
        """Verifica extração da data de vencimento."""
        text = """
DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
EMPRESA LTDA
Vencimento: 20/01/2026
CHAVE DE ACESSO: 31251210652926000115620010000020011012150983
        """
        result = extractor.extract(text)

        assert result.get("vencimento") == "2026-01-20"

    def test_extract_chave_acesso(self, extractor):
        """Verifica extração da chave de acesso de 44 dígitos."""
        text = """
DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
EMPRESA LTDA
CHAVE DE ACESSO:
3125 1210 6529 2600 0115 6200 1000 0020 0110 1215 0983
        """
        result = extractor.extract(text)

        assert (
            result.get("chave_acesso") == "31251210652926000115620010000020011012150983"
        )

    def test_is_valid_supplier_name_rejects_header(self, extractor):
        """Verifica que _is_valid_supplier_name rejeita cabeçalhos."""
        assert (
            extractor._is_valid_supplier_name("DOCUMENTO AUXILIAR DA NOTA FISCAL")
            is False
        )
        assert (
            extractor._is_valid_supplier_name(
                "NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO"
            )
            is False
        )

    def test_is_valid_supplier_name_rejects_address(self, extractor):
        """Verifica que _is_valid_supplier_name rejeita endereços."""
        assert extractor._is_valid_supplier_name("RUA DAS FLORES, 123") is False
        assert extractor._is_valid_supplier_name("AV. BRASIL, 456") is False
        assert extractor._is_valid_supplier_name("AVENIDA PAULISTA, 1000") is False

    def test_is_valid_supplier_name_rejects_cnpj(self, extractor):
        """Verifica que _is_valid_supplier_name rejeita CNPJ."""
        assert extractor._is_valid_supplier_name("10.652.926/0001-15") is False

    def test_is_valid_supplier_name_accepts_company(self, extractor):
        """Verifica que _is_valid_supplier_name aceita nomes de empresa."""
        assert extractor._is_valid_supplier_name("AGYONET LTDA") is True
        assert extractor._is_valid_supplier_name("Shield Telecom LTDA") is True
        assert extractor._is_valid_supplier_name("WN TELECOM S.A.") is True
        assert extractor._is_valid_supplier_name("EMPRESA TECNOLOGIA ME") is True

    def test_doc_type_is_danfe(self, extractor):
        """Verifica que o tipo de documento é DANFE (para classificação)."""
        text = """
DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
EMPRESA LTDA
CHAVE DE ACESSO: 31251210652926000115620010000020011012150983
        """
        result = extractor.extract(text)

        assert result.get("tipo_documento") == "DANFE"
        assert result.get("doc_type") == "DANFE"


class TestNFComEdgeCases:
    """Testes para casos de borda do extrator NFCom."""

    @pytest.fixture
    def extractor(self):
        return NFComExtractor()

    def test_header_concatenated_with_name_is_fixed(self, extractor):
        """
        Testa o bug específico onde o cabeçalho era concatenado com o nome.

        Antes: "DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA AGYONET LTDA"
        Depois: "AGYONET LTDA"
        """
        # Simula texto onde OCR pode ter juntado linhas
        text = """DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
AGYONET LTDA
RUA CAPITAO MENEZES, 68 - CENTRO
10.652.926/0001-15
CHAVE DE ACESSO: 31251210652926000115620010000020011012150983"""

        result = extractor.extract(text)
        fornecedor = result.get("fornecedor_nome", "")

        # Não deve conter o cabeçalho
        assert "DOCUMENTO AUXILIAR" not in fornecedor
        assert len(fornecedor) < 50  # Nome razoável, não concatenado

    def test_empty_lines_between_header_and_name(self, extractor):
        """Testa quando há linhas vazias entre cabeçalho e nome."""
        text = """DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA

EMPRESA TELECOM LTDA

CNPJ: 10.652.926/0001-15
CHAVE DE ACESSO: 31251210652926000115620010000020011012150983"""

        result = extractor.extract(text)
        fornecedor = result.get("fornecedor_nome", "")

        assert "EMPRESA TELECOM" in fornecedor.upper()
        assert "DOCUMENTO" not in fornecedor.upper()

    def test_multiple_companies_extracts_emitente(self, extractor):
        """Testa que extrai o emitente (primeira empresa), não o cliente."""
        text = """DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
Shield Telecom LTDA
CNPJ: 45.585.923/0001-90
CLIENTE:
ITACOLOMI COMUNICACAO LTDA
CNPJ: 13.003.072/0001-34
CHAVE DE ACESSO: 31260145585923000190620010000056191060594678"""

        result = extractor.extract(text)
        fornecedor = result.get("fornecedor_nome", "")

        # Deve extrair Shield Telecom (emitente), não ITACOLOMI (cliente)
        assert "SHIELD" in fornecedor.upper() or "Shield" in fornecedor
        assert "ITACOLOMI" not in fornecedor.upper()
