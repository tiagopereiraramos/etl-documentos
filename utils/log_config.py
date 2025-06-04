import sys
import os
import logging
import warnings
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import uvicorn
from loguru import logger

# Suprimir o aviso específico do PyTorch sobre pin_memory no MPS
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
    Isso faz com que bibliotecas como Uvicorn usem o formato Loguru.
    """
    def emit(self, record):
        # Obter o nível correspondente do Loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Encontrar o origem do log
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Enviar para o Loguru
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

class LoguruConfig:
    """Configuração centralizada do Loguru para todo o projeto."""
    
    @staticmethod
    def setup(log_file="./logs/application.log", console_level="INFO", file_level="DEBUG", 
              intercept_standard_logging=True, log_format=None):
        """
        Configura o sistema de logging com Loguru
        
        Args:
            log_file: Caminho para arquivo de log
            console_level: Nível de log para o console
            file_level: Nível de log para o arquivo
            intercept_standard_logging: Se True, intercepta logs padrão do Python (como Uvicorn)
            log_format: Formato personalizado para os logs (se None, usa o formato padrão)
        """
        # Certifica que o diretório de logs existe
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Remove handlers padrão
        logger.remove()
        
        # Formato padrão para console
        if not log_format:
            console_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            )
        else:
            console_format = log_format
        
        # Adiciona handler para console com cores
        logger.add(
            sys.stdout, 
            format=console_format, 
            level=console_level,
            colorize=True,
            enqueue=True
        )
        
        # Adiciona handler para arquivo com rotação
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        
        logger.add(
            log_file,
            format=file_format,
            level=file_level,
            rotation="10 MB",
            compression="zip",
            retention=5,
            enqueue=True
        )
        
        # Intercepta logs padrão do Python (incluindo Uvicorn)
        if intercept_standard_logging:
            # Configurar todos os loggers existentes para usar nosso handler
            for name in logging.root.manager.loggerDict:
                logging_logger = logging.getLogger(name)
                logging_logger.handlers = []
                logging_logger.propagate = True
                logging_logger.setLevel(console_level)
            
            # Configurar o logger root
            root_logger = logging.getLogger()
            root_logger.handlers = [InterceptHandler()]
            root_logger.setLevel(console_level)
            
            # Especifica os loggers que queremos interceptar
            for _log in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
                _logger = logging.getLogger(_log)
                _logger.handlers = [InterceptHandler()]
                _logger.propagate = False
        
        # Ajusta o nível dos loggers específicos
        for log_name in ["uvicorn", "uvicorn.error", "fastapi"]:
            logging.getLogger(log_name).setLevel(console_level)
        
        logger.success("Sistema de logging unificado inicializado com sucesso!")
    
    @staticmethod
    def configure_uvicorn_logging():
        """Configura o log do Uvicorn para ser consistente com o Loguru."""
        log_config = uvicorn.config.LOGGING_CONFIG
        log_config["formatters"]["default"]["fmt"] = "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
        log_config["formatters"]["access"]["fmt"] = "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
        log_config["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S.%f"
        log_config["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S.%f"
        return log_config

# Classe para logs especializados de documentos
class DocumentTracker:
    """Classe para tracking visual de processamento de documentos."""
    
    @staticmethod
    def log_processing_start(doc_id: str, doc_name: str, doc_type: str = None) -> None:
        """Log de início de processamento de um documento"""
        doc_type_str = f"| Tipo: {doc_type}" if doc_type else ""
        logger.info(f"🔄 INÍCIO PROCESSAMENTO | ID: {doc_id} | Documento: {doc_name} {doc_type_str}")
    
    @staticmethod
    def log_docling_processing(doc_id: str, doc_name: str, model_name: str = None, doc_type: str = None) -> None:
        """Log quando um documento é processado pelo Docling"""
        doc_type_str = f"| Tipo: {doc_type}" if doc_type else ""
        model_str = f"| Modelo: {model_name}" if model_name else ""
        logger.info(f"🟢 DOCLING LOCAL | ID: {doc_id} | Documento: {doc_name} {doc_type_str} {model_str}")
    
    @staticmethod
    def log_azure_processing(doc_id: str, doc_name: str, service_name: str = None, reason: str = None, doc_type: str = None) -> None:
        """Log quando um documento é processado pelo Azure"""
        doc_type_str = f"| Tipo: {doc_type}" if doc_type else ""
        service_str = f"| Serviço: {service_name}" if service_name else ""
        reason_str = f"| Motivo: {reason}" if reason else ""
        logger.warning(f"🔵 AZURE API | ID: {doc_id} | Documento: {doc_name} {doc_type_str} {service_str} {reason_str}")
    
    @staticmethod
    def log_fallback(doc_id: str, doc_name: str, from_method: str, to_method: str, reason: str) -> None:
        """Log de fallback entre métodos de processamento"""
        logger.warning(f"⚠️ FALLBACK | ID: {doc_id} | Documento: {doc_name} | De: {from_method} → Para: {to_method} | Motivo: {reason}")

# Função de conveniência para obter um logger em qualquer arquivo
def get_logger(name=None):
    """
    Obtém um logger contextualizado, identificando automaticamente o nome do módulo
    se não for fornecido.
    """
    module = name or sys._getframe(1).f_globals.get('__name__', 'unknown')
    return logger.bind(name=module)