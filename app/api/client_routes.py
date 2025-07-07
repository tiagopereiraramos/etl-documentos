"""
Rotas para gerenciamento de clientes e API Keys
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.logging import obter_logger
from app.database.connection import get_db
from app.services.client_management_service import ClientManagementService
from app.api.middleware import require_api_key

logger = obter_logger(__name__)

router = APIRouter(prefix="/clientes", tags=["Clientes"])

# Pydantic models


class ClienteCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    plano: str = "free"


class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    plano: Optional[str] = None


class APIKeyResponse(BaseModel):
    api_key: str
    created_at: datetime


class UsageReport(BaseModel):
    cliente_id: str
    periodo_dias: int
    resumo: Dict[str, Any]
    uso_por_operacao: List[Dict[str, Any]]
    uso_por_provider: List[Dict[str, Any]]
    quotas: Dict[str, Any]


# Inicializar serviço
client_service = ClientManagementService()


@router.post("/", response_model=Dict[str, Any])
async def criar_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db)
):
    """Cria um novo cliente com API key"""
    try:
        # Hash da senha
        from app.core.security import hash_password
        senha_hash = hash_password(cliente_data.senha)

        # Criar cliente
        resultado = client_service.create_client(
            nome=cliente_data.nome,
            email=cliente_data.email,
            senha_hash=senha_hash,
            db_session=db,
            plano=cliente_data.plano
        )

        logger.info(f"Cliente criado: {cliente_data.email}")

        return {
            "message": "Cliente criado com sucesso",
            "cliente": resultado
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao criar cliente: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/me", response_model=Dict[str, Any])
async def obter_perfil_cliente(
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Obtém perfil do cliente autenticado"""
    try:
        cliente = auth["cliente"]
        quotas = auth.get("quotas")

        return {
            "cliente": {
                "id": cliente.id,
                "nome": cliente.nome,
                "email": cliente.email,
                "plano": cliente.plano_tipo,
                "ativo": cliente.ativo,
                "data_criacao": cliente.data_criacao.isoformat(),
                "api_key_created_at": cliente.api_key_created_at.isoformat() if cliente.api_key_created_at else None,
                "api_key_last_used": cliente.api_key_last_used.isoformat() if cliente.api_key_last_used else None
            },
            "quotas": quotas,
            "planos_disponiveis": client_service.PLANOS
        }

    except Exception as e:
        logger.error(f"Erro ao obter perfil: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/me/usage", response_model=Dict[str, Any])
