"""
Script de diagnóstico para problema do caractere 'Ê' no OCR.

Este script testa e analisa o problema do caractere 'Ê' que aparece no lugar
de espaços em textos extraídos por OCR, causando falhas na extração de valores.

Problema identificado nos logs:
- Texto: "DOCUMENTOÊAUXILIARÊDAÊNOTAÊFISCALÊFATURAÊDEÊSERVIÇOSÊDEÊCOMUNICAÇÃOÊELETRÔNICA"
- O OCR está usando "Ê" como substituto de espaços
- Os padrões regex não reconhecem "TOTALÊAÊPAGAR:ÊR$Ê29.250,00"

Este script ajuda a:
1. Detectar a presença do caractere 'Ê' no texto
2. Testar diferentes estratégias de normalização
3. Verificar se os extratores conseguem processar texto normalizado
4. Sugerir correções no sistema
"""

import re
import logging
from typing import Dict, List, Tuple, Optional

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Exemplo de texto do log com problema do caractere 'Ê'
TEXTO_COM_PROBLEMA = """DOCUMENTOÊAUXILIARÊDAÊNOTAÊFISCALÊFATURAÊDEÊSERVIÇOSÊDEÊCOMUNICAÇÃOÊELETRÔNICA
NOME:ÊTELCABLESÊBRASILÊLTDAÊFILIALÊSAOÊPAULO
ENDEREÇO:ÊRuaÊIrmaÊGabriela,ÊNºÊ51,ÊCidadeÊMoncoes
CEP:Ê04.571-130,ÊSaoÊPauloÊ-ÊSP
CPF/CNPJ:Ê20.609.743/0004-13
INSCRIÇÃOÊESTADUAL:Ê141.170.861.118
REFERÊNCIA:Ê11/2025
NOTA FISCAL FATURA: 114
SÉRIE: 1 VENCIMENTO:Ê23/12/2025
DATA DE EMISSÃO:
TOTALÊAÊPAGAR:ÊR$Ê29.250,00
10/11/2025
CÓDIGO DO CLIENTE: 100288
Nº TELEFONE: 37999983900
PERÍODO: 01/01/0001 - 01/01/0001
QRÊCodeÊparaÊpagamentoÊPIX
CONSULTE PELA CHAVE DE ACESSO EM:
https://dfe-portal.svrs.rs.gov.br/NFCom
CHAVE DE ACESSO:
3525 1120 6097 4300 0413 6200 1000 0001 1410 2827 2913
Protocolo de Autorização:
3352500028624395 - 10/11/2025 às 16:34:41
NºÊIDENTIFICADORÊDOÊDÉBITOÊAUTOMÁTICO
03399.90038Ê58400.000004Ê00447.201013Ê5Ê13040002925000
ÁREAÊCONTRIBUINTE:
MENSAGENSÊPRIORITÁRIASÊ/ÊAVISOSÊAOÊCONSUMIDOR
ITENSÊDAÊFATURA UN QUANT PREÇOÊUNIT VALORÊTOTAL PIS/COFINS BCÊICMS ALÍQ VALORÊICMS
CNTINT02Ê-ÊIPÊTransit UN 1,00"""

# Texto sem problema para comparação
TEXTO_NORMAL = """DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA
NOME: TELCABLES BRASIL LTDA FILIAL SAO PAULO
ENDEREÇO: Rua Irma Gabriela, Nº 51, Cidade Moncoes
CEP: 04.571-130, Sao Paulo - SP
CPF/CNPJ: 20.609.743/0004-13
INSCRIÇÃO ESTADUAL: 141.170.861.118
REFERÊNCIA: 11/2025
NOTA FISCAL FATURA: 114
SÉRIE: 1 VENCIMENTO: 23/12/2025
DATA DE EMISSÃO:
TOTAL A PAGAR: R$ 29.250,00
10/11/2025
CÓDIGO DO CLIENTE: 100288
Nº TELEFONE: 37999983900
PERÍODO: 01/01/0001 - 01/01/0001
QR Code para pagamento PIX
CONSULTE PELA CHAVE DE ACESSO EM:
https://dfe-portal.svrs.rs.gov.br/NFCom
CHAVE DE ACESSO:
3525 1120 6097 4300 0413 6200 1000 0001 1410 2827 2913
Protocolo de Autorização:
3352500028624395 - 10/11/2025 às 16:34:41
Nº IDENTIFICADOR DO DÉBITO AUTOMÁTICO
03399.90038 58400.000004 00447.201013 5 13040002925000
ÁREA CONTRIBUINTE:
MENSAGENS PRIORITÁRIAS / AVISOS AO CONSUMIDOR
ITENS DA FATURA UN QUANT PREÇO UNIT VALOR TOTAL PIS/COFINS BC ICMS ALÍQ VALOR ICMS
CNTINT02 - IP Transit UN 1,00"""


