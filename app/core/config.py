"""
Configurações centralizadas da aplicação ETL Documentos
Usando Pydantic Settings para validação e tipagem forte
"""
import os
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from pydantic import Field, field_validator, model_validator, ConfigDict
from pydantic_settings import BaseSettings
from pydantic.types import SecretStr
from dotenv import load_dotenv
from enum import Enum

# Carrega variáveis de ambiente
load_dotenv()


class Environment(str, Enum):
    """Ambientes disponíveis"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DatabaseType(str, Enum):
    """Tipos de banco de dados suportados"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class VectorStoreType(str, Enum):
    """Tipos de banco vetorial suportados"""
    FAISS = "faiss"
    CHROMA = "chroma"
    PINECONE = "pinecone"


class DocumentStatus(str, Enum):
    """Status dos documentos"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentType(str, Enum):
    """Tipos de documentos suportados"""
    COMPROVANTE_BANCARIO = "Comprovante Bancário"
    CEI_OBRA = "CEI da Obra"
    INSCRICAO_MUNICIPAL = "Inscrição Municipal"
    TERMO_RESPONSABILIDADE = "Termo de Responsabilidade"
    ALVARA_MUNICIPAL = "Alvará Municipal"
    CONTRATO_SOCIAL = "Contrato Social"
    CARTAO_CNPJ = "Cartão CNPJ"
    CNH = "CNH"
    FATURA_TELEFONICA = "Fatura Telefônica"
    NOTA_FISCAL_SERVICOS = "Nota Fiscal de Serviços Eletrônica"
    OUTROS = "Outros"


class ProviderType(str, Enum):
    """Tipos de provedores de extração"""
    DOCLING = "docling"
    AZURE = "azure"
    FALLBACK = "fallback"


class DatabaseSettings(BaseSettings):
    """Configurações de banco de dados"""
    type: DatabaseType = Field(
        default=DatabaseType.SQLITE, validation_alias="DATABASE_TYPE")
    url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")
    sqlite_path: str = Field(
        default="./data/etl_documentos.db", validation_alias="SQLITE_PATH")

    @field_validator('url')
    @classmethod
    def set_database_url(cls, v, values):
        if v is None and values.data.get('type') == DatabaseType.SQLITE:
            return f"sqlite:///{values.data.get('sqlite_path', './data/etl_documentos.db')}"
        return v


class LLMSettings(BaseSettings):
    """Configurações de LLM"""
    openai_api_key: SecretStr = Field(validation_alias="OPENAI_API_KEY")
    default_model: str = Field(
        default="gpt-4o-mini", validation_alias="DEFAULT_MODEL")
    classification_model: str = Field(
        default="gpt-4o-mini", validation_alias="CLASSIFICATION_MODEL")
    extraction_model: str = Field(
        default="gpt-4o-mini", validation_alias="EXTRACTION_MODEL")

    @field_validator('openai_api_key')
    @classmethod
    def validate_openai_key(cls, v):
        if v.get_secret_value() == "sk-test-key-for-development":
            raise ValueError("OpenAI API Key não configurada")
        return v


class VectorStoreSettings(BaseSettings):
    """Configurações de banco vetorial"""
    type: VectorStoreType = Field(
        default=VectorStoreType.FAISS, validation_alias="VECTOR_STORE_TYPE")
    path: str = Field(default="./data/vector_store",
                      validation_alias="VECTOR_STORE_PATH")
    embedding_model: str = Field(
        default="text-embedding-3-small", validation_alias="EMBEDDING_MODEL")

    @field_validator('path')
    @classmethod
    def create_vector_store_path(cls, v):
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


class ProviderSettings(BaseSettings):
    """Configurações de provedores de extração"""
    docling_enabled: bool = Field(
        default=True, validation_alias="DOCLING_ENABLED")
    docling_quality_threshold: float = Field(
        default=0.7, validation_alias="DOCLING_QUALITY_THRESHOLD")
    azure_enabled: bool = Field(
        default=False, validation_alias="AZURE_ENABLED")
    azure_endpoint: Optional[str] = Field(
        default=None, validation_alias="AZURE_ENDPOINT")
    azure_key: Optional[SecretStr] = Field(
        default=None, validation_alias="AZURE_API_KEY")
    azure_api_version: str = Field(
        default="2023-07-31", validation_alias="AZURE_API_VERSION")

    @field_validator('docling_quality_threshold')
    @classmethod
    def validate_thresholds(cls, v):
        if isinstance(v, float) and not (0.0 <= v <= 1.0):
            raise ValueError("Threshold deve estar entre 0.0 e 1.0")
        return v


class QualitySettings(BaseSettings):
    """Configurações de qualidade e thresholds"""
    classification_confidence_threshold: float = Field(
        default=0.8, validation_alias="CLASSIFICATION_CONFIDENCE_THRESHOLD")
    extraction_quality_threshold: float = Field(
        default=0.7, validation_alias="EXTRACTION_QUALITY_THRESHOLD")
    qualidade_minima_extracao: float = Field(
        default=0.7, validation_alias="QUALIDADE_MINIMA_EXTRACAO")
    min_similar_documents: int = Field(
        default=3, validation_alias="MIN_SIMILAR_DOCUMENTS")
    max_similar_documents: int = Field(
        default=5, validation_alias="MAX_SIMILAR_DOCUMENTS")

    @field_validator('classification_confidence_threshold')
    @classmethod
    def validate_thresholds(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("Threshold deve estar entre 0.0 e 1.0")
        return v

    @field_validator('min_similar_documents', 'max_similar_documents')
    @classmethod
    def validate_similar_documents(cls, v):
        if v < 1:
            raise ValueError("Número de documentos similares deve ser >= 1")
        return v


class StorageSettings(BaseSettings):
    """Configurações de armazenamento"""
    upload_dir: str = Field(default="./data/uploads",
                            validation_alias="UPLOAD_DIR")
    output_dir: str = Field(default="./data/output",
                            validation_alias="OUTPUT_DIR")
    max_file_size: int = Field(
        default=10485760, validation_alias="MAX_FILE_SIZE")  # 10MB
    log_dir: str = Field(default="./logs", validation_alias="LOG_DIR")
    allowed_extensions: Set[str] = Field(
        default={".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".txt", ".docx", ".doc"})

    @field_validator('upload_dir', 'output_dir', 'log_dir')
    @classmethod
    def create_directories(cls, v):
        Path(v).mkdir(parents=True, exist_ok=True)
        return v

    @field_validator('max_file_size')
    @classmethod
    def validate_file_size(cls, v):
        if v <= 0:
            raise ValueError("Tamanho máximo de arquivo deve ser > 0")
        return v


class PerformanceSettings(BaseSettings):
    """Configurações de performance"""
    max_workers: int = Field(default=4, validation_alias="MAX_WORKERS")
    batch_size: int = Field(default=10, validation_alias="BATCH_SIZE")
    cache_ttl: int = Field(default=3600, validation_alias="CACHE_TTL")

    @field_validator('max_workers', 'batch_size')
    @classmethod
    def validate_positive_integers(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser > 0")
        return v


class DocumentProcessingSettings(BaseSettings):
    """Configurações de processamento de documentos"""
    extensive_document_threshold: int = Field(
        default=10000, validation_alias="EXTENSIVE_DOCUMENT_THRESHOLD")
    max_chunk_size: int = Field(
        default=3000, validation_alias="MAX_CHUNK_SIZE")
    chunk_overlap_size: int = Field(
        default=200, validation_alias="CHUNK_OVERLAP_SIZE")
    enable_chunking: bool = Field(
        default=True, validation_alias="ENABLE_CHUNKING")
    book_processing_enabled: bool = Field(
        default=True, validation_alias="BOOK_PROCESSING_ENABLED")
    max_book_size_mb: int = Field(
        default=50, validation_alias="MAX_BOOK_SIZE_MB")

    @field_validator('extensive_document_threshold', 'max_chunk_size', 'chunk_overlap_size', 'max_book_size_mb')
    @classmethod
    def validate_positive_integers(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser > 0")
        return v


class APISettings(BaseSettings):
    """Configurações da API"""
    title: str = Field(default="ETL Documentos API",
                       validation_alias="API_TITLE")
    version: str = Field(default="3.0.0", validation_alias="API_VERSION")
    description: str = Field(
        default="API moderna para extração, classificação e análise de documentos", validation_alias="API_DESCRIPTION")
    host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    port: int = Field(default=8000, validation_alias="API_PORT")

    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not (1024 <= v <= 65535):
            raise ValueError("Porta deve estar entre 1024 e 65535")
        return v


class SecuritySettings(BaseSettings):
    """Configurações de segurança"""
    secret_key: SecretStr = Field(validation_alias="SECRET_KEY")
    jwt_algorithm: str = Field(
        default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=1440, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        secret = v.get_secret_value()
        if not secret or len(secret) < 16:
            raise ValueError("Chave secreta deve ter pelo menos 16 caracteres")
        return v

    @field_validator('access_token_expire_minutes')
    @classmethod
    def validate_token_expiry(cls, v):
        if v <= 0:
            raise ValueError("Tempo de expiração deve ser > 0")
        return v


class LoggingSettings(BaseSettings):
    """Configurações de logging"""
    level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    max_size: str = Field(default="10MB")
    backup_count: int = Field(default=5)

    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Nível de log inválido: {v}")
        return v.upper()


class CostSettings(BaseSettings):
    """Configurações de custos"""
    model_costs: Dict[str, Dict[str, float]] = Field(default={
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
        "text-embedding-3-small": {"input": 0.00002, "output": 0},
        "text-embedding-3-large": {"input": 0.00013, "output": 0}
    })

    azure_costs: Dict[str, float] = Field(default={
        "document_intelligence": 0.0015  # por página
    })


class Settings(BaseSettings):
    """Configurações principais da aplicação"""
    model_config = ConfigDict(
        extra='ignore', env_file='.env', case_sensitive=False)

    # Configurações básicas
    debug: bool = Field(default=False, validation_alias="DEBUG")
    env: Environment = Field(
        default=Environment.DEVELOPMENT, validation_alias="ENV")

    # Subconfigurações como Optionals
    api: Optional[APISettings] = Field(default=None)
    security: Optional[SecuritySettings] = Field(default=None)
    database: Optional[DatabaseSettings] = Field(default=None)
    llm: Optional[LLMSettings] = Field(default=None)
    vector_store: Optional[VectorStoreSettings] = Field(default=None)
    provider: Optional[ProviderSettings] = Field(default=None)
    quality: Optional[QualitySettings] = Field(default=None)
    storage: Optional[StorageSettings] = Field(default=None)
    performance: Optional[PerformanceSettings] = Field(default=None)
    document_processing: Optional[DocumentProcessingSettings] = Field(
        default=None)
    logging: Optional[LoggingSettings] = Field(default=None)
    cost: Optional[Any] = None

    # Configurações Azure
    azure_enabled: bool = Field(
        default=False, description="Habilitar Azure Document Intelligence")
    azure_endpoint: Optional[str] = Field(
        default=None, description="Endpoint do Azure Document Intelligence")
    azure_key: Optional[str] = Field(
        default=None, validation_alias="AZURE_API_KEY", description="Chave do Azure Document Intelligence")
    azure_api_version: str = Field(
        default="2023-07-31", description="Versão da API Azure")

    # Configurações Azure OpenAI
    azure_openai_endpoint: Optional[str] = Field(
        default=None, description="Endpoint do Azure OpenAI")
    azure_openai_key: Optional[str] = Field(
        default=None, description="Chave do Azure OpenAI")
    azure_openai_model: str = Field(
        default="gpt-4", description="Modelo do Azure OpenAI")

    # Configurações AWS
    aws_access_key_id: Optional[str] = Field(
        default=None, description="AWS Access Key ID")
    aws_secret_access_key: Optional[str] = Field(
        default=None, description="AWS Secret Access Key")
    aws_region: str = Field(default="us-east-1", description="Região AWS")
    aws_bedrock_model: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0", description="Modelo AWS Bedrock")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api = APISettings()
        self.security = SecuritySettings()
        self.database = DatabaseSettings()
        self.llm = LLMSettings()
        self.vector_store = VectorStoreSettings()
        self.provider = ProviderSettings()
        self.quality = QualitySettings()
        self.storage = StorageSettings()
        self.performance = PerformanceSettings()
        self.document_processing = DocumentProcessingSettings()
        self.logging = LoggingSettings()
        # self.cost = CostSettings()  # Ajustar se necessário

    # Tipos de documentos suportados
    document_types: List[str] = Field(default=[
        "Comprovante Bancário",
        "CEI da Obra",
        "Inscrição Municipal",
        "Termo de Responsabilidade",
        "Alvará Municipal",
        "Contrato Social",
        "Cartão CNPJ",
        "CNH",
        "Fatura Telefônica",
        "Nota Fiscal de Serviços Eletrônica",
        "Outros"
    ])

    @property
    def document_type_ids(self) -> Dict[str, int]:
        """Mapeia tipos de documento para IDs"""
        return {doc_type: idx for idx, doc_type in enumerate(self.document_types)}

    @property
    def document_id_types(self) -> Dict[int, str]:
        """Mapeia IDs para tipos de documento"""
        return {idx: doc_type for idx, doc_type in enumerate(self.document_types)}

    def validate_config(self) -> List[str]:
        """Valida configurações e retorna lista de erros"""
        errors = []

        # Validar OpenAI API Key
        try:
            self.llm.openai_api_key.get_secret_value()
        except Exception:
            errors.append("OpenAI API Key não configurada ou inválida")

        # Validar Azure se habilitado
        if self.provider.azure_enabled:
            if not self.provider.azure_endpoint:
                errors.append("Azure endpoint não configurado")
            if not self.provider.azure_key:
                errors.append("Azure key não configurada")

        # Validar thresholds
        if self.quality.qualidade_minima_extracao < 0 or self.quality.qualidade_minima_extracao > 1:
            errors.append(
                "Qualidade mínima de extração deve estar entre 0 e 1")

        return errors

    def _create_directories(self):
        """Cria diretórios necessários"""
        directories = [
            self.storage.upload_dir,
            self.storage.output_dir,
            self.storage.log_dir,
            self.vector_store.path
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


# Instância global das configurações
settings = Settings()

# Aliases para compatibilidade
DEBUG = settings.debug
ENV = settings.env
API_PORT = settings.api.port
API_HOST = settings.api.host
SECRET_KEY = settings.security.secret_key.get_secret_value()
OPENAI_API_KEY = settings.llm.openai_api_key.get_secret_value()
AZURE_ENABLED = settings.provider.azure_enabled
AZURE_ENDPOINT = settings.provider.azure_endpoint
AZURE_KEY = settings.provider.azure_key.get_secret_value(
) if settings.provider.azure_key else None
DATABASE_URL = settings.database.url
UPLOAD_DIR = settings.storage.upload_dir
OUTPUT_DIR = settings.storage.output_dir
MAX_FILE_SIZE = settings.storage.max_file_size
ALLOWED_EXTENSIONS = settings.storage.allowed_extensions
LOG_DIR = settings.storage.log_dir
LOG_LEVEL = settings.logging.level
DOCUMENT_TYPES = settings.document_types
QUALIDADE_MINIMA_EXTRACAO = settings.quality.qualidade_minima_extracao

# Aliases adicionais para compatibilidade
MODEL_COSTS = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
    "text-embedding-3-small": {"input": 0.00002, "output": 0},
    "text-embedding-3-large": {"input": 0.00013, "output": 0}
}

# Alias para configuracoes (usado em alguns módulos)
configuracoes = settings
