"""
Schemas Pydantic para API
"""
from app.models.enums import (
    TipoDocumento, StatusProcessamento, ProviderExtracao,
    TipoOperacao, TipoFeedback, FormatoArquivo, ProcessingPriority,
    LogLevel, OperationType, DocumentType, QualityLevel, CostType,
    AnalyticsPeriod
)
from pydantic import BaseModel, Field, validator, HttpUrl, EmailStr, ConfigDict
from pydantic.types import UUID4
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class MetricasExtracao(BaseModel):
    """Métricas de extração de texto"""
    qualidade_score: float = 0.0
    metodo_extracao: str = ""
    tempo_processamento: float = 0.0
    caracteres_extraidos: int = 0
    linhas_extraidas: int = 0


# Enums
class DocumentStatus(str, Enum):
    processando = "processando"
    sucesso = "sucesso"
    erro = "erro"
    pendente = "pendente"


class ProviderType(str, Enum):
    docling = "docling"
    azure = "azure"
    fallback = "fallback"

# Schemas de Cliente


class ClienteBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')


class ClienteCreate(ClienteBase):
    senha: str = Field(..., min_length=8)


class ClienteResponse(ClienteBase):
    id: str
    ativo: bool
    data_criacao: datetime

    class Config:
        from_attributes = True


class ClienteLogin(BaseModel):
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# Schemas de Documento


class DocumentResponse(BaseModel):
    id: str
    nome_arquivo: str
    tipo_documento: str
    status_processamento: DocumentStatus
    confianca_classificacao: float
    provider_extracao: Optional[str] = None
    tempo_processamento: float
    custo_processamento: float
    data_upload: datetime
    data_processamento: Optional[datetime] = None
    dados_extraidos: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documentos: List[DocumentResponse]
    total: int
    pagina: int
    tamanho_pagina: int
    total_paginas: int

# Schemas de Classificação


class ClassificationResponse(BaseModel):
    documento_id: Optional[str] = None
    tipo_documento: str
    confianca: float
    tempo_processamento: float
    provider_usado: str


class ClassificationRequest(BaseModel):
    force_type: Optional[str] = None

# Schemas de Extração


class ExtractionResponse(BaseModel):
    documento_id: str
    tipo_documento: str
    dados_extraidos: Dict[str, Any]
    campos_obrigatorios_presentes: List[str]
    campos_faltantes: List[str]
    qualidade_extracao: float
    tempo_processamento: float
    provider_usado: str


class ExtractionRequest(BaseModel):
    force_type: Optional[str] = None
    extract_mode: str = "complete"  # "complete", "fields_only", "text_only"

# Schemas de Feedback


class FeedbackRequest(BaseModel):
    documento_id: Optional[str] = None
    tipo_feedback: str  # "classificacao" ou "extracao"


class ClassificationFeedbackRequest(FeedbackRequest):
    texto_documento: str
    tipo_predito: str
    tipo_correto: str
    confianca_original: Optional[float] = 0.0


class ExtractionFeedbackRequest(FeedbackRequest):
    texto_documento: str
    tipo_documento: str
    dados_extraidos_originais: Optional[Dict[str, Any]] = None
    dados_extraidos_corretos: Dict[str, Any]


class FeedbackResponse(BaseModel):
    sucesso: bool
    mensagem: str
    feedback_id: str
    timestamp: datetime

# Schemas de Estatísticas


class StatsResponse(BaseModel):
    documentos_processados_hoje: int
    documentos_processados_total: int
    taxa_sucesso: float
    tempo_medio_processamento: float
    custo_total_hoje: float
    custo_total_geral: float
    tipos_documentos_mais_comuns: List[Dict[str, Any]]
    providers_mais_usados: List[Dict[str, Any]]


class PerformanceMetrics(BaseModel):
    endpoint: str
    tempo_resposta_medio: float
    total_requisicoes: int
    taxa_sucesso: float
    taxa_erro: float
    timestamp: datetime

# Schemas de Custos


class CostBreakdown(BaseModel):
    custo_llm: float
    custo_azure: float
    custo_total: float
    tokens_usados: int
    documentos_processados: int