def analisar_caractere_problematico(texto: str) -> Dict[str, any]:
    """
    Analisa o texto para detectar caracteres problemáticos do OCR.

    Returns:
        Dicionário com estatísticas e problemas encontrados.
    """
    logger.info("Analisando texto para caracteres problemáticos do OCR...")

    resultado = {
        "tamanho_texto": len(texto),
        "contagem_ê": texto.count("Ê") + texto.count("ê"),
        "contagem_espacos": texto.count(" "),
        "contagem_tab": texto.count("\t"),
        "contagem_nova_linha": texto.count("\n"),
        "caracteres_unicos": set(texto),
        "padrao_total_a_pagar_encontrado": False,
        "valor_encontrado": None,
        "problemas": [],
    }

    # Verificar padrão TOTALÊAÊPAGAR
    if "TOTALÊAÊPAGAR" in texto or "TOTALÊAÊPAGAR" in texto.upper():
        resultado["padrao_total_a_pagar_encontrado"] = True

        # Tentar extrair valor
        padrao_valor = (
            r"TOTAL[Ê\s]+A[Ê\s]+PAGAR[Ê\s]*[:]?[Ê\s]*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})"
        )
        match = re.search(padrao_valor, texto, re.IGNORECASE)
        if match:
            resultado["valor_encontrado"] = match.group(1)
        else:
            resultado["problemas"].append(
                "Valor não encontrado mesmo com padrão TOTALÊAÊPAGAR presente"
            )
    else:
        resultado["problemas"].append("Padrão TOTALÊAÊPAGAR não encontrado")

    # Verificar outros caracteres problemáticos comuns no OCR
    caracteres_problematicos = ["□", "▢", "■", "▭", "▯", "�", "�", "\x00"]
    for char in caracteres_problematicos:
        if char in texto:
            contagem = texto.count(char)
            resultado["problemas"].append(
                f"Caractere problemático '{repr(char)}' encontrado {contagem} vezes"
            )
            resultado[f"contagem_{repr(char)}"] = contagem

    # Verificar codificação
    try:
        texto.encode("utf-8")
        resultado["codificacao_ok"] = True
    except UnicodeEncodeError as e:
        resultado["codificacao_ok"] = False
        resultado["problemas"].append(f"Problema de codificação: {e}")

    logger.info(
        f"Análise concluída: {resultado['contagem_ê']} caracteres 'Ê' encontrados"
    )
    return resultado


