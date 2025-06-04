from config import DEFAULT_MODEL, OPENAI_API_KEY, DOCUMENT_TYPES 
from utils.logging import get_logger
from utils.llm_tracker import LLMUsageTracker
from utils.document_logging import DocumentTracker  # Importar DocumentTracker

import uuid
import time
from typing import Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.callbacks import BaseCallbackHandler

# Obtém logger contextualizado
logger = get_logger(__name__)

class LLMUsageCallbackHandler(BaseCallbackHandler):
    """
    Callback handler para rastrear uso de tokens e custos em chamadas LLM via LangChain.
    """
    
    def __init__(self, llm_tracker: LLMUsageTracker, call_id: str, model_name: str, doc_id: str = None, doc_name: str = None):
        self.llm_tracker = llm_tracker
        self.call_id = call_id
        self.model_name = model_name
        self.start_time = time.time()
        self.input_tokens = 0
        self.output_tokens = 0
        self.successful = False
        self.metadata = {}
        
        # Adicionamos dados do documento para rastreamento
        self.doc_id = doc_id
        self.doc_name = doc_name
        
    def on_llm_start(self, serialized: Dict[str, Any], prompts: list, **kwargs):
        """Chamado quando a geração LLM começa."""
        # Registrar metadados adicionais se disponíveis
        self.metadata["operation"] = "document_classification"
        
        # Log visual do início do processo de classificação
        if self.doc_id and self.doc_name:
            DocumentTracker.log_classification(
                self.doc_id, 
                self.doc_name, 
                "Em andamento...", 
                None,
                None
            )
        
    def on_llm_end(self, response, **kwargs):
        """Chamado quando a geração LLM termina com sucesso."""
        self.successful = True
        
        # Extrair contagem de tokens da resposta se disponível
        if hasattr(response, 'llm_output') and isinstance(response.llm_output, dict):
            llm_output = response.llm_output
            self.input_tokens = llm_output.get('token_usage', {}).get('prompt_tokens', 0)
            self.output_tokens = llm_output.get('token_usage', {}).get('completion_tokens', 0)
        
        # Calcular tempo de processamento
        processing_time = time.time() - self.start_time
        self.metadata["processing_time"] = round(processing_time, 3)
        
        # Adicionar informação sobre documento
        if self.doc_id and self.doc_name:
            self.metadata["doc_id"] = self.doc_id
            self.metadata["doc_name"] = self.doc_name
        
        # Registrar uso no tracker
        self._record_usage()
        
    def on_llm_error(self, error, **kwargs):
        """Chamado quando a geração LLM termina com erro."""
        processing_time = time.time() - self.start_time
        self.metadata["error"] = str(error)
        self.metadata["processing_time"] = round(processing_time, 3)
        
        # Registrar erro no DocumentTracker
        if self.doc_id and self.doc_name:
            error_msg = f"Erro na classificação: {str(error)}"
            DocumentTracker.log_error(self.doc_id, self.doc_name, error_msg, processing_time)
        
        # Mesmo com erro, registramos o uso (pode ter havido consumo de tokens)
        self._record_usage()
    
    def _record_usage(self):
        """Registra uso no LLMUsageTracker."""
        if self.llm_tracker:
            self.llm_tracker.record_usage(
                call_id=self.call_id,
                model=self.model_name,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                success=self.successful,
                metadata=self.metadata
            )

