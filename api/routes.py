from fastapi import APIRouter, UploadFile, HTTPException, File, Form, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
import os
import uuid
import json
import tempfile
from datetime import datetime
from langchain_core.documents import Document
# Importação dos processadores e utilitários
from ocr.document_processor import DocumentProcessor
from classification.classifier import DocumentClassifier
from vector_store.store import VectorStore
from utils.logging import get_logger
from utils.document_logging import DocumentTracker  # Novo import para o DocumentTracker
from config import DOCUMENT_TYPES, DOCUMENT_TYPE_IDS

# Importação dos extratores
from extraction.comprovante_bancario import ComprovanteBancarioExtractor
from extraction.cei_obra import CEIObraExtractor
from extraction.cnh import CNHExtractor
from extraction.contrato_social import ContratoSocialExtractor
from extraction.cartao_cnpj import CartaoCNPJExtractor
from extraction.inscricao_municipal import InscricaoMunicipalExtractor
from extraction.termo_responsabilidade import TermoResponsabilidadeExtractor
from extraction.alvara_municipal import AlvaraMunicipalExtractor
from extraction.contrato_social import ContratoSocialExtractor
from extraction.fatura_telefonica import FaturaTelefonicaExtractor
from extraction.nota_fiscal_eletronica_servico import NotaFiscalServicoExtractor

# Configurar router e logger
router = APIRouter()
logger = get_logger(__name__)

# Inicializar objetos globais
document_processor = DocumentProcessor()
classifier = DocumentClassifier()
vector_store = VectorStore()

# Modelos de dados
class DocumentClassificationResponse(BaseModel):
    document_type: str
    confidence: float = 0.0

class DocumentExtractionResponse(BaseModel):
    document_id: str
    document_type: str
    extracted_data: Dict[str, Any]
    processing_time: str

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
    
class StatusResponse(BaseModel):
    status: str
    message: str
    timestamp: str

class DocumentListItem(BaseModel):
    document_id: str
    document_type: str
    upload_timestamp: str
    filename: Optional[str] = None
    extracted_data_summary: Dict[str, Any]

class DocumentListResponse(BaseModel):
    documents: List[DocumentListItem]
    total: int
    page: int
    page_size: int

