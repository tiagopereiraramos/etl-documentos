"""Refactored service to use prompts from a YAML file for easier management and extensibility."""
import hashlib
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.documents import Document
from sqlalchemy.orm import Session
import yaml

from app.providers.base import ProvedorExtracaoBase, ResultadoExtracao
from app.models.schemas import MetricasExtracao
from app.core.logging import obter_logger
from app.core.exceptions import ExtracaoException
from app.core.config import settings
from app.providers.docling_provider import DoclingProvider
try:
    from app.providers.azure_provider import AzureDocumentIntelligenceProvider
except ImportError:
    AzureDocumentIntelligenceProvider = None
from app.services.vector_service import VectorStoreService
from app.services.cost_service import CostTrackingService

logger = obter_logger(__name__)


@dataclass
class ResultadoExtracaoCompleto:
    """Resultado completo da extração de texto"""
    texto: str
    provedor_usado: str
    qualidade: float
    tempo_total: float
    metadados: Dict[str, Any]
    hash_arquivo: str


@dataclass
class ResultadoClassificacao:
    """Resultado da classificação de documento"""
    tipo_documento: str
    confianca: float
    metadados: Dict[str, Any]


@dataclass
class ResultadoExtracaoDados:
    """Resultado da extração de dados estruturados"""
    dados_extraidos: Dict[str, Any]
    confianca: float
    metadados: Dict[str, Any]


@dataclass
class ResultadoProcessamentoCompleto:
    """Resultado completo de todo o processamento"""
    documento_id: str
    hash_arquivo: str
    texto_extraido: str
    classificacao: ResultadoClassificacao
    dados_estruturados: ResultadoExtracaoDados
    tempo_total: float
    custos_totais: Dict[str, Any]
    metadados_completos: Dict[str, Any]


