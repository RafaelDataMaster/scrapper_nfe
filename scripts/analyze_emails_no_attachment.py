"""
Script de Análise de E-mails Sem Anexo.

Note: Usamos typing.TYPE_CHECKING para evitar conflito com módulo 'email'.

Este script conecta ao servidor de e-mail, busca e-mails que NÃO possuem
anexos PDF/XML válidos e analisa o corpo para identificar padrões de:
- Links de download/verificação de notas fiscais
- Códigos de autenticação/verificação
- Padrões de prefeituras e portais de NF-e

Objetivo: Identificar quais regex seriam úteis para capturar automaticamente
links e códigos de autenticação em e-mails sem anexo.

Usage:
    python scripts/analyze_emails_no_attachment.py
    python scripts/analyze_emails_no_attachment.py --subject "Nota Fiscal"
    python scripts/analyze_emails_no_attachment.py --limit 50
    python scripts/analyze_emails_no_attachment.py --output analise_emails.json
"""

from __future__ import annotations

import argparse
import imaplib
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Adiciona o diretório raiz ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.empresas import EMPRESAS_CADASTRO
from core.empresa_matcher import (
    _empresa_codigo_from_razao,
    _normalize_cnpj_to_digits,
    iter_cnpjs_in_text,
)


@dataclass
class EmailAnalysis:
    """Resultado da análise de um e-mail sem anexo."""
    email_id: str
    subject: str
    sender_name: str
    sender_address: str
    received_date: str
    body_text: str
    body_html: str = ""

    # Links encontrados
    links_encontrados: List[str] = field(default_factory=list)
    links_nfe: List[str] = field(default_factory=list)
    links_prefeitura: List[str] = field(default_factory=list)
    links_download: List[str] = field(default_factory=list)

    # Códigos encontrados
    codigos_encontrados: List[str] = field(default_factory=list)
    codigos_autenticacao: List[str] = field(default_factory=list)
    codigos_verificacao: List[str] = field(default_factory=list)

    # Números de nota/fatura
    numeros_nota: List[str] = field(default_factory=list)

    # Contexto
    menciona_nf: bool = False
    menciona_boleto: bool = False
    menciona_download: bool = False
    menciona_portal: bool = False
    menciona_prefeitura: bool = False

    # Classificação
    tipo_email: str = "INDEFINIDO"  # LINK_DOWNLOAD, CODIGO_VERIFICACAO, INFORMATIVO, etc.

    # Empresa detectada
    empresa_detectada: Optional[str] = None
    empresa_metodo: Optional[str] = None  # cnpj, nome_exato, nome_parcial
    empresa_matches: List[str] = field(default_factory=list)  # todos os matches encontrados

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# DETECTOR DE EMPRESA NO TEXTO
# =============================================================================