class SessionCostReport(BaseModel):
    session_id: str
    inicio_sessao: datetime
    fim_sessao: Optional[datetime]
    breakdown_custos: CostBreakdown
    documentos: List[str]

# Schemas de Logs


class LogEntry(BaseModel):
    id: str
    documento_id: str
    operacao: str
    provider: Optional[str]
    status: str
    detalhes: Optional[Dict[str, Any]]
    tempo_execucao: float
    timestamp: datetime


class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int
    pagina: int
    tamanho_pagina: int

# Schemas de Configuração


class SystemConfigResponse(BaseModel):
    tipos_documentos_suportados: List[str]
    providers_disponiveis: List[str]
    extensoes_suportadas: List[str]
    tamanho_maximo_arquivo: int
    configuracoes_ativas: Dict[str, Any]

# Schemas de Validação


class FileValidationResponse(BaseModel):
    valido: bool
    motivo: Optional[str] = None
    tamanho_arquivo: int
    extensao: str
    tipo_mime: Optional[str] = None

# Schemas de Saúde do Sistema


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    versao: str
    uptime: float
    banco_dados: bool
    providers_status: Dict[str, bool]
    uso_memoria: float
    uso_cpu: float

# Schemas de Erro


class ErrorResponse(BaseModel):
    erro: bool = True
    codigo: str
    mensagem: str
    detalhes: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ValidationErrorResponse(BaseModel):
    erro: bool = True
    codigo: str = "VALIDATION_ERROR"
    mensagem: str = "Dados de entrada inválidos"
    campos_invalidos: List[Dict[str, str]]
    timestamp: datetime = Field(default_factory=datetime.now)

# Schemas para Webhooks/Notificações


class WebhookPayload(BaseModel):
    evento: str
    documento_id: str
    timestamp: datetime
    dados: Dict[str, Any]

# Schemas para Relatórios


class DocumentReport(BaseModel):
    periodo_inicio: datetime
    periodo_fim: datetime
    total_documentos: int
    tipos_processados: Dict[str, int]
    taxa_sucesso_por_tipo: Dict[str, float]
    tempo_medio_por_tipo: Dict[str, float]
    custo_por_tipo: Dict[str, float]


"""
Schemas Pydantic para validação de dados da API ETL Documentos
"""


# =============================================================================
# SCHEMAS DE AUTENTICAÇÃO
# =============================================================================

class TokenRequest(BaseModel):
    """Schema para requisição de token"""
    username: str = Field(..., description="Nome de usuário")
    password: str = Field(..., description="Senha", min_length=6)


class TokenResponse(BaseModel):
    """Schema para resposta de token"""
    access_token: str = Field(..., description="Token de acesso JWT")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")
    refresh_token: Optional[str] = Field(None, description="Token de refresh")


class RefreshTokenRequest(BaseModel):
    """Schema para requisição de refresh token"""
    refresh_token: str = Field(..., description="Token de refresh")


class UserCreate(BaseModel):
    """Schema para criação de usuário"""
    username: str = Field(..., min_length=3, max_length=50,
                          description="Nome de usuário")
    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., min_length=8, description="Senha")
    full_name: Optional[str] = Field(
        None, max_length=100, description="Nome completo")
    is_active: bool = Field(default=True, description="Usuário ativo")


class UserResponse(BaseModel):
    """Schema para resposta de usuário"""
    id: UUID4 = Field(..., description="ID do usuário")
    username: str = Field(..., description="Nome de usuário")
    email: EmailStr = Field(..., description="Email do usuário")
    full_name: Optional[str] = Field(None, description="Nome completo")
    is_active: bool = Field(..., description="Usuário ativo")
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: Optional[datetime] = Field(
        None, description="Data de atualização")

    class Config:
        from_attributes = True


# =============================================================================
# SCHEMAS DE DOCUMENTOS
# =============================================================================