def get_extractor(document_type):
    """
    Retorna o extrator apropriado para o tipo de documento.
    """
    extractors = {
        "Comprovante Bancário": ComprovanteBancarioExtractor(),
        "CEI da Obra": CEIObraExtractor(),
        "CNH": CNHExtractor(),
        "Contrato Social": ContratoSocialExtractor(),
        "Cartão CNPJ": CartaoCNPJExtractor(),
        "Inscrição Municipal": InscricaoMunicipalExtractor(),
        "Termo de Responsabilidade": TermoResponsabilidadeExtractor(),
        "Alvará Municipal": AlvaraMunicipalExtractor(),
        "Fatura Telefônica": FaturaTelefonicaExtractor(),
        "Nota Fiscal de Serviços Eletrônica": NotaFiscalServicoExtractor()
    }
    
    extractor = extractors.get(document_type)
    if not extractor:
        logger.warning(f"Extrator não encontrado para o tipo: {document_type}")
    return extractor

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Verifica o status da API.
    
    Returns:
        Informações sobre o status atual do serviço.
    """
    return {
        "status": "online",
        "message": "API de extração de documentos funcionando normalmente",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/document-types", response_model=List[str])
async def get_document_types():
    """
    Retorna a lista de tipos de documentos suportados.
    
    Returns:
        Lista de tipos de documentos que o sistema pode processar.
    """
    return DOCUMENT_TYPES

@router.post("/classify", 
             response_model=DocumentClassificationResponse,
             responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def classify_document(
    file: UploadFile = File(...)
):
    """
    Classifica um documento sem extrair os dados.
    
    - `file`: Arquivo do documento a ser classificado (PDF, PNG, JPG, JPEG)
    
    Returns:
        Tipo do documento identificado.
    """
    # Gerar um ID de rastreamento para este documento
    doc_id = str(uuid.uuid4())[:6]
    doc_name = file.filename
    
    # Registrar início da chamada à API
    DocumentTracker.log_api_call("/classify", "POST", doc_id, doc_name)
    DocumentTracker.log_processing_start(doc_id, doc_name)
    
    try:
        logger.info(f"Classificando documento: {file.filename}")
        
        # 1. Verificar tipo de arquivo
        file_extension = os.path.splitext(file.filename)[1].lower().replace('.', '')
        if file_extension not in ['pdf', 'png', 'jpg', 'jpeg']:
            logger.warning(f"Tipo de arquivo não suportado: {file_extension}")
            DocumentTracker.log_error(doc_id, doc_name, f"Tipo de arquivo não suportado: {file_extension}")
            raise HTTPException(status_code=400, detail="Tipo de arquivo não suportado. Use PDF, PNG, JPG ou JPEG")
        
        # 2. Ler conteúdo do arquivo
        file_content = await file.read()
        
        # 3. Extrair texto
        try:
            document_text = document_processor.extract_text(file_content, file_extension, doc_name)
            logger.debug(f"Texto extraído: {len(document_text)} caracteres")
        except Exception as e:
            error_msg = f"Falha ao extrair texto: {str(e)}"
            logger.error(error_msg, exc_info=True)
            DocumentTracker.log_error(doc_id, doc_name, error_msg)
            raise HTTPException(status_code=500, detail=f"Falha ao extrair texto do documento: {str(e)}")
        
        # 4. Classificar documento
        start_time = datetime.now()
        try:
            document_type = classifier.classify_document(document_text)
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Documento classificado como: {document_type}")
            
            # Registrar a classificação com o DocumentTracker
            DocumentTracker.log_classification(doc_id, doc_name, document_type, confidence=0.95, elapsed_time=elapsed_time)
        except Exception as e:
            error_msg = f"Falha ao classificar documento: {str(e)}"
            logger.error(error_msg, exc_info=True)
            DocumentTracker.log_error(doc_id, doc_name, error_msg)
            raise HTTPException(status_code=500, detail=f"Falha ao classificar documento: {str(e)}")
        
        # 5. Montar resposta
        response = {
            "document_type": document_type,
            "confidence": 0.95  # Valor fixo, poderia ser implementado um cálculo real
        }
        
        # Log de conclusão do processamento
        processing_time = (datetime.now() - start_time).total_seconds()
        stats = {
            "endpoint": "/classify",
            "document_type": document_type,
            "confidence": 0.95
        }
        DocumentTracker.log_processing_complete(doc_id, doc_name, processing_time, "classifier", stats)
        
        return response
        
    except HTTPException:
        raise
    
    except Exception as e:
        error_msg = f"Erro não tratado: {str(e)}"
        logger.error(error_msg, exc_info=True)
        DocumentTracker.log_error(doc_id, doc_name, error_msg)
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao classificar o documento: {str(e)}"
        )

@router.post("/extract", 
             response_model=DocumentExtractionResponse, 
             responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def extract_document(
    file: UploadFile = File(...),
    force_type: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    """Extrai informações de um documento."""
    # Gerar um ID de rastreamento para este documento
    doc_id = str(uuid.uuid4())[:6]
    doc_name = file.filename
    
    # Registrar início da chamada à API
    DocumentTracker.log_api_call("/extract", "POST", doc_id, doc_name)
    DocumentTracker.log_processing_start(doc_id, doc_name)
    
    try:
        start_time = datetime.now()
        
        # 1. Verificar tipo de arquivo
        file_extension = os.path.splitext(file.filename)[1].lower().replace('.', '')
        if file_extension not in ['pdf', 'png', 'jpg', 'jpeg']:
            logger.warning(f"Tipo de arquivo não suportado: {file_extension}")
            DocumentTracker.log_error(doc_id, doc_name, f"Tipo de arquivo não suportado: {file_extension}")
            raise HTTPException(status_code=400, detail="Tipo de arquivo não suportado. Use PDF, PNG, JPG ou JPEG")
        
        # 2. Ler conteúdo do arquivo
        file_content = await file.read()
        
        # 3. Extrair texto usando processor dinâmico
        # O DocumentProcessor detectará automaticamente o tipo e qualidade do documento
        # Passamos doc_name para que o DocumentProcessor use o mesmo nome no log
        document_text = document_processor.extract_text(file_content, file_extension, doc_name)
        
        # 4. Classificar documento ou usar tipo forçado
        classification_start_time = datetime.now()
        if force_type:
            if force_type not in DOCUMENT_TYPES:
                error_msg = f"Tipo de documento '{force_type}' não reconhecido"
                DocumentTracker.log_error(doc_id, doc_name, error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
            document_type = force_type
            logger.info(f"Tipo de documento forçado: {document_type}")
        else:
            document_type = classifier.classify_document(document_text)
            classification_time = (datetime.now() - classification_start_time).total_seconds()
            # Registrar classificação
            DocumentTracker.log_classification(doc_id, doc_name, document_type, elapsed_time=classification_time)
        
        # 5. Extrair dados estruturados
        extractor = get_extractor(document_type)
        if not extractor:
            error_msg = f"Tipo de documento não suportado: {document_type}"
            DocumentTracker.log_error(doc_id, doc_name, error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        try:
            extraction_start_time = datetime.now()
            extracted_data = extractor.extract_data(document_text)
            extraction_time = (datetime.now() - extraction_start_time).total_seconds()
            logger.debug(f"Dados extraídos com sucesso para tipo {document_type}")
            
            # Registrar extração bem-sucedida
            DocumentTracker.log_extraction_result(doc_id, doc_name, document_text, "extractor", None)
        except Exception as e:
            error_msg = f"Falha ao extrair dados do documento {document_type}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            DocumentTracker.log_error(doc_id, doc_name, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 6. Armazenar documento no banco vetorial
        try:
            # Criar um objeto Document com o conteúdo e metadados
            document = Document(
                page_content=document_text,
                metadata={
                    "document_type": document_type,
                    "extracted_data": extracted_data,
                    "filename": file.filename,
                    "file_extension": file_extension,
                    "processing_id": doc_id,  # Adicionar ID de rastreamento aos metadados
                    "processed_at": datetime.now().isoformat()
                }
            )
            
            # Passar uma lista contendo o documento
            document_ids = vector_store.db.add_documents([document])
            
            # Pegar o primeiro ID da lista retornada
            document_id = document_ids[0]
            logger.info(f"Documento armazenado com ID: {document_id}")
        except Exception as e:
            logger.error(f"Falha ao armazenar documento: {str(e)}", exc_info=True)
            # Prossegue mesmo com falha no armazenamento, apenas loga o erro
            DocumentTracker.log_error(doc_id, doc_name, f"Falha ao armazenar no banco vetorial: {str(e)}")
            document_id = str(uuid.uuid4())
        
        # 7. Montar resposta
        elapsed_time = datetime.now() - start_time
        response = {
            "document_id": document_id,
            "document_type": document_type,
            "extracted_data": extracted_data,
            "processing_time": str(elapsed_time)
        }
        
        # Log de conclusão do processamento com estatísticas
        processing_stats = {
            "document_type": document_type,
            "extraction_fields": len(extracted_data) if extracted_data else 0,
            "storage_id": document_id,
            "text_length": len(document_text) if document_text else 0
        }
        
        DocumentTracker.log_processing_complete(doc_id, doc_name, elapsed_time.total_seconds(), document_type, processing_stats)
        logger.success(f"Documento processado com sucesso em {elapsed_time}")
        return response
        
    except HTTPException:
        # Re-lança exceções HTTP já tratadas
        raise
    
    except Exception as e:
        error_msg = f"Erro não tratado: {str(e)}"
        logger.error(error_msg, exc_info=True)
        DocumentTracker.log_error(doc_id, doc_name, error_msg)
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar o documento: {str(e)}"
        )

@router.post("/extract-text", response_model=Dict[str, Any])
async def extract_text_only(
    file: UploadFile = File(...)
):
    """
    Extrai apenas o texto de um documento, sem classificação ou extração estruturada.
    Útil para debugging do OCR.
    
    - `file`: Arquivo do documento (PDF, PNG, JPG, JPEG)
    
    Returns:
        Texto extraído do documento.
    """
    # Gerar um ID de rastreamento para este documento
    doc_id = str(uuid.uuid4())[:6]
    doc_name = file.filename
    
    # Registrar início da chamada à API
    DocumentTracker.log_api_call("/extract-text", "POST", doc_id, doc_name)
    DocumentTracker.log_processing_start(doc_id, doc_name)
    
    try:
        logger.info(f"Extraindo apenas texto do documento: {file.filename}")
        
        # Verificar tipo de arquivo
        file_extension = os.path.splitext(file.filename)[1].lower().replace('.', '')
        if file_extension not in ['pdf', 'png', 'jpg', 'jpeg']:
            DocumentTracker.log_error(doc_id, doc_name, f"Tipo de arquivo não suportado: {file_extension}")
            raise HTTPException(status_code=400, detail="Tipo de arquivo não suportado. Use PDF, PNG, JPG ou JPEG")
        
        # Ler conteúdo do arquivo
        file_content = await file.read()
        
        # Extrair texto
        extraction_start = datetime.now()
        try:
            document_text = document_processor.extract_text(file_content, file_extension, doc_name)
            extraction_time = (datetime.now() - extraction_start).total_seconds()
            
            # Registrar extração bem-sucedida
            extractor_method = "docling"  # Esta será substituída pela real no document_processor
            DocumentTracker.log_extraction_result(doc_id, doc_name, document_text, extractor_method, None)
        except Exception as e:
            error_msg = f"Falha ao extrair texto: {str(e)}"
            logger.error(error_msg, exc_info=True)
            DocumentTracker.log_error(doc_id, doc_name, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Log de conclusão do processamento com estatísticas
        total_time = (datetime.now() - extraction_start).total_seconds()
        stats = {
            "text_length": len(document_text),
            "extraction_time": f"{total_time:.3f}s"
        }
        DocumentTracker.log_processing_complete(doc_id, doc_name, total_time, "text_extraction", stats)
        
        return {
            "text": document_text,
            "length": len(document_text),
            "sample": document_text[:300] + "..." if len(document_text) > 300 else document_text
        }
        
    except HTTPException:
        raise
    
    except Exception as e:
        error_msg = f"Erro não tratado: {str(e)}"
        logger.error(error_msg, exc_info=True)
        DocumentTracker.log_error(doc_id, doc_name, error_msg)
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )