import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from classification.adaptive_classifier import AdaptiveDocumentClassifier
from extraction.adaptive_extraction_base import AdaptiveBaseExtractor
from vector_store.adaptive_store import AdaptiveVectorStore

logger = logging.getLogger(__name__)
feedback_router = APIRouter()

# Models for feedback
class ClassificationFeedbackModel(BaseModel):
    document_id: Optional[str] = Field(None, description="ID do documento (se conhecido)")
    document_text: str = Field(..., description="Texto do documento")
    correct_type: str = Field(..., description="Tipo correto do documento")

class ExtractionFeedbackModel(BaseModel):
    document_id: Optional[str] = Field(None, description="ID do documento (se conhecido)")
    document_text: str = Field(..., description="Texto do documento")
    document_type: str = Field(..., description="Tipo do documento")
    correct_data: Dict[str, Any] = Field(..., description="Dados extraídos corretos")

class FeedbackResponseModel(BaseModel):
    success: bool = Field(..., description="Status da operação")
    message: str = Field(..., description="Mensagem informativa")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")

# Get dependencies
def get_vector_store():
    # Singleton pattern - return the same instance
    return AdaptiveVectorStore()

def get_classifier(vector_store: AdaptiveVectorStore = Depends(get_vector_store)):
    return AdaptiveDocumentClassifier(vector_store=vector_store)

@feedback_router.post("/feedback/classificacao", response_model=FeedbackResponseModel)
async def provide_classification_feedback(
    feedback: ClassificationFeedbackModel,
    background_tasks: BackgroundTasks,
    classifier: AdaptiveDocumentClassifier = Depends(get_classifier)
):
    """
    Fornece feedback para melhorar a classificação de documentos.
    Este endpoint permite corrigir classificações incorretas.
    """
    try:
        # Add feedback in the background to avoid blocking
        background_tasks.add_task(
            classifier.add_feedback,
            document_text=feedback.document_text,
            correct_type=feedback.correct_type,
            document_id=feedback.document_id
        )
        
        return FeedbackResponseModel(
            success=True,
            message="Feedback de classificação registrado com sucesso"
        )
    except Exception as e:
        logger.error(f"Erro ao registrar feedback de classificação: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@feedback_router.post("/feedback/extracao", response_model=FeedbackResponseModel)
async def provide_extraction_feedback(
    feedback: ExtractionFeedbackModel,
    background_tasks: BackgroundTasks,
    vector_store: AdaptiveVectorStore = Depends(get_vector_store)
):
    """
    Fornece feedback para melhorar a extração de dados.
    Este endpoint permite corrigir dados extraídos incorretamente.
    """
    try:
        # Get the appropriate extractor for this document type
        from api.routes import EXTRACTORS
        
        if feedback.document_type not in EXTRACTORS:
            raise HTTPException(
                status_code=400, 
                detail=f"Tipo de documento não suportado: {feedback.document_type}"
            )
            
        extractor = EXTRACTORS[feedback.document_type]
        
        # Add feedback in the background
        background_tasks.add_task(
            extractor.add_feedback,
            document_text=feedback.document_text,
            correct_data=feedback.correct_data,
            document_id=feedback.document_id
        )
        
        return FeedbackResponseModel(
            success=True,
            message="Feedback de extração registrado com sucesso"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao registrar feedback de extração: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@feedback_router.get("/estatisticas")
async def get_system_statistics(
    vector_store: AdaptiveVectorStore = Depends(get_vector_store)
):
    """
    Obtém estatísticas sobre o sistema de classificação e extração.
    """
    try:
        stats = vector_store.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))