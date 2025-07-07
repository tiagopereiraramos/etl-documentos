"""Serviço de rastreamento de custos e métricas de uso"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import UsoLLM, SessaoUso, MetricasDesempenho

logger = logging.getLogger(__name__)


class CostService:
    """Serviço para cálculo e tracking de custos"""

    # Preços por 1K tokens (aproximados)
    PRECOS_OPENAI = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
        "text-embedding-3-large": {"input": 0.00013, "output": 0.0}
    }

    PRECOS_AZURE = {
        "document_intelligence": 0.001  # Por página
    }

    def __init__(self):
        self.logger = logger

    def calcular_custo_openai(
        self,
        modelo: str,
        tokens_input: int,
        tokens_output: int = 0
    ) -> float:
        """Calcula custo para modelos OpenAI"""
        if modelo not in self.PRECOS_OPENAI:
            self.logger.warning(f"Modelo {modelo} não encontrado nos preços")
            return 0.0

        precos = self.PRECOS_OPENAI[modelo]
        custo_input = (tokens_input / 1000) * precos["input"]
        custo_output = (tokens_output / 1000) * precos["output"]

        return custo_input + custo_output

    def calcular_custo_azure(self, operacao: str, quantidade: int = 1) -> float:
        """Calcula custo para Azure Document Intelligence"""
        if operacao not in self.PRECOS_AZURE:
            return 0.0

        return quantidade * self.PRECOS_AZURE[operacao]

    def registrar_uso(
        self,
        provedor: str,
        modelo: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        custo: float = 0.0,
        metadados: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Registra uso e retorna informações de custo"""
        return {
            "provedor": provedor,
            "modelo": modelo,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "tokens_total": tokens_input + tokens_output,
            "custo": custo,
            "timestamp": datetime.utcnow().isoformat(),
            "metadados": metadados or {}
        }