class DocumentUpload(BaseModel):
    """Schema para upload de documento"""
    filename: str = Field(..., description="Nome do arquivo")
    content_type: str = Field(..., description="Tipo de conteúdo")
    size: int = Field(..., description="Tamanho do arquivo em bytes")
    priority: ProcessingPriority = Field(
        default=ProcessingPriority.NORMAL, description="Prioridade de processamento")


class DocumentBase(BaseModel):
    """Schema base para documentos"""
    filename: str = Field(..., description="Nome do arquivo original")
    content_type: str = Field(..., description="Tipo de conteúdo")
    size: int = Field(..., description="Tamanho do arquivo em bytes")
    status: DocumentStatus = Field(..., description="Status do documento")
    document_type: Optional[DocumentType] = Field(
        None, description="Tipo do documento")
    quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Score de qualidade da extração")


class DocumentCreate(DocumentBase):
    """Schema para criação de documento"""
    user_id: UUID4 = Field(..., description="ID do usuário")
    file_path: str = Field(..., description="Caminho do arquivo no sistema")
    hash: str = Field(..., description="Hash do arquivo para deduplicação")


class DocumentResponse(DocumentBase):
    """Schema para resposta de documento"""
    id: UUID4 = Field(..., description="ID do documento")
    user_id: UUID4 = Field(..., description="ID do usuário")
    file_path: str = Field(..., description="Caminho do arquivo no sistema")
    hash: str = Field(..., description="Hash do arquivo")
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: Optional[datetime] = Field(
        None, description="Data de atualização")
    processed_at: Optional[datetime] = Field(
        None, description="Data de processamento")
    processing_time: Optional[float] = Field(
        None, description="Tempo de processamento em segundos")

    class Config:
        from_attributes = True


class DocumentStatusResponse(BaseModel):
    """Schema para resposta de status do documento"""
    document_id: UUID4 = Field(..., description="ID do documento")
    status: DocumentStatus = Field(..., description="Status atual")
    progress: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Progresso em porcentagem")
    message: Optional[str] = Field(None, description="Mensagem de status")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimativa de conclusão")


# =============================================================================
# SCHEMAS DE PROCESSAMENTO
# =============================================================================

class ExtractionResult(BaseModel):
    """Schema para resultado de extração"""
    provider: ProviderType = Field(..., description="Provedor utilizado")
    text_content: str = Field(..., description="Texto extraído")
    confidence_score: float = Field(..., ge=0.0,
                                    le=1.0, description="Score de confiança")
    processing_time: float = Field(...,
                                   description="Tempo de processamento em segundos")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadados da extração")


class ClassificationResult(BaseModel):
    """Schema para resultado de classificação"""
    document_type: DocumentType = Field(...,
                                        description="Tipo do documento identificado")
    confidence_score: float = Field(..., ge=0.0,
                                    le=1.0, description="Score de confiança")
    alternatives: List[Dict[str, Union[str, float]]] = Field(
        default_factory=list, description="Alternativas de classificação")
    processing_time: float = Field(...,
                                   description="Tempo de processamento em segundos")


class StructuredData(BaseModel):
    """Schema para dados estruturados extraídos"""
    field_name: str = Field(..., description="Nome do campo")
    value: Any = Field(..., description="Valor extraído")
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="Confiança da extração")
    source: str = Field(...,
                        description="Fonte da extração (texto, tabela, etc.)")


class ProcessingResult(BaseModel):
    """Schema para resultado completo do processamento"""
    document_id: UUID4 = Field(..., description="ID do documento")
    extraction: ExtractionResult = Field(...,
                                         description="Resultado da extração")
    classification: ClassificationResult = Field(
        ..., description="Resultado da classificação")
    structured_data: List[StructuredData] = Field(
        default_factory=list, description="Dados estruturados")
    quality_score: float = Field(..., ge=0.0, le=1.0,
                                 description="Score geral de qualidade")
    processing_time: float = Field(...,
                                   description="Tempo total de processamento")
    cost: float = Field(..., description="Custo total da operação")
    errors: List[str] = Field(default_factory=list,
                              description="Erros encontrados")


# =============================================================================
# SCHEMAS DE LOGS
# =============================================================================

