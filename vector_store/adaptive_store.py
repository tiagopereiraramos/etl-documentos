import os
import logging
from typing import List, Dict, Any, Optional, Tuple

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS, Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore as LangchainVectorStore

from config import OPENAI_API_KEY, VECTOR_STORE_PATH, VECTOR_STORE_TYPE, DOCUMENT_TYPES

logger = logging.getLogger(__name__)

class AdaptiveVectorStore:
    """
    Vector database for storing and retrieving document embeddings with 
    continuous learning capabilities to improve document classification over time.
    """
    
    def __init__(self, store_type: str = VECTOR_STORE_TYPE, persist_directory: str = VECTOR_STORE_PATH):
        """
        Initialize the adaptive vector store.
        
        Args:
            store_type: Type of vector store to use ('faiss' or 'chroma')
            persist_directory: Directory to persist the vector store
        """
        self.store_type = store_type.lower()
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        
        # Create separate collections/indices for each document type
        self.document_stores = {}
        for doc_type in DOCUMENT_TYPES:
            type_dir = os.path.join(persist_directory, doc_type.replace(" ", "_").lower())
            self.document_stores[doc_type] = self._initialize_vector_store(type_dir)
            
        # General store for all documents
        self.general_store = self._initialize_vector_store(persist_directory)
        
    def _initialize_vector_store(self, directory: str) -> LangchainVectorStore:
        """Initialize and return the vector store based on the specified type."""
        try:
            os.makedirs(directory, exist_ok=True)
            
            if self.store_type == "faiss":
                # Check if FAISS index exists
                if os.path.exists(f"{directory}/index.faiss"):
                    logger.info(f"Loading existing FAISS vector store from {directory}")
                    return FAISS.load_local(
                        folder_path=directory,
                        embeddings=self.embeddings
                    )
                else:
                    # Create a new empty FAISS index with a placeholder document
                    logger.info(f"Creating new FAISS vector store in {directory}")
                    placeholder_doc = Document(
                        page_content="initialization document",
                        metadata={"document_type": "placeholder"}
                    )
                    db = FAISS.from_documents(
                        documents=[placeholder_doc],
                        embedding=self.embeddings
                    )
                    db.save_local(directory)
                    return db
                    
            elif self.store_type == "chroma":
                logger.info(f"Initializing Chroma vector store in {directory}")
                return Chroma(
                    persist_directory=directory,
                    embedding_function=self.embeddings
                )
            else:
                raise ValueError(f"Unsupported vector store type: {self.store_type}")
                
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise RuntimeError(f"Failed to initialize vector store: {str(e)}")
    
    def add_document(self, 
                    document_text: str, 
                    document_type: str, 
                    extraction_data: Dict[str, Any],
                    confidence_score: float = 1.0,
                    document_id: Optional[str] = None) -> str:
        """
        Add a document to the vector store with its classification and extraction data.
        
        Args:
            document_text: Text content of the document
            document_type: Classified type of the document
            extraction_data: Extracted structured data from the document
            confidence_score: Confidence level of the classification (0.0 to 1.0)
            document_id: Optional ID to identify the document (for updates)
            
        Returns:
            Document ID in the vector store
        """
        try:
            logger.info(f"Adding document to vector store as '{document_type}'")
            
            # Create document with metadata
            metadata = {
                "document_type": document_type,
                "extracted_data": extraction_data,
                "confidence_score": confidence_score,
                "feedback": False,  # Initially not verified by human feedback
                "timestamp": datetime.now().isoformat()
            }
            
            if document_id:
                metadata["document_id"] = document_id
                
            document = Document(
                page_content=document_text,
                metadata=metadata
            )
            
            # Add to the general store
            general_ids = self.general_store.add_documents([document])
            
            # Add to the type-specific store if it exists
            if document_type in self.document_stores:
                type_ids = self.document_stores[document_type].add_documents([document])
                
                # Save the changes
                if self.store_type == "faiss":
                    self.document_stores[document_type].save_local(
                        os.path.join(self.persist_directory, document_type.replace(" ", "_").lower())
                    )
            
            # Save the general store
            if self.store_type == "faiss":
                self.general_store.save_local(self.persist_directory)
                
            logger.info(f"Document successfully added to vector store with ID: {general_ids[0]}")
            return general_ids[0]
            
        except Exception as e:
            logger.error(f"Error adding document to vector store: {str(e)}")
            raise RuntimeError(f"Failed to add document to vector store: {str(e)}")
    
    def get_similar_documents(self, document_text: str, k: int = 3) -> List[Document]:
        """
        Find similar documents across all document types.
        
        Args:
            document_text: The document text to compare against
            k: Number of similar documents to return
            
        Returns:
            List of similar documents with their metadata
        """
        try:
            logger.info(f"Finding {k} similar documents for classification...")
            
            # Search in the general store
            similar_docs = self.general_store.similarity_search(
                document_text, 
                k=k,
                filter={"feedback": True}  # Prioritize documents with human feedback
            )
            
            # If we don't have enough verified documents, get some unverified ones too
            if len(similar_docs) < k:
                additional_docs = self.general_store.similarity_search(
                    document_text,
                    k=(k - len(similar_docs))
                )
                similar_docs.extend(additional_docs)
            
            logger.info(f"Found {len(similar_docs)} similar documents")
            return similar_docs
            
        except Exception as e:
            logger.error(f"Error finding similar documents: {str(e)}")
            return []  # Return empty list instead of failing
    
    def get_similar_documents_by_type(self, document_text: str, document_type: str, k: int = 3) -> List[Document]:
        """
        Find similar documents of a specific type to help with data extraction.
        
        Args:
            document_text: The document text to compare against
            document_type: The type of document to search for
            k: Number of similar documents to return
            
        Returns:
            List of similar documents of the specified type
        """
        try:
            if document_type not in self.document_stores:
                logger.warning(f"No vector store for document type: {document_type}")
                return []
                
            logger.info(f"Finding {k} similar {document_type} documents...")
            
            # Search in the type-specific store
            similar_docs = self.document_stores[document_type].similarity_search(
                document_text, 
                k=k
            )
            
            logger.info(f"Found {len(similar_docs)} similar {document_type} documents")
            return similar_docs
            
        except Exception as e:
            logger.error(f"Error finding similar documents by type: {str(e)}")
            return []  # Return empty list instead of failing
    
    def update_with_feedback(self, document_id: str, correct_type: str, extraction_data: Dict[str, Any]) -> bool:
        """
        Update a document with human feedback to improve future classifications.
        
        Args:
            document_id: ID of the document to update
            correct_type: Correct document type (may be different from original classification)
            extraction_data: Corrected extraction data
            
        Returns:
            Success flag
        """
        try:
            # Get the document from the general store
            docs = self.general_store.similarity_search(
                "",  # Empty query
                k=1,
                filter={"document_id": document_id}
            )
            
            if not docs:
                logger.error(f"Document with ID {document_id} not found")
                return False
                
            original_doc = docs[0]
            original_type = original_doc.metadata["document_type"]
            
            # Create updated document with feedback
            updated_metadata = original_doc.metadata.copy()
            updated_metadata["document_type"] = correct_type
            updated_metadata["extracted_data"] = extraction_data
            updated_metadata["feedback"] = True
            updated_metadata["feedback_timestamp"] = datetime.now().isoformat()
            
            updated_doc = Document(
                page_content=original_doc.page_content,
                metadata=updated_metadata
            )
            
            # Remove from original type store if type changed
            if original_type != correct_type and original_type in self.document_stores:
                # We can't easily delete from FAISS, so we add a flag instead
                updated_metadata["deprecated"] = True
                self.document_stores[original_type].add_documents([
                    Document(page_content=original_doc.page_content, metadata=updated_metadata)
                ])
            
            # Add to the correct type store
            if correct_type in self.document_stores:
                self.document_stores[correct_type].add_documents([updated_doc])
                
                # Save the changes
                if self.store_type == "faiss":
                    self.document_stores[correct_type].save_local(
                        os.path.join(self.persist_directory, correct_type.replace(" ", "_").lower())
                    )
            
            # Update in general store
            self.general_store.add_documents([updated_doc])
            
            # Save the general store
            if self.store_type == "faiss":
                self.general_store.save_local(self.persist_directory)
                
            logger.info(f"Document {document_id} updated with feedback")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document with feedback: {str(e)}")
            return False
            
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with statistics about the vector store
        """
        stats = {
            "total_documents": 0,
            "documents_by_type": {},
            "verified_documents": 0
        }
        
        try:
            # Count documents in each type store
            for doc_type in self.document_stores:
                if self.store_type == "faiss":
                    # For FAISS, we can get the index size
                    type_store = self.document_stores[doc_type]
                    count = len(type_store.index_to_docstore_id)
                    stats["documents_by_type"][doc_type] = count
                    stats["total_documents"] += count
                # For Chroma, this is more complex and may require a database query
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting vector store statistics: {str(e)}")
            return stats