def testar_normalizacao_strategias(texto: str) -> Dict[str, str]:
    """
    Testa diferentes estratégias de normalização para o texto OCR.

    Returns:
        Dicionário com texto normalizado por cada estratégia.
    """
    logger.info("Testando estratégias de normalização...")

    estrategias = {}

    # Estratégia 1: Substituir 'Ê' por espaço
    estrategias["substituir_ê_por_espaco"] = texto.replace("Ê", " ").replace("ê", " ")

    # Estratégia 2: Usar regex para substituir qualquer caractere não-alfanumérico por espaço
    estrategias["regex_nao_alfanumerico"] = re.sub(
        r'[^a-zA-Z0-9áéíóúÁÉÍÓÚâêîôûÂÊÎÔÛãõÃÕçÇ.,;:!?@#$%&*()\-+=\[\]{}\\/|\'"<>]',
        " ",
        texto,
    )

    # Estratégia 3: Substituir múltiplos caracteres problemáticos
    caracteres_problema = ["Ê", "ê", "□", "▢", "■", "▭", "▯", "�"]
    texto_temp = texto
    for char in caracteres_problema:
        texto_temp = texto_temp.replace(char, " ")
    estrategias["multiplos_caracteres"] = texto_temp

    # Estratégia 4: Normalizar espaços (múltiplos espaços -> um espaço)
    texto_temp = estrategias["substituir_ê_por_espaco"]
    estrategias["normalizar_espacos"] = re.sub(r"\s+", " ", texto_temp).strip()

    # Estratégia 5: Combinação completa (usada no CarrierTelecomExtractor atual)
    def normalizacao_completa(txt):
        # Substituir caracteres problemáticos
        chars = ["Ê", "ê", "□", "▢", "■", "▭", "▯", "�"]
        for char in chars:
            txt = txt.replace(char, " ")

        # Normalizar espaços
        txt = re.sub(r"\s+", " ", txt)

        # Corrigir padrões específicos
        correcoes = {
            "SERVI OS": "SERVIÇOS",
            "COMUNICA O": "COMUNICAÇÃO",
            "ELETR NICA": "ELETRÔNICA",
            "TOTAL A PAGAR": "TOTAL A PAGAR",
            "R$  ": "R$ ",
        }

        for errado, correto in correcoes.items():
            txt = txt.replace(errado, correto)

        return txt.strip()

    estrategias["completa"] = normalizacao_completa(texto)

    logger.info(f"Estratégias testadas: {len(estrategias)}")
    return estrategias


def testar_padroes_regex(texto_normalizado: str) -> Dict[str, bool]:
    """
    Testa se os padrões regex dos extratores funcionam com texto normalizado.

    Returns:
        Dicionário com resultados para cada padrão.
    """
    logger.info("Testando padrões regex com texto normalizado...")

    resultados = {}

    # Padrões do CarrierTelecomExtractor
    padroes = [
        (
            r"(?i)TOTAL\s+A\s+PAGAR\s*[:\-]?\s*R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            "carrier_total_a_pagar_R$",
        ),
        (
            r"(?i)TOTAL\s+A\s+PAGAR\s*[:\-]?\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            "carrier_total_a_pagar_sem_R$",
        ),
        (
            r"(?i)TOTAL\s*[:\-]?\s*R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            "carrier_total_R$",
        ),
        (
            r"(?i)VALOR\s+TOTAL\s*[:\-]?\s*R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
            "carrier_valor_total_R$",
        ),
        (r"R[$]\s*(\d{1,3}(?:\.\d{3})*,\d{2})", "qualquer_R$"),
        (r"\b(\d{1,3}(?:\.\d{3})*,\d{2})\s*REAIS\b", "valor_reais"),
        # Padrões genéricos que podem estar em outros extratores
        (r"(?i)NOTA\s+FISCAL\s+FATURA\s*[:\-]?\s*(\d+)", "nota_fiscal_fatura"),
        (r"(?i)VENCIMENTO\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", "vencimento"),
        (r"(?:CPF/)?CNPJ\s*[:\-]?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", "cnpj"),
    ]

    for padrao, nome in padroes:
        match = re.search(padrao, texto_normalizado)
        resultados[nome] = bool(match)
        if match:
            logger.debug(f"Padrão '{nome}' encontrado: {match.group(0)[:50]}...")

    # Verificar se o valor específico foi encontrado
    valor_match = re.search(r"29\.250,00", texto_normalizado)
    resultados["valor_especifico_29250"] = bool(valor_match)

    logger.info(
        f"Padrões testados: {len(padroes)}, {sum(resultados.values())} encontrados"
    )
    return resultados


