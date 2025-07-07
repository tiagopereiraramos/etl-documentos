"""
Modified code based on the provided instructions and original code.
"""
"""
Serviço de Analytics e Relatórios por Cliente
Fornece métricas detalhadas e insights de uso
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.logging import obter_logger
from app.models.database import (
    Cliente, Documento, LogProcessamento, SessaoUso, 
    ConsumoLLM, MetricasPerformance
)

logger = obter_logger(__name__)

class AnalyticsService:
    """Serviço para analytics e relatórios detalhados por cliente"""

    @staticmethod
    def get_client_dashboard(
        client_id: str, 
        db_session: Session,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Dashboard completo do cliente com métricas dos últimos N dias
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)

            # Métricas básicas
            total_docs = db_session.query(Documento).filter(
                Documento.cliente_id == client_id,
                Documento.data_upload >= start_date
            ).count()

            docs_sucesso = db_session.query(Documento).filter(
                Documento.cliente_id == client_id,
                Documento.status_processamento == "sucesso",
                Documento.data_upload >= start_date
            ).count()

            docs_erro = db_session.query(Documento).filter(
                Documento.cliente_id == client_id,
                Documento.status_processamento == "erro",
                Documento.data_upload >= start_date
            ).count()

            # Custos
            custo_total = db_session.query(func.sum(Documento.custo_processamento)).filter(
                Documento.cliente_id == client_id,
                Documento.data_upload >= start_date
            ).scalar() or 0.0

            # Tempo médio de processamento
            tempo_medio = db_session.query(func.avg(Documento.tempo_processamento)).filter(
                Documento.cliente_id == client_id,
                Documento.status_processamento == "sucesso",
                Documento.data_upload >= start_date
            ).scalar() or 0.0

            # Tipos de documentos mais processados
            tipos_documentos = db_session.query(
                Documento.tipo_documento,
                func.count(Documento.id).label('quantidade')
            ).filter(
                Documento.cliente_id == client_id,
                Documento.data_upload >= start_date
            ).group_by(Documento.tipo_documento).order_by(desc('quantidade')).limit(10).all()

            # Uso de LLM
            consumo_llm = db_session.query(
                func.sum(ConsumoLLM.tokens_total).label('total_tokens'),
                func.sum(ConsumoLLM.custo_total).label('total_custo_llm')
            ).join(SessaoUso).filter(
                SessaoUso.cliente_id == client_id,
                ConsumoLLM.timestamp >= start_date
            ).first()

            # Sessões ativas
            sessoes_periodo = db_session.query(SessaoUso).filter(
                SessaoUso.cliente_id == client_id,
                SessaoUso.inicio_sessao >= start_date
            ).count()

            # Qualidade média das extrações
            qualidade_media = db_session.query(func.avg(Documento.qualidade_extracao)).filter(
                Documento.cliente_id == client_id,
                Documento.status_processamento == "sucesso",
                Documento.data_upload >= start_date
            ).scalar() or 0.0

            return {
                "periodo": {
                    "inicio": start_date.isoformat(),
                    "fim": end_date.isoformat(),
                    "dias": period_days
                },
                "documentos": {
                    "total": total_docs,
                    "sucesso": docs_sucesso,
                    "erro": docs_erro,
                    "taxa_sucesso": (docs_sucesso / total_docs * 100) if total_docs > 0 else 0
                },
                "performance": {
                    "tempo_medio_processamento": round(tempo_medio, 2),
                    "qualidade_media_extracao": round(qualidade_media, 2)
                },
                "custos": {
                    "total": round(custo_total, 4),
                    "llm": round(consumo_llm.total_custo_llm or 0, 4),
                    "custo_por_documento": round(custo_total / total_docs, 4) if total_docs > 0 else 0
                },
                "uso_llm": {
                    "total_tokens": int(consumo_llm.total_tokens or 0),
                    "tokens_por_documento": int((consumo_llm.total_tokens or 0) / total_docs) if total_docs > 0 else 0
                },
                "tipos_documentos": [
                    {"tipo": tipo.tipo_documento, "quantidade": tipo.quantidade}
                    for tipo in tipos_documentos
                ],
                "sessoes_periodo": sessoes_periodo
            }

        except Exception as e:
            logger.error(f"Erro ao gerar dashboard do cliente {client_id}: {str(e)}")
            return {"erro": str(e)}

    @staticmethod
    def get_document_timeline(
        client_id: str,
        db_session: Session,
        document_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Timeline de processamento de documentos com logs detalhados
        """
        try:
            query = db_session.query(LogProcessamento).join(Documento).filter(
                Documento.cliente_id == client_id
            )

            if document_id:
                query = query.filter(LogProcessamento.documento_id == document_id)

            logs = query.order_by(desc(LogProcessamento.timestamp)).limit(limit).all()

            timeline = []
            for log in logs:
                timeline.append({
                    "timestamp": log.timestamp.isoformat(),
                    "documento_id": log.documento_id,
                    "documento_nome": log.documento.nome_arquivo,
                    "operacao": log.operacao,
                    "provider": log.provider,
                    "status": log.status,
                    "tempo_execucao": log.tempo_execucao,
                    "detalhes": log.detalhes
                })

            return timeline

        except Exception as e:
            logger.error(f"Erro ao gerar timeline: {str(e)}")
            return []

    @staticmethod
    def get_cost_breakdown(
        client_id: str,
        db_session: Session,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Breakdown detalhado de custos por cliente
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)

            # Custos por tipo de documento
            custos_por_tipo = db_session.query(
                Documento.tipo_documento,
                func.count(Documento.id).label('quantidade'),
                func.sum(Documento.custo_processamento).label('custo_total'),
                func.avg(Documento.custo_processamento).label('custo_medio')
            ).filter(
                Documento.cliente_id == client_id,
                Documento.data_upload >= start_date
            ).group_by(Documento.tipo_documento).all()

            # Custos por provedor
            custos_por_provider = db_session.query(
                Documento.provider_extracao,
                func.count(Documento.id).label('quantidade'),
                func.sum(Documento.custo_processamento).label('custo_total')
            ).filter(
                Documento.cliente_id == client_id,
                Documento.data_upload >= start_date
            ).group_by(Documento.provider_extracao).all()

            # Uso de LLM por modelo
            uso_llm_por_modelo = db_session.query(
                ConsumoLLM.modelo,
                func.sum(ConsumoLLM.tokens_total).label('tokens'),
                func.sum(ConsumoLLM.custo_total).label('custo')
            ).join(SessaoUso).filter(
                SessaoUso.cliente_id == client_id,
                ConsumoLLM.timestamp >= start_date
            ).group_by(ConsumoLLM.modelo).all()

            return {
                "periodo": f"{period_days} dias",
                "custos_por_tipo": [
                    {
                        "tipo": item.tipo_documento,
                        "quantidade": item.quantidade,
                        "custo_total": round(item.custo_total or 0, 4),
                        "custo_medio": round(item.custo_medio or 0, 4)
                    }
                    for item in custos_por_tipo
                ],
                "custos_por_provider": [
                    {
                        "provider": item.provider_extracao or "desconhecido",
                        "quantidade": item.quantidade,
                        "custo_total": round(item.custo_total or 0, 4)
                    }
                    for item in custos_por_provider
                ],
                "uso_llm_por_modelo": [
                    {
                        "modelo": item.modelo,
                        "tokens": int(item.tokens),
                        "custo": round(item.custo or 0, 4)
                    }
                    for item in uso_llm_por_modelo
                ]
            }

        except Exception as e:
            logger.error(f"Erro ao gerar breakdown de custos: {str(e)}")
            return {"erro": str(e)}

    @staticmethod
    def record_performance_metrics(
        endpoint: str,
        response_time: float,
        success: bool,
        db_session: Session
    ) -> None:
        """
        Registra métricas de performance do sistema
        """
        try:
            # Buscar métricas do dia atual
            today = datetime.utcnow().date()
            metrics = db_session.query(MetricasPerformance).filter(
                func.date(MetricasPerformance.data_medicao) == today,
                MetricasPerformance.endpoint == endpoint
            ).first()

            if not metrics:
                metrics = MetricasPerformance(
                    endpoint=endpoint,
                    data_medicao=datetime.utcnow(),
                    tempo_resposta_medio=response_time,
                    total_requisicoes=1,
                    taxa_sucesso=100.0 if success else 0.0,
                    taxa_erro=0.0 if success else 100.0
                )
                db_session.add(metrics)
            else:
                # Atualizar métricas existentes
                total_req = metrics.total_requisicoes + 1
                novo_tempo_medio = (
                    (metrics.tempo_resposta_medio * metrics.total_requisicoes + response_time) / total_req
                )

                sucessos = (metrics.taxa_sucesso / 100 * metrics.total_requisicoes) + (1 if success else 0)
                nova_taxa_sucesso = (sucessos / total_req) * 100

                metrics.tempo_resposta_medio = novo_tempo_medio
                metrics.total_requisicoes = total_req
                metrics.taxa_sucesso = nova_taxa_sucesso
                metrics.taxa_erro = 100 - nova_taxa_sucesso

            db_session.commit()

        except Exception as e:
            logger.error(f"Erro ao registrar métricas de performance: {str(e)}")
            db_session.rollback()

    async def get_dashboard_data(
        self,
        periodo_dias: int = 30,
        db_session: Session = None
    ) -> Dict[str, Any]:
        """Gera dados completos para dashboard"""
        try:
            from datetime import datetime, timedelta
            from app.models.database import ProcessamentoDocumento, FeedbackExtracao
            data_inicio = datetime.now() - timedelta(days=periodo_dias)

            # Consultar processamentos do período
            processamentos = db_session.query(ProcessamentoDocumento).filter(
                ProcessamentoDocumento.data_criacao >= data_inicio
            ).all()

            # Estatísticas básicas
            total_documentos = len(processamentos)
            sucessos = len([p for p in processamentos if p.status == "concluido"])
            taxa_sucesso = (sucessos / total_documentos * 100) if total_documentos > 0 else 0

            # Tipos mais processados
            tipos_contagem = {}
            tempos_processamento = []
            custos_total = 0.0

            for proc in processamentos:
                tipo = proc.tipo_documento or "Não Classificado"
                tipos_contagem[tipo] = tipos_contagem.get(tipo, 0) + 1

                if proc.tempo_processamento:
                    tempos_processamento.append(proc.tempo_processamento)

                if proc.custo_total:
                    custos_total += proc.custo_total

            # Calcular tempo médio
            tempo_medio = sum(tempos_processamento) / len(tempos_processamento) if tempos_processamento else 0.0

            # Documentos por dia (últimos 7 dias)
            documentos_por_dia = {}
            for i in range(7):
                data = (datetime.now() - timedelta(days=i)).date()
                count = len([p for p in processamentos if p.data_criacao.date() == data])
                documentos_por_dia[data.isoformat()] = count

            return {
                "periodo_dias": periodo_dias,
                "total_documentos": total_documentos,
                "documentos_sucesso": sucessos,
                "taxa_sucesso": round(taxa_sucesso, 2),
                "tipos_mais_processados": dict(sorted(tipos_contagem.items(), key=lambda x: x[1], reverse=True)[:5]),
                "tempo_medio_processamento": round(tempo_medio, 2),
                "custos_total_periodo": round(custos_total, 4),
                "documentos_por_dia": documentos_por_dia,
                "estatisticas_detalhadas": {
                    "documentos_com_erro": total_documentos - sucessos,
                    "tempo_min": min(tempos_processamento) if tempos_processamento else 0,
                    "tempo_max": max(tempos_processamento) if tempos_processamento else 0,
                    "custo_medio_documento": round(custos_total / total_documentos, 6) if total_documentos > 0 else 0
                }
            }
        except Exception as e:
            logger.error(f"Erro ao gerar dashboard: {e}")
            return {"error": str(e)}

    async def get_performance_metrics(
        self,
        db_session: Session = None
    ) -> Dict[str, Any]:
        """Retorna métricas detalhadas de performance"""
        try:
            from app.models.database import ProcessamentoDocumento
            # Consultar dados de performance
            processamentos = db_session.query(ProcessamentoDocumento)\
            .order_by(ProcessamentoDocumento.data_criacao.desc()).limit(1000).all()

            if not processamentos:
                return {"message": "Nenhum dado de performance disponível"}

            # Métricas de tempo por etapa
            tempos_extracao = []
            tempos_classificacao = []
            tempos_dados = []

            for proc in processamentos:
                metadados = proc.metadados or {}
                if 'extracao_tempo' in metadados:
                    tempos_extracao.append(metadados['extracao_tempo'])
                if 'classificacao_tempo' in metadados:
                    tempos_classificacao.append(metadados['classificacao_tempo'])
                if 'extracao_dados_tempo' in metadados:
                    tempos_dados.append(metadados['extracao_dados_tempo'])

            def calc_stats(valores):
                if not valores:
                    return {"min": 0, "max": 0, "media": 0, "mediana": 0}
                valores_sorted = sorted(valores)
                return {
                    "min": round(min(valores), 3),
                    "max": round(max(valores), 3),
                    "media": round(sum(valores) / len(valores), 3),
                    "mediana": round(valores_sorted[len(valores_sorted)//2], 3)
                }

            return {
                "total_processamentos": len(processamentos),
                "performance_extracao": calc_stats(tempos_extracao),
                "performance_classificacao": calc_stats(tempos_classificacao),
                "performance_extracao_dados": calc_stats(tempos_dados),
                "distribuicao_providers": await self._get_provider_distribution(processamentos),
                "qualidade_media": await self._get_quality_metrics(processamentos)
            }
        except Exception as e:
            logger.error(f"Erro ao obter métricas de performance: {e}")
            return {"error": str(e)}

    async def get_cost_analysis(
        self,
        periodo_dias: int = 30,
        db_session: Session = None
    ) -> Dict[str, Any]:
        """Retorna análise detalhada de custos"""
        try:
            from datetime import datetime, timedelta
            from app.models.database import ProcessamentoDocumento
            data_inicio = datetime.now() - timedelta(days=periodo_dias)

            # Consultar processamentos com custos
            processamentos = db_session.query(ProcessamentoDocumento).filter(
                ProcessamentoDocumento.data_criacao >= data_inicio,
                ProcessamentoDocumento.custo_total.isnot(None)
            ).all()

            if not processamentos:
                return {"message": "Nenhum dado de custo disponível"}

            custos_por_tipo = {}
            custos_por_dia = {}
            custo_total = 0.0

            for proc in processamentos:
                custo = proc.custo_total or 0.0
                custo_total += custo

                # Por tipo de documento
                tipo = proc.tipo_documento or "Não Classificado"
                custos_por_tipo[tipo] = custos_por_tipo.get(tipo, 0.0) + custo

                # Por dia
                dia = proc.data_criacao.date().isoformat()
                custos_por_dia[dia] = custos_por_dia.get(dia, 0.0) + custo

            # Projeção mensal
            custo_medio_diario = custo_total / periodo_dias if periodo_dias > 0 else 0
            projecao_mensal = custo_medio_diario * 30

            return {
                "periodo_dias": periodo_dias,
                "custo_total": round(custo_total, 4),
                "custo_medio_documento": round(custo_total / len(processamentos), 6),
                "custo_medio_diario": round(custo_medio_diario, 4),
                "projecao_mensal": round(projecao_mensal, 2),
                "custos_por_tipo": {k: round(v, 4) for k, v in custos_por_tipo.items()},
                "custos_por_dia": {k: round(v, 4) for k, v in custos_por_dia.items()},
                "economia_vs_manual": await self._calculate_manual_cost_comparison(len(processamentos))
            }
        except Exception as e:
            logger.error(f"Erro ao analisar custos: {e}")
            return {"error": str(e)}

    async def record_user_feedback(
        self,
        feedback_data: Dict[str, Any],
        db_session: Session = None
    ) -> str:
        """Registra feedback do usuário"""
        try:
            from app.models.database import FeedbackExtracao
            feedback = FeedbackExtracao(
                document_id=feedback_data.get("document_id"),
                tipo_feedback=feedback_data.get("tipo", "geral"),
                avaliacao=feedback_data.get("avaliacao"),  # 1-5
                comentario=feedback_data.get("comentario"),
                dados_corretos=feedback_data.get("corrected_data"),
                classificacao_correta=feedback_data.get("correct_classification"),
                metadados=feedback_data.get("metadata", {})
            )

            db_session.add(feedback)
            db_session.commit()

            logger.info(f"Feedback registrado: {feedback.id}")
            return str(feedback.id)
        except Exception as e:
            logger.error(f"Erro ao registrar feedback: {e}")
            db_session.rollback()
            raise

    async def _get_provider_distribution(self, processamentos) -> Dict[str, int]:
        """Calcula distribuição de providers usados"""
        distribuicao = {}
        for proc in processamentos:
            metadados = proc.metadados or {}
            provider = metadados.get("provider_usado", "Desconhecido")
            distribuicao[provider] = distribuicao.get(provider, 0) + 1
        return distribuicao

    async def _get_quality_metrics(self, processamentos) -> Dict[str, float]:
        """Calcula métricas de qualidade"""
        qualidades = []
        for proc in processamentos:
            metadados = proc.metadados or {}
            if 'qualidade_extracao' in metadados:
                qualidades.append(metadados['qualidade_extracao'])

        if not qualidades:
            return {"media": 0.0, "min": 0.0, "max": 0.0}

        return {
            "media": round(sum(qualidades) / len(qualidades), 3),
            "min": round(min(qualidades), 3),
            "max": round(max(qualidades), 3)
        }

    async def _calculate_manual_cost_comparison(self, num_documentos: int) -> Dict[str, Any]:
        """Calcula economia vs processamento manual"""
        # Estimativas de tempo manual por documento
        tempo_manual_minutos = 15  # 15 minutos por documento
        custo_hora_analista = 50.0  # R$ 50/hora

        tempo_total_manual = (num_documentos * tempo_manual_minutos) / 60  # horas
        custo_manual_total = tempo_total_manual * custo_hora_analista

        return {
            "tempo_economizado_horas": round(tempo_total_manual, 1),
            "custo_manual_estimado": round(custo_manual_total, 2),
            "economia_percentual": 95  # Estimativa de 95% de economia
        }