class LogEntry(BaseModel):
    """Schema para entrada de log"""
    timestamp: datetime = Field(..., description="Timestamp do log")
    level: LogLevel = Field(..., description="Nível do log")
    module: str = Field(..., description="Módulo que gerou o log")
    operation: OperationType = Field(..., description="Tipo de operação")
    message: str = Field(..., description="Mensagem do log")
    document_id: Optional[UUID4] = Field(
        None, description="ID do documento relacionado")
    user_id: Optional[UUID4] = Field(None, description="ID do usuário")
    duration_ms: Optional[float] = Field(
        None, description="Duração da operação em ms")
    status: str = Field(..., description="Status da operação")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadados adicionais")


class LogFilter(BaseModel):
    """Schema para filtros de log"""
    start_date: Optional[datetime] = Field(None, description="Data inicial")
    end_date: Optional[datetime] = Field(None, description="Data final")
    level: Optional[LogLevel] = Field(None, description="Nível de log")
    module: Optional[str] = Field(None, description="Módulo")
    operation: Optional[OperationType] = Field(
        None, description="Tipo de operação")
    document_id: Optional[UUID4] = Field(None, description="ID do documento")
    user_id: Optional[UUID4] = Field(None, description="ID do usuário")
    limit: int = Field(default=100, ge=1, le=1000,
                       description="Limite de resultados")


# =============================================================================
# SCHEMAS DE FEEDBACK
# =============================================================================

class FeedbackCreate(BaseModel):
    """Schema para criação de feedback"""
    document_id: UUID4 = Field(..., description="ID do documento")
    feedback_type: str = Field(...,
                               description="Tipo de feedback (classification, extraction)")
    rating: int = Field(..., ge=1, le=5, description="Avaliação de 1 a 5")
    comment: Optional[str] = Field(
        None, max_length=1000, description="Comentário opcional")
    corrections: Dict[str, Any] = Field(
        default_factory=dict, description="Correções sugeridas")


class FeedbackResponse(BaseModel):
    """Schema para resposta de feedback"""
    id: UUID4 = Field(..., description="ID do feedback")
    document_id: UUID4 = Field(..., description="ID do documento")
    user_id: UUID4 = Field(..., description="ID do usuário")
    feedback_type: str = Field(..., description="Tipo de feedback")
    rating: int = Field(..., description="Avaliação")
    comment: Optional[str] = Field(None, description="Comentário")
    corrections: Dict[str, Any] = Field(..., description="Correções")
    created_at: datetime = Field(..., description="Data de criação")

    class Config:
        from_attributes = True


# =============================================================================
# SCHEMAS DE ANALYTICS
# =============================================================================

class AnalyticsMetrics(BaseModel):
    """Schema para métricas de analytics"""
    total_documents: int = Field(...,
                                 description="Total de documentos processados")
    documents_by_type: Dict[str,
                            int] = Field(..., description="Documentos por tipo")
    average_processing_time: float = Field(...,
                                           description="Tempo médio de processamento")
    success_rate: float = Field(..., ge=0.0, le=1.0,
                                description="Taxa de sucesso")
    total_cost: float = Field(..., description="Custo total")
    quality_distribution: Dict[QualityLevel,
                               int] = Field(..., description="Distribuição de qualidade")


class AnalyticsRequest(BaseModel):
    """Schema para requisição de analytics"""
    start_date: datetime = Field(..., description="Data inicial")
    end_date: datetime = Field(..., description="Data final")
    period: AnalyticsPeriod = Field(
        default=AnalyticsPeriod.DAILY, description="Período de agregação")
    document_types: Optional[List[DocumentType]] = Field(
        None, description="Tipos de documento para filtrar")
    user_id: Optional[UUID4] = Field(
        None, description="ID do usuário para filtrar")


class AnalyticsResponse(BaseModel):
    """Schema para resposta de analytics"""
    period: AnalyticsPeriod = Field(..., description="Período de agregação")
    start_date: datetime = Field(..., description="Data inicial")
    end_date: datetime = Field(..., description="Data final")
    metrics: AnalyticsMetrics = Field(..., description="Métricas calculadas")
    time_series: List[Dict[str, Any]
                      ] = Field(..., description="Série temporal dos dados")


