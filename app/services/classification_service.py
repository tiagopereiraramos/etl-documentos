"""
Serviço de Classificação Adaptativa de Documentos com Múltiplos LLMs
"""
import yaml
import json
import re
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from app.core.config import settings as configuracoes
from app.core.logging import obter_logger
from app.providers.base import ProvedorLLMBase, ResultadoLLM
from app.providers.azure_provider import AzureOpenAIProvider
from app.providers.aws_provider import AWSBedrockProvider
from app.services.vector_service import VectorStoreService
from app.models.database import FeedbackClassificacao

logger = obter_logger(__name__)


@dataclass
class ResultadoClassificacao:
    """Resultado da classificação de documento"""
    tipo_documento: str
    confianca: float
    metodo: str  # 'adaptive', 'llm_primary', 'llm_fallback', 'error'
    provedor_llm: str
    modelo_llm: str
    tempo_processamento: float
    documentos_similares: Optional[List[Dict[str, Any]]] = None
    erro: Optional[str] = None
    metadados: Optional[Dict[str, Any]] = None


class ClassificationService:
    """Serviço principal de classificação de documentos com múltiplos LLMs"""

    def __init__(self, vector_service: VectorStoreService):
        self.vector_service = vector_service

        # Carregar configurações
        self._load_prompts_config()
        self._load_document_types()

        # Inicializar provedores LLM
        self.llm_providers: List[ProvedorLLMBase] = []
        self._initialize_llm_providers()

        logger.info(
            f"ClassificationService inicializado com {len(self.llm_providers)} provedores LLM")

    def _load_prompts_config(self):
        """Carregar configuração de prompts"""
        try:
            config_path = Path("config/prompts.yaml")
            with open(config_path, 'r', encoding='utf-8') as file:
                self.prompts_config = yaml.safe_load(file)
            logger.info("Configuração de prompts carregada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar prompts: {e}")
            self.prompts_config = {}

    def _load_document_types(self):
        """Carregar tipos de documentos suportados"""
        classification_config = self.prompts_config.get('classificacao', {})
        self.document_types = classification_config.get('tipos_documentos', [])
        self.type_descriptions = classification_config.get(
            'descricoes_tipos', {})

    def _initialize_llm_providers(self):
        """Inicializar provedores LLM com fallback inteligente"""

        # 1. OpenAI (padrão)
        if configuracoes.llm and configuracoes.llm.openai_api_key:
            try:
                # Criar provider OpenAI inline
                openai_provider = OpenAIProvider(
                    api_key=configuracoes.llm.openai_api_key.get_secret_value(),
                    modelo=configuracoes.llm.classification_model
                )
                self.llm_providers.append(openai_provider)
                logger.info(
                    f"Provedor OpenAI configurado: {configuracoes.llm.classification_model}")
            except Exception as e:
                logger.warning(f"Erro ao configurar OpenAI: {e}")

        # 2. Azure OpenAI (fallback)
        if (configuracoes.azure_openai_endpoint and
                configuracoes.azure_openai_key):
            try:
                azure_provider = AzureOpenAIProvider(
                    endpoint=configuracoes.azure_openai_endpoint,
                    api_key=configuracoes.azure_openai_key,
                    modelo=configuracoes.azure_openai_model
                )
                self.llm_providers.append(azure_provider)
                logger.info(
                    f"Provedor Azure OpenAI configurado: {configuracoes.azure_openai_model}")
            except Exception as e:
                logger.warning(f"Erro ao configurar Azure OpenAI: {e}")

        # 3. AWS Bedrock (Claude)
        if (configuracoes.aws_access_key_id and
                configuracoes.aws_secret_access_key):
            try:
                bedrock_provider = AWSBedrockProvider(
                    aws_access_key_id=configuracoes.aws_access_key_id,
                    aws_secret_access_key=configuracoes.aws_secret_access_key,
                    modelo=configuracoes.aws_bedrock_model,
                    region=configuracoes.aws_region
                )
                self.llm_providers.append(bedrock_provider)
                logger.info(
                    f"Provedor AWS Bedrock configurado: {configuracoes.aws_bedrock_model}")
            except Exception as e:
                logger.warning(f"Erro ao configurar AWS Bedrock: {e}")

        if not self.llm_providers:
            logger.warning(
                "Nenhum provedor LLM configurado - classificação limitada ao modo adaptativo")

    async def classify_document(
        self,
        document_text: str,
        use_adaptive: bool = True,
        confidence_threshold: float = 0.8,
        prefer_adaptive: bool = True
    ) -> ResultadoClassificacao:
        """
        Classificar documento usando estratégia adaptativa com múltiplos LLMs

        Args:
            document_text: Texto do documento
            use_adaptive: Se deve usar classificação adaptativa
            confidence_threshold: Limiar de confiança
            prefer_adaptive: Se deve preferir classificação adaptativa sobre LLM

        Returns:
            ResultadoClassificacao com tipo do documento e metadados
        """
        start_time = datetime.now()

        try:
            # Limpar e preparar texto
            cleaned_text = self._preprocess_text(document_text)

            # 1. Tentar classificação adaptativa primeiro (se habilitada)
            if use_adaptive and len(cleaned_text) > 50:
                adaptive_result = await self._adaptive_classification(cleaned_text)

                if adaptive_result and adaptive_result['confidence'] >= confidence_threshold:
                    duration = (datetime.now() - start_time).total_seconds()
                    logger.info(
                        f"Classificação adaptativa bem-sucedida: {adaptive_result['type']} ({adaptive_result['confidence']:.2f})")

                    return ResultadoClassificacao(
                        tipo_documento=adaptive_result['type'],
                        confianca=adaptive_result['confidence'],
                        metodo='adaptive',
                        provedor_llm='vector_store',
                        modelo_llm='similarity_search',
                        tempo_processamento=duration,
                        documentos_similares=adaptive_result.get(
                            'similar_docs', []),
                        metadados={
                            'type_votes': adaptive_result.get('type_votes', {}),
                            'avg_similarity': adaptive_result.get('avg_similarity', 0.0)
                        }
                    )

            # 2. Fallback para LLMs (tentando cada provedor)
            if self.llm_providers:
                for i, provider in enumerate(self.llm_providers):
                    try:
                        llm_result = await self._llm_classification(cleaned_text, provider)
                        duration = (datetime.now() -
                                    start_time).total_seconds()

                        return ResultadoClassificacao(
                            tipo_documento=llm_result['type'],
                            confianca=llm_result.get('confidence', 0.85),
                            metodo=f'llm_{"primary" if i == 0 else "fallback"}',
                            provedor_llm=provider.nome,
                            modelo_llm=provider.modelo or "unknown",
                            tempo_processamento=duration,
                            metadados={
                                'llm_response': llm_result.get('llm_response', ''),
                                'provider_index': i
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            f"Erro no provedor {provider.nome}: {e}")
                        continue

            # 3. Fallback final - classificação baseada em regras
            rule_result = self._rule_based_classification(cleaned_text)
            duration = (datetime.now() - start_time).total_seconds()

            return ResultadoClassificacao(
                tipo_documento=rule_result['type'],
                confianca=rule_result['confidence'],
                metodo='rule_based',
                provedor_llm='rules_engine',
                modelo_llm='keyword_matching',
                tempo_processamento=duration,
                metadados={'keywords_found': rule_result.get('keywords', [])}
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Erro na classificação: {e}")
            return ResultadoClassificacao(
                tipo_documento='Documento Não Classificado',
                confianca=0.0,
                metodo='error',
                provedor_llm='none',
                modelo_llm='none',
                tempo_processamento=duration,
                erro=str(e)
            )

    async def _adaptive_classification(self, document_text: str) -> Optional[Dict]:
        """Classificação adaptativa baseada em documentos similares"""
        try:
            # Buscar documentos similares no banco vetorial
            similar_docs = self.vector_service.get_similar_documents_for_classification(
                document_text,
                k=5  # Usar valor fixo por enquanto
            )

            if not similar_docs or len(similar_docs) < 3:
                return None

            # Analisar tipos dos documentos similares
            type_votes = {}
            confidence_scores = []

            for doc in similar_docs:
                doc_type = doc.metadata.get('document_type')
                similarity = doc.metadata.get('similarity', 0.0)
                confidence = doc.metadata.get('confidence_score', 0.8)

                if doc_type:
                    # Peso baseado na similaridade e confiança original
                    weight = similarity * confidence
                    type_votes[doc_type] = type_votes.get(doc_type, 0) + weight
                    confidence_scores.append(similarity)

            if not type_votes:
                return None

            # Determinar tipo mais provável
            predicted_type = max(
                type_votes.keys(), key=lambda k: type_votes[k])
            total_weight = sum(type_votes.values())
            confidence = type_votes[predicted_type] / total_weight

            # Ajustar confiança baseada na qualidade das similaridades
            avg_similarity = sum(confidence_scores) / len(confidence_scores)
            adjusted_confidence = min(confidence * avg_similarity, 0.95)

            return {
                'type': predicted_type,
                'confidence': adjusted_confidence,
                'similar_docs': [doc.dict() for doc in similar_docs],
                'type_votes': type_votes,
                'avg_similarity': avg_similarity
            }

        except Exception as e:
            logger.error(f"Erro na classificação adaptativa: {e}")
            return None

    async def _llm_classification(self, document_text: str, provider: ProvedorLLMBase) -> Dict:
        """Classificação usando LLM específico"""
        try:
            # Construir prompt de classificação
            prompt = self._build_classification_prompt(document_text)

            # Chamar LLM
            response = await provider.gerar_resposta(
                prompt=prompt,
                temperature=0.1,
                max_tokens=50
            )

            if not response.sucesso:
                raise Exception(
                    f"Erro no LLM {provider.nome}: {response.erro}")

            # Extrair tipo do documento da resposta
            predicted_type = self._extract_document_type(response.resposta)

            # Validar tipo
            if predicted_type not in self.document_types:
                logger.warning(
                    f"Tipo não reconhecido pelo {provider.nome}: {predicted_type}")
                predicted_type = "Documento Não Classificado"

            return {
                'type': predicted_type,
                'confidence': 0.85,  # Confiança padrão para LLM
                'llm_response': response.resposta,
                'tokens_used': response.tokens_input + response.tokens_output,
                'cost': response.custo
            }

        except Exception as e:
            logger.error(f"Erro na classificação LLM {provider.nome}: {e}")
            raise

    def _rule_based_classification(self, document_text: str) -> Dict:
        """Classificação baseada em regras e palavras-chave"""
        text_lower = document_text.lower()
        keywords_found = []

        # Mapeamento de palavras-chave para tipos
        keyword_mapping = {
            'Comprovante Bancário': ['banco', 'transferência', 'depósito', 'pix', 'ted', 'doc', 'agência', 'conta'],
            'CEI da Obra': ['cei', 'obra', 'construção', 'matrícula cei', 'inss'],
            'Inscrição Municipal': ['inscrição municipal', 'prefeitura', 'município'],
            'Termo de Responsabilidade': ['responsabilidade', 'termo', 'obrigação', 'compromisso'],
            'Alvará Municipal': ['alvará', 'licença', 'autorização municipal'],
            'Cartão CNPJ': ['cnpj', 'razão social', 'nome fantasia', 'cnae'],
            'Contrato Social': ['contrato social', 'sociedade', 'sócios', 'capital social'],
            'CNH': ['cnh', 'habilitação', 'carteira nacional', 'categoria'],
            'Fatura Telefônica': ['fatura', 'telefone', 'ligações', 'minutos'],
            'Nota Fiscal de Serviços Eletrônica': ['nfs-e', 'nota fiscal', 'serviços', 'iss']
        }

        type_scores = {}

        for doc_type, keywords in keyword_mapping.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
                    keywords_found.append(keyword)
            if score > 0:
                type_scores[doc_type] = score

        if type_scores:
            predicted_type = max(type_scores.keys(),
                                 key=lambda k: type_scores[k])
            confidence = min(
                type_scores[predicted_type] / len(keyword_mapping[predicted_type]), 0.7)
        else:
            predicted_type = "Documento Não Classificado"
            confidence = 0.0

        return {
            'type': predicted_type,
            'confidence': confidence,
            'keywords': keywords_found
        }

    def _build_classification_prompt(self, document_text: str) -> str:
        """Construir prompt de classificação"""
        base_prompt = self.prompts_config.get(
            'classificacao', {}).get('prompt_base', '')

        # Substituir placeholders
        prompt = base_prompt.format(
            tipos_documentos='\n'.join(
                [f"- {tipo}" for tipo in self.document_types]),
            descricoes_tipos='\n'.join([
                f"{tipo}: {desc}" for tipo, desc in self.type_descriptions.items()
            ]),
            texto_documento=document_text[:3000]  # Limitar tamanho
        )

        return prompt

    def _extract_document_type(self, llm_response: str) -> str:
        """Extrair tipo de documento da resposta do LLM"""
        # Limpar resposta
        response_clean = llm_response.strip().lower()

        # Mapear variações para tipos padrão
        type_mapping = {
            'comprovante bancário': 'Comprovante Bancário',
            'comprovante bancario': 'Comprovante Bancário',
            'cei da obra': 'CEI da Obra',
            'cei': 'CEI da Obra',
            'inscrição municipal': 'Inscrição Municipal',
            'inscricao municipal': 'Inscrição Municipal',
            'termo de responsabilidade': 'Termo de Responsabilidade',
            'alvará municipal': 'Alvará Municipal',
            'alvara municipal': 'Alvará Municipal',
            'cartão cnpj': 'Cartão CNPJ',
            'cartao cnpj': 'Cartão CNPJ',
            'contrato social': 'Contrato Social',
            'cnh': 'CNH',
            'fatura telefônica': 'Fatura Telefônica',
            'fatura telefonica': 'Fatura Telefônica',
            'nota fiscal de serviços eletrônica': 'Nota Fiscal de Serviços Eletrônica',
            'nfs-e': 'Nota Fiscal de Serviços Eletrônica'
        }

        # Buscar por tipos exatos primeiro
        for variation, standard_type in type_mapping.items():
            if variation in response_clean:
                return standard_type

        # Se não encontrar, retornar resposta original ou padrão
        for doc_type in self.document_types:
            if doc_type.lower() in response_clean:
                return doc_type

        return "Documento Não Classificado"

    def _preprocess_text(self, text: str) -> str:
        """Pré-processar texto para classificação"""
        # Remover caracteres especiais excessivos
        text = re.sub(r'[^\w\s\-\.\,\;\:\!\?\(\)\[\]\{\}]', ' ', text)

        # Normalizar espaços
        text = re.sub(r'\s+', ' ', text)

        # Remover linhas muito curtas (provavelmente ruído)
        lines = text.split('\n')
        filtered_lines = [line.strip()
                          for line in lines if len(line.strip()) > 3]

        return ' '.join(filtered_lines).strip()

    async def add_feedback(
        self,
        document_text: str,
        predicted_type: str,
        correct_type: str,
        confidence: float = 0.0,
        db_session=None
    ):
        """
        Adicionar feedback para aprendizado

        Args:
            document_text: Texto do documento
            predicted_type: Tipo predito pelo sistema
            correct_type: Tipo correto fornecido pelo usuário
            confidence: Confiança da predição original
            db_session: Sessão do banco de dados
        """
        try:
            # Salvar feedback no banco
            feedback = FeedbackClassificacao(
                documento_id=None,  # Será preenchido se necessário
                texto_documento=document_text[:1000],  # Limitar tamanho
                tipo_predito=predicted_type,
                tipo_correto=correct_type,
                confianca_original=confidence,
                timestamp=datetime.now()
            )

            if db_session:
                db_session.add(feedback)
                db_session.commit()
                logger.info(
                    f"Feedback salvo: {predicted_type} -> {correct_type}")

            # Atualizar banco vetorial se necessário
            if predicted_type != correct_type:
                # Buscar documento no vetorial e atualizar
                self.vector_service.update_with_feedback(
                    vector_id="",  # Será buscado internamente
                    correct_type=correct_type,
                    correct_data={},  # Dados vazios para classificação
                    db_session=db_session
                )

        except Exception as e:
            logger.error(f"Erro ao adicionar feedback: {e}")

    def get_supported_types(self) -> List[str]:
        """Retorna tipos de documentos suportados"""
        return self.document_types.copy()

    def get_type_description(self, document_type: str) -> str:
        """Retorna descrição de um tipo de documento"""
        return self.type_descriptions.get(document_type, "Descrição não disponível")

    def get_llm_providers_info(self) -> List[Dict[str, Any]]:
        """Retorna informações sobre os provedores LLM configurados"""
        return [
            {
                'nome': provider.nome,
                'modelo': provider.modelo,
                'configurado': provider.validar_configuracao()
            }
            for provider in self.llm_providers
        ]


class OpenAIProvider(ProvedorLLMBase):
    """Provider OpenAI para LLM"""

    def __init__(self, api_key: str, modelo: str = "gpt-4o-mini"):
        super().__init__("openai", api_key, modelo)
        self.client = None
        self._inicializar_cliente()

    def _inicializar_cliente(self):
        """Inicializa o cliente OpenAI"""
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            self.logger.info("Cliente OpenAI inicializado")
        except ImportError:
            self.logger.error(
                "openai não está instalado. Execute: pip install openai")
            self.client = None
        except Exception as e:
            self.logger.error(f"Erro ao inicializar cliente OpenAI: {e}")
            self.client = None

    def validar_configuracao(self) -> bool:
        """Valida se o provedor está configurado corretamente"""
        return bool(self.api_key) and self.client is not None

    async def gerar_resposta(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> ResultadoLLM:
        """Gera resposta usando OpenAI"""
        import time

        inicio = time.time()

        try:
            if not self.validar_configuracao() or self.client is None:
                raise ValueError(
                    "Provider OpenAI não está configurado corretamente")

            model_name = self.modelo or "gpt-4o-mini"
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens or 100
            )

            tempo_resposta = time.time() - inicio

            # Calcular tokens (aproximação)
            tokens_input = len(prompt.split()) * 1.3  # Aproximação
            response_content = response.choices[0].message.content or ""
            tokens_output = len(response_content.split()) * 1.3

            return ResultadoLLM(
                resposta=response_content,
                tokens_input=int(tokens_input),
                tokens_output=int(tokens_output),
                custo=await self.calcular_custo(int(tokens_input), int(tokens_output)),
                tempo_resposta=tempo_resposta,
                provedor=self.nome,
                modelo=model_name,
                sucesso=True
            )

        except Exception as e:
            tempo_resposta = time.time() - inicio
            self.logger.error(f"Erro OpenAI: {e}")
            return ResultadoLLM(
                resposta="",
                tokens_input=0,
                tokens_output=0,
                custo=0.0,
                tempo_resposta=tempo_resposta,
                provedor=self.nome,
                modelo=self.modelo or "gpt-4o-mini",
                sucesso=False,
                erro=str(e)
            )

    async def calcular_custo(
        self,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """Calcula custo da operação OpenAI"""
        # Preços por 1K tokens (aproximados)
        precos = {
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
        }

        modelo_preco = precos.get(
            self.modelo or "gpt-4o-mini", precos["gpt-4o-mini"])
        custo_input = (tokens_input / 1000) * modelo_preco["input"]
        custo_output = (tokens_output / 1000) * modelo_preco["output"]

        return custo_input + custo_output
