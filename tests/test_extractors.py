"""
Testes unitários para os extratores de dados.

Este módulo contém testes automatizados para validar a lógica
de extração de NFSe e Boletos, sem dependência de arquivos reais.
"""
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from extractors.generic import GenericExtractor
from extractors.boleto import BoletoExtractor
from core.models import InvoiceData, BoletoData


class TestGenericExtractor(unittest.TestCase):
    """Testes unitários para o extrator genérico de NFSe."""
    
    def setUp(self):
        """Inicializa o extrator antes de cada teste."""
        self.extractor = GenericExtractor()
    
    def test_can_handle_nfse(self):
        """Verifica se identifica NFSe corretamente."""
        texto_nfse = "PREFEITURA MUNICIPAL NOTA FISCAL ELETRÔNICA Número: 12345"
        self.assertTrue(GenericExtractor.can_handle(texto_nfse))
    
    def test_reject_boleto(self):
        """Verifica se rejeita boletos corretamente."""
        texto_boleto = "BANCO BRADESCO LINHA DIGITÁVEL CÓDIGO DE BARRAS BENEFICIÁRIO"
        self.assertFalse(GenericExtractor.can_handle(texto_boleto))
    
    def test_extract_numero_nota_success(self):
        """Testa extração bem-sucedida de número de nota."""
        texto = """
        PREFEITURA MUNICIPAL DE SÃO PAULO
        Nota Fiscal de Serviço Eletrônica
        Número: 12345
        Data de Emissão: 15/12/2025
        """
        result = self.extractor._extract_numero_nota(texto)
        self.assertEqual(result, "12345")
    
    def test_extract_numero_nota_with_noise(self):
        """Testa extração com ruído no texto (RPS, Lote, etc)."""
        texto = """
        RPS 999 Lote 888
        Nota Fiscal Eletrônica
        Número da Nota: 54321
        Competência: 12/2025
        """
        result = self.extractor._extract_numero_nota(texto)
        self.assertIsNotNone(result)
        # Verifica se extraiu algum número válido
        self.assertTrue(len(result) > 0)
    
    def test_extract_valor_monetario_formatado(self):
        """Testa conversão de valores monetários brasileiros."""
        texto = "Valor Total dos Serviços: R$ 1.234,56"
        result = self.extractor._extract_valor(texto)
        self.assertAlmostEqual(result, 1234.56, places=2)
    
    def test_extract_valor_sem_milhar(self):
        """Testa extração de valor sem separador de milhar."""
        texto = "Total: R$ 999,99"
        result = self.extractor._extract_valor(texto)
        self.assertAlmostEqual(result, 999.99, places=2)
    
    def test_extract_valor_grande(self):
        """Testa extração de valores grandes."""
        texto = "Valor: R$ 123.456,78"
        result = self.extractor._extract_valor(texto)
        self.assertAlmostEqual(result, 123456.78, places=2)
    
    def test_extract_cnpj_formatado(self):
        """Testa extração de CNPJ formatado."""
        texto = "Prestador: EMPRESA XYZ LTDA CNPJ: 12.345.678/0001-99"
        result = self.extractor._extract_cnpj(texto)
        self.assertEqual(result, "12.345.678/0001-99")
    
    def test_extract_data_emissao_formatada(self):
        """Testa conversão de data para formato ISO."""
        texto = "Data de Emissão: 15/12/2025"
        result = self.extractor._extract_data_emissao(texto)
        self.assertEqual(result, "2025-12-15")
    
    def test_extract_retorna_dict_completo(self):
        """Testa se o método extract retorna todos os campos."""
        texto = """
        PREFEITURA DE TESTE
        NFS-e Número: 999
        CNPJ: 11.222.333/0001-44
        Emissão: 01/01/2025
        Valor: R$ 5.000,00
        """
        result = self.extractor.extract(texto)
        
        self.assertIn('tipo_documento', result)
        self.assertEqual(result['tipo_documento'], 'NFSE')
        self.assertIn('numero_nota', result)
        self.assertIn('valor_total', result)
        self.assertIn('cnpj_prestador', result)
        self.assertIn('data_emissao', result)


