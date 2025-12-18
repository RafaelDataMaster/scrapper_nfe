"""
Módulo centralizado para diagnóstico e análise de qualidade de extração.

Este módulo consolida a lógica de validação e relatórios de diagnóstico,
eliminando duplicação entre scripts de validação e análise.
"""
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from core.models import InvoiceData, BoletoData

@dataclass
class DiagnosticReport:
    """
    Resultado da análise de qualidade.
    
    Attributes:
        total_arquivos: Total de arquivos processados
        nfse_sucesso: Quantidade de NFSe extraídas com sucesso
        nfse_falhas: Quantidade de NFSe com falhas
        boleto_sucesso: Quantidade de Boletos extraídos com sucesso
        boleto_falhas: Quantidade de Boletos com falhas
        taxa_sucesso_nfse: Percentual de sucesso nas NFSe
        taxa_sucesso_boleto: Percentual de sucesso nos Boletos
        falhas_detalhadas: Lista de dicionários com detalhes das falhas
    """
    total_arquivos: int
    nfse_sucesso: int
    nfse_falhas: int
    boleto_sucesso: int
    boleto_falhas: int
    taxa_sucesso_nfse: float
    taxa_sucesso_boleto: float
    falhas_detalhadas: List[Dict]


class ExtractionDiagnostics:
    """
    Classe responsável por análise de qualidade de extração.
    
    Centraliza as regras de validação e geração de relatórios para
    evitar duplicação entre scripts de diagnóstico e validação.
    """
    
    @staticmethod
    def classificar_nfse(result: InvoiceData) -> Tuple[bool, List[str]]:
        """
        Classifica uma NFSe como sucesso ou falha.
        
        Critérios de SUCESSO: Número da Nota preenchido E Valor > 0
        
        Args:
            result: Dados extraídos da NFSe
            
        Returns:
            Tupla (é_sucesso, lista_de_motivos_falha)
            
        Examples:
            >>> nfse = InvoiceData(arquivo_origem="teste.pdf", texto_bruto="...", 
            ...                    numero_nota="12345", valor_total=100.0)
            >>> sucesso, motivos = ExtractionDiagnostics.classificar_nfse(nfse)
            >>> assert sucesso is True
            >>> assert motivos == []
        """
        motivos = []
        tem_numero = result.numero_nota and result.numero_nota.strip()
        tem_valor = result.valor_total > 0
        
        if not tem_numero:
            motivos.append('SEM_NUMERO')
        if not tem_valor:
            motivos.append('VALOR_ZERO')
        if not result.cnpj_prestador:
            motivos.append('SEM_CNPJ')
        
        return (tem_numero and tem_valor, motivos)
    
    @staticmethod
    def classificar_boleto(result: BoletoData) -> Tuple[bool, List[str]]:
        """
        Classifica um Boleto como sucesso ou falha.
        
        Critérios de SUCESSO: Valor > 0 E (Vencimento OU Linha Digitável)
        
        Args:
            result: Dados extraídos do boleto
            
        Returns:
            Tupla (é_sucesso, lista_de_motivos_falha)
            
        Examples:
            >>> boleto = BoletoData(arquivo_origem="teste.pdf", texto_bruto="...",
            ...                     valor_documento=500.0, vencimento="2025-12-31")
            >>> sucesso, motivos = ExtractionDiagnostics.classificar_boleto(boleto)
            >>> assert sucesso is True
        """
        motivos = []
        tem_valor = result.valor_documento > 0
        tem_identificacao = result.vencimento or result.linha_digitavel
        
        if not tem_valor:
            motivos.append('VALOR_ZERO')
        if not result.vencimento:
            motivos.append('SEM_VENCIMENTO')
        if not result.linha_digitavel:
            motivos.append('SEM_LINHA_DIGITAVEL')
        
        return (tem_valor and tem_identificacao, motivos)
    
    @staticmethod
    def gerar_relatorio_texto(dados: Dict) -> str:
        """
        Gera relatório de qualidade em formato texto.
        
        Args:
            dados: Dicionário com estatísticas de extração contendo:
                - total: Total de arquivos processados
                - nfse_ok: NFSe extraídas com sucesso
                - nfse_falha: NFSe com falhas
                - boleto_ok: Boletos extraídos com sucesso
                - boleto_falha: Boletos com falhas
                - erros: Quantidade de erros críticos
                - nfse_falhas_detalhe: Lista de dict com detalhes das falhas NFSe
                - boleto_falhas_detalhe: Lista de dict com detalhes das falhas Boleto
            
        Returns:
            String formatada do relatório
            
        Examples:
            >>> dados = {'total': 10, 'nfse_ok': 8, 'nfse_falha': 2, 
            ...          'boleto_ok': 5, 'boleto_falha': 1, 'erros': 0,
            ...          'nfse_falhas_detalhe': [], 'boleto_falhas_detalhe': []}
            >>> relatorio = ExtractionDiagnostics.gerar_relatorio_texto(dados)
            >>> assert 'RELATÓRIO DE QUALIDADE' in relatorio
        """
        linhas = []
        linhas.append("=" * 80)
        linhas.append("📊 RELATÓRIO DE QUALIDADE DA EXTRAÇÃO")
        linhas.append("=" * 80)
        linhas.append("")
        
        linhas.append(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        linhas.append(f"📦 Total de arquivos: {dados['total']}")
        linhas.append("")
        
        # NFSe
        linhas.append("--- NFSe ---")
        linhas.append(f"✅ Completas: {dados['nfse_ok']}")
        linhas.append(f"⚠️ Com falhas: {dados['nfse_falha']}")
        total_nfse = dados['nfse_ok'] + dados['nfse_falha']
        if total_nfse > 0:
            taxa = (dados['nfse_ok'] / total_nfse) * 100
            linhas.append(f"📈 Taxa de sucesso: {taxa:.1f}%")
        
        # Boletos
        linhas.append("")
        linhas.append("--- Boletos ---")
        linhas.append(f"✅ Completos: {dados['boleto_ok']}")
        linhas.append(f"⚠️ Com falhas: {dados['boleto_falha']}")
        total_boleto = dados['boleto_ok'] + dados['boleto_falha']
        if total_boleto > 0:
            taxa = (dados['boleto_ok'] / total_boleto) * 100
            linhas.append(f"📈 Taxa de sucesso: {taxa:.1f}%")
        
        linhas.append("")
        linhas.append(f"❌ Erros: {dados['erros']}")
        
        # Detalhes das falhas NFSe
        if dados.get('nfse_falhas_detalhe'):
            linhas.append("")
            linhas.append("=" * 80)
            linhas.append("🔍 FALHAS - NFSe")
            linhas.append("=" * 80)
            for item in dados['nfse_falhas_detalhe']:
                linhas.append("")
                linhas.append(f"📄 {item['arquivo_origem']}")
                linhas.append(f"   Motivo: {item.get('motivo_falha', 'N/A')}")
                linhas.append(f"   Número: {item.get('numero_nota', 'N/A')}")
                linhas.append(f"   Valor: R$ {item.get('valor_total', 0):,.2f}")
        
        # Detalhes das falhas Boletos
        if dados.get('boleto_falhas_detalhe'):
            linhas.append("")
            linhas.append("=" * 80)
            linhas.append("🔍 FALHAS - BOLETOS")
            linhas.append("=" * 80)
            for item in dados['boleto_falhas_detalhe']:
                linhas.append("")
                linhas.append(f"📄 {item['arquivo_origem']}")
                linhas.append(f"   Motivo: {item.get('motivo_falha', 'N/A')}")
                linhas.append(f"   Valor: R$ {item.get('valor_documento', 0):,.2f}")
        
        return "\n".join(linhas)
    
    @staticmethod
    def salvar_relatorio(dados: Dict, caminho_arquivo) -> None:
        """
        Gera e salva o relatório em arquivo de texto.
        
        Args:
            dados: Dicionário com estatísticas de extração
            caminho_arquivo: Path ou string com caminho do arquivo de saída
        """
        relatorio = ExtractionDiagnostics.gerar_relatorio_texto(dados)
        
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(relatorio)
    
    @staticmethod
    def diagnosticar_tipo_falha(arquivo: str, texto_snippet: str, numero_nota: str, valor: float) -> str:
        """
        Tenta classificar automaticamente o tipo de falha de extração.
        
        Args:
            arquivo: Nome do arquivo origem
            texto_snippet: Trecho do texto extraído
            numero_nota: Número da nota extraído (pode ser vazio)
            valor: Valor extraído
            
        Returns:
            String com diagnóstico sugerido
            
        Examples:
            >>> diag = ExtractionDiagnostics.diagnosticar_tipo_falha(
            ...     "boleto123.pdf", "BOLETO BANCÁRIO", "", 0.0
            ... )
            >>> assert "BOLETO/RECIBO" in diag
        """
        texto_lower = texto_snippet.lower()
        arquivo_lower = arquivo.lower()
        
        # Verifica se é boleto/recibo (não deveria ser processado como NFSe)
        if "boleto" in arquivo_lower or "recibo" in arquivo_lower:
            return "BOLETO/RECIBO (Ignorar se não for NF)."
        
        # Verifica se é locação (layout atípico)
        if "locação" in texto_lower or "locacao" in texto_lower:
            return "LOCAÇÃO (Layout atípico)."
        
        # Diagnóstico específico por campo
        if valor == 0.0 or not valor:
            return "Regex de VALOR falhou."
        
        if not numero_nota or numero_nota == "VAZIO":
            return "Regex de NÚMERO DA NOTA falhou."
        
        return "Falha genérica de extração."
