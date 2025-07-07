"""
Exceções customizadas para o sistema ETL Documentos
"""
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime

from app.core.logging import obter_logger

logger = obter_logger(__name__)


# =============================================================================
# EXCEÇÕES CUSTOMIZADAS
# =============================================================================

class ETLDocumentosException(Exception):
    """Exceção base para o sistema ETL Documentos"""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class DocumentProcessingError(ETLDocumentosException):
    """Erro no processamento de documentos"""
    pass


class DocumentNotFoundError(ETLDocumentosException):
    """Documento não encontrado"""
    pass


class DocumentValidationError(ETLDocumentosException):
    """Erro de validação de documento"""
    pass


class ProviderError(ETLDocumentosException):
    """Erro em provedor de extração"""
    pass


class ClassificationError(ETLDocumentosException):
    """Erro na classificação de documentos"""
    pass


class ExtractionError(ETLDocumentosException):
    """Erro na extração de dados"""
    pass


class ExtracaoException(ExtractionError):
    """Exceção de extração de dados (alias para ExtractionError)"""
    pass


class AuthenticationError(ETLDocumentosException):
    """Erro de autenticação"""
    pass


class AuthorizationError(ETLDocumentosException):
    """Erro de autorização"""
    pass


class DatabaseError(ETLDocumentosException):
    """Erro de banco de dados"""
    pass


class ConfigurationError(ETLDocumentosException):
    """Erro de configuração"""
    pass


class RateLimitError(ETLDocumentosException):
    """Erro de rate limit"""
    pass


class QuotaExceededError(ETLDocumentosException):
    """Erro de quota excedida"""
    pass


class ServiceUnavailableError(ETLDocumentosException):
    """Serviço indisponível"""
    pass


class ValidationError(ETLDocumentosException):
    """Erro de validação"""
    pass


class FileProcessingError(ETLDocumentosException):
    """Erro no processamento de arquivos"""
    pass


class CostCalculationError(ETLDocumentosException):
    """Erro no cálculo de custos"""
    pass


class AnalyticsError(ETLDocumentosException):
    """Erro em analytics"""
    pass


# =============================================================================
# MAPEAMENTO DE EXCEÇÕES PARA HTTP STATUS
# =============================================================================

