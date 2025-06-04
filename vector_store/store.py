import os
import logging
from typing import List, Dict, Any, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS, Chroma
from langchain_core.documents import Document

from config import OPENAI_API_KEY, VECTOR_STORE_PATH, VECTOR_STORE_TYPE, DOCUMENT_TYPES
from utils.logging import get_logger

logger = get_logger(__name__)

class VectorStore:
    """
    Vector database for storing and retrieving document embeddings.
    """
    
    def __init__(self, persist_directory: str = VECTOR_STORE_PATH):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Directory to persist the vector store
        """
        self.persist_directory = persist_directory
        logger.info(f"Initializing vector store in {persist_directory}")
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        
        # Initialize vector store
        self.db = self._initialize_vector_store()
        
    def _initialize_vector_store(self):
        """Initialize and return the vector store based on configuration."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize based on configuration
            if VECTOR_STORE_TYPE.lower() == "faiss":
                # Check if FAISS index exists
                if os.path.exists(f"{self.persist_directory}/index.faiss"):
                    logger.info(f"Loading existing FAISS vector store from {self.persist_directory}")
                    return FAISS.load_local(
                        folder_path=self.persist_directory,
                        embeddings=self.embeddings,
                        allow_dangerous_deserialization=True  # Adicionado este parâmetro
                    )
                else:
                    # Create a new empty FAISS index
                    logger.info(f"Creating new FAISS vector store in {self.persist_directory}")
                    return FAISS.from_documents(
                        documents=[],  # Empty list for initial index
                        embedding=self.embeddings
                    )
                    
            elif VECTOR_STORE_TYPE.lower() == "chroma":
                logger.info(f"Initializing Chroma vector store in {self.persist_directory}")
                return Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            else:
                raise ValueError(f"Unsupported vector store type: {VECTOR_STORE_TYPE}")
                
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise RuntimeError(f"Failed to initialize vector store: {str(e)}")
    
    # [Resto do código mantido como está...]