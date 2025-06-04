import sys
import os
import logging
import warnings
from datetime import datetime
from loguru import logger
import uvicorn

# Suprimir o aviso específico do PyTorch
warnings.filterwarnings("ignore", message=".*'pin_memory' argument is set as true but not supported on MPS.*")

# Cores para diferentes níveis de log
LOG_COLORS = {
    "TRACE": "<dim>",
    "DEBUG": "<blue>",
    "INFO": "<green>",
    "SUCCESS": "<green><bold>",
    "WARNING": "<yellow>",
    "ERROR": "<red>",
    "CRITICAL": "<red><bold>",
}

class InterceptHandler(logging.Handler):
    """
    Intercepta logs padrão do Python e os redireciona para o Loguru.
    Isso permite que bibliotecas como Uvicorn e PyTorch usem o formato Loguru.
    """
    def emit(self, record):
        # Obter o nível correspondente do Loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Encontrar a origem do log
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Verificar se é um aviso de PyTorch que queremos suprimir
        if record.levelname == "WARNING" and "pin_memory" in record.getMessage() and "MPS" in record.getMessage():
            return  # Suprimir este aviso específico
            
        # Enviar para o Loguru
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

class LoguruConfig:
    """Configuração centralizada do Loguru para todo o projeto."""
    
    @staticmethod
    def setup(log_file="./logs/document_extractor.log", console_level="INFO", file_level="DEBUG", intercept_libraries=True):
        """
        Configura o sistema de logging com Loguru
        
        Args:
            log_file: Caminho para arquivo de log
            console_level: Nível de log para o console
            file_level: Nível de log para o arquivo
            intercept_libraries: Se True, intercepta logs de outras bibliotecas
        """
        # Certifica que o diretório de logs existe
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Remove handlers padrão
        logger.remove()
        
        # Adiciona handler para console com cores personalizadas
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        
        logger.add(
            sys.stdout, 
            format=console_format, 
            level=console_level,
            colorize=True,
            enqueue=True  # Thread-safe
        )
        
        # Adiciona handler para arquivo com rotação de 10MB
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{line} | "
            "{message}"
        )
        
        logger.add(
            log_file,
            format=file_format,
            level=file_level,
            rotation="10 MB",  # Rotaciona ao atingir 10MB
            compression="zip",  # Comprime arquivos antigos
            retention=5,       # Mantém 5 arquivos de backup
            enqueue=True       # Thread-safe
        )
        
        # Intercepta logs padrão de outras bibliotecas
        if intercept_libraries:
            # Configurar handler para logging padrão
            logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
            
            # Interceptar logs específicos
            for logger_name in [
                "uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", 
                "torch", "docling", "langchain", "azure"
            ]:
                lib_logger = logging.getLogger(logger_name)
                lib_logger.handlers = [InterceptHandler()]
                lib_logger.propagate = False
                lib_logger.level = logging.INFO
        
        logger.success("Sistema de logging unificado inicializado com sucesso!")
    
    @staticmethod
    def configure_uvicorn():
        """Configura o Uvicorn para usar formato consistente com o projeto"""
        log_config = uvicorn.config.LOGGING_CONFIG
        
        # Definir formatos consistentes
        log_format = "%(asctime)s | %(levelprefix)s | %(message)s"
        log_config["formatters"]["default"]["fmt"] = log_format
        log_config["formatters"]["access"]["fmt"] = log_format
        
        # Ajustar formato de data para consistência
        date_format = "%Y-%m-%d %H:%M:%S.%f"
        log_config["formatters"]["default"]["datefmt"] = date_format
        log_config["formatters"]["access"]["datefmt"] = date_format
        
        return log_config
    
    @staticmethod
    def get_logger(name):
        """
        Obtém um logger contextualizado para um módulo específico
        
        Args:
            name: Nome do módulo (geralmente __name__)
            
        Returns:
            Logger do Loguru contextualizado
        """
        # Loguru não suporta getLogger como o módulo logging padrão,
        # mas podemos usar os contextos para criar uma experiência similar
        context_logger = logger.bind(name=name)
        return context_logger

# Função de conveniência para obter um logger em qualquer arquivo
def get_logger(name=None):
    """
    Obtém um logger contextualizado, identificando automaticamente o nome do módulo
    se não for fornecido.
    """
    module = name or sys._getframe(1).f_globals.get('__name__', 'unknown')
    return LoguruConfig.get_logger(module)