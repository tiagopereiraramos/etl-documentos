"""
Middleware para autenticação por API Key e rastreamento de uso
"""
import time
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.logging import obter_logger
from app.database.connection import get_db
from app.models.database import Cliente
from app.services.client_management_service import ClientManagementService
from app.core.exceptions import QuotaExceededError, RateLimitError

logger = obter_logger(__name__)


def require_api_key(request: Request):
    """Dependência para autenticação por API Key"""
    try:
        # Extrair API key do header
        api_key = request.headers.get("Authorization")
        if not api_key or not api_key.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="API key obrigatória no header Authorization: Bearer <api_key>"
            )

        api_key = api_key.replace("Bearer ", "")

        # Buscar cliente no banco
        db = next(get_db())
        cliente = db.query(Cliente).filter(
            Cliente.api_key_hash == hashlib.sha256(
                api_key.encode()).hexdigest(),
            Cliente.ativo == True
        ).first()

        if not cliente:
            raise HTTPException(
                status_code=401,
                detail="API key inválida ou cliente inativo"
            )

        # Verificar rate limiting (exceto para superadmin)
        if cliente.plano_tipo != "superadmin":
            rate_limit = int(cliente.rate_limit_por_minuto)
            if not _check_rate_limit(str(cliente.id), rate_limit):
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit excedido. Máximo: {rate_limit} req/min"
                )

        # Calcular quotas
        quotas = ClientManagementService().check_quotas(cliente, db)

        return {"cliente": cliente, "db_session": db, "quotas": quotas}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na autenticação: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


# Cache para rate limiting
_rate_limit_store = {}


def _check_rate_limit(client_id: str, limit_per_minute: int) -> bool:
    """Verifica rate limit do cliente"""
    current_time = time.time()
    minute_window = int(current_time / 60)

    if client_id not in _rate_limit_store:
        _rate_limit_store[client_id] = {}

    client_data = _rate_limit_store[client_id]

    if minute_window not in client_data:
        client_data[minute_window] = 0

    # Limpar janelas antigas (mais de 1 minuto)
    for window in list(client_data.keys()):
        if window < minute_window:
            del client_data[window]

    # Verificar limite
    if client_data[minute_window] >= limit_per_minute:
        return False

    # Incrementar contador
    client_data[minute_window] += 1
    return True


def get_client_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Extrai informações do cliente da requisição"""
    # Esta função será usada em endpoints que já passaram pela autenticação
    return request.state.client_info if hasattr(request.state, 'client_info') else None
