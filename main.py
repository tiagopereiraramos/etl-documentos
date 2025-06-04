# -*- coding: utf-8 -*-
# main.py
# Este arquivo é parte do projeto Sistema de Extração Inteligente de Documentos.

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import router as api_router
from utils.logging import LoguruConfig, get_logger
from config import API_HOST, API_PORT, LOG_LEVEL

# Inicializa a configuração do Loguru para todo o projeto
# Suprimindo logs de DEBUG tanto no console quanto no arquivo
LoguruConfig.setup(
    log_file="./logs/document_extractor.log", 
    console_level="INFO",  # Suprime DEBUG no console
    file_level="INFO",     # Suprime DEBUG no arquivo
    intercept_libraries=True
)

# Obtém um logger para este módulo
logger = get_logger(__name__)

# Define o gerenciador de lifespan (substitui os handlers on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código de inicialização (antigo startup_event)
    logger.success("========== Aplicação iniciada com sucesso ==========")
    logger.info(f"Servidor rodando em http://{API_HOST}:{API_PORT}")
    
    yield  # A aplicação executa aqui
    
    # Código de encerramento (antigo shutdown_event)
    logger.warning("========== Aplicação encerrada ==========")

# Cria a aplicação FastAPI com o lifespan configurado
app = FastAPI(
    title="Sistema de Extração Inteligente de Documentos",
    description="API para classificação e extração de dados de documentos com OCR, LangChain e LLMs",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Add a health check endpoint
@app.get("/health")
async def health_check():
    logger.info("Verificação de saúde realizada")
    return {"status": "ok"}

if __name__ == "__main__":
    logger.info(f"Iniciando servidor em {API_HOST}:{API_PORT}")
    
    # Configurar o Uvicorn para usar o formato de log unificado
    uvicorn_log_config = LoguruConfig.configure_uvicorn()
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info",  # Forçar log level INFO para Uvicorn também
        log_config=uvicorn_log_config
    )