def testar_extrator_carrier_diretamente(texto: str) -> Dict[str, any]:
    """
    Testa o CarrierTelecomExtractor diretamente com o texto.

    Returns:
        Resultados da extração.
    """
    logger.info("Testando CarrierTelecomExtractor diretamente...")

    try:
        # Importar dinamicamente para não quebrar se o módulo não existir
        from extractors.carrier_telecom import CarrierTelecomExtractor

        extrator = CarrierTelecomExtractor()

        # Testar can_handle
        can_handle = extrator.can_handle(texto)

        # Testar extract
        dados = extrator.extract(texto)

        resultado = {
            "can_handle": can_handle,
            "valor_total": dados.get("valor_total", 0),
            "dados_completos": dados,
            "sucesso": dados.get("valor_total", 0) > 0,
        }

        logger.info(f"CarrierTelecomExtractor.can_handle: {can_handle}")
        logger.info(
            f"CarrierTelecomExtractor.extract valor: R$ {resultado['valor_total']:.2f}"
        )

        return resultado

    except ImportError as e:
        logger.error(f"Erro ao importar CarrierTelecomExtractor: {e}")
        return {"error": f"ImportError: {e}", "sucesso": False}
    except Exception as e:
        logger.error(f"Erro ao testar CarrierTelecomExtractor: {e}")
        return {"error": f"Exception: {e}", "sucesso": False}


def comparar_textos_antes_depois(original: str, normalizado: str) -> Dict[str, any]:
    """
    Compara texto original e normalizado para identificar diferenças.

    Returns:
        Estatísticas de comparação.
    """
    logger.info("Comparando textos antes/depois da normalização...")

    comparacao = {
        "tamanho_original": len(original),
        "tamanho_normalizado": len(normalizado),
        "diferenca_tamanho": len(normalizado) - len(original),
        "linhas_original": original.count("\n") + 1,
        "linhas_normalizado": normalizado.count("\n") + 1,
        "espacos_original": original.count(" "),
        "espacos_normalizado": normalizado.count(" "),
        "caracteres_ê_original": original.count("Ê") + original.count("ê"),
        "caracteres_ê_normalizado": normalizado.count("Ê") + normalizado.count("ê"),
        "exemplos_diferencas": [],
    }

    # Encontrar diferenças visíveis
    linhas_orig = original.split("\n")
    linhas_norm = normalizado.split("\n")

    for i, (orig, norm) in enumerate(zip(linhas_orig, linhas_norm)):
        if orig != norm:
            # Encontrar primeira diferença
            for j, (c1, c2) in enumerate(zip(orig, norm)):
                if c1 != c2:
                    contexto_inicio = max(0, j - 10)
                    contexto_fim = min(len(orig), j + 10)
                    comparacao["exemplos_diferencas"].append(
                        {
                            "linha": i + 1,
                            "posicao": j,
                            "original_char": repr(c1),
                            "normalizado_char": repr(c2),
                            "contexto_original": orig[contexto_inicio:contexto_fim],
                            "contexto_normalizado": norm[contexto_inicio:contexto_fim],
                        }
                    )
                    break
            if len(comparacao["exemplos_diferencas"]) >= 3:
                break

    logger.info(f"Diferenças encontradas: {len(comparacao['exemplos_diferencas'])}")
    return comparacao