async def obter_relatorio_uso(
    periodo_dias: int = 30,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Obtém relatório detalhado de uso do cliente"""
    try:
        cliente = auth["cliente"]
        db = auth["db_session"]

        relatorio = client_service.get_client_usage_report(
            cliente=cliente,
            db_session=db,
            periodo_dias=periodo_dias
        )

        return relatorio

    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.post("/me/regenerate-api-key", response_model=Dict[str, Any])
async def regenerar_api_key(
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Regenera a API key do cliente"""
    try:
        cliente = auth["cliente"]
        db = auth["db_session"]

        nova_api_key = client_service.regenerate_api_key(cliente, db)

        logger.info(f"API key regenerada para cliente: {cliente.email}")

        return {
            "message": "API key regenerada com sucesso",
            "api_key": nova_api_key,
            "created_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Erro ao regenerar API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.put("/me/upgrade-plan")
async def upgrade_plan(
    novo_plano: str,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Upgrade do plano do cliente"""
    try:
        cliente = auth["cliente"]
        db = auth["db_session"]

        resultado = client_service.upgrade_plan(cliente, novo_plano, db)
        return {
            "success": True,
            "message": f"Plano atualizado para {novo_plano}",
            "novo_plano": novo_plano,
            "novas_quotas": resultado
        }
    except Exception as e:
        logger.error(f"Erro ao fazer upgrade do plano: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/me/quotas", response_model=Dict[str, Any])
async def obter_quotas(
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Obtém informações detalhadas das quotas do cliente"""
    try:
        cliente = auth["cliente"]
        db = auth["db_session"]

        quotas = client_service.check_quotas(cliente, db)
        plano_config = client_service.PLANOS.get(cliente.plano_tipo, {})

        return {
            "cliente": {
                "id": cliente.id,
                "nome": cliente.nome,
                "email": cliente.email,
                "plano": cliente.plano_tipo
            },
            "quotas_atual": quotas,
            "plano_config": plano_config,
            "uso_mes": {
                "documentos_processados": cliente.documentos_processados_mes,
                "tokens_consumidos": cliente.tokens_consumidos_mes,
                "custo_total": cliente.custo_total_mes,
                "mes_referencia": cliente.mes_referencia
            }
        }

    except Exception as e:
        logger.error(f"Erro ao obter quotas: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# Rotas administrativas (requerem autenticação especial)


@router.get("/admin/todos", response_model=List[Dict[str, Any]])
async def listar_todos_clientes(
    db: Session = Depends(get_db),
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Lista todos os clientes (rota administrativa)"""
    try:
        # Verificar se é admin (implementar lógica de admin)
        cliente = auth["cliente"]
        if cliente.plano_tipo != "premium":  # Simplificado - usar sistema de roles real
            raise HTTPException(status_code=403, detail="Acesso negado")

        clientes = db.query(cliente.__class__).all()

        return [
            {
                "id": c.id,
                "nome": c.nome,
                "email": c.email,
                "plano": c.plano_tipo,
                "ativo": c.ativo,
                "data_criacao": c.data_criacao.isoformat(),
                "documentos_processados_mes": c.documentos_processados_mes,
                "tokens_consumidos_mes": c.tokens_consumidos_mes,
                "custo_total_mes": c.custo_total_mes
            }
            for c in clientes
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar clientes: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/admin/estatisticas", response_model=Dict[str, Any])
async def estatisticas_gerais(
    db: Session = Depends(get_db),
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Estatísticas gerais do sistema (rota administrativa)"""
    try:
        # Verificar se é admin
        cliente = auth["cliente"]
        if cliente.plano_tipo != "premium":
            raise HTTPException(status_code=403, detail="Acesso negado")

        from sqlalchemy import func
        from app.models.database import Cliente, UsoDetalhadoCliente

        # Estatísticas básicas
        total_clientes = int(db.query(Cliente).count())
        clientes_ativos = int(db.query(Cliente).filter(
            Cliente.ativo == True).count())

        taxa_ativacao = 0.0
        if total_clientes > 0:
            taxa_ativacao = round((clientes_ativos / total_clientes) * 100, 2)

        # Uso total do mês
        mes_atual = datetime.utcnow().strftime("%Y-%m")
        clientes_mes = db.query(Cliente).filter(
            Cliente.mes_referencia == mes_atual).all()

        total_documentos_mes = sum(
            c.documentos_processados_mes for c in clientes_mes)
        total_tokens_mes = sum(c.tokens_consumidos_mes for c in clientes_mes)
        total_custo_mes = sum(c.custo_total_mes for c in clientes_mes)

        # Distribuição por plano
        planos = db.query(
            Cliente.plano_tipo,
            func.count(Cliente.id).label('quantidade')
        ).group_by(Cliente.plano_tipo).all()

        return {
            "geral": {
                "total_clientes": total_clientes,
                "clientes_ativos": clientes_ativos,
                "taxa_ativacao": taxa_ativacao
            },
            "uso_mes_atual": {
                "mes": mes_atual,
                "total_documentos": total_documentos_mes,
                "total_tokens": total_tokens_mes,
                "total_custo": round(total_custo_mes, 4)
            },
            "distribuicao_planos": [
                {"plano": p.plano_tipo, "quantidade": p.quantidade}
                for p in planos
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar estatísticas: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