EXCEPTION_STATUS_MAPPING = {
    DocumentNotFoundError: status.HTTP_404_NOT_FOUND,
    DocumentValidationError: status.HTTP_400_BAD_REQUEST,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    QuotaExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    ServiceUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DocumentProcessingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ProviderError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ClassificationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ExtractionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    FileProcessingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    CostCalculationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    AnalyticsError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ETLDocumentosException: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


# =============================================================================
# HANDLERS DE EXCEÇÃO
# =============================================================================

async def etl_documentos_exception_handler(request: Request, exc: ETLDocumentosException):
    """Handler para exceções customizadas do sistema"""
    status_code = EXCEPTION_STATUS_MAPPING.get(
        type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Log do erro
    logger.error(
        f"Exceção capturada: {exc.error_code}",
        operation="exception_handler",
        status="error",
        metadata={
            'error_code': exc.error_code,
            'error_type': type(exc).__name__,
            'details': exc.details,
            'path': request.url.path,
            'method': request.method
        }
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": type(exc).__name__,
                "details": exc.details
            },
            "timestamp": str(datetime.utcnow())
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler para exceções HTTP do FastAPI"""
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        operation="http_exception",
        status="error",
        metadata={
            'status_code': exc.status_code,
            'path': request.url.path,
            'method': request.method
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "type": "HTTPException"
            },
            "timestamp": str(datetime.utcnow())
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation error: {len(errors)} errors",
        operation="validation_error",
        status="error",
        metadata={
            'errors_count': len(errors),
            'path': request.url.path,
            'method': request.method,
            'errors': errors
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Erro de validação nos dados de entrada",
                "type": "ValidationError",
                "details": {
                    "errors": errors
                }
            },
            "timestamp": str(datetime.utcnow())
        }
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler para exceções HTTP do Starlette"""
    logger.warning(
        f"Starlette HTTP Exception: {exc.status_code} - {exc.detail}",
        operation="starlette_http_exception",
        status="error",
        metadata={
            'status_code': exc.status_code,
            'path': request.url.path,
            'method': request.method
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "type": "StarletteHTTPException"
            },
            "timestamp": str(datetime.utcnow())
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handler para exceções gerais não tratadas"""
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        operation="unhandled_exception",
        status="error",
        metadata={
            'exception_type': type(exc).__name__,
            'exception_message': str(exc),
            'path': request.url.path,
            'method': request.method
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Erro interno do servidor",
                "type": "InternalServerError"
            },
            "timestamp": str(datetime.utcnow())
        }
    )


# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================

def configurar_exception_handlers(app):
    """Configura os handlers de exceção na aplicação FastAPI"""

    # Handler para exceções customizadas
    app.add_exception_handler(ETLDocumentosException,
                              etl_documentos_exception_handler)

    # Handler para exceções HTTP do FastAPI
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Handler para erros de validação
    app.add_exception_handler(RequestValidationError,
                              validation_exception_handler)

    # Handler para exceções HTTP do Starlette
    app.add_exception_handler(StarletteHTTPException,
                              starlette_http_exception_handler)

    # Handler para exceções gerais
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers configurados com sucesso")


def raise_document_not_found(document_id: str):
    """Função utilitária para levantar exceção de documento não encontrado"""
    raise DocumentNotFoundError(
        message=f"Documento com ID '{document_id}' não encontrado",
        error_code="DOCUMENT_NOT_FOUND",
        details={"document_id": document_id}
    )


def raise_validation_error(message: str, field: str = None, value: Any = None):
    """Função utilitária para levantar exceção de validação"""
    details = {}
    if field:
        details["field"] = field
    if value is not None:
        details["value"] = value

    raise ValidationError(
        message=message,
        error_code="VALIDATION_ERROR",
        details=details
    )


def raise_authentication_error(message: str = "Credenciais inválidas"):
    """Função utilitária para levantar exceção de autenticação"""
    raise AuthenticationError(
        message=message,
        error_code="AUTHENTICATION_ERROR"
    )


def raise_authorization_error(message: str = "Acesso negado"):
    """Função utilitária para levantar exceção de autorização"""
    raise AuthorizationError(
        message=message,
        error_code="AUTHORIZATION_ERROR"
    )


def raise_rate_limit_error(message: str = "Rate limit excedido"):
    """Função utilitária para levantar exceção de rate limit"""
    raise RateLimitError(
        message=message,
        error_code="RATE_LIMIT_ERROR"
    )


def raise_quota_exceeded_error(message: str = "Quota excedida"):
    """Função utilitária para levantar exceção de quota excedida"""
    raise QuotaExceededError(
        message=message,
        error_code="QUOTA_EXCEEDED"
    )


def raise_service_unavailable(message: str = "Serviço temporariamente indisponível"):
    """Função utilitária para levantar exceção de serviço indisponível"""
    raise ServiceUnavailableError(
        message=message,
        error_code="SERVICE_UNAVAILABLE"
    )


# =============================================================================
# DECORADORES PARA TRATAMENTO DE EXCEÇÕES
# =============================================================================

def handle_exceptions(func):
    """Decorador para tratamento automático de exceções"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ETLDocumentosException:
            # Re-raise custom exceptions
            raise
        except Exception as e:
            # Convert other exceptions to internal server error
            logger.error(
                f"Unexpected error in {func.__name__}: {str(e)}",
                operation="unexpected_error",
                status="error",
                metadata={
                    'function': func.__name__,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            raise ETLDocumentosException(
                message="Erro interno inesperado",
                error_code="UNEXPECTED_ERROR",
                details={"function": func.__name__}
            )
    return wrapper


def handle_document_processing_errors(func):
    """Decorador específico para tratamento de erros de processamento de documentos"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (DocumentProcessingError, ProviderError, ClassificationError, ExtractionError):
            # Re-raise specific document processing errors
            raise
        except Exception as e:
            # Convert other exceptions to document processing error
            logger.error(
                f"Document processing error in {func.__name__}: {str(e)}",
                operation="document_processing_error",
                status="error",
                metadata={
                    'function': func.__name__,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            raise DocumentProcessingError(
                message="Erro no processamento do documento",
                error_code="DOCUMENT_PROCESSING_ERROR",
                details={"function": func.__name__, "original_error": str(e)}
            )
    return wrapper