def gerar_relatorio_diagnostico(
    analise_original: Dict,
    estrategias: Dict[str, str],
    resultados_regex: Dict[str, Dict[str, bool]],
    teste_extrator: Dict[str, any],
) -> str:
    """
    Gera um relatório completo de diagnóstico.

    Returns:
        String com relatório formatado.
    """
    logger.info("Gerando relatório de diagnóstico...")

    relatorio = []
    relatorio.append("=" * 80)
    relatorio.append("RELATÓRIO DE DIAGNÓSTICO - PROBLEMA CARACTERE 'Ê' NO OCR")
    relatorio.append("=" * 80)
    relatorio.append("")

    # Seção 1: Análise do texto original
    relatorio.append("1. ANÁLISE DO TEXTO ORIGINAL")
    relatorio.append("-" * 40)
    relatorio.append(f"Tamanho: {analise_original['tamanho_texto']} caracteres")
    relatorio.append(f"Caracteres 'Ê' encontrados: {analise_original['contagem_ê']}")
    relatorio.append(f"Espaços encontrados: {analise_original['contagem_espacos']}")
    relatorio.append(
        f"Padrão 'TOTALÊAÊPAGAR' encontrado: {analise_original['padrao_total_a_pagar_encontrado']}"
    )

    if analise_original["valor_encontrado"]:
        relatorio.append(
            f"Valor encontrado no padrão: R$ {analise_original['valor_encontrado']}"
        )
    else:
        relatorio.append("Valor NÃO encontrado no padrão")

    if analise_original["problemas"]:
        relatorio.append(f"Problemas detectados: {len(analise_original['problemas'])}")
        for problema in analise_original["problemas"][:5]:
            relatorio.append(f"  • {problema}")
    relatorio.append("")

    # Seção 2: Comparação de estratégias de normalização
    relatorio.append("2. COMPARAÇÃO DE ESTRATÉGIAS DE NORMALIZAÇÃO")
    relatorio.append("-" * 40)

    for estrategia, texto in estrategias.items():
        tem_ê = "Ê" in texto or "ê" in texto
        tem_total_a_pagar = "TOTAL A PAGAR" in texto.upper()
        tem_valor = bool(re.search(r"29\.250,00", texto))

        relatorio.append(f"{estrategia}:")
        relatorio.append(f"  • Tamanho: {len(texto)} chars")
        relatorio.append(f"  • Ainda tem 'Ê': {'SIM' if tem_ê else 'NÃO'}")
        relatorio.append(
            f"  • Tem 'TOTAL A PAGAR': {'SIM' if tem_total_a_pagar else 'NÃO'}"
        )
        relatorio.append(f"  • Tem valor '29.250,00': {'SIM' if tem_valor else 'NÃO'}")

        # Amostra das primeiras diferenças
        if estrategia == "substituir_ê_por_espaco":
            amostra = texto[:150].replace("\n", " ")
            relatorio.append(f"  • Amostra: {amostra}...")
    relatorio.append("")

    # Seção 3: Resultados dos padrões regex
    relatorio.append("3. TESTE DE PADRÕES REGEX")
    relatorio.append("-" * 40)

    melhor_estrategia = None
    melhor_resultado = -1

    for estrategia, resultados in resultados_regex.items():
        sucessos = sum(1 for v in resultados.values() if v)
        total = len(resultados)

        relatorio.append(f"{estrategia}: {sucessos}/{total} padrões encontrados")

        if sucessos > melhor_resultado:
            melhor_resultado = sucessos
            melhor_estrategia = estrategia

        # Listar padrões específicos importantes
        padroes_importantes = [
            "carrier_total_a_pagar_R$",
            "carrier_total_a_pagar_sem_R$",
            "valor_especifico_29250",
        ]
        for padrao in padroes_importantes:
            if padrao in resultados:
                status = "✓" if resultados[padrao] else "✗"
                relatorio.append(f"  {status} {padrao}")

    relatorio.append(
        f"\nMelhor estratégia: {melhor_estrategia} ({melhor_resultado} padrões)"
    )
    relatorio.append("")

    # Seção 4: Teste do extrator
    relatorio.append("4. TESTE DO CARRIER TELECOM EXTRACTOR")
    relatorio.append("-" * 40)

    if "error" in teste_extrator:
        relatorio.append(f"ERRO: {teste_extrator['error']}")
    else:
        relatorio.append(
            f"can_handle: {'✓ SIM' if teste_extrator['can_handle'] else '✗ NÃO'}"
        )
        relatorio.append(f"Valor extraído: R$ {teste_extrator['valor_total']:.2f}")
        relatorio.append(
            f"Sucesso: {'✓ SIM' if teste_extrator['sucesso'] else '✗ NÃO'}"
        )

        if teste_extrator["sucesso"]:
            relatorio.append("✓ Extrator funcionando corretamente após normalização")
        else:
            relatorio.append("✗ Extrator NÃO está extraindo valor corretamente")

    relatorio.append("")

    # Seção 5: Recomendações
    relatorio.append("5. RECOMENDAÇÕES")
    relatorio.append("-" * 40)

    if analise_original["contagem_ê"] > 0:
        relatorio.append(
            "✓ PROBLEMA CONFIRMADO: O OCR está usando 'Ê' como substituto de espaços"
        )
        relatorio.append("")
        relatorio.append("AÇÕES RECOMENDADAS:")
        relatorio.append("1. No CarrierTelecomExtractor.can_handle():")
        relatorio.append(
            "   • Adicionar text = text.replace('Ê', ' ').replace('ê', ' ') ANTES de text_upper"
        )
        relatorio.append("")
        relatorio.append("2. No CarrierTelecomExtractor._normalize_ocr_text():")
        relatorio.append("   • Adicionar 'Ê' e 'ê' na lista ocr_problem_chars")
        relatorio.append("")
        relatorio.append("3. Em TODOS os extratores (prevenção global):")
        relatorio.append("   • Considerar adicionar normalização no BaseExtractor")
        relatorio.append(
            "   • Ou criar função utilitária normalize_ocr_text() compartilhada"
        )
    else:
        relatorio.append("✓ Nenhum caractere 'Ê' encontrado no texto de teste")
        relatorio.append("  (pode ser um problema específico do terminal/encoding)")

    relatorio.append("")

    # Seção 6: Código de correção sugerido
    relatorio.append("6. CÓDIGO DE CORREÇÃO SUGERIDO")
    relatorio.append("-" * 40)

    relatorio.append("""# Adicionar no início do método can_handle de CarrierTelecomExtractor:
def can_handle(cls, text: str) -> bool:
    \"\"\"Retorna True se o documento é da Carrier Telecom/TELCABLES BRASIL LTDA.\"\"\"
    if not text:
        return False

    # CORREÇÃO: Normalizar caracteres que o OCR pode usar como espaços
    text = text.replace("Ê", " ").replace("ê", " ")

    text_upper = text.upper()
    # ... resto do código ...""")

    relatorio.append("")
    relatorio.append("""# Adicionar na lista ocr_problem_chars de _normalize_ocr_text():
ocr_problem_chars = [
    "□",  # WHITE SQUARE U+25A1
    "▢",  # WHITE SQUARE WITH ROUNDED CORNERS U+25A2
    "■",  # BLACK SQUARE U+25A0
    "▭",  # WHITE RECTANGLE U+25AD
    "▯",  # WHITE VERTICAL RECTANGLE U+25AF
    "�",  # REPLACEMENT CHARACTER U+FFFD
    "Ê",  # E WITH CIRCUMFLEX, usado como espaço pelo OCR  <-- ADICIONAR
    "ê",  # e with circumflex, minúsculo                   <-- ADICIONAR
]""")

    relatorio.append("")
    relatorio.append("=" * 80)
    relatorio.append("FIM DO RELATÓRIO")
    relatorio.append("=" * 80)

    return "\n".join(relatorio)


