import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from config import DEFAULT_MODEL, OPENAI_API_KEY, DOCUMENT_TYPES
from vector_store.adaptive_store import AdaptiveVectorStore

logger = logging.getLogger(__name__)

class AdaptiveDocumentClassifier:
    """
    Classifies documents based on their content using LangChain, LLMs,
    and vector search for continuous learning.
    """
    
    def __init__(
        self, 
        vector_store: AdaptiveVectorStore,
        model_name: str = DEFAULT_MODEL, 
        openai_api_key: str = OPENAI_API_KEY
    ):
        """
        Initialize the adaptive document classifier.
        
        Args:
            vector_store: Vector store for document retrieval and storage
            model_name: Name of the LLM model to use
            openai_api_key: OpenAI API key
        """
        self.vector_store = vector_store
        self.llm = ChatOpenAI(model=model_name, openai_api_key=openai_api_key)
        self.output_parser = StrOutputParser()
        
        # Create document types text for prompts
        self.document_types_text = "\n".join([f"{i+1}. {doc_type}" for i, doc_type in enumerate(DOCUMENT_TYPES)])
        
        # Create base classification prompt (without examples)
        self.base_classification_prompt = ChatPromptTemplate.from_template(
            f"""Você recebe um texto de um documento e precisa classificá-lo em um dos seguintes tipos:

{self.document_types_text}

Texto do documento:
{{document_text}}

Responda com apenas o tipo do documento. Exemplo: "Comprovante Bancário"
"""
        )
        
        # Create adaptive classification prompt (with examples)
        self.adaptive_classification_prompt = ChatPromptTemplate.from_template(
            f"""Você recebe um texto de um documento e precisa classificá-lo em um dos seguintes tipos:

{self.document_types_text}

Aqui estão alguns exemplos de documentos similares que já foram classificados:

{{examples}}

Agora classifique este novo documento:
{{document_text}}

Responda com apenas o tipo do documento. Exemplo: "Comprovante Bancário"
"""
        )
        
        # Build classification chains
        self.base_chain = self.base_classification_prompt | self.llm | self.output_parser
        self.adaptive_chain = self.adaptive_classification_prompt | self.llm | self.output_parser
        
    def _format_examples(self, similar_docs: List[Document]) -> str:
        """Format similar documents as examples for the prompt."""
        examples = []
        
        for i, doc in enumerate(similar_docs):
            # Get a snippet of text (first 200 characters)
            snippet = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            doc_type = doc.metadata.get("document_type", "Desconhecido")
            confidence = doc.metadata.get("confidence_score", 1.0)
            verified = "✓" if doc.metadata.get("feedback", False) else ""
            
            example = f"EXEMPLO {i+1} {verified}:\n"
            example += f"Texto: {snippet}\n"
            example += f"Classificação: {doc_type} (confiança: {confidence:.2f})\n"
            
            examples.append(example)
            
        return "\n".join(examples)
        
    def classify_document(self, document_text: str) -> Tuple[str, float]:
        """
        Classify a document based on its text content, using previously classified
        documents as examples when available.
        
        Args:
            document_text: Text content of the document
            
        Returns:
            Tuple of (document type, confidence score)
        """
        try:
            logger.info("Classifying document using adaptive approach...")
            
            # Use only the first 1500 characters for classification to save tokens
            truncated_text = document_text[:1500]
            
            # Try to find similar documents for examples
            similar_docs = self.vector_store.get_similar_documents(truncated_text, k=3)
            
            # If we have similar documents, use the adaptive approach
            if similar_docs:
                logger.info(f"Found {len(similar_docs)} similar documents for classification")
                examples = self._format_examples(similar_docs)
                
                # Use adaptive classification with examples
                document_type = self.adaptive_chain.invoke({
                    "document_text": truncated_text,
                    "examples": examples
                })
                
                # Calculate confidence based on similarity scores
                # This is a simplified approach - could be more sophisticated
                confidence = 0.7 + 0.2 * (1 if any(doc.metadata.get("feedback", False) for doc in similar_docs) else 0)
            else:
                logger.info("No similar documents found, using base classification")
                
                # Use base classification without examples
                document_type = self.base_chain.invoke({
                    "document_text": truncated_text
                })
                
                # Base confidence when no examples are available
                confidence = 0.7
            
            # Validate the classification result
            document_type = document_type.strip()
            if document_type not in DOCUMENT_TYPES:
                logger.warning(f"Unexpected document type: {document_type}. Using best match.")
                # Try to find the closest match in supported document types
                document_type = self._find_closest_match(document_type)
                confidence = max(0.5, confidence - 0.2)  # Reduce confidence for inexact matches
            
            logger.info(f"Document classified as: {document_type} (confidence: {confidence:.2f})")
            return document_type, confidence
            
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            raise RuntimeError(f"Failed to classify document: {str(e)}")
    
    def _find_closest_match(self, document_type: str) -> str:
        """Find the closest match among supported document types"""
        for supported_type in DOCUMENT_TYPES:
            if document_type.lower() in supported_type.lower() or supported_type.lower() in document_type.lower():
                return supported_type
        return DOCUMENT_TYPES[0]  # Default to the first type if no match found
    
    def add_feedback(self, document_text: str, correct_type: str, document_id: Optional[str] = None) -> bool:
        """
        Add feedback about a document classification to improve future classifications.
        
        Args:
            document_text: Text content of the document
            correct_type: Correct document type
            document_id: Optional ID of an existing document
            
        Returns:
            Success flag
        """
        try:
            if document_id:
                # If we have a document ID, update it with feedback
                return self.vector_store.update_with_feedback(
                    document_id=document_id,
                    correct_type=correct_type,
                    extraction_data={}  # Empty extraction data
                )
            else:
                # Otherwise, add as a new document with feedback
                self.vector_store.add_document(
                    document_text=document_text,
                    document_type=correct_type,
                    extraction_data={},
                    confidence_score=1.0,  # Maximum confidence since it's human-verified
                )
                return True
                
        except Exception as e:
            logger.error(f"Error adding classification feedback: {str(e)}")
            return False