class DocumentClassifier:
    """
    Classifies documents based on their content using LangChain and LLMs.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, openai_api_key: str = OPENAI_API_KEY):
        """
        Initialize the document classifier.

        Args:
            model_name: Name of the LLM model to use
            openai_api_key: OpenAI API key
        """
        logger.info(f"Inicializando classificador com modelo {model_name}")
        
        # Inicializar rastreador de uso de LLMs
        try:
            self.llm_tracker = LLMUsageTracker(log_dir="./logs")
            logger.info("Rastreador de uso de LLMs inicializado com sucesso")
        except Exception as e:
            logger.warning(f"Não foi possível inicializar rastreador de uso de LLMs: {str(e)}")
            self.llm_tracker = None

        # Guardar nome do modelo para referência
        self.model_name = model_name
        
        # Inicializar componentes LangChain
        self.llm = ChatOpenAI(model=model_name, openai_api_key=openai_api_key)
        self.output_parser = StrOutputParser()

        # Create classification prompt with detailed descriptions
        self.classification_prompt = self._create_classification_prompt()

        # Build classification chain
        self.classification_chain = self.classification_prompt | self.llm | self.output_parser
        logger.debug("Cadeia de classificação construída com sucesso")

    def _create_classification_prompt(self):
        """Cria um prompt detalhado para classificação de documentos"""
        # Criar lista de tipos de documentos como texto numerado
        document_types_text = "\n".join([f"{i+1}. {doc_type}" for i, doc_type in enumerate(DOCUMENT_TYPES)])

      # Criar descrições para cada tipo de documento
        descriptions = {
            "Comprovante Bancário": "contém dados de transferência, depósito ou pagamento bancário, valores, datas, códigos de autenticação e instituições financeiras.",
            
            "CEI da Obra": "documento do INSS que identifica uma construção perante a Receita Federal, contendo número de matrícula CEI, endereço da obra, dados do proprietário (CNPJ/CPF), responsável técnico, número ART e informações cadastrais para regularização e recolhimento de tributos.",
            
            "Inscrição Municipal": "documento emitido pela prefeitura com número de inscrição municipal de uma empresa, dados cadastrais e atividades econômicas permitidas no município.",
            
            "Termo de Responsabilidade": "documento formal onde pessoa ou entidade assume responsabilidade por determinada ação, bem ou serviço, contendo identificação do responsável, descrição das obrigações assumidas, condições para cumprimento e possíveis consequências legais.",
            
            "Alvará Municipal": "licença oficial emitida por autoridades municipais que autoriza o funcionamento legal de empresas e atividades específicas, contendo nome da empresa, registro, atividades permitidas, datas de emissão e validade, e autoridade emissora.",
            
            "Cartão CNPJ": "comprovante de inscrição e situação cadastral emitido pela Receita Federal que atesta a existência legal da empresa, contendo número do CNPJ, razão social, nome fantasia, data de abertura, código CNAE das atividades econômicas, natureza jurídica, endereço e situação cadastral.",
            
            "Contrato Social": "documento legal constitutivo que estabelece as regras da sociedade empresária, detalhando razão social, nome fantasia, CNPJ (em alterações), endereço da sede, objeto social, capital social, quotas e dados dos sócios, forma de administração e representação. Difere do Cartão CNPJ por ser o acordo entre os sócios, não apenas um comprovante cadastral.",
            
            "Fatura Telefônica": "conta de serviços telefônicos com detalhamento de ligações, mensagens, dados consumidos, valores e período de cobrança.",
            
            "Nota Fiscal de Serviços Eletrônica": "documento fiscal que comprova prestação de serviços, com valores, impostos (como ISS), dados do prestador e tomador.",
            
            "CNH": "Carteira Nacional de Habilitação, documento de habilitação de motorista, com dados pessoais, foto, categoria e validade.",
        }

        # Criar a seção de características de cada documento
        document_descriptions_text_lines = []
        for doc_type in DOCUMENT_TYPES:
            description = descriptions.get(doc_type)
            if description: # Adiciona apenas se a descrição existir
                document_descriptions_text_lines.append(f"- {doc_type}: {description}")
            else:
                logger.warning(f"Descrição não encontrada para o tipo de documento: {doc_type} em _create_classification_prompt")

        document_descriptions = "\n".join(document_descriptions_text_lines)
        
        # Criar o prompt final
        return ChatPromptTemplate.from_template(
            f"""Você é um especialista em classificação de documentos empresariais e fiscais.

Você receberá um texto extraído de um documento e deverá classificá-lo em um dos seguintes tipos:

{document_types_text}

Aqui estão as características principais de cada tipo de documento para te ajudar na identificação:
{document_descriptions}

Texto do documento:
{{document_text}}