# =============================================================================
# SCHEMAS DE CUSTOS
# =============================================================================

class CostBreakdown(BaseModel):
    """Schema para detalhamento de custos"""
    operation_type: OperationType = Field(..., description="Tipo de operação")
    provider: ProviderType = Field(..., description="Provedor utilizado")
    model: Optional[str] = Field(None, description="Modelo utilizado")
    input_tokens: Optional[int] = Field(None, description="Tokens de entrada")
    output_tokens: Optional[int] = Field(None, description="Tokens de saída")
    cost: float = Field(..., description="Custo da operação")
    cost_type: CostType = Field(..., description="Tipo de custo")


class CostSummary(BaseModel):
    """Schema para resumo de custos"""
    total_cost: float = Field(..., description="Custo total")
    cost_by_provider: Dict[ProviderType,
                           float] = Field(..., description="Custo por provedor")
    cost_by_operation: Dict[OperationType,
                            float] = Field(..., description="Custo por operação")
    cost_by_model: Dict[str,
                        float] = Field(..., description="Custo por modelo")
    breakdown: List[CostBreakdown] = Field(...,
                                           description="Detalhamento dos custos")


# =============================================================================
# SCHEMAS DE RESPOSTA PADRÃO
# =============================================================================

class StandardResponse(BaseModel):
    """Schema para resposta padrão da API"""
    success: bool = Field(...,
                          description="Indica se a operação foi bem-sucedida")
    message: str = Field(..., description="Mensagem descritiva")
    data: Optional[Any] = Field(None, description="Dados da resposta")
    errors: List[str] = Field(default_factory=list,
                              description="Lista de erros")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp da resposta")


class PaginatedResponse(BaseModel):
    """Schema para resposta paginada"""
    items: List[Any] = Field(..., description="Lista de itens")
    total: int = Field(..., description="Total de itens")
    page: int = Field(..., description="Página atual")
    size: int = Field(..., description="Tamanho da página")
    pages: int = Field(..., description="Total de páginas")
    has_next: bool = Field(..., description="Tem próxima página")
    has_prev: bool = Field(..., description="Tem página anterior")


# =============================================================================
# SCHEMAS DE VALIDAÇÃO
# =============================================================================

class ValidationError(BaseModel):
    """Schema para erro de validação"""
    field: str = Field(..., description="Campo com erro")
    message: str = Field(..., description="Mensagem de erro")
    value: Optional[Any] = Field(None, description="Valor que causou o erro")


class ValidationResponse(BaseModel):
    """Schema para resposta de validação"""
    is_valid: bool = Field(..., description="Indica se os dados são válidos")
    errors: List[ValidationError] = Field(
        default_factory=list, description="Lista de erros de validação")
    warnings: List[str] = Field(
        default_factory=list, description="Lista de avisos")


# =============================================================================
# SCHEMAS DE CONFIGURAÇÃO
# =============================================================================

class SystemHealth(BaseModel):
    """Schema para health check do sistema"""
    status: str = Field(..., description="Status geral do sistema")
    timestamp: datetime = Field(..., description="Timestamp do health check")
    version: str = Field(..., description="Versão da aplicação")
    services: Dict[str, str] = Field(..., description="Status dos serviços")
    environment: str = Field(..., description="Ambiente atual")
    uptime: float = Field(..., description="Tempo de atividade em segundos")


class ConfigurationUpdate(BaseModel):
    """Schema para atualização de configuração"""
    setting_name: str = Field(..., description="Nome da configuração")
    value: Any = Field(..., description="Novo valor")
    description: Optional[str] = Field(
        None, description="Descrição da mudança")
    requires_restart: bool = Field(
        default=False, description="Se requer reinicialização")


# =============================================================================
# VALIDADORES CUSTOMIZADOS
# =============================================================================