class EmpresaDetector:
    """Detecta qual empresa do cadastro está mencionada no texto do e-mail."""

    # Domínios a ignorar (são domínios corporativos internos, não indicam empresa)
    DOMINIOS_IGNORAR = {
        'soumaster.com.br',
        'soumaster.com',
        'gmail.com',
        'outlook.com',
        'hotmail.com',
        'yahoo.com',
        'yahoo.com.br',
    }

    # Padrões de URL a remover (tracking, analytics, etc.)
    URL_PATTERNS_REMOVER = [
        r'https?://click\.[^\s]+',       # click.omie.com, etc.
        r'https?://track\.[^\s]+',       # tracking URLs
        r'https?://[^\s]*\.cdn\.[^\s]+', # CDN URLs
        r'https?://cdn\.[^\s]+',         # CDN URLs
        r'https?://[^\s]+/track/[^\s]+', # /track/ paths
        r'https?://[^\s]+/click/[^\s]+', # /click/ paths
        r'href="[^"]*"',                 # Remove href attributes
        r'src="[^"]*"',                  # Remove src attributes
    ]

    # Palavras a ignorar no match por nome (muito genéricas)
    STOPWORDS = {
        'SERVICO', 'SERVICOS', 'SERVICE',
        'CONSULTORIA',
        'GESTAO', 'INTEGRADA',
        'COMERCIO', 'INDUSTRIA',
        'TECNOLOGIA', 'SOLUCOES',
        'SISTEMA', 'SISTEMAS',
        'EMPRESA', 'EMPRESAS',
        'ADMINISTRACAO', 'ADMINISTRADORA',
        'PARTICIPACOES', 'SOCIETARIAS',
        'GRUPO', 'HOLDING',
        'COMPANHIA', 'CIA',
        'LTDA', 'SA', 'S/A', 'EIRELI', 'EPP', 'ME',
        'PROVEDOR', 'ACESSO', 'INTERNET',
        'TELECOM', 'TELECOMUNICACOES', 'COMUNICACAO',
        'MATRIZ', 'FILIAL',
        'BRASIL', 'BRASILEIRA',
        'REDE',
        # Palavras comuns em HTML/emails
        'CLICK', 'TRACK', 'VIEW', 'OPEN',
        'LINK', 'HTTP', 'HTTPS', 'WWW',
        'STYLE', 'WIDTH', 'HEIGHT', 'FONT',
        'ALIGN', 'CENTER', 'LEFT', 'RIGHT',
        'VISTA',  # SPE VISTA ALEGRE - muito genérico
        'ALEGRE',
        'PAULO', 'SAO',  # Muito genérico
    }

    def __init__(self):
        self.cadastro = self._load_cadastro()
        self.empresas_por_codigo = self._build_codigo_map()

    def _load_cadastro(self) -> Dict[str, Dict]:
        """Carrega cadastro normalizado."""
        normalized = {}
        for cnpj, payload in (EMPRESAS_CADASTRO or {}).items():
            cnpj_digits = _normalize_cnpj_to_digits(str(cnpj))
            if cnpj_digits:
                normalized[cnpj_digits] = payload
        return normalized

    def _build_codigo_map(self) -> Dict[str, List[str]]:
        """Mapeia código -> lista de CNPJs."""
        mapa = defaultdict(list)
        for cnpj, payload in self.cadastro.items():
            razao = payload.get("razao_social", "")
            codigo = _empresa_codigo_from_razao(razao)
            if codigo:
                mapa[codigo.upper()].append(cnpj)
        return dict(mapa)

    def _limpar_texto(self, texto: str) -> str:
        """Remove domínios a ignorar, URLs de tracking e limpa texto para análise."""
        texto_limpo = texto

        # Remove URLs de tracking/analytics
        for pattern in self.URL_PATTERNS_REMOVER:
            texto_limpo = re.sub(pattern, ' ', texto_limpo, flags=re.IGNORECASE)

        # Remove domínios específicos
        for dominio in self.DOMINIOS_IGNORAR:
            # Remove menções ao domínio (e-mails, URLs)
            texto_limpo = re.sub(
                rf'[a-zA-Z0-9._%+-]*@{re.escape(dominio)}',
                ' ',
                texto_limpo,
                flags=re.IGNORECASE
            )
            texto_limpo = re.sub(
                rf'https?://[^\s]*{re.escape(dominio)}[^\s]*',
                ' ',
                texto_limpo,
                flags=re.IGNORECASE
            )
            texto_limpo = re.sub(
                rf'\b{re.escape(dominio)}\b',
                ' ',
                texto_limpo,
                flags=re.IGNORECASE
            )

        # Remove tags HTML comuns que podem conter palavras-chave
        texto_limpo = re.sub(r'<style[^>]*>.*?</style>', ' ', texto_limpo, flags=re.IGNORECASE | re.DOTALL)
        texto_limpo = re.sub(r'<script[^>]*>.*?</script>', ' ', texto_limpo, flags=re.IGNORECASE | re.DOTALL)

        return texto_limpo

    def _extrair_destinatario_nfe(self, texto: str) -> Optional[str]:
        """
        Extrai o nome do destinatário da NF-e do campo 'Para:' do email original.
        Geralmente é a empresa que recebeu a NF-e.
        """
        # Padrão: "Para: NOME DA EMPRESA <email@...>"
        # Captura texto que vem depois de "Para:" e antes do "<" ou fim de linha
        patterns = [
            r'Para:\s*([^<\n]+?)(?:\s*<|$)',  # Para: NOME <email>
            r'To:\s*([^<\n]+?)(?:\s*<|$)',     # To: NAME <email>
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, texto, re.IGNORECASE)
            for match in matches:
                # Limpa e retorna se for um nome significativo
                nome = match.strip()
                # Ignora se for só email ou muito curto
                if '@' not in nome and len(nome) > 5:
                    return nome.upper()
        return None

    def _aparece_em_contexto_seguro(self, codigo: str, texto_upper: str) -> bool:
        """
        Verifica se o código aparece em contexto seguro (destinatário, razão social)
        vs contexto irrelevante (frase de segurança, senha).
        """
        # Padrões de contexto SEGURO (empresa é mencionada como destinatária)
        padroes_seguros = [
            rf'Para:\s*[^<\n]*{re.escape(codigo)}',  # Para: RBC Rede...
            rf'To:\s*[^<\n]*{re.escape(codigo)}',     # To: RBC Rede...
            rf'Tomador[:\s]+[^\n]*{re.escape(codigo)}',  # Tomador: RBC...
            rf'Destinat[áa]rio[:\s]+[^\n]*{re.escape(codigo)}',  # Destinatário: RBC...
            rf'Cliente[:\s]+[^\n]*{re.escape(codigo)}',  # Cliente: RBC...
        ]
        
        for pattern in padroes_seguros:
            if re.search(pattern, texto_upper, re.IGNORECASE):
                return True
        
        return False

    def _aparece_em_contexto_ignorar(self, codigo: str, texto_upper: str) -> bool:
        """
        Verifica se o código aparece apenas em contexto a ignorar
        (frase de segurança, senha, etc.)
        """
        # Padrões de contexto a IGNORAR
        padroes_ignorar = [
            rf'frase\s+de\s+seguran[çc]a[^:]*:[^\n]*{re.escape(codigo)}',
            rf'senha[^:]*:[^\n]*{re.escape(codigo)}',
            rf'password[^:]*:[^\n]*{re.escape(codigo)}',
            rf'security\s+phrase[^:]*:[^\n]*{re.escape(codigo)}',
        ]
        
        for pattern in padroes_ignorar:
            if re.search(pattern, texto_upper, re.IGNORECASE):
                return True
        
        return False

    def detectar(self, texto: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Detecta empresa no texto.

        Returns:
            (codigo_empresa, metodo, lista_matches)
            - codigo_empresa: código da empresa detectada (ex: "CSC", "RBC")
            - metodo: como foi detectada ("cnpj", "nome_exato", "nome_parcial")
            - lista_matches: todos os matches encontrados
        """
        if not texto:
            return None, None, []

        texto_limpo = self._limpar_texto(texto)
        texto_upper = texto_limpo.upper()
        matches_encontrados = []

        # 1) Primeiro tenta por CNPJ (mais confiável)
        for cnpj_digits, start, end, raw in iter_cnpjs_in_text(texto_limpo):
            if cnpj_digits in self.cadastro:
                payload = self.cadastro[cnpj_digits]
                razao = payload.get("razao_social", "")
                codigo = _empresa_codigo_from_razao(razao)
                matches_encontrados.append(f"CNPJ:{codigo}:{raw}")
                # Retorna imediatamente se achou CNPJ nosso
                return codigo, "cnpj", matches_encontrados

        # 2) Tenta por código exato (word boundary)
        codigos_contexto_seguro = []
        codigos_contexto_normal = []
        
        for codigo, cnpjs in self.empresas_por_codigo.items():
            # Ignora códigos muito curtos ou stopwords
            if len(codigo) < 3 or codigo in self.STOPWORDS:
                continue

            # Busca como palavra completa
            pattern = rf'\b{re.escape(codigo)}\b'
            if re.search(pattern, texto_upper):
                # Verifica contexto
                em_contexto_seguro = self._aparece_em_contexto_seguro(codigo, texto_upper)
                em_contexto_ignorar = self._aparece_em_contexto_ignorar(codigo, texto_upper)
                
                if em_contexto_seguro:
                    matches_encontrados.append(f"CODIGO_EXATO:{codigo}:SEGURO")
                    codigos_contexto_seguro.append(codigo)
                elif not em_contexto_ignorar:
                    matches_encontrados.append(f"CODIGO_EXATO:{codigo}")
                    codigos_contexto_normal.append(codigo)
                else:
                    matches_encontrados.append(f"CODIGO_EXATO:{codigo}:IGNORADO")

        # Prioriza códigos em contexto seguro
        if len(codigos_contexto_seguro) == 1:
            return codigos_contexto_seguro[0], "nome_exato", matches_encontrados
        
        # Se há múltiplos seguros ou nenhum seguro, usa normais
        if len(codigos_contexto_seguro) > 1:
            # Múltiplos seguros - pega o primeiro (geralmente o destinatário)
            return codigos_contexto_seguro[0], "nome_exato", matches_encontrados
        
        # Se não tem seguros, usa normais (se único)
        if len(codigos_contexto_normal) == 1:
            return codigos_contexto_normal[0], "nome_exato", matches_encontrados

        # 3) Tenta por razão social parcial (mais arriscado)
        for cnpj, payload in self.cadastro.items():
            razao = payload.get("razao_social", "")
            codigo = _empresa_codigo_from_razao(razao)

            # Extrai palavras significativas da razão social
            palavras = re.findall(r'\b[A-Z]{3,}\b', razao.upper())
            palavras_uteis = [p for p in palavras if p not in self.STOPWORDS and len(p) >= 4]

            for palavra in palavras_uteis[:2]:  # Só as 2 primeiras palavras úteis
                if re.search(rf'\b{re.escape(palavra)}\b', texto_upper):
                    matches_encontrados.append(f"NOME_PARCIAL:{codigo}:{palavra}")

        # Se encontrou matches parciais únicos
        codigos_parciais = list(set(
            m.split(":")[1] for m in matches_encontrados if m.startswith("NOME_PARCIAL:")
        ))
        if len(codigos_parciais) == 1:
            return codigos_parciais[0], "nome_parcial", matches_encontrados

        # Não conseguiu determinar com certeza
        return None, None, matches_encontrados


class EmailAnalyzer:
    """Analisador de e-mails sem anexo."""

    # Extensões de arquivos válidos (que indicariam anexo)
    VALID_EXTENSIONS = {'.pdf', '.xml'}

    # Regex para links gerais
    REGEX_URL = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)

    # Regex para links específicos de NF-e
    REGEX_LINKS_NFE = [
        # Portais de NF-e
        re.compile(r'https?://[^\s]*nf[es]?[^\s]*\.(com|gov|org)[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*nota[^\s]*fiscal[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*danfe[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*portal[^\s]*nf[^\s]*', re.IGNORECASE),
        # Prefeituras
        re.compile(r'https?://[^\s]*prefeitura[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*\.(gov\.br|sp\.gov\.br|rj\.gov\.br)[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*issnet[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*ginfes[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*betha[^\s]*', re.IGNORECASE),
        # Links de download
        re.compile(r'https?://[^\s]*download[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*\.(pdf|xml)[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*baixar[^\s]*', re.IGNORECASE),
        re.compile(r'https?://[^\s]*visualizar[^\s]*', re.IGNORECASE),
    ]

    # Regex para códigos de autenticação/verificação
    REGEX_CODIGOS = [
        # Códigos explícitos
        (re.compile(r'[Cc]ódigo\s*(?:de\s+)?(?:autenticação|verificação|acesso|validação)[:\s]+([A-Z0-9\-]{4,30})', re.IGNORECASE), 'autenticacao'),
        (re.compile(r'[Cc]ódigo\s*[:\s]+([A-Z0-9\-]{6,30})\b', re.IGNORECASE), 'generico'),
        (re.compile(r'[Cc]ód\.?\s*[:\s]+([A-Z0-9\-]{6,30})\b', re.IGNORECASE), 'generico'),
        # Chave de acesso NFe (44 dígitos)
        (re.compile(r'\b(\d{44})\b'), 'chave_nfe'),
        # Códigos de verificação de prefeituras
        (re.compile(r'[Vv]erificação[:\s]+([A-Z0-9\-]{4,20})', re.IGNORECASE), 'verificacao'),
        (re.compile(r'[Aa]utenticidade[:\s]+([A-Z0-9\-]{4,20})', re.IGNORECASE), 'autenticidade'),
        # Token em URL
        (re.compile(r'token[=:]\s*([A-Za-z0-9\-_]{8,})', re.IGNORECASE), 'token'),
        # Senha/PIN
        (re.compile(r'[Ss]enha\s*(?:de\s+)?(?:acesso)?[:\s]+([A-Z0-9\-]{4,20})', re.IGNORECASE), 'senha'),
        (re.compile(r'PIN[:\s]+([0-9]{4,8})', re.IGNORECASE), 'pin'),
        # Protocolo
        (re.compile(r'[Pp]rotocolo[:\s]+([A-Z0-9\-\/]{6,30})', re.IGNORECASE), 'protocolo'),
        # Número de série/autenticação longo
        (re.compile(r'\b([A-Z0-9]{8,12}[\-\.][A-Z0-9]{4,}[\-\.][A-Z0-9]{4,})\b'), 'serie'),
    ]

    # Regex para números de nota/fatura
    REGEX_NUMEROS = [
        re.compile(r'[Nn]ota\s*[Ff]iscal\s*(?:n[ºo°]?\.?\s*)?[:\s]*(\d{3,15})', re.IGNORECASE),
        re.compile(r'NF[Ss]?[Ee]?\s*(?:n[ºo°]?\.?\s*)?[:\s]*(\d{3,15})', re.IGNORECASE),
        re.compile(r'[Ff]atura\s*(?:n[ºo°]?\.?\s*)?[:\s]*(\d{3,15})', re.IGNORECASE),
        re.compile(r'[Dd]ocumento\s*(?:n[ºo°]?\.?\s*)?[:\s]*(\d{3,15})', re.IGNORECASE),
        re.compile(r'n[ºo°]\.?\s*[:\s]*(\d{4,10})\b', re.IGNORECASE),
    ]

    # Palavras-chave para contexto
    KEYWORDS_NF = ['nota fiscal', 'nf-e', 'nfse', 'nfs-e', 'danfe', 'xml', 'nota eletrônica']
    KEYWORDS_BOLETO = ['boleto', 'fatura', 'cobrança', 'pagamento', 'vencimento']
    KEYWORDS_DOWNLOAD = ['download', 'baixar', 'clique', 'acesse', 'visualizar', 'acessar']
    KEYWORDS_PORTAL = ['portal', 'sistema', 'plataforma', 'site', 'acesso']
    KEYWORDS_PREFEITURA = ['prefeitura', 'município', 'secretaria', 'fazenda', 'issqn', 'iss']

    def __init__(self, host: str, user: str, password: str, folder: str = "INBOX"):
        self.host = host
        self.user = user
        self.password = password
        self.folder = folder
        self.connection = None

    def connect(self) -> None:
        """Estabelece conexão SSL com o servidor IMAP."""
        self.connection = imaplib.IMAP4_SSL(self.host)
        self.connection.login(self.user, self.password)
        self.connection.select(self.folder)
        print(f"✅ Conectado a {self.host} - Pasta: {self.folder}")

    def _decode_text(self, text: str) -> str:
        """Decodifica cabeçalhos de e-mail."""
        if not text:
            return ""

        decoded_list = decode_header(text)
        final_text = ""

        for content, encoding in decoded_list:
            if isinstance(content, bytes):
                encoding = encoding or "utf-8"
                try:
                    final_text += content.decode(encoding, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    final_text += content.decode("latin-1", errors="replace")
            else:
                final_text += str(content)

        return final_text

    def _has_valid_attachment(self, msg: Message) -> bool:
        """Verifica se o e-mail tem anexo PDF ou XML."""
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if filename:
                filename_decoded = self._decode_text(filename).lower()
                if any(filename_decoded.endswith(ext) for ext in self.VALID_EXTENSIONS):
                    return True
        return False

    def _extract_body(self, msg: Message) -> Tuple[str, str]:
        """Extrai corpo do e-mail (texto e HTML)."""
        body_text = ""
        body_html = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue

                    charset = part.get_content_charset() or 'utf-8'
                    decoded = payload.decode(charset, errors='replace')

                    if content_type == "text/plain":
                        body_text += decoded
                    elif content_type == "text/html":
                        body_html += decoded
                except Exception:
                    pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    decoded = payload.decode(charset, errors='replace')

                    if msg.get_content_type() == "text/plain":
                        body_text = decoded
                    else:
                        body_html = decoded
            except Exception:
                pass

        return body_text, body_html

    def _extract_sender_info(self, msg: Message) -> Dict[str, str]:
        """Extrai informações do remetente."""
        from_header = msg.get("From", "")
        decoded_from = self._decode_text(from_header)

        sender_name = ""
        sender_address = ""

        if "<" in decoded_from and ">" in decoded_from:
            parts = decoded_from.rsplit("<", 1)
            sender_name = parts[0].strip().strip('"\'')
            sender_address = parts[1].rstrip(">").strip()
        else:
            sender_address = decoded_from.strip()

        return {"name": sender_name, "address": sender_address}

    def _analyze_email(self, msg: Message, email_id: str, empresa_detector: EmpresaDetector) -> EmailAnalysis:
        """Analisa um e-mail e extrai informações relevantes."""
        subject = self._decode_text(msg.get("Subject", ""))
        sender_info = self._extract_sender_info(msg)
        body_text, body_html = self._extract_body(msg)
        received_date = msg.get("Date", "")

        analysis = EmailAnalysis(
            email_id=email_id,
            subject=subject,
            sender_name=sender_info['name'],
            sender_address=sender_info['address'],
            received_date=received_date,
            body_text=body_text[:5000],  # Limita tamanho
            body_html=body_html[:5000] if body_html else "",
        )

        # Texto combinado para análise
        full_text = f"{subject} {body_text} {body_html}".lower()
        full_text_original = f"{subject} {body_text} {body_html}"

        # === DETECTA EMPRESA ===
        empresa, metodo, matches = empresa_detector.detectar(full_text_original)
        analysis.empresa_detectada = empresa
        analysis.empresa_metodo = metodo
        analysis.empresa_matches = matches

        # Extrai todos os links
        all_links = self.REGEX_URL.findall(f"{body_text} {body_html}")
        analysis.links_encontrados = list(set(all_links))

        # Classifica links
        for link in all_links:
            link_lower = link.lower()

            # Links de NF-e
            if any(kw in link_lower for kw in ['nf', 'nota', 'danfe', 'xml']):
                analysis.links_nfe.append(link)

            # Links de prefeitura
            if any(kw in link_lower for kw in ['prefeitura', 'gov.br', 'issnet', 'ginfes', 'betha']):
                analysis.links_prefeitura.append(link)

            # Links de download
            if any(kw in link_lower for kw in ['download', 'baixar', '.pdf', '.xml', 'visualizar']):
                analysis.links_download.append(link)

        # Remove duplicatas mantendo ordem
        analysis.links_nfe = list(dict.fromkeys(analysis.links_nfe))
        analysis.links_prefeitura = list(dict.fromkeys(analysis.links_prefeitura))
        analysis.links_download = list(dict.fromkeys(analysis.links_download))

        # Extrai códigos
        for regex, tipo in self.REGEX_CODIGOS:
            matches = regex.findall(f"{subject} {body_text}")
            for match in matches:
                if match and len(match) >= 4:
                    analysis.codigos_encontrados.append(f"{tipo}: {match}")

                    if tipo in ['autenticacao', 'verificacao', 'autenticidade']:
                        analysis.codigos_autenticacao.append(match)
                    elif tipo == 'verificacao':
                        analysis.codigos_verificacao.append(match)

        # Remove duplicatas
        analysis.codigos_encontrados = list(dict.fromkeys(analysis.codigos_encontrados))
        analysis.codigos_autenticacao = list(dict.fromkeys(analysis.codigos_autenticacao))
        analysis.codigos_verificacao = list(dict.fromkeys(analysis.codigos_verificacao))

        # Extrai números de nota
        for regex in self.REGEX_NUMEROS:
            matches = regex.findall(f"{subject} {body_text}")
            analysis.numeros_nota.extend(matches)
        analysis.numeros_nota = list(dict.fromkeys(analysis.numeros_nota))

        # Analisa contexto
        analysis.menciona_nf = any(kw in full_text for kw in self.KEYWORDS_NF)
        analysis.menciona_boleto = any(kw in full_text for kw in self.KEYWORDS_BOLETO)
        analysis.menciona_download = any(kw in full_text for kw in self.KEYWORDS_DOWNLOAD)
        analysis.menciona_portal = any(kw in full_text for kw in self.KEYWORDS_PORTAL)
        analysis.menciona_prefeitura = any(kw in full_text for kw in self.KEYWORDS_PREFEITURA)

        # Classifica tipo do e-mail
        if analysis.links_download or analysis.links_nfe:
            if analysis.codigos_autenticacao or analysis.codigos_verificacao:
                analysis.tipo_email = "LINK_COM_CODIGO"
            else:
                analysis.tipo_email = "LINK_DOWNLOAD"
        elif analysis.codigos_autenticacao or analysis.codigos_verificacao:
            analysis.tipo_email = "CODIGO_VERIFICACAO"
        elif analysis.links_prefeitura:
            analysis.tipo_email = "PORTAL_PREFEITURA"
        elif analysis.menciona_nf or analysis.menciona_boleto:
            analysis.tipo_email = "INFORMATIVO_NF"
        else:
            analysis.tipo_email = "OUTROS"

        return analysis

    def fetch_emails_without_attachments(
        self,
        subject_filter: str = "ENC",
        limit: int = 100
    ) -> List[EmailAnalysis]:
        """
        Busca e analisa e-mails SEM anexos PDF/XML.

        Args:
            subject_filter: Filtro de assunto
            limit: Máximo de e-mails a analisar

        Returns:
            Lista de análises de e-mails
        """
        if not self.connection:
            self.connect()

        # Cria detector de empresa
        empresa_detector = EmpresaDetector()

        # Busca e-mails pelo assunto
        status, messages = self.connection.search(None, f'(SUBJECT "{subject_filter}")')

        results = []
        count = 0
        skipped = 0

        if not messages or messages[0] == b'':
            print("⚠️ Nenhum e-mail encontrado com o filtro especificado.")
            return results

        email_ids = messages[0].split()
        print(f"📧 {len(email_ids)} e-mails encontrados com filtro '{subject_filter}'")

        for num in email_ids:
            if count >= limit:
                break

            try:
                _, msg_data = self.connection.fetch(num, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue

                msg = message_from_bytes(msg_data[0][1])

                # Pula e-mails COM anexos válidos
                if self._has_valid_attachment(msg):
                    skipped += 1
                    continue

                # Gera ID único
                message_id = msg.get("Message-ID", "")
                if message_id:
                    email_id = message_id.strip("<>").replace("@", "_").replace(".", "_")[:50]
                else:
                    email_id = f"email_{num.decode('utf-8')}"

                # Analisa o e-mail
                analysis = self._analyze_email(msg, email_id, empresa_detector)
                results.append(analysis)
                count += 1

                # Log de progresso
                if count % 10 == 0:
                    empresa_info = f" | Empresa: {analysis.empresa_detectada or 'N/A'}"
                    print(f"   Analisados: {count}/{limit} | Tipo: {analysis.tipo_email}{empresa_info}")

            except Exception as e:
                print(f"⚠️ Erro ao processar e-mail {num}: {e}")
                continue

        print(f"\n✅ Análise concluída:")
        print(f"   - E-mails sem anexo analisados: {count}")
        print(f"   - E-mails com anexo (ignorados): {skipped}")

        return results


def generate_report(analyses: List[EmailAnalysis]) -> Dict[str, Any]:
    """Gera relatório consolidado das análises."""

    report = {
        "total_emails": len(analyses),
        "data_analise": datetime.now().isoformat(),

        # Contadores por tipo
        "por_tipo": defaultdict(int),

        # Estatísticas de links
        "emails_com_links": 0,
        "emails_com_links_nfe": 0,
        "emails_com_links_prefeitura": 0,
        "emails_com_links_download": 0,

        # Estatísticas de códigos
        "emails_com_codigos": 0,
        "emails_com_codigos_autenticacao": 0,

        # Domínios mais comuns nos links
        "dominios_links": defaultdict(int),

        # Padrões de código encontrados
        "tipos_codigos": defaultdict(int),

        # === ESTATÍSTICAS DE DETECÇÃO DE EMPRESA ===
        "empresas_detectadas": defaultdict(int),
        "empresas_por_metodo": defaultdict(int),
        "emails_sem_empresa": 0,
        "exemplos_deteccao": [],
        "exemplos_sem_deteccao": [],

        # Exemplos relevantes
        "exemplos_link_download": [],
        "exemplos_codigo_verificacao": [],
        "exemplos_prefeitura": [],

        # Emails para revisão manual
        "emails_detalhados": [],
    }

    for analysis in analyses:
        # Contagem por tipo
        report["por_tipo"][analysis.tipo_email] += 1

        # === ESTATÍSTICAS DE EMPRESA ===
        if analysis.empresa_detectada:
            report["empresas_detectadas"][analysis.empresa_detectada] += 1
            report["empresas_por_metodo"][analysis.empresa_metodo or "desconhecido"] += 1

            # Exemplos de detecção (máximo 10)
            if len(report["exemplos_deteccao"]) < 10:
                report["exemplos_deteccao"].append({
                    "subject": analysis.subject[:80],
                    "empresa": analysis.empresa_detectada,
                    "metodo": analysis.empresa_metodo,
                    "matches": analysis.empresa_matches[:5],
                    "body_preview": analysis.body_text[:3000],
                    "html_preview": analysis.body_html[:500] if analysis.body_html else "",
                })
        else:
            report["emails_sem_empresa"] += 1

            # Exemplos sem detecção (máximo 10)
            if len(report["exemplos_sem_deteccao"]) < 10:
                report["exemplos_sem_deteccao"].append({
                    "subject": analysis.subject[:80],
                    "matches_tentados": analysis.empresa_matches[:5],
                    "body_preview": analysis.body_text[:3000],
                    "html_preview": analysis.body_html[:1000] if analysis.body_html else "",
                })

        # Links
        if analysis.links_encontrados:
            report["emails_com_links"] += 1
        if analysis.links_nfe:
            report["emails_com_links_nfe"] += 1
        if analysis.links_prefeitura:
            report["emails_com_links_prefeitura"] += 1
        if analysis.links_download:
            report["emails_com_links_download"] += 1

        # Códigos
        if analysis.codigos_encontrados:
            report["emails_com_codigos"] += 1
        if analysis.codigos_autenticacao:
            report["emails_com_codigos_autenticacao"] += 1

        # Extrai domínios dos links
        for link in analysis.links_encontrados:
            try:
                # Extrai domínio
                match = re.search(r'https?://([^/]+)', link)
                if match:
                    domain = match.group(1).lower()
                    report["dominios_links"][domain] += 1
            except Exception:
                pass

        # Tipos de código
        for cod in analysis.codigos_encontrados:
            tipo = cod.split(":")[0] if ":" in cod else "desconhecido"
            report["tipos_codigos"][tipo] += 1

        # Coleta exemplos (máximo 5 de cada)
        if analysis.tipo_email == "LINK_DOWNLOAD" and len(report["exemplos_link_download"]) < 5:
            report["exemplos_link_download"].append({
                "subject": analysis.subject[:100],
                "sender": analysis.sender_address,
                "links": analysis.links_download[:3],
            })

        if analysis.tipo_email == "CODIGO_VERIFICACAO" and len(report["exemplos_codigo_verificacao"]) < 5:
            report["exemplos_codigo_verificacao"].append({
                "subject": analysis.subject[:100],
                "sender": analysis.sender_address,
                "codigos": analysis.codigos_autenticacao[:3],
            })

        if analysis.links_prefeitura and len(report["exemplos_prefeitura"]) < 5:
            report["exemplos_prefeitura"].append({
                "subject": analysis.subject[:100],
                "sender": analysis.sender_address,
                "links": analysis.links_prefeitura[:3],
            })

        # Adiciona detalhes do email (resumido)
        report["emails_detalhados"].append({
            "email_id": analysis.email_id,
            "subject": analysis.subject[:100],
            "sender": analysis.sender_address,
            "tipo": analysis.tipo_email,
            "empresa_detectada": analysis.empresa_detectada,
            "empresa_metodo": analysis.empresa_metodo,
            "tem_links_nfe": len(analysis.links_nfe) > 0,
            "tem_links_download": len(analysis.links_download) > 0,
            "tem_codigos": len(analysis.codigos_encontrados) > 0,
            "links_exemplo": (analysis.links_download or analysis.links_nfe or analysis.links_encontrados)[:2],
            "codigos_exemplo": analysis.codigos_encontrados[:2],
        })

    # Converte defaultdicts para dicts normais
    report["por_tipo"] = dict(report["por_tipo"])
    report["dominios_links"] = dict(sorted(report["dominios_links"].items(), key=lambda x: x[1], reverse=True)[:20])
    report["tipos_codigos"] = dict(report["tipos_codigos"])
    report["empresas_detectadas"] = dict(sorted(report["empresas_detectadas"].items(), key=lambda x: x[1], reverse=True))
    report["empresas_por_metodo"] = dict(report["empresas_por_metodo"])

    return report


def print_summary(report: Dict[str, Any]) -> None:
    """Imprime resumo do relatório."""

    print("\n" + "=" * 70)
    print("📊 RELATÓRIO DE ANÁLISE - E-MAILS SEM ANEXO")
    print("=" * 70)

    print(f"\n📧 Total de e-mails analisados: {report['total_emails']}")
    print(f"📅 Data da análise: {report['data_analise']}")

    # === SEÇÃO DE DETECÇÃO DE EMPRESA (NOVA) ===
    print("\n" + "=" * 70)
    print("🏢 DETECÇÃO DE EMPRESA")
    print("=" * 70)

    total = report['total_emails']
    sem_empresa = report.get('emails_sem_empresa', 0)
    com_empresa = total - sem_empresa
    pct_com = (com_empresa / total * 100) if total > 0 else 0
    pct_sem = (sem_empresa / total * 100) if total > 0 else 0

    print(f"\n   ✅ Com empresa detectada: {com_empresa} ({pct_com:.1f}%)")
    print(f"   ❌ Sem empresa detectada: {sem_empresa} ({pct_sem:.1f}%)")

    if report.get("empresas_por_metodo"):
        print("\n   📊 Por método de detecção:")
        for metodo, count in report["empresas_por_metodo"].items():
            print(f"      - {metodo}: {count}")

    if report.get("empresas_detectadas"):
        print("\n   🏢 Empresas encontradas:")
        for empresa, count in list(report["empresas_detectadas"].items())[:15]:
            print(f"      - {empresa}: {count}")

    # Exemplos de detecção
    if report.get("exemplos_deteccao"):
        print("\n   ✅ EXEMPLOS DE DETECÇÃO BEM-SUCEDIDA:")
        print("   " + "-" * 60)
        for ex in report["exemplos_deteccao"][:5]:
            print(f"\n   📧 {ex['subject']}")
            print(f"      Empresa: {ex['empresa']} (via {ex['metodo']})")
            print(f"      Matches: {ex['matches']}")
            if ex.get('body_preview'):
                preview = ex['body_preview'].replace('\n', ' ')[:100]
                print(f"      Preview: {preview}...")

    # Exemplos sem detecção
    if report.get("exemplos_sem_deteccao"):
        print("\n   ❌ EXEMPLOS SEM DETECÇÃO (para análise):")
        print("   " + "-" * 60)
        for ex in report["exemplos_sem_deteccao"][:5]:
            print(f"\n   📧 {ex['subject']}")
            print(f"      Matches tentados: {ex.get('matches_tentados', [])}")
            if ex.get('body_preview'):
                preview = ex['body_preview'].replace('\n', ' ')[:150]
                print(f"      Preview: {preview}...")

    print("\n" + "=" * 70)

    print("\n📋 DISTRIBUIÇÃO POR TIPO:")
    print("-" * 40)
    for tipo, count in sorted(report["por_tipo"].items(), key=lambda x: x[1], reverse=True):
        pct = (count / report['total_emails'] * 100) if report['total_emails'] > 0 else 0
        print(f"   {tipo}: {count} ({pct:.1f}%)")

    print("\n🔗 ESTATÍSTICAS DE LINKS:")
    print("-" * 40)
    print(f"   Com links (qualquer): {report['emails_com_links']}")
    print(f"   Com links NF-e: {report['emails_com_links_nfe']}")
    print(f"   Com links prefeitura: {report['emails_com_links_prefeitura']}")
    print(f"   Com links download: {report['emails_com_links_download']}")

    print("\n🔑 ESTATÍSTICAS DE CÓDIGOS:")
    print("-" * 40)
    print(f"   Com códigos (qualquer): {report['emails_com_codigos']}")
    print(f"   Com código autenticação: {report['emails_com_codigos_autenticacao']}")

    if report["tipos_codigos"]:
        print("\n   Tipos de código encontrados:")
        for tipo, count in report["tipos_codigos"].items():
            print(f"      - {tipo}: {count}")

    print("\n🌐 DOMÍNIOS MAIS FREQUENTES:")
    print("-" * 40)
    for domain, count in list(report["dominios_links"].items())[:10]:
        print(f"   {domain}: {count}")

    if report["exemplos_link_download"]:
        print("\n📥 EXEMPLOS - LINKS DE DOWNLOAD:")
        print("-" * 40)
        for ex in report["exemplos_link_download"][:3]:
            print(f"   Assunto: {ex['subject']}")
            print(f"   De: {ex['sender']}")
            print(f"   Links: {ex['links']}")
            print()

    if report["exemplos_codigo_verificacao"]:
        print("\n🔐 EXEMPLOS - CÓDIGOS DE VERIFICAÇÃO:")
        print("-" * 40)
        for ex in report["exemplos_codigo_verificacao"][:3]:
            print(f"   Assunto: {ex['subject']}")
            print(f"   De: {ex['sender']}")
            print(f"   Códigos: {ex['codigos']}")
            print()

    if report["exemplos_prefeitura"]:
        print("\n🏛️ EXEMPLOS - PREFEITURAS:")
        print("-" * 40)
        for ex in report["exemplos_prefeitura"][:3]:
            print(f"   Assunto: {ex['subject']}")
            print(f"   De: {ex['sender']}")
            print(f"   Links: {ex['links']}")
            print()

    print("\n" + "=" * 70)
    print("💡 SUGESTÕES DE REGEX BASEADAS NA ANÁLISE:")
    print("=" * 70)

    # Sugere regex com base nos domínios encontrados
    print("\n🔗 Para links de NF-e/download:")
    dominios_nfe = [d for d in report["dominios_links"].keys()
                   if any(kw in d.lower() for kw in ['nf', 'nota', 'prefeitura', 'gov', 'issnet', 'ginfes'])]
    if dominios_nfe:
        print(f"   Domínios detectados: {', '.join(dominios_nfe[:5])}")
        print(f"   Regex sugerida: r'https?://[^\\s]*({'|'.join(dominios_nfe[:3])})[^\\s]*'")

    print("\n🔑 Para códigos de autenticação:")
    if report["tipos_codigos"]:
        print(f"   Tipos detectados: {', '.join(report['tipos_codigos'].keys())}")
        print("   Regex sugeridas:")
        print("     - r'[Cc]ódigo[:\\s]+([A-Z0-9\\-]{6,30})'")
        print("     - r'[Vv]erificação[:\\s]+([A-Z0-9\\-]{4,20})'")
        print("     - r'token[=:][\\s]*([A-Za-z0-9\\-_]{8,})'")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Analisa e-mails sem anexo para identificar padrões de links e códigos'
    )
    parser.add_argument(
        '--subject',
        type=str,
        default='ENC',
        help='Filtro de assunto (default: ENC)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Máximo de e-mails a analisar (default: 100)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Arquivo JSON para salvar relatório completo'
    )

    args = parser.parse_args()

    # Verifica configuração
    if not settings.EMAIL_PASS:
        print("❌ Erro: Configure as credenciais de e-mail no arquivo .env")
        print("   EMAIL_HOST, EMAIL_USER, EMAIL_PASS")
        return

    print("🔍 Iniciando análise de e-mails sem anexo...")
    print(f"   Servidor: {settings.EMAIL_HOST}")
    print(f"   Usuário: {settings.EMAIL_USER}")
    print(f"   Filtro: '{args.subject}'")
    print(f"   Limite: {args.limit}")
    print()

    # Cria analisador e conecta
    analyzer = EmailAnalyzer(
        host=settings.EMAIL_HOST,
        user=settings.EMAIL_USER,
        password=settings.EMAIL_PASS,
        folder=settings.EMAIL_FOLDER
    )

    try:
        # Busca e analisa e-mails
        analyses = analyzer.fetch_emails_without_attachments(
            subject_filter=args.subject,
            limit=args.limit
        )

        if not analyses:
            print("\n⚠️ Nenhum e-mail sem anexo encontrado.")
            return

        # Gera relatório
        report = generate_report(analyses)

        # Imprime resumo
        print_summary(report)

        # Salva JSON se solicitado
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            print(f"\n💾 Relatório completo salvo em: {output_path}")

        # Sempre salva um arquivo padrão
        default_output = Path("data/output/analise_emails_sem_anexo.json")
        default_output.parent.mkdir(parents=True, exist_ok=True)

        with open(default_output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"💾 Relatório salvo em: {default_output}")

    except Exception as e:
        print(f"\n❌ Erro durante análise: {e}")
        raise


if __name__ == "__main__":
    main()