Analise cuidadosamente o conteúdo e classifique o documento.
Responda com apenas o tipo do documento exatamente como está na lista acima. Por exemplo: "Contrato Social"
"""
        )

    def classify_document(self, document_text: str, doc_id: str = None, doc_name: str = None) -> str:
        """
        Classify a document based on its text content.

        Args:
            document_text: Text content of the document
            doc_id: Optional document ID for tracking
            doc_name: Optional document name for tracking

        Returns:
            Document type classification
        """
        # Gerar ID único para este documento se não fornecido
        if not doc_id:
            doc_id = str(uuid.uuid4())[:6]
        
        if not doc_name:
            doc_name = f"documento-{doc_id}"
            
        try:
            logger.info("Classificando documento...")
            
            # Registrar início da classificação para rastreamento visual
            DocumentTracker.log_processing_start(doc_id, doc_name, "Classificação")

            # Use only the first 2000 characters for classification to save tokens
            truncated_text = document_text[:2000]
            logger.debug(f"Usando {len(truncated_text)} caracteres para classificação | ID: {doc_id}")
            
            # Gerar ID único para esta chamada
            call_id = str(uuid.uuid4())[:8]
            
            # Criar callback para rastreamento se o tracker estiver disponível
            callbacks = []
            if self.llm_tracker:
                usage_callback = LLMUsageCallbackHandler(
                    llm_tracker=self.llm_tracker,
                    call_id=call_id,
                    model_name=self.model_name,
                    doc_id=doc_id,
                    doc_name=doc_name
                )
                callbacks.append(usage_callback)
            
            # Estimar tokens do prompt para logging (aproximação)
            prompt_chars = len(self.classification_prompt.format(document_text=truncated_text))
            estimated_input_tokens = prompt_chars // 4  # Aproximação simples: ~4 chars/token
            logger.debug(f"Enviando prompt com aproximadamente {estimated_input_tokens} tokens estimados | ID: {doc_id}")
            
            # Executar a classificação com callbacks
            start_time = time.time()
            classification_result = self.classification_chain.invoke(
                {"document_text": truncated_text},
                config={"callbacks": callbacks}
            )
            elapsed = time.time() - start_time
            
            # Registrar tokens de forma manual se callbacks não funcionaram
            if self.llm_tracker and not callbacks:
                try:
                    # Estimativa básica de tokens para o caso de falha do callback
                    output_tokens = len(classification_result) // 4
                    self.llm_tracker.record_usage(
                        call_id=call_id,
                        model=self.model_name,
                        input_tokens=estimated_input_tokens,
                        output_tokens=output_tokens,
                        success=True,
                        metadata={
                            "operation": "document_classification",
                            "processing_time": round(elapsed, 3),
                            "is_estimated": True,
                            "doc_id": doc_id,
                            "doc_name": doc_name
                        }
                    )
                except Exception as e:
                    logger.warning(f"Falha ao registrar uso estimado de LLM: {str(e)} | ID: {doc_id}")
            
            # Validate the classification result
            document_type = classification_result.strip() # Garante que não há espaços extras

            if document_type not in DOCUMENT_TYPES:
                logger.warning(f"Tipo de documento '{document_type}' retornado pelo LLM não está na lista DOCUMENT_TYPES. Tentando melhor correspondência. | ID: {doc_id}")
                document_type = self._find_closest_match(document_type)
            
            logger.success(f"Documento classificado como: {document_type} em {elapsed:.3f}s")
            
            # Registrar classificação no DocumentTracker
            DocumentTracker.log_classification(doc_id, doc_name, document_type, 0.95, elapsed)
            
            return document_type

        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            error_msg = f"Erro ao classificar documento: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Registrar erro no DocumentTracker
            DocumentTracker.log_error(doc_id, doc_name, error_msg, elapsed)
            
            # Registrar falha se o rastreador estiver disponível
            if self.llm_tracker:
                try:
                    self.llm_tracker.record_usage(
                        call_id=str(uuid.uuid4())[:8],
                        model=self.model_name,
                        input_tokens=estimated_input_tokens if 'estimated_input_tokens' in locals() else 0,
                        output_tokens=0,
                        success=False,
                        metadata={
                            "operation": "document_classification",
                            "error": str(e),
                            "doc_id": doc_id,
                            "doc_name": doc_name
                        }
                    )
                except Exception as tracking_error:
                    logger.warning(f"Erro adicional ao registrar falha no LLM tracker: {str(tracking_error)} | ID: {doc_id}")
            
            raise RuntimeError(f"Falha ao classificar documento: {str(e)}")

    def _find_closest_match(self, document_type_from_llm: str) -> str:
        """Find the closest match among supported document types"""
        # Normaliza a string retornada pelo LLM para comparação
        normalized_llm_type = document_type_from_llm.lower().strip()

        for supported_type in DOCUMENT_TYPES:
            normalized_supported_type = supported_type.lower().strip()
            if normalized_llm_type == normalized_supported_type: # Correspondência exata após normalização
                return supported_type
            # Tenta uma correspondência mais flexível se não houver exata
            if normalized_llm_type in normalized_supported_type or normalized_supported_type in normalized_llm_type:
                logger.debug(f"Correspondência flexível encontrada para '{document_type_from_llm}': '{supported_type}'")
                return supported_type
        
        logger.warning(f"Nenhuma correspondência (exata ou flexível) encontrada para '{document_type_from_llm}'. Usando o primeiro tipo da lista como padrão: '{DOCUMENT_TYPES[0]}'")
        return DOCUMENT_TYPES[0]  # Default to the first type if no robust match found
    
    def get_usage_report(self) -> Dict[str, Any]:
        """
        Retorna relatório de uso de LLMs para este classificador.
        
        Returns:
            Dicionário com estatísticas de uso
        """
        if self.llm_tracker:
            return self.llm_tracker.get_usage_report()
        return {"error": "LLM usage tracking não está habilitado"}
    
    def __del__(self):
        """Método para limpar recursos quando o objeto é destruído."""
        if hasattr(self, 'llm_tracker') and self.llm_tracker:
            try:
                self.llm_tracker.close()
            except Exception:
                pass