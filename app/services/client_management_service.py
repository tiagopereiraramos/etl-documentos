"""
Serviço de Gerenciamento de Clientes e API Keys
Gerencia clientes, planos, quotas e rastreamento de uso
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.logging import obter_logger
from app.models.database import Cliente, UsoDetalhadoCliente
from app.core.exceptions import QuotaExceededError, RateLimitError

logger = obter_logger(__name__)


class ClientManagementService:
    """Serviço para gerenciamento de clientes e controle de acesso"""

    # Configurações de planos
    PLANOS = {
        "free": {
            "documentos_mes": 10,
            "tokens_mes": 10000,
            "rate_limit_minuto": 10,
            "preco_mes": 0.0
        },
        "basic": {
            "documentos_mes": 100,
            "tokens_mes": 100000,
            "rate_limit_minuto": 60,
            "preco_mes": 29.90
        },
        "premium": {
            "documentos_mes": 1000,
            "tokens_mes": 1000000,
            "rate_limit_minuto": 300,
            "preco_mes": 99.90
        },
        "superadmin": {
            "documentos_mes": -1,  # Sem limite
            "tokens_mes": -1,      # Sem limite
            "rate_limit_minuto": -1,  # Sem limite
            "preco_mes": 0.0
        }
    }

    def __init__(self):
        self.logger = logger

    def generate_api_key(self) -> str:
        """Gera uma nova API key segura"""
        return f"etl_{secrets.token_urlsafe(32)}"

    def hash_api_key(self, api_key: str) -> str:
        """Cria hash da API key para armazenamento seguro"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def create_client(
        self,
        nome: str,
        email: str,
        senha_hash: str,
        db_session: Session,
        plano: str = "free"
    ) -> Dict[str, Any]:
        """Cria um novo cliente com API key"""
        try:
            # Validar plano
            if plano not in self.PLANOS:
                raise ValueError(f"Plano inválido: {plano}")

            # Gerar API key
            api_key = self.generate_api_key()
            api_key_hash = self.hash_api_key(api_key)

            # Configurar quotas baseadas no plano
            plano_config = self.PLANOS[plano]

            cliente = Cliente(
                nome=nome,
                email=email,
                senha_hash=senha_hash,
                api_key=api_key,
                api_key_hash=api_key_hash,
                api_key_created_at=datetime.utcnow(),
                plano_tipo=plano,
                quota_documentos_mes=plano_config["documentos_mes"],
                quota_tokens_mes=plano_config["tokens_mes"],
                rate_limit_por_minuto=plano_config["rate_limit_minuto"]
            )

            db_session.add(cliente)
            db_session.commit()

            logger.info(f"Cliente criado: {email} - Plano: {plano}")

            return {
                "cliente_id": cliente.id,
                "nome": cliente.nome,
                "email": cliente.email,
                "plano": cliente.plano_tipo,
                "api_key": api_key,  # Retornar apenas na criação
                "quotas": {
                    "documentos_mes": cliente.quota_documentos_mes,
                    "tokens_mes": cliente.quota_tokens_mes,
                    "rate_limit_minuto": cliente.rate_limit_por_minuto
                }
            }

        except Exception as e:
            db_session.rollback()
            logger.error(f"Erro ao criar cliente: {str(e)}")
            raise

    def get_client_by_api_key(self, api_key: str, db_session: Session) -> Optional[Cliente]:
        """Busca cliente por API key"""
        try:
            api_key_hash = self.hash_api_key(api_key)
            cliente = db_session.query(Cliente).filter(
                and_(
                    Cliente.api_key_hash == api_key_hash,
                    Cliente.ativo == True
                )
            ).first()

            if cliente:
                # Atualizar último uso
                cliente.api_key_last_used = datetime.utcnow()
                db_session.commit()

            return cliente

        except Exception as e:
            logger.error(f"Erro ao buscar cliente por API key: {str(e)}")
            return None

    def check_quotas(self, cliente: Cliente, db_session: Session) -> Dict[str, Any]:
        """Verifica se o cliente pode processar mais documentos/tokens"""
        try:
            # Resetar contadores se mudou o mês
            mes_atual = datetime.utcnow().strftime("%Y-%m")
            if cliente.mes_referencia != mes_atual:
                cliente.documentos_processados_mes = 0
                cliente.tokens_consumidos_mes = 0
                cliente.custo_total_mes = 0.0
                cliente.mes_referencia = mes_atual
                db_session.commit()

            # Verificar se é plano superadmin (sem limites)
            if cliente.plano_tipo == "superadmin":
                return {
                    "pode_processar": True,
                    "documentos_restantes": float('inf'),
                    "tokens_restantes": float('inf'),
                    "custo_mes": cliente.custo_total_mes,
                    "plano": cliente.plano_tipo,
                    "ilimitado": True
                }

            # Verificar quotas para outros planos
            documentos_restantes = cliente.quota_documentos_mes - \
                cliente.documentos_processados_mes
            tokens_restantes = cliente.quota_tokens_mes - cliente.tokens_consumidos_mes

            return {
                "pode_processar": documentos_restantes > 0 and tokens_restantes > 0,
                "documentos_restantes": max(0, documentos_restantes),
                "tokens_restantes": max(0, tokens_restantes),
                "custo_mes": cliente.custo_total_mes,
                "plano": cliente.plano_tipo,
                "ilimitado": False
            }

        except Exception as e:
            logger.error(f"Erro ao verificar quotas: {str(e)}")
            return {"pode_processar": False, "erro": str(e)}

    def record_usage(
        self,
        cliente: Cliente,
        operacao: str,
        provider: str,
        db_session: Session,
        tokens_input: int = 0,
        tokens_output: int = 0,
        custo_total: float = 0.0,
        tempo_execucao: float = 0.0,
        documento_id: Optional[str] = None,
        session_id: Optional[str] = None,
        sucesso: bool = True,
        erro: Optional[str] = None,
        metadados: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra uso detalhado do cliente"""
        try:
            # Atualizar contadores do cliente
            if sucesso:
                cliente.documentos_processados_mes += 1
                cliente.tokens_consumidos_mes += (tokens_input + tokens_output)
                cliente.custo_total_mes += custo_total

            # Registrar uso detalhado
            uso = UsoDetalhadoCliente(
                cliente_id=cliente.id,
                documento_id=documento_id,
                session_id=session_id,
                operacao=operacao,
                provider=provider,
                modelo_llm=metadados.get("modelo") if metadados else None,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                tokens_total=tokens_input + tokens_output,
                custo_input=metadados.get(
                    "custo_input", 0.0) if metadados else 0.0,
                custo_output=metadados.get(
                    "custo_output", 0.0) if metadados else 0.0,
                custo_total=custo_total,
                tempo_execucao=tempo_execucao,
                sucesso=sucesso,
                erro=erro,
                metadados=metadados
            )

            db_session.add(uso)
            db_session.commit()

            logger.debug(
                f"Uso registrado: Cliente {cliente.id} - {operacao} - ${custo_total:.4f}")

        except Exception as e:
            logger.error(f"Erro ao registrar uso: {str(e)}")
            if db_session:
                db_session.rollback()

    def get_client_usage_report(
        self,
        cliente: Cliente,
        db_session: Session,
        periodo_dias: int = 30
    ) -> Dict[str, Any]:
        """Gera relatório detalhado de uso do cliente"""
        try:
            data_inicio = datetime.utcnow() - timedelta(days=periodo_dias)

            # Uso por operação
            uso_por_operacao = db_session.query(
                UsoDetalhadoCliente.operacao,
                func.count(UsoDetalhadoCliente.id).label('total'),
                func.sum(UsoDetalhadoCliente.tokens_total).label('tokens'),
                func.sum(UsoDetalhadoCliente.custo_total).label('custo'),
                func.avg(UsoDetalhadoCliente.tempo_execucao).label(
                    'tempo_medio')
            ).filter(
                and_(
                    UsoDetalhadoCliente.cliente_id == cliente.id,
                    UsoDetalhadoCliente.timestamp >= data_inicio
                )
            ).group_by(UsoDetalhadoCliente.operacao).all()

            # Uso por provedor
            uso_por_provider = db_session.query(
                UsoDetalhadoCliente.provider,
                func.count(UsoDetalhadoCliente.id).label('total'),
                func.sum(UsoDetalhadoCliente.custo_total).label('custo')
            ).filter(
                and_(
                    UsoDetalhadoCliente.cliente_id == cliente.id,
                    UsoDetalhadoCliente.timestamp >= data_inicio
                )
            ).group_by(UsoDetalhadoCliente.provider).all()

            # Estatísticas gerais
            total_operacoes = sum(op.total for op in uso_por_operacao)
            total_tokens = sum(op.tokens or 0 for op in uso_por_operacao)
            total_custo = sum(op.custo or 0 for op in uso_por_operacao)

            return {
                "cliente": {
                    "id": cliente.id,
                    "nome": cliente.nome,
                    "email": cliente.email,
                    "plano": cliente.plano_tipo
                },
                "periodo": {
                    "dias": periodo_dias,
                    "inicio": data_inicio.isoformat(),
                    "fim": datetime.utcnow().isoformat()
                },
                "resumo": {
                    "total_operacoes": total_operacoes,
                    "total_tokens": total_tokens,
                    "total_custo": round(total_custo, 4),
                    "tempo_medio": round(sum(op.tempo_medio or 0 for op in uso_por_operacao) / len(uso_por_operacao), 3) if uso_por_operacao else 0
                },
                "uso_por_operacao": [
                    {
                        "operacao": op.operacao,
                        "total": op.total,
                        "tokens": op.tokens or 0,
                        "custo": round(op.custo or 0, 4),
                        "tempo_medio": round(op.tempo_medio or 0, 3)
                    }
                    for op in uso_por_operacao
                ],
                "uso_por_provider": [
                    {
                        "provider": p.provider,
                        "total": p.total,
                        "custo": round(p.custo or 0, 4)
                    }
                    for p in uso_por_provider
                ],
                "quotas": {
                    "documentos_mes": cliente.quota_documentos_mes,
                    "documentos_usados": cliente.documentos_processados_mes,
                    "documentos_restantes": max(0, cliente.quota_documentos_mes - cliente.documentos_processados_mes),
                    "tokens_mes": cliente.quota_tokens_mes,
                    "tokens_usados": cliente.tokens_consumidos_mes,
                    "tokens_restantes": max(0, cliente.quota_tokens_mes - cliente.tokens_consumidos_mes)
                }
            }

        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {str(e)}")
            return {"erro": str(e)}

    def upgrade_plan(self, cliente: Cliente, novo_plano: str, db_session: Session) -> Dict[str, Any]:
        """Atualiza o plano do cliente"""
        try:
            if novo_plano not in self.PLANOS:
                raise ValueError(f"Plano inválido: {novo_plano}")

            plano_anterior = cliente.plano_tipo
            cliente.plano_tipo = novo_plano

            # Atualizar quotas
            novo_config = self.PLANOS[novo_plano]
            cliente.quota_documentos_mes = novo_config["documentos_mes"]
            cliente.quota_tokens_mes = novo_config["tokens_mes"]
            cliente.rate_limit_por_minuto = novo_config["rate_limit_minuto"]

            db_session.commit()

            logger.info(
                f"Cliente {cliente.email} atualizado: {plano_anterior} -> {novo_plano}")

            return {
                "cliente_id": cliente.id,
                "plano_anterior": plano_anterior,
                "plano_novo": novo_plano,
                "quotas_atualizadas": {
                    "documentos_mes": cliente.quota_documentos_mes,
                    "tokens_mes": cliente.quota_tokens_mes,
                    "rate_limit_minuto": cliente.rate_limit_por_minuto
                }
            }

        except Exception as e:
            db_session.rollback()
            logger.error(f"Erro ao atualizar plano: {str(e)}")
            raise

    def regenerate_api_key(self, cliente: Cliente, db_session: Session) -> str:
        """Regenera a API key do cliente"""
        try:
            nova_api_key = self.generate_api_key()
            cliente.api_key = nova_api_key
            cliente.api_key_hash = self.hash_api_key(nova_api_key)
            cliente.api_key_created_at = datetime.utcnow()

            db_session.commit()

            logger.info(f"API key regenerada para cliente: {cliente.email}")

            return nova_api_key

        except Exception as e:
            db_session.rollback()
            logger.error(f"Erro ao regenerar API key: {str(e)}")
            raise
