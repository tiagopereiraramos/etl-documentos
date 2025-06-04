from abc import ABC, abstractmethod
import logging
import json
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from utils.document_logging import DocumentTracker

from config import DEFAULT_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Base class for document data extraction."""
    
    def __init__(self, model_name: str = DEFAULT_MODEL, openai_api_key: str = OPENAI_API_KEY):
        """
        Initialize the extractor.
        
        Args:
            model_name: Name of the LLM model to use
            openai_api_key: OpenAI API key
        """
        self.llm = ChatOpenAI(model=model_name, openai_api_key=openai_api_key)
        self.output_parser = JsonOutputParser()
        self.document_type = self._get_document_type()
        
        # Build extraction chain
        prompt_template = self._get_prompt_template()
        self.extraction_prompt = ChatPromptTemplate.from_template(prompt_template)
        self.extraction_chain = self.extraction_prompt | self.llm | self.output_parser
    
    @abstractmethod
    def _get_document_type(self) -> str:
        """Return the document type this extractor handles."""
        pass
    
    @abstractmethod
    def _get_prompt_template(self) -> str:
        """Return the prompt template for this document type."""
        pass
    
    def extract_data(self, document_text: str, document_id: str = None, document_name: str = None) -> Dict[str, Any]:
        """
        Extract structured data from document text.
        
        Args:
            document_text: Text content of the document
            document_id: Optional ID for tracking the document
            document_name: Optional name/filename for tracking purposes
            
        Returns:
            Dictionary containing extracted fields
        """
        doc_id = document_id or "unknown-id"
        doc_name = document_name or f"{self.document_type}-doc"
        
        # Log início do processamento
        if document_id or document_name:
            DocumentTracker.log_processing_start(doc_id, doc_name, self.document_type)
        
        try:
            logger.info(f"Extracting data from {self.document_type}...")
            
            # Log uso do modelo (OpenAI API)
            if document_id or document_name:
                is_azure = hasattr(self.llm, 'deployment_name') and self.llm.deployment_name is not None
                
                if is_azure:
                    # É uma chamada Azure
                    endpoint_name = getattr(self.llm, 'deployment_name', self.llm.model_name)
                    DocumentTracker.log_azure_processing(
                        doc_id, 
                        doc_name, 
                        endpoint_name, 
                        "Processamento via Azure OpenAI",
                        self.document_type
                    )
                else:
                    # É uma chamada OpenAI padrão
                    DocumentTracker.log_docling_processing(
                        doc_id,
                        doc_name,
                        self.llm.model_name,
                        self.document_type
                    )
            
            # Run extraction chain
            extracted_data = self.extraction_chain.invoke({
                "document_type": self.document_type,
                "document_text": document_text
            })
            
            # Ensure tipo_documento is set correctly
            if "tipo_documento" not in extracted_data:
                extracted_data["tipo_documento"] = self.document_type
            
            # Log resultado da extração
            if document_id or document_name:
                DocumentTracker.log_extraction_result(doc_id, doc_name, self.document_type, extracted_data)
                
            logger.info(f"Successfully extracted data from {self.document_type}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting data from {self.document_type}: {str(e)}")
            
            # Log do erro
            if document_id or document_name:
                DocumentTracker.log_extraction_error(doc_id, doc_name, self.document_type, str(e))
                
                # Se falhou e não era Azure, tentar fallback (implementação opcional)
                # Você precisaria implementar essa lógica baseado em seus requisitos
            
            raise RuntimeError(f"Failed to extract data from {self.document_type}: {str(e)}")