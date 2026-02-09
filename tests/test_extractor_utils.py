"""
Testes para funções utilitárias de extração.

Foco principal: normalização de valores monetários com problemas de OCR.
"""

import unittest
from extractors.utils import (
    normalize_ocr_money_string,
    parse_br_money,
    extract_br_money_values,
    extract_best_money_from_segment,
    normalize_whitespace,
    normalize_text_for_extraction,
    extract_cnpj,
    extract_cnpj_flexible,
    format_cnpj,
    normalize_digits,
    parse_date_br,
    strip_accents,
    normalize_entity_name,
)


class TestNormalizeOcrMoneyString(unittest.TestCase):
    """Testes para normalize_ocr_money_string - correção de espaços OCR em valores."""

    def test_espacos_entre_digitos_simples(self):
        """OCR inserindo espaço entre dígitos."""
        self.assertEqual(normalize_ocr_money_string("2 2.396,17"), "22.396,17")

    def test_espacos_entre_digitos_com_prefixo_rs(self):
        """OCR com espaços, mantendo espaço após R$."""
        result = normalize_ocr_money_string("R$ 2 2.396,17")
        self.assertEqual(result, "R$ 22.396,17")

    def test_multiplos_espacos_entre_digitos(self):
        """Múltiplos espaços entre todos os dígitos."""
        self.assertEqual(normalize_ocr_money_string("1 2 3 4,56"), "1234,56")

    def test_espacos_ao_redor_de_separadores(self):
        """Espaços ao redor de pontos e vírgulas."""
        self.assertEqual(
            normalize_ocr_money_string("R$ 1 . 2 3 4 , 5 6"), "R$ 1.234,56"
        )

    def test_valor_normal_sem_alteracao(self):
        """Valor já correto não deve ser alterado."""
        self.assertEqual(normalize_ocr_money_string("R$ 1.234,56"), "R$ 1.234,56")

    def test_valor_grande_com_espacos(self):
        """Valor grande (> 100k) com espaços OCR."""
        self.assertEqual(
            normalize_ocr_money_string("R$ 1 2 3 . 4 5 6 , 7 8"), "R$ 123.456,78"
        )

    def test_texto_vazio(self):
        """String vazia retorna vazia."""
        self.assertEqual(normalize_ocr_money_string(""), "")

    def test_none_retorna_vazio(self):
        """None retorna string vazia."""
        self.assertEqual(normalize_ocr_money_string(None), "")

    def test_texto_sem_numeros(self):
        """Texto sem números permanece inalterado."""
        self.assertEqual(
            normalize_ocr_money_string("Sem numeros aqui"), "Sem numeros aqui"
        )

    def test_preserva_espacos_legitimos(self):
        """Espaços entre palavras devem ser preservados."""
        result = normalize_ocr_money_string("Total a pagar: R$ 1 2 3,45")
        self.assertEqual(result, "Total a pagar: R$ 123,45")

    def test_caso_real_pp_empreendimentos(self):
        """Caso real identificado: PP EMPREENDIMENTOS com OCR problemático."""
        # Simula o caso real que causou o problema
        texto = "Valor Total: R$ 2 2.396,17"
        result = normalize_ocr_money_string(texto)
        self.assertEqual(result, "Valor Total: R$ 22.396,17")


class TestParseBrMoney(unittest.TestCase):
    """Testes para parse_br_money - conversão de formato brasileiro para float."""

    def test_formato_padrao_com_milhar(self):
        """Formato padrão brasileiro com separador de milhar."""
        self.assertAlmostEqual(parse_br_money("1.234,56"), 1234.56, places=2)

    def test_formato_sem_milhar(self):
        """Valor sem separador de milhar."""
        self.assertAlmostEqual(parse_br_money("999,99"), 999.99, places=2)

    def test_formato_grande(self):
        """Valor grande com múltiplos separadores de milhar."""
        self.assertAlmostEqual(parse_br_money("1.234.567,89"), 1234567.89, places=2)

    def test_valor_inteiro(self):
        """Valor inteiro com centavos zerados."""
        self.assertAlmostEqual(parse_br_money("1.000,00"), 1000.0, places=2)

    def test_string_vazia(self):
        """String vazia retorna 0.0."""
        self.assertAlmostEqual(parse_br_money(""), 0.0, places=2)

    def test_valor_invalido(self):
        """Valor inválido retorna 0.0."""
        self.assertAlmostEqual(parse_br_money("abc"), 0.0, places=2)


