"""
Sistema de logging centralizado para o ETL Documentos
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager
import time
import traceback

from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """Formatador para logs estruturados em JSON"""

    def format(self, record: logging.LogRecord) -> str:
        """Formata o log record em JSON estruturado"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "logger": record.name
        }

        # Adicionar campos extras se existirem
        for attr in ['operation', 'document_id', 'user_id', 'duration_ms', 'status', 'metadata']:
            if hasattr(record, attr):
                value = getattr(record, attr)
                if value is not None:
                    log_entry[attr] = value

        # Adicionar exceção se existir
        if record.exc_info and record.exc_info[0] is not None:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class CustomLogger:
    """Logger customizado com métodos para logs estruturados"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log com contexto adicional"""
        extra = {}
        for key, value in kwargs.items():
            if value is not None:
                extra[key] = value

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log de debug"""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log de informação"""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log de aviso"""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log de erro"""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log crítico"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def log_operation(self, operation: str, message: str,
                      document_id: Optional[str] = None, user_id: Optional[str] = None,
                      duration_ms: Optional[float] = None, status: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None, **kwargs):
        """Log estruturado para operações"""
        self.info(
            message,
            operation=operation,
            document_id=document_id,
            user_id=user_id,
            duration_ms=duration_ms,
            status=status,
            metadata=metadata or {},
            **kwargs
        )

    def log_document_processing(self, document_id: str, operation: str, message: str,
                                status: str = "processing", duration_ms: Optional[float] = None,
                                metadata: Optional[Dict[str, Any]] = None):
        """Log específico para processamento de documentos"""
        self.log_operation(
            operation=operation,
            message=message,
            document_id=document_id,
            status=status,
            duration_ms=duration_ms,
            metadata=metadata
        )

    def log_api_request(self, operation: str, message: str, user_id: Optional[str] = None,
                        duration_ms: Optional[float] = None, status: str = "success",
                        metadata: Optional[Dict[str, Any]] = None):
        """Log específico para requisições da API"""
        self.log_operation(
            operation=operation,
            message=message,
            user_id=user_id,
            duration_ms=duration_ms,
            status=status,
            metadata=metadata
        )

    def log_error(self, operation: str, message: str, error: Exception,
                  document_id: Optional[str] = None, user_id: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None):
        """Log específico para erros"""
        error_metadata = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_traceback': traceback.format_exc()
        }
        if metadata:
            error_metadata.update(metadata)

        self.log_operation(
            operation=operation,
            message=message,
            document_id=document_id,
            user_id=user_id,
            status="error",
            metadata=error_metadata
        )


