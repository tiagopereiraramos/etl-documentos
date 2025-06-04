from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class DocumentUploadRequest(BaseModel):
    """Schema for document upload request."""
    file_name: str = Field(..., description="Name of the uploaded file")
    file_extension: str = Field(..., description="Extension of the uploaded file")
    

class ClassificationRequest(BaseModel):
    """Schema for document classification request."""
    document_text: str = Field(..., description="Text content of the document to classify")
    

class ClassificationResponse(BaseModel):
    """Schema for document classification response."""
    document_type: str = Field(..., description="Classified document type")
    confidence: Optional[float] = Field(None, description="Classification confidence score")
    

class ExtractionRequest(BaseModel):
    """Schema for data extraction request."""
    document_type: str = Field(..., description="Type of the document")
    document_text: str = Field(..., description="Text content of the document")


class BaseExtractionData(BaseModel):
    """Base schema for extraction response data."""
    tipo_documento: str = Field(..., description="Type of the document")


class ComprovanteBancarioData(BaseExtractionData):
    """Schema for Comprovante Bancário data."""
    banco: str = Field(..., description="Nome do banco")
    data_transacao: str = Field(..., description="Data da transação")
    valor: str = Field(..., description="Valor da transação")
    conta_origem: Optional[str] = Field(None, description="Conta de origem")
    conta_destino: Optional[str] = Field(None, description="Conta de destino")
    numero_comprovante: Optional[str] = Field(None, description="Número do comprovante")


class CEIObraData(BaseExtractionData):
    """Schema for CEI da Obra data."""
    razao_social: str = Field(..., description="Razão Social do cliente")
    cnpj: str = Field(..., description="CNPJ do cliente")
    endereco: str = Field(..., description="Endereço completo")
    numero_cei: Optional[str] = Field(None, description="Número da matrícula CEI")
    data_registro: Optional[str] = Field(None, description="Data de registro")


class InscricaoMunicipalData(BaseExtractionData):
    """Schema for Inscrição Municipal data."""
    razao_social: str = Field(..., description="Razão Social")
    cnpj: str = Field(..., description="CNPJ")
    numero_inscricao: str = Field(..., description="Número da Inscrição Municipal")
    municipio: str = Field(..., description="Município")
    endereco: Optional[str] = Field(None, description="Endereço")
    data_inscricao: Optional[str] = Field(None, description="Data de Inscrição")


class TermoResponsabilidadeData(BaseExtractionData):
    """Schema for Termo de Responsabilidade data."""
    responsavel: str = Field(..., description="Nome do responsável")
    cpf_cnpj: str = Field(..., description="CPF ou CNPJ do responsável")
    objeto: str = Field(..., description="Objeto do termo")
    data_assinatura: Optional[str] = Field(None, description="Data de assinatura")
    vigencia: Optional[str] = Field(None, description="Período de vigência")


class AlvaraMunicipalData(BaseExtractionData):
    """Schema for Alvará Municipal data."""
    razao_social: str = Field(..., description="Razão Social")
    cnpj: str = Field(..., description="CNPJ")
    numero_alvara: str = Field(..., description="Número do Alvará")
    municipio: str = Field(..., description="Município")
    validade: str = Field(..., description="Data de validade")
    endereco: Optional[str] = Field(None, description="Endereço")
    atividade: Optional[str] = Field(None, description="Atividade permitida")


class ContratoSocialData(BaseExtractionData):
    """Schema for Contrato Social data."""
    razao_social: str = Field(..., description="Razão Social")
    cnpj: str = Field(..., description="CNPJ")
    objeto_social: str = Field(..., description="Objeto Social")
    capital_social: str = Field(..., description="Capital Social")
    socios: Optional[List[Dict[str, str]]] = Field(None, description="Lista de sócios")
    data_constituicao: Optional[str] = Field(None, description="Data de constituição")


class ExtractionResponse(BaseModel):
    """Schema for data extraction response."""
    extracted_data: Dict[str, Any] = Field(..., description="Extracted data")
    document_type: str = Field(..., description="Type of the document")
    timestamp: datetime = Field(default_factory=datetime.now, description="Extraction timestamp")