class CostTrackingService:
    """Serviço para rastreamento de custos de LLMs, Azure e outras operações"""

    def __init__(self):
        """Inicializa o serviço de rastreamento de custos"""
        logger.info("Serviço de rastreamento de custos inicializado")

    def record_llm_usage(
        self,
        call_id: str,
        model: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        success: bool,
        processing_time: float,
        document_id: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> Dict[str, float]:
        """Registra uso de LLM e calcula custos"""
        try:
            # Calcular custos
            costs = self._calculate_llm_costs(
                model, input_tokens, output_tokens)

            # Registrar no banco se sessão disponível
            if db_session:
                uso_llm = UsoLLM(
                    call_id=call_id,
                    documento_id=int(document_id) if document_id else None,
                    modelo=model,
                    operacao=operation,
                    tokens_entrada=input_tokens,
                    tokens_saida=output_tokens,
                    custo_entrada=costs["input_cost"],
                    custo_saida=costs["output_cost"],
                    custo_total=costs["total_cost"],
                    tempo_resposta=processing_time,
                    sucesso=success,
                    erro=error,
                    metadados=metadata or {}
                )

                db_session.add(uso_llm)
                db_session.commit()

                logger.debug(
                    f"Uso de LLM registrado: {call_id} - ${costs['total_cost']:.4f}")

            return costs

        except Exception as e:
            logger.error(f"Erro ao registrar uso de LLM: {str(e)}")
            return {"input_cost": 0.0, "output_cost": 0.0, "total_cost": 0.0}

    def record_azure_usage(
        self,
        operation_type: str,
        pages_processed: int,
        success: bool,
        processing_time: float,
        document_id: Optional[str] = None,
        error: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> float:
        """
        Registra uso do Azure Document Intelligence
        """
        try:
            # Calcular custo baseado no tipo de operação
            if operation_type == "read":
                cost = pages_processed * settings.AZURE_COSTS["read_operation"]
            elif operation_type == "prebuilt":
                cost = pages_processed * \
                    settings.AZURE_COSTS["prebuilt_operation"]
            else:
                cost = 0.0

            # Registrar no banco (implementar tabela específica se necessário)
            # Por enquanto, usar metadados no UsoLLM
            if db_session and document_id:
                uso_azure = UsoLLM(
                    call_id=f"azure_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    documento_id=int(document_id),
                    modelo="azure_document_intelligence",
                    operacao=operation_type,
                    tokens_entrada=0,
                    tokens_saida=0,
                    custo_entrada=0.0,
                    custo_saida=0.0,
                    custo_total=cost,
                    tempo_resposta=processing_time,
                    sucesso=success,
                    erro=error,
                    metadados={
                        "service": "azure",
                        "operation_type": operation_type,
                        "pages_processed": pages_processed
                    }
                )

                db_session.add(uso_azure)
                db_session.commit()

            logger.debug(
                f"Uso do Azure registrado: {operation_type} - ${cost:.4f}")
            return cost

        except Exception as e:
            logger.error(f"Erro ao registrar uso do Azure: {str(e)}")
            return 0.0

    def _calculate_llm_costs(self, model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """Calcula custos de um modelo LLM"""
        try:
            model_pricing = settings.MODEL_COSTS.get(
                model, {"input": 0.0, "output": 0.0})
        except:
            model_pricing = {"input": 0.0, "output": 0.0}

        # Custos por 1K tokens
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }

    def get_session_costs(self, session_id: str, db_session: Session) -> Dict[str, Any]:
        """
        Obtém custos de uma sessão específica
        """
        try:
            # Buscar dados da sessão
            sessao = db_session.query(SessaoUso).filter(
                SessaoUso.session_id == session_id
            ).first()

            if not sessao:
                return {"error": "Sessão não encontrada"}

            # Buscar usos de LLM da sessão (aproximação por timestamp)
            inicio = sessao.inicio_sessao
            fim = sessao.fim_sessao or datetime.now()

            usos_llm = db_session.query(UsoLLM).filter(
                UsoLLM.criado_em >= inicio,
                UsoLLM.criado_em <= fim
            ).all()

            # Calcular totais
            total_llm_cost = sum(uso.custo_total for uso in usos_llm)
            total_tokens = sum(uso.tokens_entrada +
                               uso.tokens_saida for uso in usos_llm)

            # Estatísticas por modelo
            costs_by_model = {}
            for uso in usos_llm:
                if uso.modelo not in costs_by_model:
                    costs_by_model[uso.modelo] = {
                        "calls": 0,
                        "total_cost": 0.0,
                        "total_tokens": 0
                    }

                costs_by_model[uso.modelo]["calls"] += 1
                costs_by_model[uso.modelo]["total_cost"] += uso.custo_total
                costs_by_model[uso.modelo]["total_tokens"] += uso.tokens_entrada + \
                    uso.tokens_saida

            return {
                "session_id": session_id,
                "total_llm_cost": total_llm_cost,
                "total_tokens": total_tokens,
                "total_calls": len(usos_llm),
                "costs_by_model": costs_by_model,
                "session_duration": (fim - inicio).total_seconds(),
                "documents_processed": sessao.documentos_processados
            }

        except Exception as e:
            logger.error(f"Erro ao obter custos da sessão: {str(e)}")
            return {"error": str(e)}

    def get_daily_costs(self, date: datetime, db_session: Session) -> Dict[str, Any]:
        """
        Obtém custos de um dia específico
        """
        try:
            start_date = date.replace(
                hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            # Consultar usos do dia
            usos_dia = db_session.query(UsoLLM).filter(
                UsoLLM.criado_em >= start_date,
                UsoLLM.criado_em <= end_date
            ).all()

            # Calcular totais
            total_cost = sum(uso.custo_total for uso in usos_dia)
            total_tokens = sum(uso.tokens_entrada +
                               uso.tokens_saida for uso in usos_dia)
            successful_calls = sum(1 for uso in usos_dia if uso.sucesso)

            # Custos por operação
            costs_by_operation = {}
            for uso in usos_dia:
                op = uso.operacao
                if op not in costs_by_operation:
                    costs_by_operation[op] = {"calls": 0, "cost": 0.0}

                costs_by_operation[op]["calls"] += 1
                costs_by_operation[op]["cost"] += uso.custo_total

            return {
                "date": date.strftime("%Y-%m-%d"),
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "total_calls": len(usos_dia),
                "successful_calls": successful_calls,
                "success_rate": successful_calls / len(usos_dia) if usos_dia else 0,
                "costs_by_operation": costs_by_operation
            }

        except Exception as e:
            logger.error(f"Erro ao obter custos diários: {str(e)}")
            return {"error": str(e)}

    def update_session_metrics(
        self,
        session_id: str,
        documents_processed: int,
        documents_success: int,
        documents_error: int,
        db_session: Session
    ):
        """
        Atualiza métricas de uma sessão
        """
        try:
            sessao = db_session.query(SessaoUso).filter(
                SessaoUso.session_id == session_id
            ).first()

            if sessao:
                sessao.documentos_processados = documents_processed
                sessao.documentos_sucesso = documents_success
                sessao.documentos_erro = documents_error

                # Calcular custos totais da sessão
                total_costs = self.get_session_costs(session_id, db_session)
                if "total_llm_cost" in total_costs:
                    sessao.custo_total_llm = total_costs["total_llm_cost"]
                    # + outros custos
                    sessao.custo_total = total_costs["total_llm_cost"]

                db_session.commit()
                logger.debug(f"Métricas de sessão atualizadas: {session_id}")

        except Exception as e:
            logger.error(f"Erro ao atualizar métricas de sessão: {str(e)}")

    def generate_cost_report(
        self,
        start_date: datetime,
        end_date: datetime,
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Gera relatório de custos para um período
        """
        try:
            # Consultar usos do período
            usos_periodo = db_session.query(UsoLLM).filter(
                UsoLLM.criado_em >= start_date,
                UsoLLM.criado_em <= end_date
            ).all()

            if not usos_periodo:
                return {"message": "Nenhum uso encontrado no período"}

            # Calcular totais
            total_cost = sum(uso.custo_total for uso in usos_periodo)
            total_tokens = sum(uso.tokens_entrada +
                               uso.tokens_saida for uso in usos_periodo)

            # Análise por modelo
            by_model = {}
            for uso in usos_periodo:
                model = uso.modelo
                if model not in by_model:
                    by_model[model] = {
                        "calls": 0,
                        "cost": 0.0,
                        "tokens": 0,
                        "avg_response_time": 0.0
                    }

                by_model[model]["calls"] += 1
                by_model[model]["cost"] += uso.custo_total
                by_model[model]["tokens"] += uso.tokens_entrada + \
                    uso.tokens_saida
                by_model[model]["avg_response_time"] += uso.tempo_resposta or 0

            # Calcular médias
            for model_data in by_model.values():
                if model_data["calls"] > 0:
                    model_data["avg_response_time"] /= model_data["calls"]
                    model_data["cost_per_call"] = model_data["cost"] / \
                        model_data["calls"]
                    model_data["tokens_per_call"] = model_data["tokens"] / \
                        model_data["calls"]

            # Análise por operação
            by_operation = {}
            for uso in usos_periodo:
                op = uso.operacao
                if op not in by_operation:
                    by_operation[op] = {"calls": 0, "cost": 0.0}

                by_operation[op]["calls"] += 1
                by_operation[op]["cost"] += uso.custo_total

            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": (end_date - start_date).days
                },
                "totals": {
                    "cost": total_cost,
                    "tokens": total_tokens,
                    "calls": len(usos_periodo),
                    "avg_cost_per_call": total_cost / len(usos_periodo),
                    "avg_tokens_per_call": total_tokens / len(usos_periodo)
                },
                "by_model": by_model,
                "by_operation": by_operation
            }

        except Exception as e:
            logger.error(f"Erro ao gerar relatório de custos: {str(e)}")
            return {"error": str(e)}
