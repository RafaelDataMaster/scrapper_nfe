"""
Testes para o SabespWaterBillExtractor.

Testa a extração de dados de faturas da Sabesp a partir do corpo do email.
"""

import pytest

from extractors.sabesp import (
    SabespWaterBillExtractor,
    extract_sabesp_from_email,
)


class TestSabespWaterBillExtractorCanHandle:
    """Testes para o método can_handle_email."""

    def test_can_handle_by_sender_address(self):
        """Deve detectar email Sabesp pelo endereço do remetente."""
        assert SabespWaterBillExtractor.can_handle_email(
            email_sender="fatura_sabesp@sabesp.com.br"
        )
        assert SabespWaterBillExtractor.can_handle_email(
            email_sender="noreply@sabesp.com.br"
        )
        assert SabespWaterBillExtractor.can_handle_email(
            email_sender="fatura.sabesp@sabesp.com.br"
        )

    def test_can_handle_by_subject(self):
        """Deve detectar email Sabesp pelo assunto."""
        assert SabespWaterBillExtractor.can_handle_email(
            email_subject="Sabesp - Fatura por e-mail"
        )
        assert SabespWaterBillExtractor.can_handle_email(
            email_subject="Sua fatura digital da Sabesp"
        )
        assert SabespWaterBillExtractor.can_handle_email(
            email_subject="SABESP - Sua fatura chegou"
        )

    def test_can_handle_by_body_content(self):
        """Deve detectar email Sabesp pelo conteúdo do corpo."""
        body = """
        <b>Fornecimento:</b> 86040721896813<br>
        <b>Unidade:</b> TAUBATE<br>
        <b>Vencimento:</b> 20/01/2026<br>
        <b>Valor:</b> R$ 138,56<br>
        """
        assert SabespWaterBillExtractor.can_handle_email(email_body=body)

    def test_cannot_handle_non_sabesp(self):
        """Não deve detectar emails que não são da Sabesp."""
        assert not SabespWaterBillExtractor.can_handle_email(
            email_sender="fatura@cemig.com.br"
        )
        assert not SabespWaterBillExtractor.can_handle_email(
            email_subject="Sua fatura CEMIG"
        )
        assert not SabespWaterBillExtractor.can_handle_email(
            email_body="Fatura de energia elétrica"
        )

    def test_cannot_handle_empty_inputs(self):
        """Não deve detectar quando todos os inputs são vazios."""
        assert not SabespWaterBillExtractor.can_handle_email()
        assert not SabespWaterBillExtractor.can_handle_email(
            email_sender="", email_subject="", email_body=""
        )


class TestSabespWaterBillExtractorExtract:
    """Testes para o método extract."""

    @pytest.fixture
    def sabesp_email_body(self):
        """Corpo de email típico da Sabesp."""
        return """
        <table style="font-family:Tahoma; font-size:14pt; color:#003854; border-style:none" width="700px">
            <tr>
                <td colspan="2">
                    <p style="font-size:20pt; font-weight:bold; color:#12CDFF">Olá, Cliente !</p>
                    <b>Sua fatura digital chegou!</b>
                </td>
            </tr>
            <tr>
                <td style="background-color:#12CDFF; color:white; padding-left:20px" width="70%">
                    <b>Fornecimento:</b> 86040721896813<br>
                    <b>Unidade:</b> TAUBATE<br>
                    <b>Vencimento:</b> 20/01/2026<br>
                    <b>Valor:</b> R$ 138,56<br>
                </td>
            </tr>
            <tr>
                <td colspan="2" style="padding:10px;">
                    <b>Código de barras:</b><br>82660000001 0  38560097091 2  10655945380 3  19573630603 4
                </td>
            </tr>
        </table>
        """

    def test_extract_basic_fields(self, sabesp_email_body):
        """Deve extrair campos básicos da fatura."""
        extractor = SabespWaterBillExtractor()
        result = extractor.extract(sabesp_email_body)

        assert result["tipo_documento"] == "UTILITY_BILL"
        assert result["subtipo"] == "WATER"
        assert result["fornecedor_nome"] == "SABESP"
        assert result["cnpj_fornecedor"] == "43.776.517/0001-80"

    def test_extract_valor(self, sabesp_email_body):
        """Deve extrair o valor corretamente."""
        extractor = SabespWaterBillExtractor()
        result = extractor.extract(sabesp_email_body)

        assert result["valor_total"] == 138.56

    def test_extract_vencimento(self, sabesp_email_body):
        """Deve extrair e formatar a data de vencimento."""
        extractor = SabespWaterBillExtractor()
        result = extractor.extract(sabesp_email_body)

        assert result["vencimento"] == "2026-01-20"

    def test_extract_numero_fornecimento(self, sabesp_email_body):
        """Deve extrair o número de fornecimento como numero_documento."""
        extractor = SabespWaterBillExtractor()
        result = extractor.extract(sabesp_email_body)

        assert result["numero_documento"] == "86040721896813"
        assert result["instalacao"] == "86040721896813"

    def test_extract_codigo_barras(self, sabesp_email_body):
        """Deve extrair o código de barras."""
        extractor = SabespWaterBillExtractor()
        result = extractor.extract(sabesp_email_body)

        # O código de barras deve estar na linha_digitavel
        assert "linha_digitavel" in result
        assert len(result["linha_digitavel"]) >= 44

    def test_extract_unidade(self, sabesp_email_body):
        """Deve extrair a unidade/localidade."""
        extractor = SabespWaterBillExtractor()
        result = extractor.extract(sabesp_email_body)

        assert "observacoes" in result
        assert "TAUBATE" in result["observacoes"]

    def test_extract_valor_different_formats(self):
        """Deve extrair valores em diferentes formatos."""
        extractor = SabespWaterBillExtractor()

        # Valor com milhar
        body1 = "<b>Valor:</b> R$ 1.234,56"
        result1 = extractor.extract(body1)
        assert result1["valor_total"] == 1234.56

        # Valor simples
        body2 = "Valor: R$ 99,99"
        result2 = extractor.extract(body2)
        assert result2["valor_total"] == 99.99

    def test_extract_vencimento_different_formats(self):
        """Deve extrair vencimentos em diferentes formatos."""
        extractor = SabespWaterBillExtractor()

        # Formato com tags HTML
        body1 = "<b>Vencimento:</b> 15/02/2026"
        result1 = extractor.extract(body1)
        assert result1["vencimento"] == "2026-02-15"

        # Formato sem tags
        body2 = "Vencimento: 28/12/2025"
        result2 = extractor.extract(body2)
        assert result2["vencimento"] == "2025-12-28"

    def test_extract_with_missing_fields(self):
        """Deve lidar com campos faltantes graciosamente."""
        extractor = SabespWaterBillExtractor()

        # Só valor presente
        body = "<b>Valor:</b> R$ 50,00"
        result = extractor.extract(body)

        assert result["tipo_documento"] == "UTILITY_BILL"
        assert result["subtipo"] == "WATER"
        assert result["valor_total"] == 50.00
        assert result.get("vencimento") is None
        assert result.get("numero_documento") is None


