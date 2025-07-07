"""
Rotas da API do sistema ETL Documentos
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.logging import obter_logger
from app.database.connection import get_db
from app.core.config import (
    OPENAI_API_KEY, DOCUMENT_TYPES, MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS, UPLOAD_DIR
)
from app.api.middleware import require_api_key
from app.services.client_management_service import ClientManagementService

logger = obter_logger(__name__)

# Inicializar serviços com tratamento de erro
vector_service = None
classification_service = None
extraction_service = None
analytics_service = None
cost_service = None
document_processor = None

try:
    from app.services.vector_service import VectorStoreService
    vector_service = VectorStoreService()
    logger.info("Vector service inicializado")
except Exception as e:
    logger.warning(f"Vector service não disponível: {e}")

try:
    from app.services.analytics_service import AnalyticsService
    analytics_service = AnalyticsService()
    logger.info("Analytics service inicializado")
except Exception as e:
    logger.warning(f"Analytics service não disponível: {e}")

try:
    from app.services.cost_service import CostService
    cost_service = CostService()
    logger.info("Cost service inicializado")
except Exception as e:
    logger.warning(f"Cost service não disponível: {e}")

try:
    from app.services.document_processor import DocumentProcessorService
    document_processor = DocumentProcessorService()
    logger.info("Document processor service inicializado")
except Exception as e:
    logger.warning(f"Document processor service não disponível: {e}")

# Services que dependem de configurações especiais serão inicializados quando necessário
classification_service = None
extraction_service = None

# Router principal
router = APIRouter()

# Configurar diretórios
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/health")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Health check detalhado com status dos serviços"""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "services": {
                "database": await _check_database_health(),
                "vector_store": "healthy" if vector_service and vector_service.initialized else "disabled",
                "openai": "healthy" if OPENAI_API_KEY != "sk-test-key-for-development" else "not_configured",
                "azure": "disabled",
                "classification": "healthy" if classification_service else "disabled",
                "extraction": "healthy" if extraction_service else "disabled",
                "analytics": "healthy" if analytics_service else "disabled",
                "document_processor": "healthy" if document_processor else "disabled"
            },
            "environment": os.environ.get("ENV", "development")
        }

        # Verificar se algum serviço está com problema
        unhealthy_services = [
            service for service, status in health_data["services"].items()
            if status not in ["healthy", "disabled", "not_configured"]
        ]

        if unhealthy_services:
            health_data["status"] = "degraded"
            health_data["issues"] = unhealthy_services

        return health_data
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/tipos-suportados")
async def listar_tipos_suportados():
    """Lista os tipos de documentos suportados pelo sistema"""
    return {
        "tipos_suportados": DOCUMENT_TYPES,
        "total": len(DOCUMENT_TYPES)
    }