class LoggingManager:
    """Gerenciador centralizado de logging"""

    def __init__(self):
        self.loggers: Dict[str, CustomLogger] = {}
        self._configured = False

    def configure_logging(self):
        """Configura o sistema de logging"""
        if self._configured:
            return

        # Criar diretório de logs se não existir
        log_dir = Path(settings.storage.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configurar logging root
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.logging.level))

        # Remover handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        if settings.debug:
            # Formato detalhado para desenvolvimento
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            # Formato JSON para produção
            console_formatter = StructuredFormatter()

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # Handler para arquivo
        try:
            file_handler = logging.FileHandler(
                log_dir / "etl_documentos.log",
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Erro ao configurar handler de arquivo: {e}")

        # Handler para erros
        try:
            error_handler = logging.FileHandler(
                log_dir / "errors.log",
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(error_handler)
        except Exception as e:
            print(f"Erro ao configurar handler de erros: {e}")

        self._configured = True

        # Log inicial
        self.get_logger(__name__).info(
            "Sistema de logging configurado com sucesso")

    def get_logger(self, name: str) -> CustomLogger:
        """Obtém um logger customizado"""
        if not self._configured:
            self.configure_logging()

        if name not in self.loggers:
            self.loggers[name] = CustomLogger(name)

        return self.loggers[name]

    def get_module_logger(self, module_name: str) -> CustomLogger:
        """Obtém um logger para um módulo específico"""
        return self.get_logger(f"app.{module_name}")

    def log_startup(self):
        """Log de inicialização do sistema"""
        logger = self.get_logger(__name__)
        logger.info("Iniciando sistema ETL Documentos",
                    operation="startup",
                    status="starting",
                    metadata={
                        'version': settings.api.version,
                        'environment': settings.env.value,
                        'debug': settings.debug
                    })

    def log_shutdown(self):
        """Log de finalização do sistema"""
        logger = self.get_logger(__name__)
        logger.info("Finalizando sistema ETL Documentos",
                    operation="shutdown",
                    status="shutting_down")


# Instância global do gerenciador de logging
logging_manager = LoggingManager()


def obter_logger(name: str) -> CustomLogger:
    """Função utilitária para obter logger"""
    return logging_manager.get_logger(name)


def obter_logger_modulo(module_name: str) -> CustomLogger:
    """Função utilitária para obter logger de módulo"""
    return logging_manager.get_module_logger(module_name)


@contextmanager
def log_operation(operation: str, logger: Optional[CustomLogger] = None,
                  document_id: Optional[str] = None, user_id: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None):
    """Context manager para log de operações com timing"""
    if logger is None:
        logger = obter_logger(__name__)

    start_time = time.time()
    operation_metadata = metadata or {}

    try:
        logger.log_operation(
            operation=operation,
            message=f"Iniciando operação: {operation}",
            document_id=document_id,
            user_id=user_id,
            status="started",
            metadata=operation_metadata
        )

        yield logger

        duration_ms = (time.time() - start_time) * 1000
        logger.log_operation(
            operation=operation,
            message=f"Operação concluída: {operation}",
            document_id=document_id,
            user_id=user_id,
            duration_ms=duration_ms,
            status="completed",
            metadata={**operation_metadata, 'duration_ms': duration_ms}
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.log_error(
            operation=operation,
            message=f"Erro na operação: {operation}",
            error=e,
            document_id=document_id,
            user_id=user_id,
            metadata={**operation_metadata, 'duration_ms': duration_ms}
        )
        raise


def log_document_processing(document_id: str, operation: str, message: str,
                            status: str = "processing", duration_ms: Optional[float] = None,
                            metadata: Optional[Dict[str, Any]] = None):
    """Função utilitária para log de processamento de documentos"""
    logger = obter_logger("document_processing")
    logger.log_document_processing(
        document_id=document_id,
        operation=operation,
        message=message,
        status=status,
        duration_ms=duration_ms,
        metadata=metadata
    )


def log_api_request(operation: str, message: str, user_id: Optional[str] = None,
                    duration_ms: Optional[float] = None, status: str = "success",
                    metadata: Optional[Dict[str, Any]] = None):
    """Função utilitária para log de requisições da API"""
    logger = obter_logger("api")
    logger.log_api_request(
        operation=operation,
        message=message,
        user_id=user_id,
        duration_ms=duration_ms,
        status=status,
        metadata=metadata
    )


def log_error(operation: str, message: str, error: Exception,
              document_id: Optional[str] = None, user_id: Optional[str] = None,
              metadata: Optional[Dict[str, Any]] = None):
    """Função utilitária para log de erros"""
    logger = obter_logger("error")
    logger.log_error(
        operation=operation,
        message=message,
        error=error,
        document_id=document_id,
        user_id=user_id,
        metadata=metadata
    )


# Configurar logging na inicialização
def configurar_logging():
    """Função para configurar o logging (mantida para compatibilidade)"""
    logging_manager.configure_logging()
    return logging_manager.get_logger(__name__)


# Loggers específicos para diferentes módulos
def get_document_logger() -> CustomLogger:
    """Logger para processamento de documentos"""
    return obter_logger("document_processing")


def get_api_logger() -> CustomLogger:
    """Logger para API"""
    return obter_logger("api")


def get_security_logger() -> CustomLogger:
    """Logger para segurança"""
    return obter_logger("security")


def get_database_logger() -> CustomLogger:
    """Logger para banco de dados"""
    return obter_logger("database")


def get_provider_logger() -> CustomLogger:
    """Logger para provedores"""
    return obter_logger("providers")


def get_service_logger() -> CustomLogger:
    """Logger para serviços"""
    return obter_logger("services")
