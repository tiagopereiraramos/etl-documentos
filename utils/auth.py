from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# Configuração básica do OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

class User(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: bool = False

# Função fictícia para autenticação - em produção usaria JWT ou similar
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    """
    Função simplificada para autenticação.
    Em um ambiente real, validaria o token JWT e buscaria o usuário no banco de dados.
    
    Para desenvolvimento, sempre retorna um usuário administrador fictício.
    """
    if token is None:
        # Para desenvolvimento, não exigimos autenticação
        return User(
            id="dev-user-123",
            username="developer",
            email="dev@example.com",
            full_name="Developer User",
            is_admin=True
        )
    
    # Em produção, aqui validaria o token
    # Se inválido, lançaria HTTPException
    
    # Usuário fictício para desenvolvimento
    return User(
        id="dev-user-123",
        username="developer",
        email="dev@example.com",
        full_name="Developer User",
        is_admin=True
    )