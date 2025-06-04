import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config import OPENAI_API_KEY, DOCUMENT_TYPES
from utils.logging import get_logger

# Obtém logger contextualizado
logger = get_logger(__name__)

class FAISSAdaptiveStore:
    """
    Sistema de banco vetorial adaptativo usando FAISS para armazenar 
    e recuperar documentos, implementando aprendizado contínuo.
    """
    
    def __init__(self, persist_directory: str = "./vector_store_db"):
        """
        Inicializa o banco vetorial FAISS.
        
        Args:
            persist_directory: Diretório base para persistir os índices FAISS
        """
        self.persist_directory = persist_directory
        logger.info(f"Inicializando banco vetorial FAISS em {persist_directory}")
        
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        
        # Cria índices separados para cada tipo de documento
        self.document_stores = {}
        for doc_type in DOCUMENT_TYPES:
            type_dir = os.path.join(persist_directory, doc_type.replace(" ", "_").lower())
            logger.debug(f"Inicializando índice para {doc_type}")
            self.document_stores[doc_type] = self._initialize_faiss_index(type_dir)
            
        # Índice geral para todos os documentos
        logger.debug(f"Inicializando índice geral")
        self.general_store = self._initialize_faiss_index(persist_directory)
        
        logger.success(f"Banco vetorial FAISS inicializado com sucesso com {len(DOCUMENT_TYPES)} tipos de documentos")
        
    def _initialize_faiss_index(self, directory: str) -> FAISS:
        """Inicializa e retorna um índice FAISS."""
        try:
            os.makedirs(directory, exist_ok=True)
            
            # Verifica se o índice FAISS já existe
            if os.path.exists(f"{directory}/index.faiss"):
                logger.info(f"Carregando índice FAISS existente de {directory}")
                return FAISS.load_local(
                    folder_path=directory,
                    embeddings=self.embeddings
                )
            else:
                # Cria um novo índice FAISS vazio com um documento placeholder
                logger.info(f"Criando novo índice FAISS em {directory}")
                placeholder_doc = Document(
                    page_content="documento de inicialização",
                    metadata={"document_type": "placeholder"}
                )
                db = FAISS.from_documents(
                    documents=[placeholder_doc],
                    embedding=self.embeddings
                )
                db.save_local(directory)
                return db
                
        except Exception as e:
            logger.error(f"Erro ao inicializar índice FAISS: {str(e)}", exc_info=True)
            raise RuntimeError(f"Falha ao inicializar índice FAISS: {str(e)}")
    
    def add_document(self, 
                    document_text: str, 
                    document_type: str, 
                    extraction_data: Dict[str, Any],
                    confidence_score: float = 1.0,
                    document_id: Optional[str] = None) -> str:
        """
        Adiciona um documento ao banco vetorial com sua classificação e dados extraídos.
        """
        try:
            logger.info(f"Adicionando documento ao banco vetorial como '{document_type}'")
            
            # Cria documento com metadados
            metadata = {
                "document_type": document_type,
                "extracted_data": extraction_data,
                "confidence_score": confidence_score,
                "feedback": False,
                "timestamp": datetime.now().isoformat()
            }
            
            if document_id:
                metadata["document_id"] = document_id
                
            document = Document(
                page_content=document_text,
                metadata=metadata
            )
            
            # Adiciona ao índice geral
            general_ids = self.general_store.add_documents([document])
            
            # Adiciona ao índice específico do tipo se existir
            if document_type in self.document_stores:
                type_ids = self.document_stores[document_type].add_documents([document])
                logger.debug(f"Documento adicionado ao índice de '{document_type}' com ID: {type_ids[0]}")
                
                # Salva as alterações
                self.document_stores[document_type].save_local(
                    os.path.join(self.persist_directory, document_type.replace(" ", "_").lower())
                )
            
            # Salva o índice geral
            self.general_store.save_local(self.persist_directory)
                
            logger.success(f"Documento adicionado com sucesso ao banco vetorial com ID: {general_ids[0]}")
            return general_ids[0]
            
        except Exception as e:
            logger.error(f"Erro ao adicionar documento ao banco vetorial: {str(e)}", exc_info=True)
            raise RuntimeError(f"Falha ao adicionar documento ao banco vetorial: {str(e)}")
    
    # [Resto dos métodos com implementação similar usando logger]