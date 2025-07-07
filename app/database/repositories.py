"""
Repositories para acesso aos dados usando pattern repository
"""
from typing import List, Optional, Dict, Any, TypeVar, Generic
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, desc, asc
from datetime import datetime
import uuid

from app.core.logging import obter_logger
from app.models.database import (
    Base, Cliente, Documento, LogProcessamento, SessaoUso,
    ConsumoLLM, FeedbackClassificacao, FeedbackExtracao,
    UsoLLM, MetricasDesempenho, DocumentoVetorial
)

logger = obter_logger(__name__)

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """Repository base com operações CRUD genéricas"""

    def __init__(self, model: type[T]):
        self.model = model

    def create(self, db: Session, **kwargs) -> T:
        """Cria uma nova entidade"""
        try:
            instance = self.model(**kwargs)
            db.add(instance)
            db.commit()
            db.refresh(instance)
            logger.debug(
                f"Entidade {self.model.__name__} criada: {instance.id}")
            return instance
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao criar {self.model.__name__}: {e}")
            raise

    def get_by_id(self, db: Session, id: str) -> Optional[T]:
        """Busca entidade por ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[T]:
        """Busca todas as entidades com paginação"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def update(self, db: Session, id: str, **kwargs) -> Optional[T]:
        """Atualiza uma entidade"""
        try:
            instance = self.get_by_id(db, id)
            if instance:
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                db.commit()
                db.refresh(instance)
                logger.debug(
                    f"Entidade {self.model.__name__} atualizada: {id}")
                return instance
            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao atualizar {self.model.__name__}: {e}")
            raise

    def delete(self, db: Session, id: str) -> bool:
        """Remove uma entidade"""
        try:
            instance = self.get_by_id(db, id)
            if instance:
                db.delete(instance)
                db.commit()
                logger.debug(f"Entidade {self.model.__name__} removida: {id}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao remover {self.model.__name__}: {e}")
            raise

    def count(self, db: Session) -> int:
        """Conta total de entidades"""
        return db.query(self.model).count()

    # Métodos em português para compatibilidade
    def criar(self, db: Session, **kwargs) -> T:
        """Cria uma nova entidade (método em português)"""
        return self.create(db, **kwargs)

    def atualizar(self, db: Session, id: str, **kwargs) -> Optional[T]:
        """Atualiza uma entidade (método em português)"""
        return self.update(db, id, **kwargs)

    def obter_por_id(self, db: Session, id: str) -> Optional[T]:
        """Busca entidade por ID (método em português)"""
        return self.get_by_id(db, id)


class ClienteRepository(BaseRepository[Cliente]):
    """Repository para clientes"""

    def __init__(self):
        super().__init__(Cliente)

    def get_by_email(self, db: Session, email: str) -> Optional[Cliente]:
        """Busca cliente por email"""
        return db.query(Cliente).filter(Cliente.email == email).first()

    def get_active_clients(self, db: Session) -> List[Cliente]:
        """Busca clientes ativos"""
        return db.query(Cliente).filter(Cliente.ativo == True).all()

    def get_clients_with_documents(self, db: Session, limit: int = 10) -> List[Cliente]:
        """Busca clientes que têm documentos processados"""
        return db.query(Cliente).join(Documento).group_by(Cliente.id).limit(limit).all()


class DocumentoRepository(BaseRepository[Documento]):
    """Repository para documentos"""

    def __init__(self):
        super().__init__(Documento)

    def get_by_cliente(self, db: Session, cliente_id: str, skip: int = 0, limit: int = 50) -> List[Documento]:
        """Busca documentos de um cliente"""
        return db.query(Documento).filter(
            Documento.cliente_id == cliente_id
        ).order_by(desc(Documento.data_upload)).offset(skip).limit(limit).all()

    def get_by_tipo(self, db: Session, tipo_documento: str, skip: int = 0, limit: int = 50) -> List[Documento]:
        """Busca documentos por tipo"""
        return db.query(Documento).filter(
            Documento.tipo_documento == tipo_documento
        ).order_by(desc(Documento.data_upload)).offset(skip).limit(limit).all()

    def get_by_status(self, db: Session, status: str) -> List[Documento]:
        """Busca documentos por status"""
        return db.query(Documento).filter(Documento.status_processamento == status).all()

    def get_recent_documents(self, db: Session, days: int = 7) -> List[Documento]:
        """Busca documentos recentes"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return db.query(Documento).filter(
            Documento.data_upload >= cutoff_date
        ).order_by(desc(Documento.data_upload)).all()

    def get_documents_by_quality(self, db: Session, min_quality: float = 0.7) -> List[Documento]:
        """Busca documentos com qualidade mínima"""
        return db.query(Documento).filter(
            Documento.qualidade_extracao >= min_quality
        ).order_by(desc(Documento.qualidade_extracao)).all()

    def get_document_stats(self, db: Session, cliente_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtém estatísticas dos documentos"""
        query = db.query(Documento)

        if cliente_id:
            query = query.filter(Documento.cliente_id == cliente_id)

        total = query.count()
        processados = query.filter(
            Documento.status_processamento == "concluido").count()
        com_erro = query.filter(
            Documento.status_processamento == "erro").count()

        # Tipos mais comuns
        tipos = db.query(Documento.tipo_documento, db.func.count(Documento.id)).group_by(
            Documento.tipo_documento
        ).order_by(desc(db.func.count(Documento.id))).limit(5).all()

        return {
            "total": total,
            "processados": processados,
            "com_erro": com_erro,
            "taxa_sucesso": (processados / total * 100) if total > 0 else 0,
            "tipos_mais_comuns": dict(tipos)
        }


