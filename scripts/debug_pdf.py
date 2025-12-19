"""
Script de Debug para Extração de PDFs

Este script facilita o debug de problemas de extração em PDFs de boletos e NFSe.
Permite visualizar o texto bruto, contexto de campos e testar padrões regex.

Uso:
    python scripts/debug_pdf.py <arquivo.pdf> [opções]
    
Exemplos:
    # Debug básico
    python scripts/debug_pdf.py failed_cases_pdf/37e40903.pdf
    
    # Campo específico
    python scripts/debug_pdf.py failed_cases_pdf/fe43b71e.pdf -f nosso_numero
    
    # Mostrar texto completo
    python scripts/debug_pdf.py arquivo.pdf --full-text
    
    # Testar padrão customizado
    python scripts/debug_pdf.py arquivo.pdf -p "r'(?i)Nosso.*?(\d+/\d+-\d+)'"
    
    # Comparar múltiplos PDFs
    python scripts/debug_pdf.py file1.pdf file2.pdf file3.pdf --compare
"""

import pdfplumber
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Cores ANSI para output no terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    @staticmethod
    def disable():
        """Desabilita cores (útil para redirecionamento de output)"""
        Colors.HEADER = ''
        Colors.BLUE = ''
        Colors.CYAN = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.RED = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''
        Colors.END = ''


