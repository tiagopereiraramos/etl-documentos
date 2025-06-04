import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from config import DEFAULT_MODEL, OPENAI_API_KEY, DOCUMENT_TYPES
from vector_store.faiss_store import FAISSAdaptiveStore

logger = logging.getLogger(__name__)

class FAISSAdaptiveClassifier:
    """
    Classifica documentos com base no conteúdo usando LangChain, LLMs,
    e busca vetorial FAISS para aprendizado contínuo.
    """
    
    def __init__(
        self, 
        vector_store: FAISSAdaptiveStore,
        model_name: str = DEFAULT_MODEL, 
        openai_api_key: str = OPENAI_API_KEY
    ):
        """
        Inicializa o classificador adaptativo.
        
        Args:
            vector_store: Banco vetorial FAISS para recuperação e armazenamento de documentos
            model_name: Nome do modelo LLM a ser usado
            openai_api_key: Chave da API OpenAI
        """
        self.vector_store = vector_store
        self.llm = ChatOpenAI(model=model_name, openai_api_key=openai_api_key)
        self.output_parser = StrOutputParser()
        
        # Cria texto de tipos de documentos para prompts
        self.document_types_text = "\n".join([f"{i+1}. {doc_type}" for i, doc_type in enumerate(DOCUMENT_TYPES)])
        
        # Cria prompt de classificação base (sem exemplos)
        self.base_classification_prompt = ChatPromptTemplate.from_template(
            f"""Você recebe um texto de um documento e precisa classificá-lo em um dos seguintes tipos:

{self.document_types_text}

Texto do documento:
{{document_text}}

Responda com apenas o tipo do documento. Exemplo: "Comprovante Bancário"
"""
        )
        
        # Cria prompt de classificação adaptativo (com exemplos)
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
        
        # Constrói cadeias de classificação
        self.base_chain = self.base_classification_prompt | self.llm | self.output_parser
        self.adaptive_chain = self.adaptive_classification_prompt | self.llm | self.output_parser
        
    def _format_examples(self, similar_docs: List[Document]) -> str:
        """Formata documentos similares como exemplos para o prompt."""
        examples = []
        
        for i, doc in enumerate(similar_docs):
            # Obtém um trecho do texto (primeiros 200 caracteres)
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
        Classifica um documento com base no seu conteúdo, usando documentos previamente
        classificados como exemplos quando disponíveis.
        
        Args:
            document_text: Conteúdo textual do documento
            
        Returns:
            Tupla com (tipo de documento, pontuação de confiança)
        """
        try:
            logger.info("Classificando documento usando abordagem adaptativa...")
            
            # Usa apenas os primeiros 1500 caracteres para economizar tokens
            truncated_text = document_text[:1500]
            
            # Tenta encontrar documentos similares como exemplos
            similar_docs = self.vector_store.get_similar_documents(truncated_text, k=3)
            
            # Se temos documentos similares, usamos a abordagem adaptativa
            if similar_docs:
                logger.info(f"Encontrados {len(similar_docs)} documentos similares para classificação")
                examples = self._format_examples(similar_docs)
                
                # Usa classificação adaptativa com exemplos
                document_type = self.adaptive_chain.invoke({
                    "document_text": truncated_text,
                    "examples": examples
                })
                
                # Calcula confiança com base na pontuação de similaridade
                # Esta é uma abordagem simplificada - poderia ser mais sofisticada
                confidence = 0.7 + 0.2 * (1 if any(doc.metadata.get("feedback", False) for doc in similar_docs) else 0)
            else:
                logger.info("Nenhum documento similar encontrado, usando classificação base")
                
                # Usa classificação base sem exemplos
                document_type = self.base_chain.invoke({
                    "document_text": truncated_text
                })
                
                # Confiança base quando não há exemplos disponíveis
                confidence = 0.7
            
            # Valida o resultado da classificação
            document_type = document_type.strip()
            if document_type not in DOCUMENT_TYPES:
                logger.warning(f"Tipo de documento inesperado: {document_type}. Usando melhor correspondência.")
                # Tenta encontrar a correspondência mais próxima nos tipos de documentos suportados
                document_type = self._find_closest_match(document_type)
                confidence = max(0.5, confidence - 0.2)  # Reduz confiança para correspondências inexatas
            
            logger.info(f"Documento classificado como: {document_type} (confiança: {confidence:.2f})")
            return document_type, confidence
            
        except Exception as e:
            logger.error(f"Erro ao classificar documento: {str(e)}")
            raise RuntimeError(f"Falha ao classificar documento: {str(e)}")
    
    def _find_closest_match(self, document_type: str) -> str:
        """Encontra a correspondência mais próxima entre os tipos de documentos suportados"""
        for supported_type in DOCUMENT_TYPES:
            if document_type.lower() in supported_type.lower() or supported_type.lower() in document_type.lower():
                return supported_type
        return DOCUMENT_TYPES[0]  # Padrão para o primeiro tipo se nenhuma correspondência for encontrada
    
    def add_feedback(self, document_text: str, correct_type: str, document_id: Optional[str] = None) -> bool:
        """
        Adiciona feedback sobre uma classificação de documento para melhorar classificações futuras.
        
        Args:
            document_text: Conteúdo textual do documento
            correct_type: Tipo correto do documento
            document_id: ID opcional de um documento existente
            
        Returns:
            Indicador de sucesso
        """
        try:
            if document_id:
                # Se temos um ID de documento, atualizamos com feedback
                return self.vector_store.update_with_feedback(
                    document_id=document_id,
                    correct_type=correct_type,
                    extraction_data={}  # Dados de extração vazios
                )
            else:
                # Caso contrário, adicionamos como um novo documento com feedback
                self.vector_store.add_document(
                    document_text=document_text,
                    document_type=correct_type,
                    extraction_data={},
                    confidence_score=1.0,  # Confiança máxima já que é verificado por humano
                )
                return True
                
        except Exception as e:
            logger.error(f"Erro ao adicionar feedback de classificação: {str(e)}")
            return False