# Prompt: Criação de Novo Extrator

> **Uso:** Criar um extrator Python especializado para um layout de documento específico
> 
> **Pré-requisitos:** Análise do caso com `review.md` ou `diagnosis.md` confirmando necessidade de novo extrator

---

## Input de Diagnóstico

```yaml
# Identificação do documento
TIPO_DOCUMENTO: #[NFSe/Boleto/DANFE/Administrativo/Fatura específica]
PADRAO_IDENTIFICADO: #[ex: "NFSe da Prefeitura de X", "Boleto do Banco Y", "Fatura Z"]

# Justificativa para novo extrator
JUSTIFICATIVA: |
  [Por que o extrator genérico não funciona?]
  [Ex: "Layout específico com campos em posições diferentes"]
  [Ex: "CNPJ único permite identificação precisa"]

# Prioridade no registry (0 = mais prioritário)
PRIORIDADE_SUGERIDA: #[0-15 - veja notas abaixo]

# Trechos de texto de referência (obrigatório)
TRECHOS_TEXTO:
  - |
    [Cole aqui o TEXTO BRUTO completo ou trechos-chave do PDF]
    [Use: python scripts/inspect_pdf.py <arquivo.pdf> --raw]
  - |
    [Trecho 2 se houver variações]

# Variações esperadas
VARIACOES:
  valor: #[ex: "pode vir com/sem símbolo R$", "ponto vs vírgula decimal"]
  data: #[ex: "DD/MM/AAAA vs AAAA-MM-DD", "nome do mês por extenso"]
  numero: #[ex: "com/sem zeros à esquerda", "formato 0001-20"]
  fornecedor: #[ex: "razão social completa vs fantasia"]

# Campos problemáticos específicos
CAMPOS_PROBLEMATICOS:
  - campo: #[valor/vencimento/fornecedor/numero/etc]
    padrao_atual_falha: #[regex que não funciona]
    padrao_correto_no_pdf: #[como aparece no texto bruto]
```

### Notas sobre Prioridade no Registry

A ordem em `extractors/__init__.py` define a prioridade (0 = mais prioritário):

```
# 0-3: Extratores muito específicos (CNPJ único, layout único)
# 4-7: Extratores por tipo de documento/empresa
# 8-11: Extratores administrativos específicos
# 12-14: Genéricos (fallback)
# 15: DANFE (último, pois é muito abrangente)
```

**Sua prioridade sugerida:** #[PRIORIDADE_SUGERIDA]

---

## Template de Código a Gerar

### 1. CABEÇALHO DO ARQUIVO

```python
"""
Extrator de [Tipo de Documento] - [Identificação Específica].

Este módulo implementa extração de dados de [descrição do documento].
[Características específicas que diferenciam este layout].

Campos extraídos:
    - [campo_1]: [descrição]
    - [campo_2]: [descrição]
    - ...

Identificação:
    - [Critério único: CNPJ específico, termo exclusivo, padrão de layout]
    - CNPJ: [XX.XXX.XXX/XXXX-XX] (se aplicável)

Example:
    >>> from extractors.[nome_arquivo] import [NomeExtrator]
    >>> extractor = [NomeExtrator]()
    >>> dados = extractor.extract(texto_pdf)
    >>> print(f"[campo]: {dados['[campo]']}")
"""
import re
from typing import Any, Dict, Optional

from core.extractors import BaseExtractor, register_extractor
from extractors.utils import (
    normalize_text_for_extraction,
    parse_br_money,
    parse_date_br,
)
```

### 2. CLASSE DO EXTRATOR