class TestExtractBrMoneyValues(unittest.TestCase):
    """Testes para extract_br_money_values - extração de múltiplos valores."""

    def test_multiplos_valores(self):
        """Extrai múltiplos valores de um texto."""
        texto = "Total: R$ 1.234,56 + R$ 100,00 = R$ 1.334,56"
        valores = extract_br_money_values(texto)
        self.assertEqual(len(valores), 3)
        self.assertAlmostEqual(valores[0], 1234.56, places=2)
        self.assertAlmostEqual(valores[1], 100.0, places=2)
        self.assertAlmostEqual(valores[2], 1334.56, places=2)

    def test_valor_com_espacos_ocr(self):
        """Extrai valor mesmo com espaços OCR."""
        texto = "R$ 2 2.396,17"
        valores = extract_br_money_values(texto)
        self.assertEqual(len(valores), 1)
        self.assertAlmostEqual(valores[0], 22396.17, places=2)

    def test_texto_vazio(self):
        """Texto vazio retorna lista vazia."""
        self.assertEqual(extract_br_money_values(""), [])

    def test_texto_sem_valores(self):
        """Texto sem valores monetários retorna lista vazia."""
        self.assertEqual(extract_br_money_values("Sem valores aqui"), [])

    def test_ignora_valores_zero(self):
        """Valores zero não são incluídos."""
        texto = "0,00 e 100,00"
        valores = extract_br_money_values(texto)
        self.assertEqual(len(valores), 1)
        self.assertAlmostEqual(valores[0], 100.0, places=2)


class TestExtractBestMoneyFromSegment(unittest.TestCase):
    """Testes para extract_best_money_from_segment - extração do maior valor."""

    def test_retorna_maior_valor(self):
        """Retorna o maior valor do segmento."""
        texto = "0,00 0,00 4.800,00"
        self.assertAlmostEqual(extract_best_money_from_segment(texto), 4800.0, places=2)

    def test_segmento_vazio(self):
        """Segmento vazio retorna 0.0."""
        self.assertAlmostEqual(extract_best_money_from_segment(""), 0.0, places=2)

    def test_unico_valor(self):
        """Segmento com único valor retorna esse valor."""
        self.assertAlmostEqual(
            extract_best_money_from_segment("Total: 1.234,56"), 1234.56, places=2
        )


class TestNormalizeWhitespace(unittest.TestCase):
    """Testes para normalize_whitespace."""

    def test_multiplos_espacos(self):
        """Colapsa múltiplos espaços."""
        self.assertEqual(
            normalize_whitespace("Nome    da   Empresa"), "Nome da Empresa"
        )

    def test_nbsp(self):
        """Converte non-breaking space."""
        self.assertEqual(normalize_whitespace("Teste\u00a0aqui"), "Teste aqui")

    def test_tabs(self):
        """Converte tabs para espaços."""
        self.assertEqual(normalize_whitespace("A\tB\tC"), "A B C")

    def test_string_vazia(self):
        """String vazia retorna vazia."""
        self.assertEqual(normalize_whitespace(""), "")


class TestNormalizeTextForExtraction(unittest.TestCase):
    """Testes para normalize_text_for_extraction."""

    def test_hifen_especial(self):
        """Normaliza hífens especiais."""
        self.assertIn("-", normalize_text_for_extraction("teste\u2013aqui"))  # en-dash
        self.assertIn("-", normalize_text_for_extraction("teste\u2014aqui"))  # em-dash

    def test_caracteres_problematicos(self):
        """Remove caracteres OCR problemáticos."""
        result = normalize_text_for_extraction("Teste□aqui")
        self.assertNotIn("□", result)


