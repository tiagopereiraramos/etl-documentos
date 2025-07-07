"""
Enumerações utilizadas no sistema ETL Documentos
"""
from enum import Enum
from typing import List


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


class ProviderExtracao(str, Enum):
    """Provedores de extração disponíveis"""
    DOCLING = "docling"
    AZURE = "azure"
    AWS = "aws"
    FALLBACK = "fallback"


class TipoFeedback(str, Enum):
    """Tipos de feedback"""
    CLASSIFICACAO = "classificacao"
    EXTRACAO = "extracao"
    QUALIDADE = "qualidade"
    GERAL = "geral"


class FormatoArquivo(str, Enum):
    """Formatos de arquivo suportados"""
    PDF = ".pdf"
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"
    TIFF = ".tiff"
    BMP = ".bmp"
    TXT = ".txt"
    DOCX = ".docx"
    DOC = ".doc"
    PPTX = ".pptx"
    PPT = ".ppt"
    XLSX = ".xlsx"
    XLS = ".xls"
    CSV = ".csv"
    RTF = ".rtf"
    HTML = ".html"
    MD = ".md"

    @classmethod
    def get_all_extensions(cls) -> List[str]:
        """Retorna todas as extensões suportadas"""
        return [formato.value for formato in cls]


class OperationType(str, Enum):
    """Tipos de operações"""
    UPLOAD = "upload"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    PROCESSING = "processing"
    ANALYSIS = "analysis"


class LogLevel(str, Enum):
    """Níveis de log"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FileExtension(str, Enum):
    """Extensões de arquivo suportadas"""
    PDF = ".pdf"
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"
    TIFF = ".tiff"
    BMP = ".bmp"
    TXT = ".txt"
    DOCX = ".docx"
    DOC = ".doc"


class AuthenticationMethod(str, Enum):
    """Métodos de autenticação"""
    JWT = "jwt"
    API_KEY = "api_key"
    OAUTH = "oauth"


class ProcessingPriority(str, Enum):
    """Prioridades de processamento"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class QualityLevel(str, Enum):
    """Níveis de qualidade"""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class CostType(str, Enum):
    """Tipos de custo"""
    INPUT = "input"
    OUTPUT = "output"
    OPERATION = "operation"
    STORAGE = "storage"


class AnalyticsPeriod(str, Enum):
    """Períodos para analytics"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class TipoDocumento(str, Enum):
    """Tipos de documentos suportados pelo sistema"""
    CNH = "CNH"
    COMPROVANTE_BANCARIO = "Comprovante Bancário"
    CARTAO_CNPJ = "Cartão CNPJ"
    CEI_OBRA = "CEI da Obra"
    INSCRICAO_MUNICIPAL = "Inscrição Municipal"
    TERMO_RESPONSABILIDADE = "Termo de Responsabilidade"
    ALVARA_MUNICIPAL = "Alvará Municipal"
    CONTRATO_SOCIAL = "Contrato Social"
    FATURA_TELEFONICA = "Fatura Telefônica"
    NOTA_FISCAL_SERVICOS = "Nota Fiscal de Serviços Eletrônica"
    DOCUMENTO_NAO_CLASSIFICADO = "Documento Não Classificado"

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Retorna todos os tipos de documento exceto 'não classificado'"""
        return [tipo.value for tipo in cls if tipo != cls.DOCUMENTO_NAO_CLASSIFICADO]


class StatusProcessamento(str, Enum):
    """Status de processamento de documentos"""
    AGUARDANDO = "aguardando"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"
    CANCELADO = "cancelado"


class TipoOperacao(str, Enum):
    """Tipos de operações do sistema"""
    VETORIZACAO = "vetorizacao"
    ANALISE = "analise"


class ModeloLLM(str, Enum):
    """Modelos de LLM disponíveis"""
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4 = "gpt-4"
    GPT_35_TURBO = "gpt-3.5-turbo"


class ModeloEmbedding(str, Enum):
    """Modelos de embedding disponíveis"""
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"


class TipoMetrica(str, Enum):
    """Tipos de métricas"""
    PERFORMANCE = "performance"
    CUSTO = "custo"
    QUALIDADE = "qualidade"
    USO = "uso"


class TipoRelatorio(str, Enum):
    """Tipos de relatórios"""
    DASHBOARD = "dashboard"
    PERFORMANCE = "performance"
    CUSTOS = "custos"
    QUALIDADE = "qualidade"
    USO = "uso"
