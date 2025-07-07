"""Modelos de banco de dados para o sistema ETL Documentos"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Cliente(Base):
    """Modelo para clientes do sistema"""
    __tablename__ = "clientes"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)

    # Sistema de API Keys
    api_key = Column(String(64), unique=True, nullable=True)
    api_key_hash = Column(String(255), nullable=True)
    api_key_created_at = Column(DateTime, nullable=True)
    api_key_last_used = Column(DateTime, nullable=True)

    # Sistema de Planos e Quotas
    plano_tipo = Column(String(50), default="free")  # free, basic, premium
    quota_documentos_mes = Column(Integer, default=10)
    quota_tokens_mes = Column(Integer, default=10000)
    rate_limit_por_minuto = Column(Integer, default=10)

    # Contadores de uso
    documentos_processados_mes = Column(Integer, default=0)
    tokens_consumidos_mes = Column(Integer, default=0)
    custo_total_mes = Column(Float, default=0.0)

    # Reset de contadores
    mes_referencia = Column(
        String(7), default=lambda: datetime.utcnow().strftime("%Y-%m"))

    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    documentos = relationship("Documento", back_populates="cliente")
    sessoes = relationship("SessaoUso", back_populates="cliente")
    logs_processamento = relationship(
        "LogProcessamento", back_populates="cliente")
    consumos_llm = relationship("ConsumoLLM", back_populates="cliente")
    feedbacks_classificacao = relationship(
        "FeedbackClassificacao", back_populates="cliente")
    feedbacks_extracao = relationship(
        "FeedbackExtracao", back_populates="cliente")
    metricas_performance = relationship(
        "MetricasDesempenho", back_populates="cliente")
    usos_llm = relationship("UsoLLM", back_populates="cliente")


class Documento(Base):
    """Modelo para documentos processados"""
    __tablename__ = "documentos"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=False)
    nome_arquivo = Column(String(255), nullable=False)
    tipo_documento = Column(String(100), nullable=False)
    extensao_arquivo = Column(String(10), nullable=False)
    tamanho_arquivo = Column(Integer, nullable=False)
    texto_extraido = Column(Text)
    dados_extraidos = Column(JSON)
    confianca_classificacao = Column(Float, default=0.0)
    provider_extracao = Column(String(50))
    qualidade_extracao = Column(Float, default=0.0)
    tempo_processamento = Column(Float, default=0.0)
    custo_processamento = Column(Float, default=0.0)
    status_processamento = Column(String(50), default="processando")
    data_upload = Column(DateTime, default=datetime.utcnow)
    data_processamento = Column(DateTime)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="documentos")
    logs = relationship("LogProcessamento", back_populates="documento")
    vetoriais = relationship("DocumentoVetorial", back_populates="documento")


class LogProcessamento(Base):
    """Logs detalhados de processamento"""
    __tablename__ = "logs_processamento"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    documento_id = Column(String(36), ForeignKey(
        "documentos.id"), nullable=False)
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=True)
    operacao = Column(String(100), nullable=False)
    provider = Column(String(50))
    status = Column(String(50), nullable=False)
    detalhes = Column(JSON)
    tempo_execucao = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    documento = relationship("Documento", back_populates="logs")
    cliente = relationship("Cliente", back_populates="logs_processamento")


class SessaoUso(Base):
    """Sessões de uso para rastreamento de custos"""
    __tablename__ = "sessoes_uso"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    session_id = Column(String(100), unique=True, nullable=False)
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=False)
    inicio_sessao = Column(DateTime, default=datetime.utcnow)
    fim_sessao = Column(DateTime)
    documentos_processados = Column(Integer, default=0)
    documentos_sucesso = Column(Integer, default=0)
    documentos_erro = Column(Integer, default=0)
    custo_total_llm = Column(Float, default=0.0)
    custo_total_azure = Column(Float, default=0.0)
    custo_total = Column(Float, default=0.0)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="sessoes")
    consumos_llm = relationship("ConsumoLLM", back_populates="sessao")


class ConsumoLLM(Base):
    """Rastreamento detalhado de uso de LLM"""
    __tablename__ = "consumo_llm"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    session_id = Column(String(100), ForeignKey(
        "sessoes_uso.session_id"), nullable=False)
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=True)
    modelo = Column(String(100), nullable=False)
    operacao = Column(String(100), nullable=False)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)
    custo_input = Column(Float, default=0.0)
    custo_output = Column(Float, default=0.0)
    custo_total = Column(Float, default=0.0)
    tempo_resposta = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    sessao = relationship("SessaoUso", back_populates="consumos_llm")
    cliente = relationship("Cliente", back_populates="consumos_llm")


class FeedbackClassificacao(Base):
    """Feedback para melhorar classificação"""
    __tablename__ = "feedback_classificacao"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    documento_id = Column(String(36), nullable=True)
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=True)
    texto_documento = Column(Text, nullable=False)
    tipo_predito = Column(String(100), nullable=False)
    tipo_correto = Column(String(100), nullable=False)
    confianca_original = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="feedbacks_classificacao")


class FeedbackExtracao(Base):
    """Feedback para melhorar extração"""
    __tablename__ = "feedback_extracao"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    documento_id = Column(String(36), nullable=True)
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=True)
    texto_documento = Column(Text, nullable=False)
    tipo_documento = Column(String(100), nullable=False)
    dados_extraidos_originais = Column(JSON)
    dados_extraidos_corretos = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="feedbacks_extracao")


class UsoLLM(Base):
    """Modelo para rastreamento de uso de LLM (legacy)"""
    __tablename__ = "uso_llm"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(36), ForeignKey("clientes.id"))
    documento_id = Column(String, index=True)
    modelo = Column(String)
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    custo = Column(Float)
    operacao = Column(String)
    data_criacao = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="usos_llm")


class MetricasDesempenho(Base):
    """Métricas de desempenho do sistema"""
    __tablename__ = "metricas_desempenho"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=True)
    data_medicao = Column(DateTime, default=datetime.utcnow)
    endpoint = Column(String(100), nullable=False)
    tempo_resposta_medio = Column(Float, default=0.0)
    total_requisicoes = Column(Integer, default=0)
    taxa_sucesso = Column(Float, default=0.0)
    taxa_erro = Column(Float, default=0.0)
    uso_memoria_mb = Column(Float, default=0.0)
    uso_cpu_percent = Column(Float, default=0.0)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="metricas_performance")


# Alias para compatibilidade
MetricasPerformance = MetricasDesempenho


class DocumentoVetorial(Base):
    """Documentos no banco vetorial"""
    __tablename__ = "documentos_vetoriais"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    documento_id = Column(String(36), ForeignKey(
        "documentos.id"), nullable=False)
    vetor_id = Column(String(255), nullable=False)
    tipo_documento = Column(String(100), nullable=False)
    texto_indexado = Column(Text)
    metadados = Column(JSON)
    confianca_inicial = Column(Float, default=0.0)
    feedback_aplicado = Column(Boolean, default=False)
    uso_count = Column(Integer, default=0)
    data_criacao = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    documento = relationship("Documento", back_populates="vetoriais")


class UsoDetalhadoCliente(Base):
    """Rastreamento detalhado de uso por cliente"""
    __tablename__ = "uso_detalhado_cliente"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=False)
    documento_id = Column(String(36), nullable=True)
    session_id = Column(String(100), nullable=True)

    # Tipo de operação
    # classification, extraction, embedding
    operacao = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)   # openai, azure, docling

    # Métricas de LLM
    modelo_llm = Column(String(100), nullable=True)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)

    # Custos
    custo_input = Column(Float, default=0.0)
    custo_output = Column(Float, default=0.0)
    custo_total = Column(Float, default=0.0)

    # Performance
    tempo_execucao = Column(Float, default=0.0)
    sucesso = Column(Boolean, default=True)
    erro = Column(Text, nullable=True)

    # Metadados
    metadados = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    cliente = relationship("Cliente")