```python
@register_extractor
class [NomeDoExtrator](BaseExtractor):
    """
    Extrator para [descrição específica do documento].
    
    [Detalhes sobre o que torna este extrator necessário]
    """

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Identifica se este é o extrator correto para o texto.
        
        [Documente os critérios de identificação]
        
        Args:
            text: Texto extraído do PDF.
            
        Returns:
            True se o documento corresponde a este extrator.
        """
        text_upper = (text or "").upper()
        
        # Indicadores FORTES (se presentes, documento É este tipo)
        strong_indicators = [
            #["TERMO_ESPECIFICO_1"],
            #["TERMO_ESPECIFICO_2"],
            # CNPJ específico se aplicável:
            #[r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"],
        ]
        
        # Verificar indicadores fortes
        has_strong = any(
            indicator in text_upper if not indicator.startswith("r\"") 
            else re.search(indicator, text)
            for indicator in strong_indicators
        )
        
        if has_strong:
            return True
            
        # Padrões negativos (se presentes, NÃO é este tipo)
        negative_patterns = [
            #["TERMO_DE_OUTRO_TIPO"],
        ]
        
        for pattern in negative_patterns:
            if pattern in text_upper:
                return False
                
        # Score-based (múltiplos indicadores fracos)
        score = 0
        weak_indicators = [
            #["TERMO_FRACO_1", 2],  # [termo, peso]
            #["TERMO_FRACO_2", 1],
        ]
        
        for term, weight in weak_indicators:
            if term in text_upper:
                score += weight
                
        return score >= 3  # Ajustar threshold conforme necessário

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extrai dados do documento.
        
        Args:
            text: Texto extraído do PDF.
            
        Returns:
            Dicionário com dados extraídos.
        """
        text = self._normalize_text(text or "")
        
        data: Dict[str, Any] = {"tipo_documento": "[NFSE/BOLETO/DANFE/OUTRO]"}
        
        # Campos principais
        data["cnpj_prestador"] = self._extract_cnpj(text)  # ou cnpj_beneficiario, cnpj_emitente
        data["numero_nota"] = self._extract_numero_nota(text)
        data["valor_total"] = self._extract_valor(text)
        data["data_emissao"] = self._extract_data_emissao(text)
        data["vencimento"] = self._extract_vencimento(text)
        data["fornecedor_nome"] = self._extract_fornecedor(text)
        
        # Campos específicos deste tipo de documento
        #[data["campo_especifico_1"] = self._extract_campo_especifico_1(text)]
        #[data["campo_especifico_2"] = self._extract_campo_especifico_2(text)]
        
        return data

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para extração."""
        return normalize_text_for_extraction(text)
```

### 3. MÉTODOS DE EXTRAÇÃO ESPECÍFICOS

Para cada campo problemático, forneça:

```python
    def _extract_valor(self, text: str) -> float:
        """
        Extrai valor total do documento.
        
        Padrões buscados:
        - "Valor Total: R$ 1.234,56"
        - "TOTAL R$ 1.234,56"
        
        Args:
            text: Texto normalizado.
            
        Returns:
            Valor como float ou 0.0 se não encontrado.
        """
        # Padrões específicos do layout (mais confiáveis primeiro)
        specific_patterns = [
            r"(?i)Valor\s+Total\s*[:\s]+R\$\s*([\d\.]+,\d{2})",
            r"(?i)TOTAL\s*[:\s]+R\$\s*([\d\.]+,\d{2})",
        ]
        
        for pattern in specific_patterns:
            match = re.search(pattern, text)
            if match:
                return parse_br_money(match.group(1))
                
        # Fallback: buscar valores monetários próximos a labels
        fallback_patterns = [
            r"(?i)Valor\s*[:\s]+R\$\s*([\d\.]+,\d{2})",
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, text)
            if match:
                return parse_br_money(match.group(1))
                
        return 0.0

    def _extract_numero_nota(self, text: str) -> Optional[str]:
        """
        Extrai número da nota/documento.
        
        Variações suportadas:
        - "Nota Fiscal Nº 12345"
        - "NFSe: 12345"
        - "Número: 00123"
        
        Args:
            text: Texto normalizado.
            
        Returns:
            Número da nota ou None.
        """
        patterns = [
            r"(?i)Nota\s+Fiscal\s*N[º°]?\s*[:\s]+(\d+)",
            r"(?i)NFSe\s*[:\s]+(\d+)",
            r"(?i)N[º°]\s*[:\s]+(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
                
        return None

    def _extract_vencimento(self, text: str) -> Optional[str]:
        """
        Extrai data de vencimento.
        
        Formatos suportados:
        - "Vencimento: 15/01/2026"
        - "Vence em: 15/01/2026"
        - "Data: 2026-01-15"
        
        Returns:
            Data no formato ISO (YYYY-MM-DD) ou None.
        """
        patterns = [
            r"(?i)Vencimento\s*[:\s]+(\d{2}/\d{2}/\d{4})",
            r"(?i)Vence\s+em\s*[:\s]+(\d{2}/\d{2}/\d{4})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return parse_date_br(match.group(1))
                
        return None

    def _extract_fornecedor(self, text: str) -> Optional[str]:
        """
        Extrai nome do fornecedor.
        
        Estratégia:
        1. Buscar após label específico
        2. Extrair empresa com base no CNPJ
        3. Fallback: inferir do texto
        
        Args:
            text: Texto normalizado.
            
        Returns:
            Nome do fornecedor ou None.
        """
        # Método 1: Regex específico
        patterns = [
            r"(?i)Prestador\s*[:\s]+([A-Z][A-Z\s\.]+(?:LTDA|S\.?A\.?|ME|EPP)?)",
            r"(?i)Fornecedor\s*[:\s]+([A-Z][A-Z\s\.]+(?:LTDA|S\.?A\.?|ME|EPP)?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
                
        # Método 2: Buscar pelo CNPJ
        cnpj = self._extract_cnpj(text)
        if cnpj:
            # Usar empresa_matcher se disponível
            from core.empresa_matcher import infer_fornecedor_from_text
            return infer_fornecedor_from_text(text, cnpj)
            
        return None

    def _extract_cnpj(self, text: str) -> Optional[str]:
        """Extrai e formata CNPJ."""
        # Padrão: XX.XXX.XXX/XXXX-XX ou XXXXXXXXXXXXXX
        pattern = r"(?<!\d)(\d{2})\D?(\d{3})\D?(\d{3})\D?(\d{4})\D?(\d{2})(?!\d)"
        match = re.search(pattern, text)
        
        if match:
            return f"{match.group(1)}.{match.group(2)}.{match.group(3)}/{match.group(4)}-{match.group(5)}"
            
        return None
```