class LogProcessamentoRepository(BaseRepository[LogProcessamento]):
    """Repository para logs de processamento"""

    def __init__(self):
        super().__init__(LogProcessamento)

    def get_by_documento(self, db: Session, documento_id: str) -> List[LogProcessamento]:
        """Busca logs de um documento"""
        return db.query(LogProcessamento).filter(
            LogProcessamento.documento_id == documento_id
        ).order_by(desc(LogProcessamento.timestamp)).all()

    def get_by_operacao(self, db: Session, operacao: str, limit: int = 100) -> List[LogProcessamento]:
        """Busca logs por operação"""
        return db.query(LogProcessamento).filter(
            LogProcessamento.operacao == operacao
        ).order_by(desc(LogProcessamento.timestamp)).limit(limit).all()

    def get_recent_logs(self, db: Session, hours: int = 24) -> List[LogProcessamento]:
        """Busca logs recentes"""
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return db.query(LogProcessamento).filter(
            LogProcessamento.timestamp >= cutoff_time
        ).order_by(desc(LogProcessamento.timestamp)).all()

    def get_error_logs(self, db: Session, limit: int = 100) -> List[LogProcessamento]:
        """Busca logs de erro"""
        return db.query(LogProcessamento).filter(
            LogProcessamento.status == "erro"
        ).order_by(desc(LogProcessamento.timestamp)).limit(limit).all()


class SessaoUsoRepository(BaseRepository[SessaoUso]):
    """Repository para sessões de uso"""

    def __init__(self):
        super().__init__(SessaoUso)

    def get_by_cliente(self, db: Session, cliente_id: str) -> List[SessaoUso]:
        """Busca sessões de um cliente"""
        return db.query(SessaoUso).filter(
            SessaoUso.cliente_id == cliente_id
        ).order_by(desc(SessaoUso.inicio_sessao)).all()

    def get_active_sessions(self, db: Session) -> List[SessaoUso]:
        """Busca sessões ativas (sem fim_sessao)"""
        return db.query(SessaoUso).filter(
            SessaoUso.fim_sessao.is_(None)
        ).all()

    def get_session_stats(self, db: Session, cliente_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtém estatísticas das sessões"""
        query = db.query(SessaoUso)

        if cliente_id:
            query = query.filter(SessaoUso.cliente_id == cliente_id)

        total_sessions = query.count()
        total_docs = query.with_entities(db.func.sum(
            SessaoUso.documentos_processados)).scalar() or 0
        total_cost = query.with_entities(
            db.func.sum(SessaoUso.custo_total)).scalar() or 0.0

        return {
            "total_sessoes": total_sessions,
            "total_documentos": total_docs,
            "custo_total": total_cost,
            "media_docs_por_sessao": (total_docs / total_sessions) if total_sessions > 0 else 0
        }


class ConsumoLLMRepository(BaseRepository[ConsumoLLM]):
    """Repository para consumo de LLM"""

    def __init__(self):
        super().__init__(ConsumoLLM)

    def get_by_cliente(self, db: Session, cliente_id: str, days: int = 30) -> List[ConsumoLLM]:
        """Busca consumo de LLM de um cliente"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return db.query(ConsumoLLM).filter(
            and_(
                ConsumoLLM.cliente_id == cliente_id,
                ConsumoLLM.timestamp >= cutoff_date
            )
        ).order_by(desc(ConsumoLLM.timestamp)).all()

    def get_by_modelo(self, db: Session, modelo: str, limit: int = 100) -> List[ConsumoLLM]:
        """Busca consumo por modelo"""
        return db.query(ConsumoLLM).filter(
            ConsumoLLM.modelo == modelo
        ).order_by(desc(ConsumoLLM.timestamp)).limit(limit).all()

    def get_cost_summary(self, db: Session, cliente_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Obtém resumo de custos"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = db.query(ConsumoLLM).filter(
            ConsumoLLM.timestamp >= cutoff_date)

        if cliente_id:
            query = query.filter(ConsumoLLM.cliente_id == cliente_id)

        total_cost = query.with_entities(db.func.sum(
            ConsumoLLM.custo_total)).scalar() or 0.0
        total_tokens = query.with_entities(
            db.func.sum(ConsumoLLM.tokens_total)).scalar() or 0

        # Custo por modelo
        cost_by_model = db.query(
            ConsumoLLM.modelo,
            db.func.sum(ConsumoLLM.custo_total).label('custo_total'),
            db.func.sum(ConsumoLLM.tokens_total).label('tokens_total')
        ).filter(ConsumoLLM.timestamp >= cutoff_date).group_by(ConsumoLLM.modelo).all()

        return {
            "custo_total": total_cost,
            "tokens_total": total_tokens,
            "custo_por_modelo": {model: {"custo": custo, "tokens": tokens} for model, custo, tokens in cost_by_model}
        }