class ServicoExtracaoUnificado:
    """
    Serviço unificado que gerencia todo o pipeline de processamento:
    1. Extração de texto dos documentos
    2. Classificação adaptativa com aprendizado
    3. Extração de dados estruturados
    """

    def __init__(self, vector_service: VectorStoreService, cost_service: CostTrackingService):
        """
        Inicializa o serviço unificado

        Args:
            vector_service: Serviço de banco vetorial
            cost_service: Serviço de rastreamento de custos
        """
        self.vector_service = vector_service
        self.cost_service = cost_service

        # Log explícito da chave OpenAI usada
        try:
            openai_key = settings.llm.openai_api_key.get_secret_value()
        except Exception as e:
            openai_key = f"(erro ao obter chave: {e})"
        logger.info(f"[ETL] Chave OpenAI para classificação: {openai_key}")
        logger.info(f"[ETL] Chave OpenAI para extração: {openai_key}")

        # Provedores de extração de texto
        self.provedores: List[ProvedorExtracaoBase] = []
        self._inicializar_provedores()

        # LLMs para classificação e extração
        self.llm_classificacao = ChatOpenAI(
            model=settings.llm.classification_model,
            api_key=openai_key,
            temperature=0
        )

        self.llm_extracao = ChatOpenAI(
            model=settings.llm.extraction_model,
            api_key=openai_key,
            temperature=0
        )

        # Parsers
        self.str_parser = StrOutputParser()
        self.json_parser = JsonOutputParser()

        # Schemas de extração
        self.extraction_schemas = self._load_extraction_schemas()

        # Criar prompts
        self._create_prompts()

        logger.info("Serviço de extração unificado inicializado")

    def _inicializar_provedores(self):
        """Inicializa os provedores de extração de texto"""
        # Docling é sempre o primeiro (padrão)
        self.provedores.append(DoclingProvider())

        # Azure como fallback se configurado
        if settings.azure_endpoint and settings.azure_key:
            if AzureDocumentIntelligenceProvider:
                self.provedores.append(AzureDocumentIntelligenceProvider(
                    endpoint=settings.azure_endpoint,
                    api_key=settings.azure_key
                ))
                logger.info("Provedor Azure configurado como fallback")

        logger.info(
            f"Provedores inicializados: {[p.nome for p in self.provedores]}")

    def _load_extraction_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Carrega schemas de extração para cada tipo de documento"""
        return {
            "CNH": {
                "nome_completo": "string - Nome completo do portador",
                "numero_registro": "string - Número do registro da CNH",
                "cpf": "string - CPF do portador",
                "data_nascimento": "string - Data de nascimento (DD/MM/AAAA)",
                "categoria": "string - Categoria da habilitação (A, B, C, D, E)",
                "data_primeira_habilitacao": "string - Data da primeira habilitação",
                "data_validade": "string - Data de validade da CNH",
                "orgao_expedidor": "string - Órgão que expediu a CNH",
                "numero_espelho": "string - Número do espelho/segurança"
            },
            "Comprovante Bancário": {
                "banco": "string - Nome do banco",
                "agencia": "string - Número da agência",
                "conta": "string - Número da conta",
                "tipo_operacao": "string - Tipo da operação (transferência, depósito, etc.)",
                "valor": "string - Valor da operação",
                "data_operacao": "string - Data da operação",
                "codigo_autenticacao": "string - Código de autenticação",
                "favorecido": "string - Nome do favorecido/destinatário",
                "documento_favorecido": "string - CPF/CNPJ do favorecido"
            },
            "Cartão CNPJ": {
                "cnpj": "string - Número do CNPJ",
                "razao_social": "string - Razão social da empresa",
                "nome_fantasia": "string - Nome fantasia",
                "data_abertura": "string - Data de abertura da empresa",
                "cnae_principal": "string - Código CNAE principal",
                "natureza_juridica": "string - Natureza jurídica",
                "endereco_completo": "string - Endereço completo",
                "situacao_cadastral": "string - Situação cadastral atual",
                "data_situacao": "string - Data da situação cadastral"
            },
            "CEI da Obra": {
                "numero_cei": "string - Número da matrícula CEI",
                "endereco_obra": "string - Endereço completo da obra",
                "proprietario_nome": "string - Nome do proprietário",
                "proprietario_documento": "string - CPF/CNPJ do proprietário",
                "responsavel_tecnico": "string - Nome do responsável técnico",
                "numero_art": "string - Número da ART",
                "data_inicio": "string - Data de início da obra",
                "tipo_obra": "string - Tipo da obra"
            },
            "Inscrição Municipal": {
                "numero_inscricao": "string - Número da inscrição municipal",
                "razao_social": "string - Razão social",
                "nome_fantasia": "string - Nome fantasia",
                "cnpj": "string - CNPJ da empresa",
                "endereco": "string - Endereço do estabelecimento",
                "atividade_principal": "string - Atividade econômica principal",
                "data_inscricao": "string - Data da inscrição",
                "situacao": "string - Situação da inscrição"
            },
            "Termo de Responsabilidade": {
                "responsavel_nome": "string - Nome do responsável",
                "responsavel_documento": "string - CPF/CNPJ do responsável",
                "objeto_responsabilidade": "string - Objeto da responsabilidade",
                "descricao_obrigacoes": "string - Descrição das obrigações",
                "prazo_validade": "string - Prazo de validade",
                "data_assinatura": "string - Data da assinatura",
                "testemunhas": "array - Nomes das testemunhas"
            },
            "Alvará Municipal": {
                "numero_alvara": "string - Número do alvará",
                "razao_social": "string - Razão social da empresa",
                "cnpj": "string - CNPJ",
                "endereco": "string - Endereço do estabelecimento",
                "atividades_permitidas": "array - Lista de atividades permitidas",
                "data_emissao": "string - Data de emissão",
                "data_validade": "string - Data de validade",
                "orgao_emissor": "string - Órgão emissor"
            },
            "Contrato Social": {
                "razao_social": "string - Razão social da empresa",
                "nome_fantasia": "string - Nome fantasia",
                "cnpj": "string - CNPJ (se for alteração)",
                "objeto_social": "string - Objeto social",
                "capital_social": "string - Valor do capital social",
                "endereco_sede": "string - Endereço da sede",
                "socios": "array - Lista de sócios com participação",
                "administradores": "array - Lista de administradores",
                "data_constituicao": "string - Data de constituição"
            },
            "Fatura Telefônica": {
                "operadora": "string - Nome da operadora",
                "numero_linha": "string - Número da linha",
                "periodo_referencia": "string - Período de referência",
                "valor_total": "string - Valor total da fatura",
                "data_vencimento": "string - Data de vencimento",
                "consumo_dados": "string - Consumo de dados",
                "chamadas_locais": "string - Quantidade/valor de chamadas locais",
                "servicos_adicionais": "array - Serviços adicionais cobrados"
            },
            "Nota Fiscal de Serviços Eletrônica": {
                "numero_nota": "string - Número da nota fiscal",
                "prestador_nome": "string - Nome do prestador",
                "prestador_cnpj": "string - CNPJ do prestador",
                "tomador_nome": "string - Nome do tomador",
                "tomador_documento": "string - CPF/CNPJ do tomador",
                "descricao_servicos": "string - Descrição dos serviços",
                "valor_servicos": "string - Valor dos serviços",
                "iss": "string - Valor do ISS",
                "valor_total": "string - Valor total da nota",
                "data_emissao": "string - Data de emissão"
            }
        }

    def _get_prompt_for_document_type(self, tipo_documento: str) -> Optional[str]:
        """Carrega prompt específico do YAML para o tipo de documento"""
        try:
            import yaml
            import os

            prompts_file = os.path.join(os.path.dirname(
                __file__), '../../config/prompts.yaml')

            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts_data = yaml.safe_load(f)

            # Normalizar nome do tipo para garantir correspondência
            def normaliza(s):
                return s.strip().lower()

            tipos_yaml = prompts_data.get('extracao', {}).get('tipos', {})
            tipos_disponiveis = list(tipos_yaml.keys())
            tipo_normalizado = normaliza(tipo_documento)
            for tipo_yaml in tipos_disponiveis:
                if normaliza(tipo_yaml) == tipo_normalizado:
                    return tipos_yaml[tipo_yaml].get('prompt')

            logger.warning(
                f"Prompt não encontrado para tipo: {tipo_documento}. Tipos disponíveis: {tipos_disponiveis}")
            return None

        except Exception as e:
            logger.error(f"Erro ao carregar prompt do YAML: {e}")
            return None

    def _create_prompts(self):
        """Criar prompts - LLMs já foram inicializados no __init__"""
        # Os LLMs já foram criados no __init__ com a chave correta
        # Não precisamos recriar aqui para evitar problemas de chave
        logger.info("Prompts configurados - LLMs já inicializados no __init__")

    def _calcular_hash_arquivo(self, conteudo: bytes) -> str:
        """Calcula hash SHA-256 do arquivo"""
        return hashlib.sha256(conteudo).hexdigest()

    def _provedor_suporta_formato(self, provedor: ProvedorExtracaoBase, extensao: str) -> bool:
        """Verifica se provedor suporta o formato"""
        return extensao.lower() in [fmt.lower() for fmt in provedor.suporta_formatos]

    async def processar_documento_completo(
        self,
        conteudo_arquivo: bytes,
        extensao: str,
        nome_arquivo: str = None,
        db_session: Optional[Session] = None
    ) -> ResultadoProcessamentoCompleto:
        """
        Processa documento completo: extração, classificação e extração de dados

        Args:
            conteudo_arquivo: Conteúdo binário do arquivo
            extensao: Extensão do arquivo
            nome_arquivo: Nome do arquivo
            db_session: Sessão do banco de dados

        Returns:
            Resultado completo do processamento
        """
        document_id = str(uuid.uuid4())
        inicio_processamento = time.time()

        logger.info(
            f"Iniciando processamento completo do documento {document_id}")

        try:
            # 1. Extração de texto
            resultado_texto = await self.extrair_texto(
                conteudo_arquivo, extensao, nome_arquivo
            )
            logger.info(
                f"Texto extraído com qualidade {resultado_texto.qualidade:.2f}")

            # 2. Classificação do documento
            resultado_classificacao = await self.classificar_documento(
                resultado_texto.texto, document_id, db_session
            )
            logger.info(
                f"Documento classificado como '{resultado_classificacao.tipo_documento}' com confiança {resultado_classificacao.confianca:.2f}")

            # 3. Extração de dados estruturados
            resultado_dados = await self.extrair_dados_estruturados(
                resultado_texto.texto,
                resultado_classificacao.tipo_documento,
                document_id,
                db_session
            )
            logger.info(
                f"Dados estruturados extraídos: {len(resultado_dados.dados_extraidos)} campos")

            # 4. Salvar no banco vetorial para aprendizado futuro
            await self._salvar_no_banco_vetorial(
                resultado_texto.texto,
                resultado_classificacao.tipo_documento,
                resultado_dados.dados_extraidos,
                resultado_classificacao.confianca,
                db_session
            )

            # 5. Calcular custos totais
            custos_totais = self._calcular_custos_totais([
                resultado_classificacao.metadados,
                resultado_dados.metadados
            ])

            tempo_total = time.time() - inicio_processamento

            # 6. Montar resultado completo
            resultado_completo = ResultadoProcessamentoCompleto(
                documento_id=document_id,
                hash_arquivo=resultado_texto.hash_arquivo,
                texto_extraido=resultado_texto.texto,
                classificacao=resultado_classificacao,
                dados_estruturados=resultado_dados,
                tempo_total=tempo_total,
                custos_totais=custos_totais,
                metadados_completos={
                    "extracao_texto": resultado_texto.metadados,
                    "classificacao": resultado_classificacao.metadados,
                    "extracao_dados": resultado_dados.metadados,
                    "arquivo_original": {
                        "nome": nome_arquivo,
                        "extensao": extensao,
                        "tamanho_bytes": len(conteudo_arquivo),
                        "hash": resultado_texto.hash_arquivo
                    }
                }
            )

            logger.info(
                f"Processamento completo finalizado em {tempo_total:.2f}s")
            return resultado_completo

        except Exception as e:
            tempo_total = time.time() - inicio_processamento
            error_msg = f"Erro no processamento completo: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ExtracaoException(
                error_msg,
                details={
                    "document_id": document_id,
                    "processing_time": tempo_total,
                    "stage": "processamento_completo"
                },
                error_code="PROCESSAMENTO_COMPLETO_FALHOU"
            )

    async def extrair_texto(
        self,
        conteudo_arquivo: bytes,
        extensao: str,
        nome_arquivo: str = None
    ) -> ResultadoExtracaoCompleto:
        """
        Extrai texto do documento usando estratégia de fallback
        """
        hash_arquivo = self._calcular_hash_arquivo(conteudo_arquivo)
        logger.info(
            f"Iniciando extração para arquivo {nome_arquivo or 'desconhecido'} "
            f"({extensao}, {len(conteudo_arquivo)} bytes, hash: {hash_arquivo[:8]}...)"
        )

        melhor_resultado: Optional[ResultadoExtracao] = None
        provedores_usados = []

        for provedor in self.provedores:
            if not self._provedor_suporta_formato(provedor, extensao):
                logger.debug(
                    f"Provedor {provedor.nome} não suporta formato {extensao}")
                continue

            try:
                logger.info(f"Tentando extração com {provedor.nome}")
                resultado = await provedor.extrair_texto(
                    conteudo_arquivo, extensao, nome_arquivo
                )

                provedores_usados.append({
                    "provedor": provedor.nome,
                    "sucesso": resultado.sucesso,
                    "qualidade": resultado.metricas.qualidade_score,
                    "caracteres": resultado.metricas.caracteres_extraidos,
                    "tempo": resultado.metricas.tempo_processamento
                })

                if resultado.sucesso:
                    # Se é o primeiro resultado ou é melhor que o anterior
                    if (melhor_resultado is None or
                            resultado.metricas.qualidade_score > melhor_resultado.metricas.qualidade_score):
                        melhor_resultado = resultado

                    # Se qualidade é boa o suficiente, usar este resultado
                    if resultado.metricas.qualidade_score >= settings.quality.qualidade_minima_extracao:
                        logger.info(
                            f"Qualidade suficiente alcançada com {provedor.nome}: "
                            f"{resultado.metricas.qualidade_score:.2f}"
                        )
                        break
                else:
                    logger.warning(
                        f"Falha na extração com {provedor.nome}: {resultado.erro}")

            except Exception as e:
                logger.error(
                    f"Erro inesperado com provedor {provedor.nome}: {e}")
                provedores_usados.append({
                    "provedor": provedor.nome,
                    "sucesso": False,
                    "erro": str(e)
                })

        if melhor_resultado is None or not melhor_resultado.sucesso:
            raise ExtracaoException(
                "Nenhum provedor conseguiu extrair texto do documento",
                details={
                    "extensao": extensao,
                    "tamanho_bytes": len(conteudo_arquivo),
                    "provedores_tentados": provedores_usados
                },
                error_code="EXTRACAO_FALHOU"
            )

        return ResultadoExtracaoCompleto(
            texto=melhor_resultado.texto,
            provedor_usado=melhor_resultado.metricas.metodo_extracao,
            qualidade=melhor_resultado.metricas.qualidade_score,
            tempo_total=sum(p.get("tempo", 0)
                            for p in provedores_usados if p.get("tempo")),
            metadados={
                "provedores_usados": provedores_usados,
                "metadata_extracao": melhor_resultado.metadata or {},
                "metricas": melhor_resultado.metricas.dict()
            },
            hash_arquivo=hash_arquivo
        )

    async def classificar_documento(
        self,
        texto_documento: str,
        document_id: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> ResultadoClassificacao:
        """
        Classifica documento usando aprendizado adaptativo
        """
        import os
        logger.info(
            f"[DEBUG][classificar_documento] id(settings): {id(settings)}")
        logger.info(
            f"[DEBUG][classificar_documento] settings.llm.openai_api_key: {getattr(settings.llm.openai_api_key, 'get_secret_value', lambda: 'N/A')()}")
        logger.info(
            f"[DEBUG][classificar_documento] os.environ['OPENAI_API_KEY']: {os.environ.get('OPENAI_API_KEY', 'N/A')}")
        logger.info(f"[DEBUG][classificar_documento] CWD: {os.getcwd()}")

        call_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        try:
            logger.info(
                f"Iniciando classificação adaptativa - Call ID: {call_id}")

            # Estratégia para documentos extensos
            if len(texto_documento) > 5000:
                text_length = len(texto_documento)
                start_text = texto_documento[:800]
                middle_text = texto_documento[text_length //
                                              2-400:text_length//2+400]
                end_text = texto_documento[-800:]
                truncated_text = f"{start_text}\n...\n{middle_text}\n...\n{end_text}"
                logger.info(
                    "Documento extenso: usando estratégia de amostragem")
            else:
                truncated_text = texto_documento[:2000]

            # Buscar documentos similares
            similar_docs = self.vector_service.get_similar_documents_for_classification(
                truncated_text, k=3
            )

            # Escolher abordagem
            if similar_docs and len(similar_docs) > 0:
                logger.info(
                    f"Usando classificação adaptativa com {len(similar_docs)} exemplos")
                examples = self._format_classification_examples(similar_docs)

                classification_result = self.classification_adaptive_chain.invoke({
                    "document_text": truncated_text,
                    "examples": examples
                })

                confianca = self._calculate_adaptive_confidence(similar_docs)
            else:
                logger.info("Usando classificação base (sem exemplos)")
                classification_result = self.classification_base_chain.invoke({
                    "document_text": truncated_text
                })
                confianca = 0.7

            # Processar resultado
            tipo_documento = classification_result.strip()
            tipo_documento = self._validate_and_fix_type(tipo_documento)

            # Calcular métricas
            elapsed_time = time.time() - start_time
            estimated_input_tokens = len(truncated_text) // 4
            estimated_output_tokens = len(classification_result) // 4

            # Rastrear custos
            if self.cost_service:
                self.cost_service.record_llm_usage(
                    call_id=call_id,
                    model=settings.llm.classification_model,
                    operation="classification",
                    input_tokens=estimated_input_tokens,
                    output_tokens=estimated_output_tokens,
                    success=True,
                    processing_time=elapsed_time,
                    document_id=document_id,
                    db_session=db_session
                )

            metadados = {
                "call_id": call_id,
                "model_used": settings.llm.classification_model,
                "processing_time": elapsed_time,
                "examples_used": len(similar_docs) if similar_docs else 0,
                "approach": "adaptive" if similar_docs else "base",
                "input_tokens": estimated_input_tokens,
                "output_tokens": estimated_output_tokens
            }

            logger.info(
                f"Documento classificado como '{tipo_documento}' com confiança {confianca:.3f}")

            return ResultadoClassificacao(
                tipo_documento=tipo_documento,
                confianca=confianca,
                metadados=metadados
            )

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Erro na classificação: {str(e)}"
            logger.error(error_msg, exc_info=True)

            if self.cost_service:
                self.cost_service.record_llm_usage(
                    call_id=call_id,
                    model=settings.llm.classification_model,
                    operation="classification",
                    input_tokens=0,
                    output_tokens=0,
                    success=False,
                    processing_time=elapsed_time,
                    error=error_msg,
                    document_id=document_id,
                    db_session=db_session
                )

            raise RuntimeError(f"Falha na classificação: {str(e)}")

    async def extrair_dados_estruturados(
        self,
        texto_documento: str,
        tipo_documento: str,
        document_id: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> ResultadoExtracaoDados:
        """
        Extrai dados estruturados usando aprendizado adaptativo
        """
        import os
        logger.info(
            f"[DEBUG][extrair_dados_estruturados] id(settings): {id(settings)}")
        logger.info(
            f"[DEBUG][extrair_dados_estruturados] settings.llm.openai_api_key: {getattr(settings.llm.openai_api_key, 'get_secret_value', lambda: 'N/A')()}")
        logger.info(
            f"[DEBUG][extrair_dados_estruturados] os.environ['OPENAI_API_KEY']: {os.environ.get('OPENAI_API_KEY', 'N/A')}")
        logger.info(f"[DEBUG][extrair_dados_estruturados] CWD: {os.getcwd()}")

        from datetime import datetime
        call_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        try:
            logger.info(
                f"Iniciando extração adaptativa para {tipo_documento} - Call ID: {call_id}")

            # Verificar schema
            if tipo_documento not in self.extraction_schemas:
                raise ValueError(
                    f"Schema não encontrado para tipo: {tipo_documento}")

            schema = self.extraction_schemas[tipo_documento]
            schema_text = self._format_schema(schema)

            # Estratégia para documentos extensos
            if len(texto_documento) > 8000:
                # Para documentos muito extensos, usar chunking inteligente
                from app.services.document_chunking_service import IntelligentChunkingService

                chunking_service = IntelligentChunkingService(
                    max_chunk_size=3000)
                chunks = chunking_service.chunk_document(
                    texto_documento, tipo_documento)

                logger.info(
                    f"Processando documento extenso em {len(chunks)} chunks")

                # Processar cada chunk
                chunk_results = []
                for chunk in chunks:
                    chunk_data = await self._extract_from_chunk(chunk, tipo_documento, schema_text)
                    chunk_results.append((chunk, chunk_data))

                # Consolidar resultados
                dados_extraidos = self._consolidate_chunk_results(
                    chunk_results, schema)
                confianca = self._calculate_chunked_confidence(chunk_results)

                elapsed_time = time.time() - start_time

                metadados = {
                    "call_id": call_id,
                    "model_used": settings.llm.extraction_model,
                    "processing_time": elapsed_time,
                    "approach": "chunked",
                    "total_chunks": len(chunks),
                    "fields_extracted": len(dados_extraidos)
                }

                return ResultadoExtracaoDados(
                    dados_extraidos=dados_extraidos,
                    confianca=confianca,
                    metadados=metadados
                )
            else:
                # Truncar normalmente
                truncated_text = texto_documento[:3000]

            # Buscar exemplos similares
            similar_docs = self.vector_service.get_similar_documents_for_extraction(
                truncated_text, tipo_documento, k=3
            )

            # Usar APENAS prompt específico do YAML
                logger.info(
                f"🎯 Usando prompt ESPECÍFICO do YAML para {tipo_documento}")

            # Carregar prompt específico do YAML
            prompt_especifico = self._get_prompt_for_document_type(
                tipo_documento)

            if not prompt_especifico:
                raise ValueError(
                    f"Prompt específico não encontrado para tipo: {tipo_documento}")

            if not self.llm_extracao:
                raise ValueError("LLM de extração não inicializado")

            # Substituir placeholder pelo texto do documento
            prompt_formatado = prompt_especifico.replace(
                "DOCUMENT_TEXT_PLACEHOLDER", truncated_text)

            # Usar LLM diretamente com o prompt específico
            from langchain_core.messages import HumanMessage
            response = await self.llm_extracao.ainvoke([HumanMessage(content=prompt_formatado)])

            # Capturar a resposta completa da LLM
            resposta_completa_llm = response.content
            logger.info(
                f"🎯 Resposta completa da LLM capturada: {len(resposta_completa_llm)} caracteres")

            # Fazer parse do JSON para validação
            try:
                dados_extraidos_parsed = json.loads(resposta_completa_llm)
                # Se o parse foi bem-sucedido, usar a resposta completa como dados extraídos
                dados_extraidos = dados_extraidos_parsed
                confianca = 0.85  # Alta confiança para prompts específicos do YAML
                status_extracao = "extraido_com_sucesso"
            except json.JSONDecodeError:
                # Se não conseguir fazer parse, ainda assim retornar a resposta completa
                dados_extraidos = {
                    "resposta_completa_llm": resposta_completa_llm,
                    "tipo_documento": tipo_documento,
                    "texto_analisado": len(truncated_text),
                    "timestamp_extracao": datetime.utcnow().isoformat(),
                    "status": "resposta_nao_json_mas_completa"
                }
                confianca = 0.7
                status_extracao = "resposta_completa_capturada"

            logger.info(
                f"✅ Extração QUALIFICADA bem-sucedida: {len(str(dados_extraidos))} caracteres de resposta")
            logger.debug(f"Dados extraídos: {dados_extraidos}")

            # Calcular métricas
            elapsed_time = time.time() - start_time
            estimated_input_tokens = len(truncated_text + schema_text) // 4
            estimated_output_tokens = len(resposta_completa_llm) // 4

            # Rastrear custos
            if self.cost_service:
                self.cost_service.record_llm_usage(
                    call_id=call_id,
                    model=settings.llm.extraction_model,
                    operation="extraction",
                    input_tokens=estimated_input_tokens,
                    output_tokens=estimated_output_tokens,
                    success=True,
                    processing_time=elapsed_time,
                    document_id=document_id,
                    db_session=db_session
                )

            metadados = {
                "call_id": call_id,
                "model_used": settings.llm.extraction_model,
                "processing_time": elapsed_time,
                "examples_used": len(similar_docs) if similar_docs else 0,
                "approach": "adaptive" if similar_docs else "base",
                "fields_extracted": len(dados_extraidos),
                "input_tokens": estimated_input_tokens,
                "output_tokens": estimated_output_tokens
            }

            logger.info(
                f"Dados estruturados extraídos: {len(dados_extraidos)} campos")

            return ResultadoExtracaoDados(
                dados_extraidos=dados_extraidos,
                confianca=confianca,
                metadados=metadados
            )

        except json.JSONDecodeError as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Erro ao fazer parse do JSON da resposta: {e}"
            logger.error(error_msg)
            logger.debug(
                f"Resposta da LLM: {response.content if 'response' in locals() else 'N/A'}")

            # Retornar dados básicos como fallback
            from datetime import datetime
            dados_basicos = {
                "tipo_documento": tipo_documento,
                "texto_analisado": len(truncated_text),
                "timestamp_extracao": datetime.utcnow().isoformat(),
                "status": "erro_parse_json",
                "erro_detalhado": str(e)
            }

            return ResultadoExtracaoDados(
                dados_extraidos=dados_basicos,
                confianca=0.2,
                metadados={
                    "call_id": call_id,
                    "processing_time": elapsed_time,
                    "erro": error_msg,
                    "approach": "fallback_basico"
                }
            )

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Erro na extração qualificada: {str(e)}"
            logger.error(error_msg)

            # Retornar dados básicos como fallback
            from datetime import datetime
            dados_basicos = {
                "tipo_documento": tipo_documento,
                "texto_analisado": len(texto_documento),
                "timestamp_extracao": datetime.utcnow().isoformat(),
                "status": "extraido_com_fallback",
                "erro_extracao_completa": str(e)
            }

            return ResultadoExtracaoDados(
                dados_extraidos=dados_basicos,
                confianca=0.3,
                metadados={
                    "call_id": call_id,
                    "processing_time": elapsed_time,
                    "erro": error_msg,
                    "approach": "fallback_basico"
                }
            )

    def _format_schema(self, schema: Dict[str, str]) -> str:
        """Formata schema para o prompt"""
        return "\n".join([f"- {field}: {desc}" for field, desc in schema.items()])

    def _format_classification_examples(self, similar_docs: list) -> str:
        """Formata exemplos para classificação"""
        examples = []
        for doc in similar_docs:
            examples.append(
                f"Texto: {doc['text'][:200]}...\nTipo: {doc['document_type']}")
        return "\n\n".join(examples)

    def _format_extraction_examples(self, similar_docs: list) -> str:
        """Formata exemplos para extração"""
        examples = []
        for doc in similar_docs:
            examples.append(
                f"Documento: {doc['text'][:200]}...\nDados: {doc['extracted_data']}")
        return "\n\n".join(examples)

    def _validate_and_fix_type(self, tipo_documento: str) -> str:
        """Valida e corrige tipo de documento"""
        tipos_validos = settings.DOCUMENT_TYPES
        if tipo_documento in tipos_validos:
            return tipo_documento

        # Tentar encontrar tipo similar
        for tipo in tipos_validos:
            if tipo.lower() in tipo_documento.lower():
                return tipo

        return "Documento Não Classificado"

    def _validate_extracted_data(self, dados: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
        """Valida dados extraídos"""
        if not isinstance(dados, dict):
            return {}

        # Filtrar apenas campos válidos do schema
        dados_validos = {}
        for campo, valor in dados.items():
            if campo in schema and valor is not None:
                dados_validos[campo] = valor

        return dados_validos

    def _calculate_adaptive_confidence(self, similar_docs: list) -> float:
        """Calcula confiança adaptativa"""
        if not similar_docs:
            return 0.7

        # Baseado na similaridade dos documentos encontrados
        avg_similarity = sum(doc.get('similarity', 0.8)
                             for doc in similar_docs) / len(similar_docs)
        return min(0.95, avg_similarity + 0.1)

    def _calculate_extraction_confidence(self, similar_docs: list, dados_extraidos: Dict) -> float:
        """Calcula confiança da extração"""
        base_confidence = 0.6

        if similar_docs:
            base_confidence += 0.2

        if dados_extraidos and len(dados_extraidos) > 0:
            base_confidence += 0.1

        return min(0.95, base_confidence)

    def _calcular_custos_totais(self, metadados_list: list) -> Dict[str, Any]:
        """Calcula custos totais"""
        custos = {"total_input_tokens": 0, "total_output_tokens": 0}

        for metadata in metadados_list:
            custos["total_input_tokens"] += metadata.get("input_tokens", 0)
            custos["total_output_tokens"] += metadata.get("output_tokens", 0)

        return custos

    async def _salvar_no_banco_vetorial(
        self, texto: str, tipo_documento: str, dados_extraidos: Dict,
        confianca: float, db_session: Optional[Session]
    ):
        """Salva documento no banco vetorial"""
        try:
            if self.vector_service:
                await self.vector_service.add_document(
                    text=texto,
                    document_type=tipo_documento,
                    extracted_data=dados_extraidos,
                    metadata={
                        "confidence": confianca,
                        "timestamp": time.time()
                    }
                )
        except Exception as e:
            logger.warning(f"Erro ao salvar no banco vetorial: {e}")

    async def _extract_from_chunk(self, chunk: str, document_type: str, schema_text: str) -> Dict:
        """Extrai dados de um chunk específico"""
        try:
            result = self.extraction_base_chain.invoke({
                "document_type": document_type,
                "schema": schema_text,
                "document_text": chunk
            })
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error(f"Erro ao extrair de chunk: {e}")
            return {}

    def _consolidate_chunk_results(self, chunk_results: list, schema: Dict) -> Dict:
        """Consolida resultados de múltiplos chunks"""
        consolidated = {}

        for chunk, data in chunk_results:
            for field, value in data.items():
                if field in schema and value:
                    if field not in consolidated:
                        consolidated[field] = value
                    elif len(str(value)) > len(str(consolidated[field])):
                        # Manter o valor mais detalhado
                        consolidated[field] = value

        return consolidated

    def _calculate_chunked_confidence(self, chunk_results: list) -> float:
        """Calcula confiança para resultados de chunks"""
        if not chunk_results:
            return 0.0

        successful_chunks = sum(1 for _, data in chunk_results if data)
        total_chunks = len(chunk_results)

        return min(0.9, successful_chunks / total_chunks * 0.8)