class DocumentSchemas:
    """Validador para schemas de documentos"""

    @validator('filename')
    def validate_filename(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Nome do arquivo não pode estar vazio")
        if len(v) > 255:
            raise ValueError("Nome do arquivo muito longo")
        return v.strip()

    @validator('size')
    def validate_size(cls, v):
        if v <= 0:
            raise ValueError("Tamanho do arquivo deve ser maior que zero")
        if v > 100 * 1024 * 1024:  # 100MB
            raise ValueError("Arquivo muito grande (máximo 100MB)")
        return v


class ProcessingSchemas:
    """Validador para schemas de processamento"""

    @validator('confidence_score', 'quality_score')
    def validate_score(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("Score deve estar entre 0.0 e 1.0")
        return v

    @validator('processing_time')
    def validate_processing_time(cls, v):
        if v < 0:
            raise ValueError("Tempo de processamento não pode ser negativo")
        return v


# Schemas de Documento
class DocumentoBase(BaseModel):
    """Schema base para documentos"""
    nome_arquivo: str = Field(..., description="Nome do arquivo original")
    tipo_documento: str = Field(..., description="Tipo do documento")
    extensao_arquivo: str = Field(..., description="Extensão do arquivo")
    tamanho_arquivo: int = Field(...,
                                 description="Tamanho do arquivo em bytes")


class DocumentoCreate(DocumentoBase):
    """Schema para criação de documento"""
    id: str = Field(..., description="ID único do documento")
    cliente_id: str = Field(..., description="ID do cliente")
    status_processamento: str = Field(
        default="processando", description="Status do processamento")


class DocumentoUpdate(BaseModel):
    """Schema para atualização de documento"""
    texto_extraido: Optional[str] = None
    dados_extraidos: Optional[Dict[str, Any]] = None
    confianca_classificacao: Optional[float] = None
    provider_extracao: Optional[str] = None
    qualidade_extracao: Optional[float] = None
    tempo_processamento: Optional[float] = None
    custo_processamento: Optional[float] = None
    status_processamento: Optional[str] = None
    data_processamento: Optional[datetime] = None


class DocumentoResponse(DocumentoBase):
    """Schema para resposta de documento"""
    id: str
    cliente_id: str
    texto_extraido: Optional[str] = None
    dados_extraidos: Optional[Dict[str, Any]] = None
    confianca_classificacao: Optional[float] = None
    provider_extracao: Optional[str] = None
    qualidade_extracao: Optional[float] = None
    tempo_processamento: Optional[float] = None
    custo_processamento: Optional[float] = None
    status_processamento: str
    data_upload: datetime
    data_processamento: Optional[datetime] = None
    erro: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Schemas de Cliente
class ClienteBase(BaseModel):
    """Schema base para clientes"""
    nome: str = Field(..., description="Nome do cliente")
    email: str = Field(..., description="Email do cliente")


class ClienteCreate(ClienteBase):
    """Schema para criação de cliente"""
    senha: str = Field(..., description="Senha do cliente")


class ClienteUpdate(BaseModel):
    """Schema para atualização de cliente"""
    nome: Optional[str] = None
    email: Optional[str] = None
    senha: Optional[str] = None
    ativo: Optional[bool] = None


class ClienteResponse(ClienteBase):
    """Schema para resposta de cliente"""
    id: str
    ativo: bool
    data_criacao: datetime
    data_atualizacao: datetime

    model_config = ConfigDict(from_attributes=True)


# Schemas de Log
class LogProcessamentoBase(BaseModel):
    """Schema base para logs de processamento"""
    documento_id: str = Field(..., description="ID do documento")
    cliente_id: str = Field(..., description="ID do cliente")
    operacao: str = Field(..., description="Tipo de operação")
    status: str = Field(..., description="Status da operação")


class LogProcessamentoCreate(LogProcessamentoBase):
    """Schema para criação de log"""
    provider: Optional[str] = None
    detalhes: Optional[Dict[str, Any]] = None
    tempo_execucao: Optional[float] = None


class LogProcessamentoResponse(LogProcessamentoBase):
    """Schema para resposta de log"""
    id: str
    provider: Optional[str] = None
    detalhes: Optional[Dict[str, Any]] = None
    tempo_execucao: Optional[float] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Schemas de Sessão
class SessaoUsoBase(BaseModel):
    """Schema base para sessões de uso"""
    session_id: str = Field(..., description="ID da sessão")
    cliente_id: str = Field(..., description="ID do cliente")


class SessaoUsoCreate(SessaoUsoBase):
    """Schema para criação de sessão"""
    pass


class SessaoUsoUpdate(BaseModel):
    """Schema para atualização de sessão"""
    fim_sessao: Optional[datetime] = None
    documentos_processados: Optional[int] = None
    documentos_sucesso: Optional[int] = None
    documentos_erro: Optional[int] = None
    custo_total_llm: Optional[float] = None
    custo_total_azure: Optional[float] = None
    custo_total: Optional[float] = None


class SessaoUsoResponse(SessaoUsoBase):
    """Schema para resposta de sessão"""
    id: str
    inicio_sessao: datetime
    fim_sessao: Optional[datetime] = None
    documentos_processados: int
    documentos_sucesso: int
    documentos_erro: int
    custo_total_llm: float
    custo_total_azure: float
    custo_total: float

    model_config = ConfigDict(from_attributes=True)


# Schemas de Consumo LLM
class ConsumoLLMBase(BaseModel):
    """Schema base para consumo de LLM"""
    session_id: str = Field(..., description="ID da sessão")
    modelo: str = Field(..., description="Modelo usado")
    operacao: str = Field(..., description="Tipo de operação")


class ConsumoLLMCreate(ConsumoLLMBase):
    """Schema para criação de consumo LLM"""
    cliente_id: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    tokens_total: Optional[int] = None
    custo_input: Optional[float] = None
    custo_output: Optional[float] = None
    custo_total: Optional[float] = None
    tempo_resposta: Optional[float] = None


class ConsumoLLMResponse(ConsumoLLMBase):
    """Schema para resposta de consumo LLM"""
    id: str
    cliente_id: Optional[str] = None
    tokens_input: int
    tokens_output: int
    tokens_total: int
    custo_input: float
    custo_output: float
    custo_total: float
    tempo_resposta: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Enums e constantes
class ProcessamentoStatus(str):
    """Status de processamento de documentos"""
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"
    CANCELADO = "cancelado"


class TipoDocumento(str):
    """Tipos de documentos suportados"""
    NOTA_FISCAL = "nota_fiscal"
    CONTRATO = "contrato"
    RELATORIO = "relatorio"
    RECIBO = "recibo"
    BOLETO = "boleto"
    EXTRATO = "extrato"
    DECLARACAO = "declaracao"
    CERTIFICADO = "certificado"
    DESCONHECIDO = "desconhecido"


# Schemas de resposta da API
class APIResponse(BaseModel):
    """Schema padrão para respostas da API"""
    success: bool = Field(...,
                          description="Indica se a operação foi bem-sucedida")
    message: str = Field(..., description="Mensagem descritiva")
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    """Schema para respostas paginadas"""
    items: List[Dict[str, Any]] = Field(..., description="Lista de itens")
    total: int = Field(..., description="Total de itens")
    page: int = Field(..., description="Página atual")
    size: int = Field(..., description="Tamanho da página")
    pages: int = Field(..., description="Total de páginas")


# Schemas de autenticação
class LoginRequest(BaseModel):
    """Schema para requisição de login"""
    email: str = Field(..., description="Email do usuário")
    senha: str = Field(..., description="Senha do usuário")


class TokenResponse(BaseModel):
    """Schema para resposta de token"""
    access_token: str = Field(..., description="Token de acesso")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")


class UserInfo(BaseModel):
    """Schema para informações do usuário"""
    id: str = Field(..., description="ID do usuário")
    nome: str = Field(..., description="Nome do usuário")
    email: str = Field(..., description="Email do usuário")
    ativo: bool = Field(..., description="Status do usuário")
    data_criacao: datetime = Field(..., description="Data de criação")