class FeedbackRepository:
    """Repository para feedbacks"""

    def __init__(self):
        self.classificacao_repo = BaseRepository(FeedbackClassificacao)
        self.extracao_repo = BaseRepository(FeedbackExtracao)

    def add_classification_feedback(
        self,
        db: Session,
        texto_documento: str,
        tipo_predito: str,
        tipo_correto: str,
        confianca_original: float,
        cliente_id: Optional[str] = None,
        documento_id: Optional[str] = None
    ) -> FeedbackClassificacao:
        """Adiciona feedback de classificação"""
        return self.classificacao_repo.create(
            db,
            texto_documento=texto_documento,
            tipo_predito=tipo_predito,
            tipo_correto=tipo_correto,
            confianca_original=confianca_original,
            cliente_id=cliente_id,
            documento_id=documento_id
        )

    def add_extraction_feedback(
        self,
        db: Session,
        texto_documento: str,
        tipo_documento: str,
        dados_extraidos_corretos: Dict[str, Any],
        dados_extraidos_originais: Optional[Dict[str, Any]] = None,
        cliente_id: Optional[str] = None,
        documento_id: Optional[str] = None
    ) -> FeedbackExtracao:
        """Adiciona feedback de extração"""
        return self.extracao_repo.create(
            db,
            texto_documento=texto_documento,
            tipo_documento=tipo_documento,
            dados_extraidos_corretos=dados_extraidos_corretos,
            dados_extraidos_originais=dados_extraidos_originais,
            cliente_id=cliente_id,
            documento_id=documento_id
        )

    def get_classification_feedback(self, db: Session, tipo_documento: str, limit: int = 50) -> List[FeedbackClassificacao]:
        """Busca feedback de classificação por tipo de documento"""
        return db.query(FeedbackClassificacao).filter(
            FeedbackClassificacao.tipo_correto == tipo_documento
        ).order_by(desc(FeedbackClassificacao.timestamp)).limit(limit).all()

    def get_extraction_feedback(self, db: Session, tipo_documento: str, limit: int = 50) -> List[FeedbackExtracao]:
        """Busca feedback de extração por tipo de documento"""
        return db.query(FeedbackExtracao).filter(
            FeedbackExtracao.tipo_documento == tipo_documento
        ).order_by(desc(FeedbackExtracao.timestamp)).limit(limit).all()


class MetricasRepository(BaseRepository[MetricasDesempenho]):
    """Repository para métricas de desempenho"""

    def __init__(self):
        super().__init__(MetricasDesempenho)

    def get_recent_metrics(self, db: Session, hours: int = 24) -> List[MetricasDesempenho]:
        """Busca métricas recentes"""
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return db.query(MetricasDesempenho).filter(
            MetricasDesempenho.data_medicao >= cutoff_time
        ).order_by(desc(MetricasDesempenho.data_medicao)).all()

    def get_endpoint_metrics(self, db: Session, endpoint: str, days: int = 7) -> List[MetricasDesempenho]:
        """Busca métricas de um endpoint específico"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return db.query(MetricasDesempenho).filter(
            and_(
                MetricasDesempenho.endpoint == endpoint,
                MetricasDesempenho.data_medicao >= cutoff_date
            )
        ).order_by(desc(MetricasDesempenho.data_medicao)).all()


class DocumentoVetorialRepository(BaseRepository[DocumentoVetorial]):
    """Repository para documentos vetoriais"""

    def __init__(self):
        super().__init__(DocumentoVetorial)

    def get_by_documento(self, db: Session, documento_id: str) -> List[DocumentoVetorial]:
        """Busca vetores de um documento"""
        return db.query(DocumentoVetorial).filter(
            DocumentoVetorial.documento_id == documento_id
        ).all()

    def get_by_tipo(self, db: Session, tipo_documento: str) -> List[DocumentoVetorial]:
        """Busca vetores por tipo de documento"""
        return db.query(DocumentoVetorial).filter(
            DocumentoVetorial.tipo_documento == tipo_documento
        ).all()

    def get_most_used(self, db: Session, limit: int = 10) -> List[DocumentoVetorial]:
        """Busca documentos vetoriais mais utilizados"""
        return db.query(DocumentoVetorial).order_by(
            desc(DocumentoVetorial.uso_count)
        ).limit(limit).all()


# Instâncias globais dos repositories
cliente_repo = ClienteRepository()
documento_repo = DocumentoRepository()
log_repo = LogProcessamentoRepository()
sessao_repo = SessaoUsoRepository()
consumo_llm_repo = ConsumoLLMRepository()
feedback_repo = FeedbackRepository()
metricas_repo = MetricasRepository()
documento_vetorial_repo = DocumentoVetorialRepository()
