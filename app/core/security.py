"""
Módulo de segurança para autenticação JWT e controle de acesso
"""
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from uuid import uuid4

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import obter_logger

logger = obter_logger(__name__)

# Configuração de hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuração do security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Dados do token JWT"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    permissions: Optional[list] = None
    exp: Optional[datetime] = None


class SecurityManager:
    """Gerenciador de segurança centralizado"""

    def __init__(self):
        self.secret_key = settings.security.secret_key.get_secret_value()
        self.algorithm = settings.security.jwt_algorithm
        self.access_token_expire_minutes = settings.security.access_token_expire_minutes

        # Rate limiting
        self.rate_limit_requests = 100  # requests per window
        self.rate_limit_window = 3600  # 1 hour in seconds
        self.rate_limit_store: Dict[str, Dict[str, Any]] = {}

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica se a senha está correta"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Erro ao verificar senha: {e}")
            return False

    def get_password_hash(self, password: str) -> str:
        """Gera hash da senha"""
        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Erro ao gerar hash da senha: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao processar senha"
            )

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Cria token de acesso JWT"""
        try:
            to_encode = data.copy()

            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

            to_encode.update({"exp": expire, "jti": str(uuid4())})
            encoded_jwt = jwt.encode(
                to_encode, self.secret_key, algorithm=self.algorithm)

            logger.info(
                f"Token criado para usuário: {data.get('username', 'unknown')}")
            return encoded_jwt

        except Exception as e:
            logger.error(f"Erro ao criar token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao criar token"
            )

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Cria token de refresh"""
        try:
            to_encode = data.copy()
            # Refresh token expira em 30 dias
            expire = datetime.utcnow() + timedelta(days=30)
            to_encode.update(
                {"exp": expire, "jti": str(uuid4()), "type": "refresh"})
            encoded_jwt = jwt.encode(
                to_encode, self.secret_key, algorithm=self.algorithm)

            logger.info(
                f"Refresh token criado para usuário: {data.get('username', 'unknown')}")
            return encoded_jwt

        except Exception as e:
            logger.error(f"Erro ao criar refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao criar refresh token"
            )

    def verify_token(self, token: str) -> TokenData:
        """Verifica e decodifica o token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key,
                                 algorithms=[self.algorithm])

            # Verificar se é um refresh token
            if payload.get("type") == "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token não pode ser usado para acesso"
                )

            user_id: Optional[str] = payload.get("user_id")
            username: Optional[str] = payload.get("username")
            email: Optional[str] = payload.get("email")
            permissions: list = payload.get("permissions", [])
            exp: Optional[datetime] = payload.get("exp")

            if user_id is None or username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido"
                )

            return TokenData(
                user_id=user_id,
                username=username,
                email=email,
                permissions=permissions,
                exp=exp
            )

        except JWTError as e:
            logger.warning(f"Token JWT inválido: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado"
            )
        except Exception as e:
            logger.error(f"Erro ao verificar token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao verificar token"
            )

    def verify_refresh_token(self, token: str) -> TokenData:
        """Verifica e decodifica o refresh token"""
        try:
            payload = jwt.decode(token, self.secret_key,
                                 algorithms=[self.algorithm])

            # Verificar se é um refresh token
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token não é um refresh token"
                )

            user_id: Optional[str] = payload.get("user_id")
            username: Optional[str] = payload.get("username")
            email: Optional[str] = payload.get("email")
            permissions: list = payload.get("permissions", [])
            exp: Optional[datetime] = payload.get("exp")

            if user_id is None or username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token inválido"
                )

            return TokenData(
                user_id=user_id,
                username=username,
                email=email,
                permissions=permissions,
                exp=exp
            )

        except JWTError as e:
            logger.warning(f"Refresh token JWT inválido: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou expirado"
            )
        except Exception as e:
            logger.error(f"Erro ao verificar refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao verificar refresh token"
            )

    def check_rate_limit(self, client_id: str) -> bool:
        """Verifica se o cliente não excedeu o rate limit"""
        current_time = time.time()

        if client_id not in self.rate_limit_store:
            self.rate_limit_store[client_id] = {
                "requests": 1,
                "window_start": current_time
            }
            return True

        client_data = self.rate_limit_store[client_id]

        # Verificar se a janela de tempo expirou
        if current_time - client_data["window_start"] > self.rate_limit_window:
            client_data["requests"] = 1
            client_data["window_start"] = current_time
            return True

        # Verificar se excedeu o limite
        if client_data["requests"] >= self.rate_limit_requests:
            logger.warning(f"Rate limit excedido para cliente: {client_id}")
            return False

        client_data["requests"] += 1
        return True

    def get_client_id(self, request: Request) -> str:
        """Extrai o ID do cliente da requisição"""
        # Tentar obter do header X-Client-ID
        client_id = request.headers.get("X-Client-ID")
        if client_id:
            return client_id

        # Tentar obter do token JWT
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                token_data = self.verify_token(token)
                return token_data.user_id or "unknown"
        except:
            pass

        # Usar IP como fallback
        return request.client.host if request.client else "unknown"


# Instância global do gerenciador de segurança
security_manager = SecurityManager()


# =============================================================================
# DEPENDÊNCIAS PARA AUTENTICAÇÃO
# =============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Dependência para obter o usuário atual"""
    try:
        token_data = security_manager.verify_token(credentials.credentials)
        return token_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter usuário atual: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível validar as credenciais"
        )


