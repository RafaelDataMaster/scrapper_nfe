import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any
from core.interfaces import EmailIngestorStrategy

class ImapIngestor(EmailIngestorStrategy):
    """
    Implementação de ingestão de e-mails via protocolo IMAP.

    Esta classe gerencia a conexão segura (SSL) com servidores de e-mail,
    realiza buscas filtradas por assunto e extrai anexos PDF.

    Attributes:
        host (str): Endereço do servidor IMAP (ex: imap.gmail.com).
        user (str): Usuário para autenticação.
        password (str): Senha ou App Password.
        folder (str): Pasta do e-mail a ser monitorada (Padrão: INBOX).
    """

    def __init__(self, host: str, user: str, password: str, folder: str = "INBOX"):
        self.host = host
        self.user = user
        self.password = password
        self.folder = folder
        self.connection = None

    def connect(self) -> None:
        """
        Estabelece conexão SSL com o servidor IMAP e realiza login.

        Raises:
            imaplib.IMAP4.error: Se houver falha na conexão ou autenticação.
        """
        # Conexão SSL padrão (Porta 993)
        self.connection = imaplib.IMAP4_SSL(self.host)
        self.connection.login(self.user, self.password)
        self.connection.select(self.folder) # Seleciona caixa de entrada

    def fetch_attachments(self, subject_filter: str = "Nota Fiscal") -> List[Dict[str, Any]]:
        """
        Busca e-mails pelo assunto e extrai anexos PDF.

        Args:
            subject_filter (str): Texto para filtrar o assunto dos e-mails.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários contendo:
                - filename (str): Nome do arquivo decodificado.
                - content (bytes): Conteúdo binário do arquivo.
                - source (str): E-mail de origem (usuário).
                - subject (str): Assunto do e-mail.
        """
        if not self.connection:
            self.connect()
            
        # Busca no servidor (Filtering Server-side é limitado no IMAP)
        # [cite: 21] IMAP search é verboso
        status, messages = self.connection.search(None, f'(SUBJECT "{subject_filter}")')
        
        results = []
        if not messages or messages[0] == b'':
            return results

        for num in messages[0].split():
            _, msg_data = self.connection.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            
            # Navegar pela árvore MIME para achar anexos [cite: 27]
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                    
                filename = part.get_filename()
                if filename and filename.lower().endswith('.pdf'):
                    # Decodificar nome do arquivo (ex: =?utf-8?Q?...) [cite: 26]
                    decoded_list = decode_header(filename)
                    filename = "".join([t[0].decode(t[1] or 'utf-8') if isinstance(t[0], bytes) else t[0] for t in decoded_list])
                    
                    results.append({
                        'filename': filename,
                        'content': part.get_payload(decode=True),
                        'source': self.user,
                        'subject': subject
                    })
        return results