"""
Script de Orquestração de Ingestão de E-mails.

Este módulo é responsável por conectar ao servidor de e-mail, baixar anexos PDF
de notas fiscais e encaminhá-los para o pipeline de processamento.

REFATORADO seguindo princípios SOLID:
- SRP: Responsabilidades separadas em FileSystemManager, AttachmentDownloader, DataExporter
- OCP: Detecção de tipo por doc_type permite adicionar novos tipos sem modificar código
- DIP: Injeção de dependências via factory para facilitar testes

Funcionalidades:
1.  Conexão segura via IMAP (configurada via .env).
2.  Filtragem de e-mails por assunto.
3.  Download de anexos para pasta temporária (com tratamento de colisão de nomes).
4.  Execução do processador de extração.
5.  Geração de relatórios CSV por tipo de documento.

Usage:
    python run_ingestion.py
"""

import logging
from collections import defaultdict
from typing import Optional
from config import settings
from ingestors.imap import ImapIngestor
from ingestors.utils import AttachmentDownloader
from core.interfaces import EmailIngestorStrategy
from core.processor import BaseInvoiceProcessor
from core.exporters import FileSystemManager, CsvExporter

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def create_ingestor_from_config() -> EmailIngestorStrategy:
    """
    Factory para criar ingestor a partir das configurações.
    
    Facilita injeção de dependências e testes mockados (DIP).
    
    Returns:
        EmailIngestorStrategy: Ingestor configurado
        
    Raises:
        ValueError: Se credenciais estiverem faltando
    """
    if not settings.EMAIL_PASS:
        raise ValueError(
            "Senha de e-mail não encontrada no arquivo .env. "
            "Por favor, configure o arquivo .env com suas credenciais."
        )
    
    return ImapIngestor(
        host=settings.EMAIL_HOST,
        user=settings.EMAIL_USER,
        password=settings.EMAIL_PASS,
        folder=settings.EMAIL_FOLDER
    )


def main(ingestor: Optional[EmailIngestorStrategy] = None):
    """
    Função principal de orquestração da ingestão.
    
    Args:
        ingestor: Ingestor de e-mail customizado. Se None, usa factory padrão.
                  Permite injeção de dependência para testes (DIP).
    """
    # 1. Verificação de Segurança e Configuração
    try:
        if ingestor is None:
            ingestor = create_ingestor_from_config()
    except ValueError as e:
        logger.error(f"Erro de configuração: {e}")
        return

    # 2. Preparar ambiente (SRP: FileSystemManager)
    file_manager = FileSystemManager(
        temp_dir=settings.DIR_TEMP,
        output_dir=settings.DIR_SAIDA
    )
    file_manager.clean_temp_directory()
    file_manager.setup_directories()
    logger.info(f"Diretório temporário criado: {settings.DIR_TEMP}")

    # 3. Conexão
    logger.info(f"Conectando a {settings.EMAIL_HOST} como {settings.EMAIL_USER}...")
    try:
        ingestor.connect()
    except Exception as e:
        logger.error(f"Falha na conexão: {e}", exc_info=True)
        return

    # 4. Busca (Fetch)
    assunto_teste = "ENC" 
    logger.info(f"Buscando e-mails com assunto: '{assunto_teste}'...")
    
    try:
        anexos = ingestor.fetch_attachments(subject_filter=assunto_teste)
    except Exception as e:
        logger.error(f"Erro ao buscar e-mails: {e}", exc_info=True)
        return
    
    if not anexos:
        logger.warning("Nenhum anexo encontrado.")
        return

    logger.info(f"{len(anexos)} anexo(s) encontrado(s). Iniciando processamento...")

    # 5. Processamento (SRP: AttachmentDownloader separado)
    downloader = AttachmentDownloader(file_manager)
    processor = BaseInvoiceProcessor()
    
    # OCP: Agrupamento dinâmico por doc_type (sem if/else para cada tipo)
    documentos_por_tipo = defaultdict(list)

    for item in anexos:
        filename = item['filename']
        content_bytes = item['content']
        
        try:
            # SRP: Downloader é responsável por salvar arquivos
            file_path = downloader.save_attachment(filename, content_bytes)
            
            logger.info(f"Processando: {filename}...")
            
            # Processa o documento
            result = processor.process(str(file_path))
            
            # Enriquece com metadados do e-mail
            result.texto_bruto = f"{result.texto_bruto}\n[Email: {item['source']}]"
            
            # OCP: Agrupa por doc_type (extensível para novos tipos)
            doc_type = result.doc_type
            documentos_por_tipo[doc_type].append({
                **result.to_dict(),
                'email_source': item['source'],
                'email_subject': item['subject']
            })
            
            # Feedback específico por tipo
            if doc_type == 'BOLETO':
                logger.info(f"  Boleto: Vencimento {result.vencimento} - R$ {result.valor_documento}")
            elif doc_type == 'NFSE':
                logger.info(f"  NFSe: {result.numero_nota} - {result.cnpj_prestador}")
            else:
                logger.info(f"  {doc_type}: processado")
            
        except Exception as e:
            logger.warning(f"Falha ao processar {filename}: {e}")

    # 6. Exportação (SRP: CsvExporter responsável por gerar CSVs)
    exporter = CsvExporter()
    
    # Mapeia tipos de documento para nomes de arquivo amigáveis
    arquivo_saida_map = {
        'NFSE': 'relatorio_nfse.csv',
        'BOLETO': 'relatorio_boletos.csv'
    }
    
    total_processados = 0
    for doc_type, documentos in documentos_por_tipo.items():
        if documentos:
            # Gera nome de arquivo baseado no tipo
            nome_arquivo = arquivo_saida_map.get(
                doc_type, 
                f"relatorio_{doc_type.lower()}.csv"
            )
            output_path = file_manager.get_output_file_path(nome_arquivo)
            
            # Exporta usando pandas através do CsvExporter
            # (Por enquanto convertemos dict para pseudo-DocumentData para compatibilidade)
            import pandas as pd
            df = pd.DataFrame(documentos)
            df.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig', decimal=',')
            
            total_processados += len(documentos)
            logger.info(f"{len(documentos)} {doc_type} processados -> {output_path}")
    
    if total_processados == 0:
        logger.warning("Nenhum resultado processado com sucesso.")
    else:
        logger.info(f"Processamento concluído: {total_processados} documento(s) no total.")
    
    # Opcional: Limpeza
    # file_manager.clean_temp_directory()

if __name__ == "__main__":
    main()