class TestCnpjFunctions(unittest.TestCase):
    """Testes para funções de CNPJ."""

    def test_extract_cnpj_formatado(self):
        """Extrai CNPJ no formato padrão."""
        texto = "CNPJ: 12.345.678/0001-90"
        self.assertEqual(extract_cnpj(texto), "12.345.678/0001-90")

    def test_extract_cnpj_flexible(self):
        """Extrai CNPJ em formato flexível."""
        texto = "CNPJ 12345678000190"
        result = extract_cnpj_flexible(texto)
        self.assertIsNotNone(result)

    def test_format_cnpj(self):
        """Formata CNPJ com pontuação."""
        self.assertEqual(format_cnpj("12345678000190"), "12.345.678/0001-90")


class TestNormalizeDigits(unittest.TestCase):
    """Testes para normalize_digits."""

    def test_remove_pontuacao_cnpj(self):
        """Remove pontuação de CNPJ."""
        self.assertEqual(normalize_digits("12.345.678/0001-90"), "12345678000190")

    def test_mantem_apenas_digitos(self):
        """Remove todos os não-dígitos."""
        self.assertEqual(normalize_digits("abc123def456"), "123456")

    def test_string_vazia(self):
        """String vazia retorna vazia."""
        self.assertEqual(normalize_digits(""), "")

    def test_none(self):
        """None retorna string vazia."""
        self.assertEqual(normalize_digits(None), "")


class TestParseDateBr(unittest.TestCase):
    """Testes para parse_date_br - retorna formato ISO (YYYY-MM-DD)."""

    def test_formato_barra(self):
        """Formato DD/MM/YYYY -> YYYY-MM-DD."""
        result = parse_date_br("15/03/2025")
        self.assertIsNotNone(result)
        self.assertEqual(result, "2025-03-15")

    def test_formato_hifen(self):
        """Formato DD-MM-YYYY -> YYYY-MM-DD."""
        result = parse_date_br("15-03-2025")
        self.assertIsNotNone(result)
        self.assertEqual(result, "2025-03-15")

    def test_data_invalida(self):
        """Data inválida retorna None."""
        self.assertIsNone(parse_date_br("32/13/2025"))


class TestStripAccents(unittest.TestCase):
    """Testes para strip_accents."""

    def test_remove_acentos_comuns(self):
        """Remove acentos comuns do português."""
        self.assertEqual(strip_accents("São Paulo"), "Sao Paulo")
        self.assertEqual(strip_accents("Ação"), "Acao")
        self.assertEqual(strip_accents("Índice"), "Indice")

    def test_string_vazia(self):
        """String vazia retorna vazia."""
        self.assertEqual(strip_accents(""), "")


class TestNormalizeEntityName(unittest.TestCase):
    """Testes para normalize_entity_name."""

    def test_normaliza_espacos(self):
        """Normaliza espaços extras."""
        result = normalize_entity_name("EMPRESA   LTDA")
        self.assertNotIn("   ", result)

    def test_string_vazia(self):
        """String vazia retorna vazia."""
        self.assertEqual(normalize_entity_name(""), "")


class TestIntegracaoOcrMoney(unittest.TestCase):
    """Testes de integração: fluxo completo de extração com OCR problemático."""

    def test_fluxo_completo_ocr_espacos(self):
        """Testa extração completa com texto OCR problemático."""
        # Simula texto real de PDF com OCR problemático
        texto_ocr = """
        NOTA FISCAL DE SERVIÇOS
        Prestador: PP EMPREENDIMENTOS LTDA
        CNPJ: 12.345.678/0001-90

        Valor dos Serviços: R$ 2 2.396,17
        Data: 15/01/2026
        """

        valores = extract_br_money_values(texto_ocr)
        self.assertEqual(len(valores), 1)
        self.assertAlmostEqual(valores[0], 22396.17, places=2)

    def test_multiplos_valores_com_ocr_misto(self):
        """Texto com valores normais e com OCR problemático."""
        texto = "Subtotal: R$ 1 0.000,00 + Taxa: R$ 500,00 = Total: R$ 1 0.500,00"
        valores = extract_br_money_values(texto)

        self.assertEqual(len(valores), 3)
        self.assertAlmostEqual(valores[0], 10000.0, places=2)
        self.assertAlmostEqual(valores[1], 500.0, places=2)
        self.assertAlmostEqual(valores[2], 10500.0, places=2)


if __name__ == "__main__":
    unittest.main()