### 4. LOGGING PARA DEBUG

Adicione logging ao extrator para facilitar diagnóstico:

```python
import logging

logger = logging.getLogger(__name__)

@register_extractor
class MeuExtractor(BaseExtractor):
    @classmethod
    def can_handle(cls, text: str) -> bool:
        logger.debug(f"{cls.__name__}.can_handle chamado")
        
        has_indicator = "MEU_INDICADOR" in text.upper()
        logger.debug(f"Indicador encontrado: {has_indicator}")
        
        return has_indicator
    
    def extract(self, text: str) -> Dict[str, Any]:
        logger.info(f"{self.__class__.__name__}.extract iniciado")
        
        data: Dict[str, Any] = {"tipo_documento": "OUTRO"}
        
        numero = self._extract_numero(text)
        if numero:
            data["numero_documento"] = numero
            logger.info(f"Número extraído: {numero}")
        else:
            logger.warning("Número não encontrado")
        
        return data
```

**Veja detalhes completos em:** [`logging_guide.md`](./logging_guide.md)

---

### 5. TESTES DE VALIDAÇÃO

```python
# =============================================================================
# TESTES (para validar o extrator)
# =============================================================================

TEST_CASES = [
    # (input_text_fragment, expected_field, expected_value)
    (
        "Valor Total: R$ 1.234,56\nNota Fiscal Nº 12345",
        "valor_total",
        1234.56
    ),
    (
        "Vencimento: 15/01/2026\nPrestador: EMPRESA LTDA",
        "vencimento",
        "2026-01-15"
    ),
    # Casos edge/bordo:
    (
        "Valor Total: R$ 0,00\nValor dos Serviços: R$ 500,00",
        "valor_total",
        500.00  # Deve pegar o valor dos serviços, não o zero
    ),
]

EDGE_CASES = [
    # Documentos que NÃO devem ser processados por este extrator
    "DANFE - CHAVE DE ACESSO",  # Deve retornar False no can_handle
    "BOLETO - LINHA DIGITÁVEL",  # Deve retornar False no can_handle
]
```

### 5. INSTRUÇÕES DE INTEGRAÇÃO

Após gerar o código:

```bash
# 1. Salvar arquivo em extractors/[nome_arquivo].py

# 2. Verificar se está importado em extractors/__init__.py
# Deve estar na posição de prioridade correta (0 = mais prioritário)

# 3. Testar o extrator
python scripts/inspect_pdf.py <arquivo_teste.pdf>

# 4. Validar can_handle não quebra outros casos
python scripts/validate_extraction_rules.py --batch-mode

# 5. Reprocessar batches afetados
python run_ingestion.py --reprocess --batch-folder <pasta>

# 6. Verificar CSV de saída
grep <padrao> data/output/relatorio_lotes.csv

# 7. Exportar para Sheets (dry-run)
python scripts/export_to_sheets.py --dry-run
```

