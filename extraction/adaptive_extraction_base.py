from abc import ABC, abstractmethod
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.documents import Document

from config import DEFAULT_MODEL, OPENAI_API_KEY
from vector_store.adaptive_store import AdaptiveVectorStore

logger = logging.getLogger(__name__)

class AdaptiveBaseExtractor(ABC):
    """Base class for adaptive document data extraction with continuous learning."""
    
    def __init__(
        self, 
        vector_store: AdaptiveVectorStore,
        model_name: str = DEFAULT_MODEL, 
        openai_api_key: str = OPENAI_API_KEY
    ):
        """
        Initialize the adaptive extractor.
        
        Args:
            vector_store: Vector store for similar document retrieval
            model_name: Name of the LLM model to use
            openai_api_key: OpenAI API key
        """
        self.vector_store = vector_store
        self.llm = ChatOpenAI(model=model_name, openai_api_key=openai_api_key)
        self.output_parser = JsonOutputParser()
        self.document_type = self._get_document_type()
        
        # Build base extraction prompt and chain
        base_prompt_template = self._get_prompt_template()
        self.base_extraction_prompt = ChatPromptTemplate.from_template(base_prompt_template)
        self.base_extraction_chain = self.base_extraction_prompt | self.llm | self.output_parser
        
        # Build adaptive extraction prompt and chain
        adaptive_prompt_template = self._get_adaptive_prompt_template()
        self.adaptive_extraction_prompt = ChatPromptTemplate.from_template(adaptive_prompt_template)
        self.adaptive_extraction_chain = self.adaptive_extraction_prompt | self.llm | self.output_parser
    
    @abstractmethod
    def _get_document_type(self) -> str:
        """Return the document type this extractor handles."""
        pass
    
    @abstractmethod
    def _get_prompt_template(self) -> str:
        """Return the base prompt template for this document type."""
        pass
    
    def _get_adaptive_prompt_template(self) -> str:
        """Return the adaptive prompt template with examples for this document type."""
        # Default adaptive template includes examples section
        base_template = self._get_prompt_template()
        
        # Insert examples section before the document text
        parts = base_template.split("{document_text}")
        if len(parts) == 2:
            return parts[0] + """
Aqui estão alguns exemplos de documentos similares e suas informações extraídas:

{examples}

Agora extraia as informações deste documento:
{document_text}""" + parts[1]
        else:
            # Fallback if the template doesn't have the expected format
            return base_template
    
    def _format_examples(self, similar_docs: List[Document]) -> str:
        """Format similar documents and their extracted data as examples."""
        examples = []
        
        for i, doc in enumerate(similar_docs):
            # Get a snippet of text (first 150 characters)
            snippet = doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
            
            # Get extracted data
            extracted_data = doc.metadata.get("extracted_data", {})
            extracted_str = json.dumps(extracted_data, ensure_ascii=False, indent=2)
            
            example = f"EXEMPLO {i+1}:\n"
            example += f"Texto: {snippet}\n"
            example += f"Dados extraídos:\n{extracted_str}\n"
            
            examples.append(example)
            
        return "\n".join(examples)
    
    def extract_data(self, document_text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured data from document text, using similar documents as examples.
        
        Args:
            document_text: Text content of the document
            document_id: Optional ID for tracking the document
            
        Returns:
            Dictionary containing extracted fields
        """
        try:
            logger.info(f"Extraindo dados de {self.document_type}...")
            
            # Try to find similar documents of the same type
            similar_docs = self.vector_store.get_similar_documents_by_type(
                document_text=document_text,
                document_type=self.document_type,
                k=3
            )
            
            # If we have similar documents, use the adaptive approach
            if similar_docs:
                logger.info(f"Encontrados {len(similar_docs)} documentos similares para extração")
                examples = self._format_examples(similar_docs)
                
                # Use adaptive extraction with examples
                extracted_data = self.adaptive_extraction_chain.invoke({
                    "document_type": self.document_type,
                    "document_text": document_text,
                    "examples": examples
                })
            else:
                logger.info("Nenhum documento similar encontrado, usando extração básica")
                
                # Use base extraction without examples
                extracted_data = self.base_extraction_chain.invoke({
                    "document_type": self.document_type,
                    "document_text": document_text
                })
                
            # Ensure tipo_documento is set correctly
            if "tipo_documento" not in extracted_data:
                extracted_data["tipo_documento"] = self.document_type
            
            # Store the extraction results in vector store for future reference
            self._store_extraction_result(document_text, extracted_data, document_id)
                
            logger.info(f"Dados extraídos com sucesso de {self.document_type}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados de {self.document_type}: {str(e)}")
            raise RuntimeError(f"Falha ao extrair dados de {self.document_type}: {str(e)}")
    
    def _store_extraction_result(
        self, 
        document_text: str, 
        extracted_data: Dict[str, Any], 
        document_id: Optional[str] = None
    ) -> None:
        """Store extraction results in vector store for continuous learning."""
        try:
            self.vector_store.add_document(
                document_text=document_text,
                document_type=self.document_type,
                extraction_data=extracted_data,
                confidence_score=0.8,  # Default confidence
                document_id=document_id
            )
        except Exception as e:
            logger.warning(f"Não foi possível armazenar resultados da extração: {str(e)}")
    
    def add_feedback(
        self, 
        document_text: str, 
        correct_data: Dict[str, Any], 
        document_id: Optional[str] = None
    ) -> bool:
        """
        Add feedback about extraction results to improve future extractions.
        
        Args:
            document_text: Text content of the document
            correct_data: Correct extracted data
            document_id: Optional ID of an existing document
            
        Returns:
            Success flag
        """
        try:
            if document_id:
                # If we have a document ID, update it with feedback
                return self.vector_store.update_with_feedback(
                    document_id=document_id,
                    correct_type=self.document_type,
                    extraction_data=correct_data
                )
            else:
                # Otherwise, add as a new document with feedback
                self.vector_store.add_document(
                    document_text=document_text,
                    document_type=self.document_type,
                    extraction_data=correct_data,
                    confidence_score=1.0,  # Maximum confidence since it's human-verified
                )
                return True
                
        except Exception as e:
            logger.error(f"Erro ao adicionar feedback de extração: {str(e)}")
            return False