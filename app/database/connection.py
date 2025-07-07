"""
Conexão e gerenciamento do banco de dados
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import os

from app.core.config import Settings
from app.core.logging import obter_logger
from app.models.database import Base

logger = obter_logger(__name__)

# Instância global das configurações
settings = Settings()


class DatabaseManager:
    """Gerenciador de banco de dados centralizado"""

    def __init__(self):
        self.settings = settings
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self._initialized = False

    def _get_database_url(self) -> str:
        """Obtém a URL do banco de dados baseada nas configurações"""
        if self.settings.database.type.value == "sqlite":
            # Garantir que o diretório existe
            db_dir = os.path.dirname(self.settings.database.sqlite_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            return f"sqlite:///{self.settings.database.sqlite_path}"

        elif self.settings.database.type.value == "postgresql":
            if self.settings.database.url:
                # Garantir que usa o driver correto
                url = self.settings.database.url
                if url.startswith("postgres://"):
                    url = url.replace("postgres://", "postgresql://", 1)
                return url
            else:
                raise ValueError("URL do banco PostgreSQL não configurada")

        else:
            raise ValueError(
                f"Tipo de banco não suportado: {self.settings.database.type}")

    def _get_engine_kwargs(self) -> dict:
        """Obtém argumentos específicos para o engine baseado no tipo de banco"""
        if self.settings.database.type.value == "sqlite":
            return {
                "echo": self.settings.debug,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 30
                },
                "pool_pre_ping": True
            }

        elif self.settings.database.type.value == "postgresql":
            return {
                "echo": self.settings.debug,
                "pool_pre_ping": True,
                "pool_size": self.settings.performance.pool_size,
                "max_overflow": self.settings.performance.max_overflow,
                "pool_recycle": self.settings.performance.pool_recycle,
                "pool_timeout": self.settings.performance.pool_timeout,
                "connect_args": {
                    "connect_timeout": 10,
                    "application_name": "etl_documentos_api"
                }
            }

        return {"echo": self.settings.debug}

    def initialize(self):
        """Inicializa as conexões do banco de dados"""
        if self._initialized:
            return

        try:
            database_url = self._get_database_url()
            engine_kwargs = self._get_engine_kwargs()

            logger.info(
                f"Inicializando banco de dados: {self.settings.database.type.value}")
            logger.debug(f"URL do banco: {database_url}")

            # Engine síncrono
            self.engine = create_engine(database_url, **engine_kwargs)
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Engine assíncrono (apenas para PostgreSQL)
            if self.settings.database.type.value == "postgresql":
                async_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://")
                self.async_engine = create_async_engine(
                    async_url,
                    echo=self.settings.debug,
                    pool_pre_ping=True
                )
                self.AsyncSessionLocal = async_sessionmaker(
                    self.async_engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
                logger.info("Engine assíncrono PostgreSQL configurado")
            else:
                logger.info("Engine assíncrono desabilitado para SQLite")

            self._initialized = True
            logger.info("Database manager inicializado com sucesso")

        except Exception as e:
            logger.error(f"Erro ao inicializar database manager: {e}")
            raise

    async def create_tables(self):
        """Cria todas as tabelas do banco de dados"""
        if not self._initialized:
            self.initialize()

        try:
            logger.info("Criando tabelas do banco de dados...")
            Base.metadata.create_all(bind=self.engine)

            # Verificar tabelas criadas
            inspector = inspect(self.engine)
            tabelas = inspector.get_table_names()
            logger.info(f"Tabelas criadas: {tabelas}")

        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {e}")
            raise

    def get_session(self) -> Session:
        """Obtém uma sessão síncrona do banco"""
        if not self._initialized:
            self.initialize()

        if not self.SessionLocal:
            raise RuntimeError("SessionLocal não foi inicializado")

        return self.SessionLocal()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager para sessão assíncrona"""
        if not self._initialized:
            self.initialize()

        if not self.AsyncSessionLocal:
            raise RuntimeError("Sessão assíncrona não configurada")

        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def close(self):
        """Fecha as conexões do banco de dados"""
        if self.engine:
            self.engine.dispose()
        if self.async_engine:
            self.async_engine.dispose()
        logger.info("Conexões do banco de dados fechadas")


# Instância global do database manager
db_manager = DatabaseManager()

# Funções de conveniência para compatibilidade


async def inicializar_banco():
    """Inicializa o banco de dados (função de compatibilidade)"""
    db_manager.initialize()
    await db_manager.create_tables()


def get_db():
    """Dependency para obter sessão do banco (FastAPI)"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


def obter_sessao():
    """Alias para compatibilidade"""
    return get_db()


@asynccontextmanager
async def obter_sessao_async() -> AsyncGenerator[AsyncSession, None]:
    """Context manager para sessão assíncrona (função de compatibilidade)"""
    async with db_manager.get_async_session() as session:
        yield session