---

## Padrões de Código e Arquitetura

### SOLID Principles (Aplicados)

| Princípio | Aplicação | Exemplo |
|-----------|-----------|---------|
| **S**ingle Responsibility | Extrator faz UMA coisa | `TunnaFaturaExtractor` extrai APENAS faturas Tunna |
| **O**pen/Closed | Extensível, não modificável | Crie novo extrator, não modifique `NfseGeneric` |
| **L**iskov Substitution | Substitui BaseExtractor | `MeuExtractor(BaseExtractor)` mantém contrato |
| **I**nterface Segregation | Apenas métodos necessários | `can_handle()` e `extract()` obrigatórios apenas |
| **D**ependency Inversion | Depende de abstrações | `BaseExtractor` define contrato, não implementação |

### DRY - Don't Repeat Yourself (Com Cuidado!)

> ⚠️ **IMPORTANTE:** DRY aplica-se a **REGRAS DE NEGÓCIO**, não lógica pura.

**✅ EXTRAIR para `utils.py` (Regras de Negócio):**
- Parse de valores monetários brasileiros (`parse_br_money`)
- Parse de datas brasileiras (`parse_date_br`)
- Regex de CNPJ, CEP (padrões compartilhados)
- Normalização de texto (`normalize_text_for_extraction`)

**❌ NÃO EXTRAIR (Lógica Específica do Contexto):**
- Estratégia de extração de valor (cada fornecedor é único)
- Fallbacks específicos (EMC usa maior valor, outro usa primeiro)
- Padrões regex específicos do layout

**Exemplo:**
```python
# ✅ Usa utils.py (regra de negócio compartilhada)
from extractors.utils import parse_br_money

valor = parse_br_money(match.group(1))

# ✅ Mantém no extrator (lógica específica EMC)
def _extract_valor_total(self, text: str) -> float:
    # Estratégia única EMC: procurar "TOTAL" na última página
    m = re.search(r'TOTAL\s+R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})', text)
    if m:
        return parse_br_money(m.group(1))  # Usa utils
    
    # Fallback específico EMC: maior valor
    all_values = re.findall(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})', text)
    ...  # Lógica específica, não extrair
```

**Veja detalhes completos em:** [`coding_standards.md`](./coding_standards.md)

---

## Regras de Negócio Importantes

1. **Valores monetários:** Sempre retornar `float`, nunca string. Use `parse_br_money()`.
2. **Datas:** Retornar formato ISO `YYYY-MM-DD` ou `None`. Use `parse_date_br()`.
3. **CNPJ:** Formatar como `XX.XXX.XXX/XXXX-XX` ou retornar apenas números consistentemente.
4. **Campos vazios:** Retornar `None`, nunca string vazia `""`.
5. **Prioridade:** Extratores específicos devem vir ANTES de genéricos no registry.
6. **can_handle():** Deve ser conservador - melhor recusar do que aceitar errado.

---

## Checklist de Qualidade do Extrator

Antes de considerar o extrator pronto:

### Funcional
- [ ] `can_handle()` identifica corretamente documentos deste tipo
- [ ] `can_handle()` recusa documentos de outros tipos
- [ ] Valor é extraído corretamente (formato float)
- [ ] Número da nota/documento é extraído
- [ ] Vencimento é extraído (formato ISO)
- [ ] Fornecedor é extraído (não genérico)
- [ ] CNPJ é formatado corretamente
- [ ] Testado com pelo menos 3 PDFs reais
- [ ] Não quebra casos existentes (regressão)
- [ ] Posicionado corretamente no registry (prioridade)

### Código (basedpyright)
- [ ] Type hints em todos os métodos públicos
- [ ] Docstrings em módulo, classe e métodos públicos
- [ ] Sem imports não usados (`reportUnusedImport`)
- [ ] Sem variáveis não usadas (`reportUnusedVariable`)
- [ ] Sem warnings de Optional (`reportOptionalMemberAccess`)
- [ ] Rode: `basedpyright extractors/meu_extrator.py`

### Logging
- [ ] Logger obtido: `logger = logging.getLogger(__name__)`
- [ ] `can_handle()` loga decisão (DEBUG)
- [ ] `extract()` loga início/fim (INFO)
- [ ] Campos principais logam quando encontrados (INFO)
- [ ] Não usa `print()` (apenas `logger`)
- [ ] Logs aparecem em `logs/scrapper.log` ao testar