def main():
    """Função principal."""
    print("🔍 DIAGNÓSTICO DO PROBLEMA DO CARACTERE 'Ê' NO OCR")
    print("=" * 80)

    # 1. Analisar texto com problema
    print("\n1. Analisando texto com problema do caractere 'Ê'...")
    analise = analisar_caractere_problematico(TEXTO_COM_PROBLEMA)

    print(f"   • Caracteres 'Ê' encontrados: {analise['contagem_ê']}")
    print(
        f"   • 'TOTALÊAÊPAGAR' encontrado: {analise['padrao_total_a_pagar_encontrado']}"
    )

    if analise["problemas"]:
        print(f"   • Problemas: {', '.join(analise['problemas'][:2])}")

    # 2. Testar estratégias de normalização
    print("\n2. Testando estratégias de normalização...")
    estrategias = testar_normalizacao_strategias(TEXTO_COM_PROBLEMA)

    resultados_por_estrategia = {}
    for estrategia, texto in estrategias.items():
        print(f"   • {estrategia}: {len(texto)} chars")
        resultados_por_estrategia[estrategia] = testar_padroes_regex(texto)

    # 3. Testar extrator diretamente
    print("\n3. Testando CarrierTelecomExtractor...")
    resultado_extrator = testar_extrator_carrier_diretamente(TEXTO_COM_PROBLEMA)

    if "error" in resultado_extrator:
        print(f"   • ERRO: {resultado_extrator['error']}")
    else:
        print(f"   • can_handle: {resultado_extrator['can_handle']}")
        print(f"   • Valor extraído: R$ {resultado_extrator['valor_total']:.2f}")

    # 4. Comparar com texto normal
    print("\n4. Comparando com texto sem problema...")
    analise_normal = analisar_caractere_problematico(TEXTO_NORMAL)
    comparacao = comparar_textos_antes_depois(TEXTO_COM_PROBLEMA, TEXTO_NORMAL)

    print(f"   • Texto normal tem 'Ê': {analise_normal['contagem_ê'] > 0}")
    print(f"   • Diferença de tamanho: {comparacao['diferenca_tamanho']} chars")

    # 5. Gerar relatório completo
    print("\n5. Gerando relatório completo...")
    relatorio = gerar_relatorio_diagnostico(
        analise, estrategias, resultados_por_estrategia, resultado_extrator
    )

    # Salvar relatório em arquivo
    with open("diagnostico_ocr_problema_ê.txt", "w", encoding="utf-8") as f:
        f.write(relatorio)

    print("\n" + "=" * 80)
    print("✅ DIAGNÓSTICO CONCLUÍDO")
    print("=" * 80)
    print(f"\n📄 Relatório salvo em: diagnostico_ocr_problema_ê.txt")
    print(f"🔧 Problemas detectados: {len(analise['problemas'])}")

    # Resumo das recomendações
    if analise["contagem_ê"] > 0:
        print(f"\n⚠️  PROBLEMA CONFIRMADO:")
        print(f"   O OCR está usando 'Ê' como substituto de espaços")
        print(f"   Caracteres 'Ê' encontrados: {analise['contagem_ê']}")
        print(f"\n✅ SOLUÇÃO:")
        print(f"   1. Adicionar normalização no CarrierTelecomExtractor.can_handle()")
        print(f"   2. Adicionar 'Ê' e 'ê' na lista ocr_problem_chars")
        print(f"   3. Testar com o script de correção sugerido no relatório")
    else:
        print(f"\n✅ Nenhum problema com 'Ê' encontrado no texto de teste")
        print(f"   O problema pode ser específico do terminal/encoding")

    print("\n" + "=" * 80)


