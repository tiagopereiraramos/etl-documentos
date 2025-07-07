"""
Aplicação principal do Sistema ETL Documentos
"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.config as config
from app.core.logging import configurar_logging, obter_logger

logger = obter_logger(__name__)

try:
    from app.api.routes import router as router_api
    logger.info("Rotas da API carregadas com sucesso")
except ImportError as e:
    logger.error(f"Erro na importação das rotas: {e}")
    # Criar um router básico para permitir que a aplicação inicie
    from fastapi import APIRouter
    router_api = APIRouter()

    @router_api.get("/health")
    async def health_check():
        return {"status": "ok", "message": "Aplicação iniciada com dependências limitadas"}

try:
    from app.api.client_routes import router as router_clientes
    logger.info("Rotas de clientes carregadas com sucesso")
except ImportError as e:
    logger.warning(f"Rotas de clientes não encontradas: {e}")
    from fastapi import APIRouter
    router_clientes = APIRouter()

try:
    from app.core.exceptions import configurar_exception_handlers
    logger.info("Exception handlers carregados com sucesso")
except ImportError as e:
    logger.warning(f"Exception handlers não encontrados: {e}")

    def configurar_exception_handlers(app):
        pass

try:
    from app.database.connection import inicializar_banco
    logger.info("Módulo de banco de dados carregado com sucesso")
except ImportError as e:
    logger.warning(f"Módulo de banco de dados não encontrado: {e}")

    async def inicializar_banco():
        logger.warning("Banco de dados não disponível - modo offline")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciador de ciclo de vida da aplicação"""
    # Inicialização
    logger.info("Iniciando aplicação ETL Documentos...")

    try:
        await inicializar_banco()
        logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")

    # Verificar configurações críticas
    if config.OPENAI_API_KEY == "sk-test-key-for-development":
        logger.warning(
            "⚠️  OpenAI API Key não configurada - funcionalidades limitadas")

    if not config.AZURE_ENABLED:
        logger.info("Azure Document Intelligence desabilitado")

    logger.info("✅ Aplicação ETL Documentos iniciada com sucesso")

    yield

    # Finalização
    logger.info("Finalizando aplicação...")


def criar_aplicacao() -> FastAPI:
    """Factory para criar a aplicação FastAPI"""
    app = FastAPI(
        title="Sistema ETL Documentos",
        description="API moderna para extração, classificação e análise de documentos",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if config.DEBUG else None,
        redoc_url="/redoc" if config.DEBUG else None
    )

    # Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    configurar_exception_handlers(app)

    # Rotas
    app.include_router(router_api, prefix="/api/v1")
    app.include_router(router_clientes, prefix="/api/v1")

    # Rota de health check na raiz
    @app.get("/")
    async def root():
        return {
            "message": "Sistema ETL Documentos API",
            "version": "2.0.0",
            "status": "online",
            "docs": "/docs" if config.DEBUG else "disabled in production"
        }

    return app


app = criar_aplicacao()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level="info"
    )
