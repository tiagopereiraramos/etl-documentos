"""
Serviço de banco vetorial adaptativo para aprendizado contínuo
"""
import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pydantic.types import SecretStr

try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS, Chroma
    from langchain_core.documents import Document
except ImportError:
    # Fallback para versões mais antigas
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import FAISS, Chroma
    from langchain.schema import Document
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import DocumentoVetorial
from app.database.connection import get_db

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Serviço de banco vetorial adaptativo para armazenamento e recuperação
    de documentos com capacidade de aprendizado contínuo
    """

    def __init__(self, persist_directory: str = None):
        """
        Inicializa o serviço de banco vetorial
        """
        vector_store_path = None
        if hasattr(settings, 'vector_store') and settings.vector_store and getattr(settings.vector_store, 'path', None):
            vector_store_path = settings.vector_store.path
        else:
            vector_store_path = './data/vector_store'
        self.persist_directory = str(
            persist_directory) if persist_directory else vector_store_path
        self.embeddings = None
        self.document_stores = {}
        self.general_store = None
        self.initialized = False
        logger.info(
            f"Inicializando serviço de banco vetorial em {self.persist_directory}")
        try:
            self._initialize_embeddings()
            self._initialize_stores()
            self.initialized = True
            logger.info("Banco vetorial inicializado com sucesso")
        except Exception as e:
            logger.warning(
                f"Banco vetorial será inicializado em modo offline: {str(e)}")
            self.initialized = False

    def _initialize_embeddings(self):
        """Inicializa embeddings com fallback para modo offline"""
        openai_api_key = None
        embedding_model = "text-embedding-3-small"
        if hasattr(settings, 'vector_store') and settings.vector_store and getattr(settings.vector_store, 'embedding_model', None):
            embedding_model = settings.vector_store.embedding_model
        if hasattr(settings, 'llm') and settings.llm and getattr(settings.llm, 'openai_api_key', None):
            openai_api_key = settings.llm.openai_api_key.get_secret_value()
        if not openai_api_key:
            raise ValueError("OpenAI API Key não configurada - modo offline")
        self.embeddings = OpenAIEmbeddings(
            api_key=openai_api_key, model=embedding_model)

    def _initialize_stores(self):
        """Inicializa os stores vetoriais para cada tipo de documento"""
        if not self.embeddings:
            logger.warning(
                "Embeddings não disponíveis - pulando inicialização de stores")
            return
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            general_path = os.path.join(self.persist_directory, "general")
            self.general_store = self._create_store(general_path)
            doc_types = getattr(settings, 'document_types', [
                "Comprovante Bancário", "CEI da Obra", "Inscrição Municipal", "Termo de Responsabilidade", "Alvará Municipal", "Contrato Social", "Cartão CNPJ", "CNH", "Fatura Telefônica", "Nota Fiscal de Serviços Eletrônica"
            ])
            for doc_type in doc_types:
                type_path = os.path.join(
                    self.persist_directory,
                    doc_type.replace(" ", "_").lower()
                )
                self.document_stores[doc_type] = self._create_store(type_path)
            logger.info(
                f"Banco vetorial inicializado com {len(doc_types)} tipos de documento")
        except Exception as e:
            logger.error(f"Erro ao inicializar banco vetorial: {str(e)}")
            raise RuntimeError(
                f"Falha ao inicializar banco vetorial: {str(e)}")

    def _create_store(self, store_path: str):
        if not self.embeddings:
            return None
        os.makedirs(store_path, exist_ok=True)
        vector_store_type = "faiss"
        if hasattr(settings, 'vector_store') and settings.vector_store and getattr(settings.vector_store, 'type', None):
            vector_store_type = settings.vector_store.type.value if hasattr(
                settings.vector_store.type, 'value') else settings.vector_store.type
        if vector_store_type.lower() == "faiss":
            index_path = os.path.join(store_path, "index.faiss")
            if os.path.exists(index_path):
                logger.debug(f"Carregando store FAISS existente: {store_path}")
                return FAISS.load_local(
                    folder_path=store_path,
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
            else:
                logger.debug(f"Criando novo store FAISS: {store_path}")
                placeholder = Document(
                    page_content="documento de inicialização",
                    metadata={"tipo": "placeholder",
                              "created_at": datetime.now().isoformat()}
                )
                store = FAISS.from_documents([placeholder], self.embeddings)
                store.save_local(store_path)
                return store
        elif vector_store_type.lower() == "chroma":
            logger.debug(f"Inicializando store Chroma: {store_path}")
            return Chroma(
                persist_directory=store_path,
                embedding_function=self.embeddings
            )
        else:
            raise ValueError(
                f"Tipo de vector store não suportado: {vector_store_type}")

    def add_document(
        self,
        document_text: str,
        document_type: str,
        extracted_data: Dict[str, Any],
        document_id: Optional[str] = None,
        confidence_score: float = 1.0,
        db_session: Optional[Session] = None
    ) -> str:
        """
        Adiciona um documento ao banco vetorial

        Args:
            document_text: Texto do documento
            document_type: Tipo do documento
            extracted_data: Dados extraídos estruturados
            document_id: ID do documento na base de dados
            confidence_score: Pontuação de confiança
            db_session: Sessão do banco de dados

        Returns:
            ID do documento no banco vetorial
        """
        if not self.initialized:
            logger.warning(
                "Banco vetorial não inicializado - operação ignorada")
            return "offline-mode"

        try:
            logger.info(
                f"Adicionando documento ao banco vetorial: {document_type}")

            # Criar documento LangChain
            metadata = {
                "document_type": document_type,
                "extracted_data": extracted_data,
                "confidence_score": confidence_score,
                "document_id": document_id,
                "timestamp": datetime.now().isoformat(),
                "feedback_verified": False,
                "usage_count": 0
            }

            document = Document(
                page_content=document_text,
                metadata=metadata
            )

            # Adicionar ao store geral
            vector_id = None
            if self.general_store and hasattr(self.general_store, 'add_documents'):
                general_ids = self.general_store.add_documents([document])
                vector_id = general_ids[0]
            else:
                logger.warning("general_store não inicializado!")
                return "erro"

            # Adicionar ao store específico do tipo
            vector_store_type = 'faiss'
            if hasattr(settings, 'vector_store') and settings.vector_store and getattr(settings.vector_store, 'type', None):
                vector_store_type = settings.vector_store.type.value if hasattr(
                    settings.vector_store.type, 'value') else settings.vector_store.type
            if document_type in self.document_stores and self.document_stores[document_type] and hasattr(self.document_stores[document_type], 'add_documents'):
                self.document_stores[document_type].add_documents([document])
                if vector_store_type.lower() == "faiss" and hasattr(self.document_stores[document_type], 'save_local'):
                    type_path = os.path.join(
                        self.persist_directory,
                        document_type.replace(" ", "_").lower()
                    )
                    self.document_stores[document_type].save_local(type_path)

            # Salvar store geral se for FAISS
            if vector_store_type.lower() == "faiss" and self.general_store and hasattr(self.general_store, 'save_local'):
                general_path = os.path.join(self.persist_directory, "general")
                self.general_store.save_local(general_path)

            # Registrar no banco de dados se sessão fornecida
            if db_session and document_id:
                self._register_vector_document(
                    db_session, document_id, vector_id, document_type,
                    document_text, metadata, confidence_score
                )

            logger.info(
                f"Documento adicionado com sucesso. Vector ID: {vector_id}")
            return vector_id

        except Exception as e:
            logger.error(
                f"Erro ao adicionar documento ao banco vetorial: {str(e)}")
            return "erro"

    def get_similar_documents_for_classification(
        self,
        document_text: str,
        k: int = 3
    ) -> List[Document]:
        """
        Busca documentos similares para auxiliar na classificação

        Args:
            document_text: Texto do documento para busca
            k: Número de documentos similares a retornar

        Returns:
            Lista de documentos similares
        """
        if not self.initialized:
            logger.warning("Banco vetorial não inicializado - busca ignorada")
            return []

        try:
            logger.debug(
                f"Buscando {k} documentos similares para classificação")

            docs = self.general_store.similarity_search_with_score(
                document_text, k=k)
            result = []
            for doc, score in docs:
                doc.metadata["similarity"] = score
                result.append(doc)

            # Atualizar contador de uso
            self._update_usage_count(result)

            logger.debug(f"Encontrados {len(result)} documentos similares")
            return result

        except Exception as e:
            logger.error(f"Erro na busca de documentos similares: {str(e)}")
            return []

    def get_similar_documents_for_extraction(
        self,
        document_text: str,
        document_type: str,
        k: int = 3
    ) -> List[Document]:
        """
        Busca documentos similares do mesmo tipo para auxiliar na extração

        Args:
            document_text: Texto do documento
            document_type: Tipo específico do documento
            k: Número de documentos similares

        Returns:
            Lista de documentos similares do mesmo tipo
        """
        if not self.initialized:
            logger.warning("Banco vetorial não inicializado - busca ignorada")
            return []

        try:
            if document_type not in self.document_stores:
                logger.warning(
                    f"Store não encontrado para tipo: {document_type}")
                return []

            logger.debug(
                f"Buscando {k} documentos {document_type} similares para extração")

            docs = self.document_stores[document_type].similarity_search_with_score(
                document_text, k=k)
            result = []
            for doc, score in docs:
                doc.metadata["similarity"] = score
                result.append(doc)

            # Atualizar contador de uso
            self._update_usage_count(result)

            logger.debug(
                f"Encontrados {len(result)} documentos {document_type} similares")
            return result

        except Exception as e:
            logger.error(
                f"Erro na busca de documentos similares para extração: {str(e)}")
            return []

    def update_with_feedback(
        self,
        vector_id: str,
        correct_type: str,
        correct_data: Dict[str, Any],
        db_session: Optional[Session] = None
    ) -> bool:
        """
        Atualiza documento com feedback humano para melhorar aprendizado

        Args:
            vector_id: ID do documento no banco vetorial
            correct_type: Tipo correto do documento
            correct_data: Dados corretos extraídos
            db_session: Sessão do banco de dados

        Returns:
            Sucesso da operação
        """
        if not self.initialized:
            logger.warning(
                "Banco vetorial não inicializado - feedback ignorado")
            return False

        try:
            logger.info(
                f"Feedback recebido para vetor {vector_id}: {correct_type}")

            # Buscar documento original
            docs = self.general_store.similarity_search(
                "",  # Query vazia
                k=1,
                filter={"vector_id": vector_id}
            )

            if not docs:
                logger.error(f"Documento não encontrado: {vector_id}")
                return False

            original_doc = docs[0]
            original_type = original_doc.metadata.get("document_type")

            # Criar documento atualizado com feedback
            updated_metadata = original_doc.metadata.copy()
            updated_metadata.update({
                "document_type": correct_type,
                "extracted_data": correct_data,
                "feedback_verified": True,
                "feedback_timestamp": datetime.now().isoformat(),
                "original_type": original_type,
                "confidence_score": 1.0  # Máxima confiança para dados verificados
            })

            updated_doc = Document(
                page_content=original_doc.page_content,
                metadata=updated_metadata
            )

            # Adicionar documento corrigido
            self.general_store.add_documents([updated_doc])

            # Adicionar ao store do tipo correto se necessário
            if correct_type in self.document_stores:
                self.document_stores[correct_type].add_documents([updated_doc])

                if vector_store_type.lower() == "faiss":
                    type_path = os.path.join(
                        self.persist_directory,
                        correct_type.replace(" ", "_").lower()
                    )
                    self.document_stores[correct_type].save_local(type_path)

            # Salvar store geral
            vector_store_type = settings.vector_store.type.value if hasattr(
                settings.vector_store.type, 'value') else settings.vector_store.type
            if vector_store_type.lower() == "faiss":
                general_path = os.path.join(self.persist_directory, "general")
                self.general_store.save_local(general_path)

            # Atualizar registro no banco de dados
            if db_session:
                self._update_vector_feedback(
                    db_session, vector_id, correct_type, correct_data)

            logger.info(
                f"Feedback aplicado com sucesso para documento {vector_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao aplicar feedback: {str(e)}")
            return False

    def _register_vector_document(
        self,
        db_session: Session,
        document_id: str,
        vector_id: str,
        document_type: str,
        text_content: str,
        metadata: Dict[str, Any],
        confidence: float
    ):
        """Registra documento vetorial no banco de dados"""
        try:
            vector_doc = DocumentoVetorial(
                documento_id=int(document_id),
                vetor_id=vector_id,
                tipo_documento=document_type,
                texto_indexado=text_content[:1000],  # Primeiros 1000 chars
                metadados=metadata,
                confianca_inicial=confidence
            )
            db_session.add(vector_doc)
            db_session.commit()

        except Exception as e:
            logger.error(
                f"Erro ao registrar documento vetorial no BD: {str(e)}")

    def _update_vector_feedback(
        self,
        db_session: Session,
        vector_id: str,
        correct_type: str,
        correct_data: Dict[str, Any]
    ):
        """Atualiza registro de feedback no banco de dados"""
        try:
            vector_doc = db_session.query(DocumentoVetorial).filter(
                DocumentoVetorial.vetor_id == vector_id
            ).first()

            if vector_doc:
                vector_doc.feedback_aplicado = True
                vector_doc.tipo_documento = correct_type
                vector_doc.metadados = {
                    **vector_doc.metadados,
                    "corrected_data": correct_data,
                    "feedback_timestamp": datetime.now().isoformat()
                }
                db_session.commit()

        except Exception as e:
            logger.error(f"Erro ao atualizar feedback no BD: {str(e)}")

    def _update_usage_count(self, documents: List[Document]):
        """Atualiza contador de uso dos documentos"""
        for doc in documents:
            if "usage_count" in doc.metadata:
                doc.metadata["usage_count"] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do banco vetorial

        Returns:
            Dicionário com estatísticas
        """
        try:
            stats = {
                "total_documents": 0,
                "documents_by_type": {},
                "feedback_verified": 0,
                "store_type": settings.vector_store.type,
                "embedding_model": settings.vector_store.embedding_model,
                "initialized": self.initialized
            }

            if not self.initialized:
                stats["status"] = "offline"
                return stats

            # Contar documentos por tipo (aproximação para FAISS)
            for doc_type, store in self.document_stores.items():
                if store and hasattr(store, 'index') and hasattr(store.index, 'ntotal'):
                    count = store.index.ntotal
                    stats["documents_by_type"][doc_type] = count
                    stats["total_documents"] += count

            return stats

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {"error": str(e), "initialized": self.initialized}

    def cleanup_old_documents(self, days_old: int = 90):
        """
        Remove documentos antigos sem feedback para otimizar performance

        Args:
            days_old: Dias de idade para remoção
        """
        # Implementação futura - FAISS não permite remoção fácil
        # Seria necessário reconstruir o índice
        logger.info(
            f"Cleanup de documentos antigos não implementado para {settings.vector_store.type}")
