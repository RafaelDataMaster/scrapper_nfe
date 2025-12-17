class ScrapperException(Exception):
    """Exceção base para o projeto Scrapper NFe."""
    pass

class ExtractionError(ScrapperException):
    """Levantada quando falha a extração de texto de um arquivo."""
    pass

class IngestionError(ScrapperException):
    """Levantada quando falha a conexão ou download de e-mails."""
    pass