class TestExtractSabespFromEmailHelper:
    """Testes para a função helper extract_sabesp_from_email."""

    def test_returns_none_for_non_sabesp(self):
        """Deve retornar None para emails que não são da Sabesp."""
        result = extract_sabesp_from_email(
            email_body="Fatura CEMIG",
            email_subject="Sua conta de luz",
            email_sender="fatura@cemig.com.br",
        )
        assert result is None

    def test_returns_data_for_sabesp(self):
        """Deve retornar dados para emails da Sabesp."""
        body = """
        <b>Fornecimento:</b> 12345678901234<br>
        <b>Vencimento:</b> 10/03/2026<br>
        <b>Valor:</b> R$ 200,00<br>
        """
        result = extract_sabesp_from_email(
            email_body=body,
            email_subject="Sabesp - Fatura por e-mail",
            email_sender="fatura_sabesp@sabesp.com.br",
        )

        assert result is not None
        assert result["tipo_documento"] == "UTILITY_BILL"
        assert result["subtipo"] == "WATER"
        assert result["valor_total"] == 200.00
        assert result["vencimento"] == "2026-03-10"


class TestSabespRealWorldCases:
    """Testes com casos reais observados em produção."""

    def test_real_email_body_format(self):
        """Testa com formato real do email da Sabesp."""
        # Este é o formato exato encontrado nos emails reais
        body = """
        <table style="font-family:Tahoma; font-size:14pt; color:#003854; border-style:none" width="700px">
        <tbody><tr>
            <td colspan="2">
            <img src="https://agenciavirtual.sabesp.com.br/static-files-neta/header.png">
        </td></tr>
        <tr>
            <td colspan="2">
            <p style="font-size:20pt; font-weight:bold; color:#12CDFF">Olá, Carrier !</p>
                <b>Sua fatura digital chegou!</b>
            </td>
        </tr>
        <tr>
            <td colspan="2">
            <table>
                <tbody><tr>
                    <td width="70%">&nbsp;</td>
                    <td width="30%" align="center">
                        <b>Acesse</b>
                    </td>
                </tr>
                <tr>
                    <td style="background-color:#12CDFF; color:white; padding-left:20px" width="70%">
                        <b>Fornecimento:</b> 86040721896813<br>
                        <b>Unidade:</b> TAUBATE<br>
                        <b>Vencimento:</b> 20/01/2026<br>
                        <b>Valor:</b> R$ 138,56<br>
                    </td>
                </tr>
            </tbody></table>
            </td>
        </tr>
        <tr>
            <td colspan="2" style="padding:10px;">
            <b>Código de barras:</b><br>82660000001 0  38560097091 2  10655945380 3  19573630603 4
            </td>
        </tr>
        </tbody></table>
        """

        extractor = SabespWaterBillExtractor()
        result = extractor.extract(body)

        assert result["tipo_documento"] == "UTILITY_BILL"
        assert result["subtipo"] == "WATER"
        assert result["fornecedor_nome"] == "SABESP"
        assert result["valor_total"] == 138.56
        assert result["vencimento"] == "2026-01-20"
        assert result["numero_documento"] == "86040721896813"
        assert "TAUBATE" in result.get("observacoes", "")

    def test_multiple_real_batches(self):
        """Testa extração para múltiplos valores reais observados."""
        extractor = SabespWaterBillExtractor()

        # Valores reais dos 3 batches Sabesp identificados
        test_cases = [
            {"valor_esperado": 138.56, "venc_esperado": "2026-01-20"},
            {"valor_esperado": 140.65, "venc_esperado": "2026-01-25"},
            {"valor_esperado": 145.15, "venc_esperado": "2026-02-20"},
        ]

        for case in test_cases:
            body = f"""
            <b>Vencimento:</b> {case["venc_esperado"][8:10]}/{case["venc_esperado"][5:7]}/{case["venc_esperado"][:4]}<br>
            <b>Valor:</b> R$ {str(case["valor_esperado"]).replace(".", ",")}<br>
            """
            result = extractor.extract(body)

            assert result["valor_total"] == case["valor_esperado"]
            assert result["vencimento"] == case["venc_esperado"]