@router.post("/processar")
async def processar_documento(
    background_tasks: BackgroundTasks,
    arquivo: UploadFile = File(...),
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Processa um documento enviado com autenticação por API key"""
    start_time = datetime.utcnow()
    cliente = auth["cliente"]
    db = auth["db_session"]

    try:
        # Validar arquivo
        if not arquivo.filename:
            raise HTTPException(400, "Nome do arquivo não fornecido")

        extensao = os.path.splitext(arquivo.filename)[1].lower()
        if extensao not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Extensão {extensao} não suportada")

        # Ler conteúdo
        conteudo = await arquivo.read()
        if len(conteudo) > MAX_FILE_SIZE:
            raise HTTPException(400, "Arquivo muito grande")

        # Verificar se document processor está disponível
        if not document_processor:
            # Registrar tentativa de uso
            logger.info(
                f"Document processor não disponível para cliente {cliente.id}")

            return {
                "message": "Serviços de processamento não disponíveis",
                "status": "offline_mode",
                "filename": arquivo.filename,
                "size": len(conteudo),
                "extension": extensao
            }

        # Processar documento usando DocumentProcessorService
        resultado = await document_processor.processar_documento(
            arquivo_bytes=conteudo,
            nome_arquivo=arquivo.filename,
            cliente_id=cliente.id,
            db=db,
            metadados={"upload_time": start_time.isoformat()}
        )

        # Registrar uso no banco
        client_service = ClientManagementService()

        # Calcular tokens e custo baseado no resultado
        # Estimativa aproximada
        texto_extraido = getattr(resultado, 'texto_extraido', '') or ''
        tokens_input = len(texto_extraido) // 4 if texto_extraido else 0
        tokens_output = 0
        custo_total = getattr(resultado, 'custo_processamento', 0.001) or 0.001

        client_service.record_usage(
            cliente=cliente,
            operacao="processamento_completo",
            provider=getattr(resultado, 'provider_extracao',
                             'docling') or 'docling',
            db_session=db,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            custo_total=custo_total,
            tempo_execucao=(datetime.utcnow() - start_time).total_seconds(),
            documento_id=resultado.id,
            sucesso=resultado.status_processamento == "concluido"
        )

        # Extrair dados da extração qualificada dos dados_extraidos
        dados_extraidos = getattr(resultado, 'dados_extraidos', {})
        extracao_qualificada = {}

        if dados_extraidos and isinstance(dados_extraidos, dict):
            extracao_qualificada = dados_extraidos.get(
                'extracao_qualificada', {})

        return {
            "success": resultado.status_processamento == "concluido",
            "documento_id": resultado.id,
            "filename": arquivo.filename,
            "size": len(conteudo),
            "status": resultado.status_processamento,
            "provider": resultado.provider_extracao if hasattr(resultado, 'provider_extracao') else "docling",
            "tipo_documento": resultado.tipo_documento,
            "confianca": resultado.confianca_classificacao if hasattr(resultado, 'confianca_classificacao') else 0.0,

            # === EXTRAÇÃO QUALIFICADA (RESPOSTA DA LLM COM PROMPTS ESPECÍFICOS) ===
            "extracao_qualificada": extracao_qualificada,

            # === DADOS DO DOCLING ELITE ===
            "extracao": {
                "texto_extraido": getattr(resultado, 'texto_extraido', '') or '',
                "qualidade": getattr(resultado, 'qualidade_extracao', 0.0),
                "provider_usado": getattr(resultado, 'provider_extracao', 'docling'),
                "tempo_extracao": getattr(resultado, 'tempo_extracao', 0.0),
                "metadados_extracao": getattr(resultado, 'metadados_extracao', {})
            },
            "classificacao": {
                "tipo_detectado": resultado.tipo_documento,
                "confianca": resultado.confianca_classificacao if hasattr(resultado, 'confianca_classificacao') else 0.0,
                "provider_usado": getattr(resultado, 'provider_classificacao', 'openai'),
                "tempo_classificacao": getattr(resultado, 'tempo_classificacao', 0.0),
                "metadados_classificacao": getattr(resultado, 'metadados_classificacao', {})
            },
            "docling_elite": {
                "enrichment_detectado": getattr(resultado, 'metadados_extracao', {}).get('enrichment_detectado', {}),
                "funcionalidades_avancadas": getattr(resultado, 'metadados_extracao', {}).get('funcionalidades_avancadas', {}),
                "pipeline_config": getattr(resultado, 'metadados_extracao', {}).get('pipeline_config', {}),
                "qualidade_premium": getattr(resultado, 'qualidade_extracao', 0.0) >= 0.7
            },
            "processamento": {
                "tempo_execucao": (datetime.utcnow() - start_time).total_seconds(),
                "tokens_consumidos": tokens_input + tokens_output,
                "custo_total": custo_total,
                "timestamp": start_time.isoformat(),
                "detalhes": {
                    "tempo_extracao": getattr(resultado, 'tempo_extracao', 0.0),
                    "tempo_classificacao": getattr(resultado, 'tempo_classificacao', 0.0),
                    "tempo_total_processamento": getattr(resultado, 'tempo_total', 0.0)
                }
            },
            "cliente": {
                "id": cliente.id,
                "nome": cliente.nome,
                "plano": cliente.plano_tipo
            }
        }

    except HTTPException:
        # Registrar erro
        logger.error(f"Erro HTTP no processamento para cliente {cliente.id}")
        raise
    except Exception as e:
        # Registrar erro
        logger.error(
            f"Erro no processamento para cliente {cliente.id}: {str(e)}")
        logger.error(f"Erro ao processar documento: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.get("/documentos/{documento_id}")
async def obter_documento(
    documento_id: str,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Obtém dados de um documento processado"""
    try:
        cliente = auth["cliente"]

        return {
            "documento_id": documento_id,
            "status": "exemplo",
            "cliente": {
                "id": cliente.id,
                "nome": cliente.nome,
                "plano": cliente.plano_tipo
            },
            "message": "Endpoint em desenvolvimento"
        }
    except Exception as e:
        logger.error(f"Erro ao obter documento: {str(e)}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.get("/analytics/dashboard")
async def dashboard_analytics(
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Dashboard de analytics do cliente"""
    if not analytics_service:
        return {
            "message": "Analytics service não disponível",
            "mock_data": {
                "total_documentos": 0,
                "tipos_processados": {},
                "tempo_medio": 0,
                "custo_total": 0
            }
        }

    try:
        cliente = auth["cliente"]
        db = auth["db_session"]

        # Usar analytics service para gerar dashboard do cliente
        from app.services.analytics_service import AnalyticsService
        analytics = AnalyticsService()

        dashboard = analytics.get_client_dashboard(
            client_id=cliente.id,
            db_session=db,
            period_days=30
        )

        return {
            "cliente": {
                "id": cliente.id,
                "nome": cliente.nome,
                "plano": cliente.plano_tipo
            },
            "dashboard": dashboard
        }
    except Exception as e:
        logger.error(f"Erro no dashboard: {e}")
        return {"error": str(e)}


async def _check_database_health():
    """Verifica saúde do banco de dados"""
    try:
        db = next(get_db())
        # Teste simples de conexão
        db.execute(text("SELECT 1"))
        return "healthy"
    except Exception as e:
        logger.error(f"Erro no banco: {e}")
        return "unhealthy"