class TestBoletoExtractor(unittest.TestCase):
    """Testes unitários para o extrator de boletos."""
    
    def setUp(self):
        """Inicializa o extrator antes de cada teste."""
        self.extractor = BoletoExtractor()
    
    def test_can_handle_boleto(self):
        """Verifica se identifica boletos corretamente."""
        texto_boleto = """
        BANCO BRADESCO S.A.
        LINHA DIGITÁVEL: 23790.00009 12345.678901 23456.789012 3 12345678901234
        BENEFICIÁRIO: EMPRESA ABC LTDA
        VALOR DO DOCUMENTO: R$ 1.500,00
        VENCIMENTO: 31/12/2025
        """
        self.assertTrue(BoletoExtractor.can_handle(texto_boleto))
    
    def test_reject_nfse(self):
        """Verifica se rejeita NFSe corretamente."""
        texto_nfse = "PREFEITURA MUNICIPAL NFS-E NOTA FISCAL ELETRÔNICA"
        self.assertFalse(BoletoExtractor.can_handle(texto_nfse))
    
    def test_extract_linha_digitavel(self):
        """Testa extração de linha digitável."""
        texto = "LINHA DIGITÁVEL: 23790.00009 12345.678901 23456.789012 3 12345678901234"
        result = self.extractor._extract_linha_digitavel(texto)
        self.assertIsNotNone(result)
        # Verifica se contém dígitos
        self.assertTrue(any(c.isdigit() for c in result))
    
    def test_extract_valor_documento(self):
        """Testa extração do valor do boleto."""
        texto = "VALOR DO DOCUMENTO: R$ 2.500,75"
        result = self.extractor._extract_valor(texto)
        self.assertAlmostEqual(result, 2500.75, places=2)
    
    def test_extract_vencimento(self):
        """Testa extração e conversão da data de vencimento."""
        texto = "VENCIMENTO: 31/12/2025"
        result = self.extractor._extract_vencimento(texto)
        self.assertEqual(result, "2025-12-31")
    
    def test_extract_cnpj_beneficiario(self):
        """Testa extração do CNPJ do beneficiário."""
        texto = "BENEFICIÁRIO: EMPRESA XYZ LTDA CNPJ: 98.765.432/0001-10"
        result = self.extractor._extract_cnpj_beneficiario(texto)
        self.assertIsNotNone(result)
        self.assertIn("98.765.432/0001-10", result)
    
    def test_extract_retorna_dict_completo(self):
        """Testa se o método extract retorna todos os campos do boleto."""
        texto = """
        BANCO DO BRASIL
        BENEFICIÁRIO: EMPRESA ABC
        CNPJ: 11.222.333/0001-99
        VALOR DO DOCUMENTO: R$ 1.000,00
        VENCIMENTO: 15/01/2026
        LINHA DIGITÁVEL: 12345.67890 12345.678901 23456.789012 1 12345678901234
        """
        result = self.extractor.extract(texto)
        
        self.assertIn('tipo_documento', result)
        self.assertEqual(result['tipo_documento'], 'BOLETO')
        self.assertIn('valor_documento', result)
        self.assertIn('vencimento', result)
        self.assertIn('cnpj_beneficiario', result)
        self.assertIn('linha_digitavel', result)


class TestExtractionIntegration(unittest.TestCase):
    """Testes de integração para validar o fluxo completo."""
    
    def test_roteamento_nfse_vs_boleto(self):
        """Verifica se o roteamento entre NFSe e Boleto funciona corretamente."""
        texto_nfse = "PREFEITURA MUNICIPAL NOTA FISCAL ELETRÔNICA"
        texto_boleto = "BANCO BRADESCO LINHA DIGITÁVEL BENEFICIÁRIO VENCIMENTO CÓDIGO DE BARRAS"
        
        # NFSe deve ser aceita pelo GenericExtractor e rejeitada pelo BoletoExtractor
        self.assertTrue(GenericExtractor.can_handle(texto_nfse))
        self.assertFalse(BoletoExtractor.can_handle(texto_nfse))
        
        # Boleto deve ser rejeitado pelo GenericExtractor e aceito pelo BoletoExtractor
        self.assertFalse(GenericExtractor.can_handle(texto_boleto))
        self.assertTrue(BoletoExtractor.can_handle(texto_boleto))
    
    def test_extract_nfse_campos_minimos(self):
        """Testa se extração de NFSe retorna pelo menos número e valor."""
        texto = """
        PREFEITURA MUNICIPAL
        NFS-e 12345
        Valor: R$ 500,00
        """
        extractor = GenericExtractor()
        result = extractor.extract(texto)
        
        # Deve ter número ou valor (critério mínimo)
        tem_numero = result.get('numero_nota') is not None
        tem_valor = result.get('valor_total', 0) > 0
        
        self.assertTrue(tem_numero or tem_valor, 
                       "Extração deve retornar pelo menos número ou valor")
    
    def test_extract_boleto_campos_minimos(self):
        """Testa se extração de boleto retorna pelo menos valor e identificação."""
        texto = """
        BANCO XYZ
        VALOR: R$ 1.500,00
        VENCIMENTO: 31/12/2025
        LINHA DIGITÁVEL: 12345.67890 12345.678901
        """
        extractor = BoletoExtractor()
        result = extractor.extract(texto)
        
        # Deve ter valor
        tem_valor = result.get('valor_documento', 0) > 0
        # Deve ter vencimento OU linha digitável
        tem_identificacao = (result.get('vencimento') is not None or 
                            result.get('linha_digitavel') is not None)
        
        self.assertTrue(tem_valor, "Boleto deve ter valor")
        self.assertTrue(tem_identificacao, 
                       "Boleto deve ter vencimento ou linha digitável")


class TestEdgeCases(unittest.TestCase):
    """Testes para casos extremos e situações adversas."""
    
    def test_texto_vazio(self):
        """Testa comportamento com texto vazio."""
        extractor = GenericExtractor()
        result = extractor.extract("")
        
        # Não deve lançar exceção
        self.assertIsInstance(result, dict)
    
    def test_texto_sem_numeros(self):
        """Testa extração quando não há números no texto."""
        extractor = GenericExtractor()
        texto = "TEXTO SEM NENHUM DIGITO"
        result = extractor.extract(texto)
        
        # Deve retornar valores vazios/zero, mas não None para o dict
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('valor_total', 0), 0.0)
    
    def test_valor_com_formato_invalido(self):
        """Testa extração de valor com formato inesperado."""
        extractor = GenericExtractor()
        texto = "Valor: 1.234.567,89 reais"  # Sem R$
        result = extractor._extract_valor(texto)
        
        # Deve retornar 0.0 ou tentar extrair mesmo assim
        self.assertIsInstance(result, (int, float))


if __name__ == '__main__':
    # Configura o runner para mostrar resultados detalhados
    unittest.main(verbosity=2)