def testar_com_arquivo_pdf(pdf_path: str):
    """
    Função para testar com arquivo PDF real.

    Args:
        pdf_path: Caminho para o arquivo PDF.
    """
    try:
        import pdfplumber

        print(f"\n📄 Testando com arquivo PDF: {pdf_path}")

        # Extrair texto do PDF
        texto_pdf = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                texto_pdf += page.extract_text() or ""

        print(f"   • Texto extraído: {len(texto_pdf)} caracteres")

        # Analisar
        analise = analisar_caractere_problematico(texto_pdf)

        print(f"   • Caracteres 'Ê': {analise['contagem_ê']}")
        print(f"   • Problemas detectados: {len(analise['problemas'])}")

        if analise["contagem_ê"] > 0:
            print(f"   ⚠️  PROBLEMA CONFIRMADO NO PDF!")
        else:
            print(f"   ✅ PDF não tem problema com 'Ê'")

        return texto_pdf

    except ImportError:
        print("   ⚠️  pdfplumber não instalado. Instale com: pip install pdfplumber")
        return None
    except Exception as e:
        print(f"   ❌ Erro ao processar PDF: {e}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Testar com arquivo PDF fornecido
        pdf_path = sys.argv[1]
        texto_pdf = testar_com_arquivo_pdf(pdf_path)

        if texto_pdf:
            # Usar texto do PDF para análise
            TEXTO_COM_PROBLEMA = texto_pdf
            print("\n" + "=" * 80)
            print("Continuando análise com texto do PDF...")
            print("=" * 80)

    main()
