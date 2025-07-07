
"""
Sistema de autenticação com JWT
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import configuracoes
from app.database.connection import obter_sessao
from app.models.database import Cliente
from app.core.logging import obter_logger

logger = obter_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def criar_hash_senha(senha: str) -> str:
    """Cria hash da senha"""
    return pwd_context.hash(senha)


def verificar_senha(senha_plain: str, senha_hash: str) -> bool:
    """Verifica se a senha confere com o hash"""
    return pwd_context.verify(senha_plain, senha_hash)


def criar_token_acesso(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=configuracoes.TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        configuracoes.SECRET_KEY, 
        algorithm=configuracoes.JWT_ALGORITHM
    )
    return encoded_jwt


def validar_token(token: str) -> Optional[str]:
    """Valida token JWT e retorna o ID do cliente"""
    try:
        payload = jwt.decode(
            token, 
            configuracoes.SECRET_KEY, 
            algorithms=[configuracoes.JWT_ALGORITHM]
        )
        cliente_id: str = payload.get("sub")
        if cliente_id is None:
            return None
        return cliente_id
    except JWTError:
        return None


async def obter_cliente_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(obter_sessao)
) -> Cliente:
    """Dependency para obter cliente autenticado"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    cliente_id = validar_token(token)
    
    if cliente_id is None:
        logger.warning("Token inválido fornecido")
        raise credentials_exception
    
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.ativo == True).first()
    if cliente is None:
        logger.warning(f"Cliente não encontrado ou inativo: {cliente_id}")
        raise credentials_exception
    
    return cliente