# Padrões pré-definidos para testes
PATTERN_LIBRARY = {
    'nosso_numero': [
        (r'\b(\d{3}/\d{8}-\d)\b', 'Formato 3/8-1 (109/00000507-1)'),
        (r'\b(\d{2,3}/\d{7,}-\d+)\b', 'Formato 2-3/7+-1+ flexível'),
        (r'(?i)Nosso\s+N.mero.*?(\d{2,3}/\d{7,}-\d+)', 'Com label + re.DOTALL'),
        (r'(?i)Nosso\s+N.mero[:\s]+(\d+/\d+-\d+)', 'Com label mesma linha'),
    ],
    'numero_documento': [
        (r'(?i)N.?\s*Documento.*?\d{2}/\d{2}/\d{4}\s+(\d+/\d+)', 'Layout tabular (pula data)'),
        (r'(?i)N.?\s*Documento[:\s]+(\d{4}\.\d+)', 'Formato ano.número (2025.122)'),
        (r'(?i)N.?\s*Documento[:\s]+(\d+/\d+)', 'Formato X/Y'),
        (r'(\d{4}\.\d+)', 'Genérico ano.número'),
        (r'Documento[:\s]*(\d+)', 'Número simples após label'),
    ],
    'vencimento': [
        (r'(?i)Vencimento[:\s]+(\d{2}/\d{2}/\d{4})', 'DD/MM/YYYY com label'),
        (r'(?i)Venc\.?[:\s]+(\d{2}/\d{2}/\d{4})', 'DD/MM/YYYY abreviado'),
        (r'\b(\d{2}/\d{2}/\d{4})\b', 'DD/MM/YYYY genérico'),
        (r'(?i)data.*?vencimento.*?(\d{2}/\d{2}/\d{4})', 'Data de vencimento'),
    ],
    'valor': [
        (r'(?i)Valor\s+(?:do\s+)?Documento[:\s]+R?\$?\s*([\d.,]+)', 'Valor documento'),
        (r'(?i)Valor[:\s]+R?\$?\s*([\d.,]+)', 'Valor genérico'),
        (r'R\$\s*([\d.,]+)', 'Apenas R$'),
    ],
    'cnpj': [
        (r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', 'CNPJ formatado'),
        (r'(?i)CNPJ[:\s]+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', 'CNPJ com label'),
        (r'(\d{14})', 'CNPJ sem formatação'),
    ],
    'linha_digitavel': [
        (r'(\d{5}\.\d{5}\s+\d{5}\.\d{6}\s+\d{5}\.\d{6}\s+\d\s+\d{14})', 'Linha completa formatada'),
        (r'(\d{47,48})', 'Linha digitável sem espaços'),
    ],
}


def extract_pdf_text(pdf_path: str) -> str:
    """Extrai texto da primeira página do PDF"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return ""
            return pdf.pages[0].extract_text() or ""
    except Exception as e:
        print(f"{Colors.RED}Erro ao abrir PDF: {e}{Colors.END}")
        return ""


def find_field_context(text: str, field_name: str, context_chars: int = 80) -> Optional[str]:
    """Encontra e retorna o contexto ao redor de um campo específico"""
    patterns = {
        'nosso_numero': r'Nosso.{0,20}N.mero',
        'numero_documento': r'N.{0,5}Documento',
        'vencimento': r'Venc(?:imento)?',
        'valor': r'Valor\s+(?:do\s+)?Documento|Valor',
        'cnpj': r'CNPJ',
        'linha_digitavel': r'Linha\s+Digit.vel|C.digo\s+de\s+Barras',
    }
    
    if field_name not in patterns:
        return None
    
    match = re.search(patterns[field_name], text, re.IGNORECASE)
    if match:
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars * 2)
        return text[start:end]
    
    return None


def test_patterns(text: str, field_name: str, custom_patterns: List[str] = None) -> List[Tuple[str, str, bool]]:
    """
    Testa padrões contra o texto
    
    Returns:
        Lista de tuplas (padrão, resultado, sucesso)
    """
    results = []
    
    # Usa biblioteca de padrões ou padrões customizados
    if custom_patterns:
        patterns = [(p, f'Custom pattern {i+1}') for i, p in enumerate(custom_patterns)]
    elif field_name in PATTERN_LIBRARY:
        patterns = PATTERN_LIBRARY[field_name]
    else:
        return [(f"Nenhum padrão definido para '{field_name}'", "", False)]
    
    for pattern, description in patterns:
        try:
            # Testa com e sem DOTALL
            match_normal = re.search(pattern, text)
            match_dotall = re.search(pattern, text, re.DOTALL)
            
            if match_dotall and match_dotall != match_normal:
                # DOTALL fez diferença
                result = match_dotall.group(1) if match_dotall.groups() else match_dotall.group(0)
                results.append((description, f"{result} {Colors.CYAN}(com DOTALL){Colors.END}", True))
            elif match_normal:
                result = match_normal.group(1) if match_normal.groups() else match_normal.group(0)
                results.append((description, result, True))
            else:
                results.append((description, f"{Colors.RED}❌ Não encontrado{Colors.END}", False))
                
        except Exception as e:
            results.append((description, f"{Colors.RED}Erro: {str(e)}{Colors.END}", False))
    
    return results


def find_all_matches(text: str, field_name: str) -> List[str]:
    """Encontra TODAS as ocorrências de um padrão no texto"""
    patterns = {
        'nosso_numero': r'\d{2,4}/\d{7,}-\d',
        'numero_documento': r'\d{4}\.\d+|\d+/\d+',
        'vencimento': r'\d{2}/\d{2}/\d{4}',
        'valor': r'R?\$?\s*[\d.,]+(?:\.\d{2})?',
        'cnpj': r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}',
    }
    
    if field_name not in patterns:
        return []
    
    matches = re.findall(patterns[field_name], text)
    return list(set(matches))  # Remove duplicados


def debug_pdf(pdf_path: str, field_name: str = None, show_full_text: bool = False, 
              custom_patterns: List[str] = None, no_color: bool = False) -> None:
    """Função principal de debug de um PDF"""
    
    if no_color:
        Colors.disable()
    
    pdf_name = Path(pdf_path).name
    
    # Extrai texto
    text = extract_pdf_text(pdf_path)
    if not text:
        print(f"{Colors.RED}Não foi possível extrair texto do PDF{Colors.END}")
        return
    
    # Header
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}Debug de PDF: {pdf_name}{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    # Informações básicas
    print(f"{Colors.BOLD}📄 Informações Básicas:{Colors.END}")
    print(f"  Caminho: {pdf_path}")
    print(f"  Tamanho do texto: {len(text)} caracteres")
    print(f"  Linhas: {text.count(chr(10)) + 1}")
    
    # Texto completo (se solicitado)
    if show_full_text:
        print(f"\n{Colors.BOLD}📝 Texto Completo (repr):{Colors.END}")
        print(f"{Colors.CYAN}{repr(text)}{Colors.END}\n")
    else:
        print(f"\n{Colors.BOLD}📝 Preview (primeiros 300 caracteres):{Colors.END}")
        print(f"{Colors.CYAN}{repr(text[:300])}...{Colors.END}\n")
    
    # Debug de campo específico
    if field_name:
        print(f"{Colors.BOLD}🔍 Debug do Campo: {Colors.YELLOW}{field_name}{Colors.END}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.END}\n")
        
        # Contexto do campo
        context = find_field_context(text, field_name)
        if context:
            print(f"{Colors.BOLD}Contexto encontrado:{Colors.END}")
            print(f"{Colors.CYAN}{repr(context)}{Colors.END}\n")
        else:
            print(f"{Colors.YELLOW}⚠ Label do campo não encontrado no texto{Colors.END}\n")
        
        # Todas as ocorrências
        all_matches = find_all_matches(text, field_name)
        if all_matches:
            print(f"{Colors.BOLD}Todas as ocorrências do formato:{Colors.END}")
            for i, match in enumerate(all_matches, 1):
                print(f"  {i}. {Colors.GREEN}{match}{Colors.END}")
            print()
        
        # Testa padrões
        print(f"{Colors.BOLD}Teste de Padrões:{Colors.END}")
        results = test_patterns(text, field_name, custom_patterns)
        
        max_desc_len = max(len(r[0]) for r in results) if results else 40
        for description, result, success in results:
            status = f"{Colors.GREEN}✓{Colors.END}" if success else f"{Colors.RED}✗{Colors.END}"
            print(f"  {status} {description:<{max_desc_len}} → {result}")
    
    else:
        # Debug geral - testa todos os campos
        print(f"{Colors.BOLD}🔍 Análise Geral de Campos:{Colors.END}")
        print(f"{Colors.BOLD}{'─'*70}{Colors.END}\n")
        
        for field in ['nosso_numero', 'numero_documento', 'vencimento', 'valor', 'cnpj']:
            print(f"{Colors.BOLD}{Colors.YELLOW}{field.upper()}{Colors.END}")
            
            all_matches = find_all_matches(text, field)
            if all_matches:
                print(f"  Ocorrências: {Colors.GREEN}{', '.join(all_matches[:5])}{Colors.END}")
                if len(all_matches) > 5:
                    print(f"  ... e mais {len(all_matches) - 5} ocorrências")
            
            results = test_patterns(text, field)
            success_count = sum(1 for _, _, s in results if s)
            total = len(results)
            print(f"  Padrões testados: {success_count}/{total} sucesso")
            print()
    
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")


def compare_pdfs(pdf_paths: List[str], field_name: str = None) -> None:
    """Compara múltiplos PDFs lado a lado"""
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}Comparação de PDFs{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    results = {}
    
    for pdf_path in pdf_paths:
        pdf_name = Path(pdf_path).name
        text = extract_pdf_text(pdf_path)
        
        if not text:
            results[pdf_name] = {"error": "Não foi possível extrair texto"}
            continue
        
        # Se campo específico, testa padrões
        if field_name:
            test_results = test_patterns(text, field_name)
            results[pdf_name] = {
                "length": len(text),
                "patterns": test_results
            }
        else:
            # Análise geral
            results[pdf_name] = {
                "length": len(text),
                "fields": {
                    field: find_all_matches(text, field)
                    for field in ['nosso_numero', 'numero_documento', 'vencimento', 'cnpj']
                }
            }
    
    # Exibe comparação
    if field_name:
        # Comparação de campo específico
        print(f"{Colors.BOLD}Campo: {Colors.YELLOW}{field_name}{Colors.END}\n")
        
        # Tabela de comparação
        for pdf_name, data in results.items():
            print(f"{Colors.BOLD}{pdf_name}{Colors.END}")
            if "error" in data:
                print(f"  {Colors.RED}Erro: {data['error']}{Colors.END}\n")
                continue
            
            print(f"  Tamanho: {data['length']} caracteres")
            for desc, result, success in data["patterns"]:
                status = f"{Colors.GREEN}✓{Colors.END}" if success else f"{Colors.RED}✗{Colors.END}"
                print(f"  {status} {desc}: {result}")
            print()
    else:
        # Comparação geral
        print(f"{Colors.BOLD}Resumo por PDF:{Colors.END}\n")
        
        for pdf_name, data in results.items():
            print(f"{Colors.BOLD}{pdf_name}{Colors.END} ({data['length']} chars)")
            if "error" in data:
                print(f"  {Colors.RED}{data['error']}{Colors.END}\n")
                continue
            
            for field, matches in data["fields"].items():
                if matches:
                    preview = ', '.join(matches[:3])
                    if len(matches) > 3:
                        preview += f" (+{len(matches)-3})"
                    print(f"  {field}: {Colors.GREEN}{preview}{Colors.END}")
                else:
                    print(f"  {field}: {Colors.RED}não encontrado{Colors.END}")
            print()
    
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Debug de extração de dados de PDFs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  
  Debug básico de um PDF:
    python scripts/debug_pdf.py failed_cases_pdf/37e40903.pdf
  
  Debug de campo específico:
    python scripts/debug_pdf.py arquivo.pdf -f nosso_numero
  
  Mostrar texto completo:
    python scripts/debug_pdf.py arquivo.pdf --full-text
  
  Testar padrão customizado:
    python scripts/debug_pdf.py arquivo.pdf -f nosso_numero -p "r'Nosso.*?(\\d+/\\d+-\\d+)'"
  
  Comparar múltiplos PDFs:
    python scripts/debug_pdf.py file1.pdf file2.pdf --compare
        """
    )
    
    parser.add_argument('pdf_files', nargs='+', help='Caminho(s) para o(s) arquivo(s) PDF')
    parser.add_argument('-f', '--field', help='Campo específico para debugar (nosso_numero, numero_documento, etc.)')
    parser.add_argument('--full-text', action='store_true', help='Mostrar texto completo do PDF')
    parser.add_argument('-p', '--pattern', action='append', help='Padrão regex customizado para testar')
    parser.add_argument('--compare', action='store_true', help='Comparar múltiplos PDFs')
    parser.add_argument('--no-color', action='store_true', help='Desabilitar cores no output')
    
    args = parser.parse_args()
    
    # Valida arquivos
    for pdf_file in args.pdf_files:
        if not Path(pdf_file).exists():
            print(f"{Colors.RED}Erro: Arquivo não encontrado: {pdf_file}{Colors.END}")
            return 1
    
    # Modo comparação
    if args.compare or len(args.pdf_files) > 1:
        compare_pdfs(args.pdf_files, args.field)
    else:
        # Debug único
        debug_pdf(
            args.pdf_files[0],
            field_name=args.field,
            show_full_text=args.full_text,
            custom_patterns=args.pattern,
            no_color=args.no_color
        )
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