async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Dependência para obter usuário ativo"""
    # Aqui você pode adicionar verificações adicionais como:
    # - Verificar se o usuário está ativo no banco
    # - Verificar se o usuário tem permissões específicas
    # - Verificar se a conta não foi suspensa

    return current_user


async def check_rate_limit_dependency(request: Request):
    """Dependência para verificar rate limit"""
    client_id = security_manager.get_client_id(request)

    if not security_manager.check_rate_limit(client_id):
        logger.warning(f"Rate limit excedido para cliente: {client_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit excedido. Tente novamente mais tarde."
        )


# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================

def create_user_tokens(user_data: Dict[str, Any]) -> Dict[str, str]:
    """Cria tokens de acesso e refresh para um usuário"""
    try:
        access_token = security_manager.create_access_token(data=user_data)
        refresh_token = security_manager.create_refresh_token(data=user_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.security.access_token_expire_minutes * 60
        }

    except Exception as e:
        logger.error(f"Erro ao criar tokens para usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar tokens"
        )


def hash_password(password: str) -> str:
    """Função utilitária para hash de senha"""
    return security_manager.get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Função utilitária para verificar senha"""
    return security_manager.verify_password(plain_password, hashed_password)


def get_token_expiration() -> datetime:
    """Retorna a data de expiração padrão dos tokens"""
    return datetime.utcnow() + timedelta(minutes=settings.security.access_token_expire_minutes)


# =============================================================================
# DECORADORES DE PERMISSÃO
# =============================================================================

def require_permissions(*required_permissions: str):
    """Decorador para verificar permissões específicas"""
    def decorator(func):
        async def wrapper(*args, current_user: TokenData = Depends(get_current_user), **kwargs):
            user_permissions = current_user.permissions or []

            for permission in required_permissions:
                if permission not in user_permissions:
                    logger.warning(
                        f"Usuário {current_user.username} não tem permissão: {permission}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permissão necessária: {permission}"
                    )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_admin():
    """Decorador para verificar se o usuário é administrador"""
    return require_permissions("admin")


def require_user_access(user_id: str):
    """Decorador para verificar se o usuário pode acessar recursos de outro usuário"""
    def decorator(func):
        async def wrapper(*args, current_user: TokenData = Depends(get_current_user), **kwargs):
            user_permissions = current_user.permissions or []

            # Administradores podem acessar qualquer recurso
            if "admin" in user_permissions:
                return await func(*args, current_user=current_user, **kwargs)

            # Usuários só podem acessar seus próprios recursos
            if current_user.user_id != user_id:
                logger.warning(
                    f"Usuário {current_user.username} tentou acessar recurso de {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado"
                )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
