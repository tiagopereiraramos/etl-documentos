"""
Serviço principal de processamento de documentos
"""
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.providers.base import GerenciadorProvedores, ResultadoExtracao, ResultadoLLM
from app.database.repositories import (
    DocumentoRepository,
    ClienteRepository,
    LogProcessamentoRepository,
    SessaoUsoRepository,
    ConsumoLLMRepository
)
from app.models.database import Documento, Cliente, LogProcessamento
from app.models.schemas import (
    DocumentoCreate,
    DocumentoResponse,
    ProcessamentoStatus,
    TipoDocumento
)
from app.core.logging import obter_logger
from app.core.config import settings
from sqlalchemy.orm import Session
from app.services.extraction_service import ServicoExtracaoUnificado, ResultadoExtracaoDados


class DocumentProcessorService:
    """Serviço principal para processamento de documentos"""

    def __init__(self):
        self.logger = obter_logger(__name__)
        self.gerenciador_providers = GerenciadorProvedores()
        self.documento_repo = DocumentoRepository()
        self.cliente_repo = ClienteRepository()
        self.log_repo = LogProcessamentoRepository()
        self.sessao_repo = SessaoUsoRepository()
        self.consumo_repo = ConsumoLLMRepository()

        # Inicializar providers
        self._inicializar_providers()

    def _inicializar_providers(self):
        """Inicializa todos os providers disponíveis"""
        try:
            # Docling (local)
            from app.providers.docling_provider import DoclingProvider
            docling = DoclingProvider()
            self.gerenciador_providers.adicionar_provedor_extracao(docling)

            # Azure Document Intelligence
            if settings.azure_endpoint and settings.azure_key:
                from app.providers.azure_provider import AzureDocumentIntelligenceProvider
                azure_extracao = AzureDocumentIntelligenceProvider(
                    endpoint=settings.azure_endpoint,
                    api_key=settings.azure_key
                )
                self.gerenciador_providers.adicionar_provedor_extracao(
                    azure_extracao)

            # Azure OpenAI
            if settings.azure_openai_endpoint and settings.azure_openai_key:
                from app.providers.azure_provider import AzureOpenAIProvider
                azure_llm = AzureOpenAIProvider(
                    endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_key,
                    modelo=settings.azure_openai_model
                )
                self.gerenciador_providers.adicionar_provedor_llm(azure_llm)

            # AWS Textract
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                from app.providers.aws_provider import AWSTextractProvider
                aws_extracao = AWSTextractProvider(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region=settings.aws_region
                )
                self.gerenciador_providers.adicionar_provedor_extracao(
                    aws_extracao)

            # AWS Bedrock
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                from app.providers.aws_provider import AWSBedrockProvider
                aws_llm = AWSBedrockProvider(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    modelo=settings.aws_bedrock_model,
                    region=settings.aws_region
                )
                self.gerenciador_providers.adicionar_provedor_llm(aws_llm)

            self.logger.info(
                f"Providers inicializados: {len(self.gerenciador_providers.listar_provedores_extracao())} extração, {len(self.gerenciador_providers.listar_provedores_llm())} LLM")

        except Exception as e:
            self.logger.error(f"Erro ao inicializar providers: {e}")

    async def processar_documento(
        self,
        arquivo_bytes: bytes,
        nome_arquivo: str,
        cliente_id: str,
        db: Session,
        metadados: Optional[Dict[str, Any]] = None
    ) -> DocumentoResponse:
        """
        Processa um documento completo (extração + classificação + análise)

        Args:
            arquivo_bytes: Bytes do arquivo
            nome_arquivo: Nome do arquivo original
            cliente_id: ID do cliente
            db: Sessão do banco de dados
            metadados: Metadados adicionais

        Returns:
            DocumentoResponse com resultado do processamento
        """
        inicio_processamento = time.time()
        documento_id = str(uuid.uuid4())

        try:
            # 1. Criar registro do documento
            documento_data = DocumentoCreate(
                id=documento_id,
                cliente_id=cliente_id,
                nome_arquivo=nome_arquivo,
                tipo_documento="desconhecido",
                extensao_arquivo=self._obter_extensao(nome_arquivo),
                tamanho_arquivo=len(arquivo_bytes),
                status_processamento=ProcessamentoStatus.PROCESSANDO
            )

            documento = self.documento_repo.criar(db, **documento_data.dict())
            await self._log_operacao(
                db, documento_id=documento_id,
                cliente_id=cliente_id,
                operacao="inicio_processamento",
                status="iniciado"
            )

            # 2. Extrair texto
            resultado_extracao = await self._extrair_texto(
                arquivo_bytes, nome_arquivo, documento_id, cliente_id, metadados
            )

            # Fallback defensivo: garantir que texto nunca é None
            if resultado_extracao.texto is None:
                resultado_extracao.texto = ""

            if not resultado_extracao.sucesso:
                await self._finalizar_com_erro(db, documento_id, cliente_id, "Erro na extração de texto")
                return await self._criar_resposta_erro(documento_id, "Erro na extração de texto")

            # 3. Classificar documento
            resultado_classificacao = await self._classificar_documento(
                resultado_extracao.texto, documento_id, cliente_id
            )

            if not resultado_classificacao.sucesso:
                await self._finalizar_com_erro(db, documento_id, cliente_id, "Erro na classificação")
                return await self._criar_resposta_erro(documento_id, "Erro na classificação")

            # 4. Extrair dados estruturados
            resultado_extracao_dados = await self._extrair_dados_estruturados(
                resultado_extracao.texto, resultado_classificacao.resposta, documento_id, db
            )

            # 5. Atualizar documento com resultados CORRIGIDO
            # Usar dados da classificação original se disponível
            classificacao_data = resultado_classificacao.to_dict()
            if hasattr(self, '_dados_classificacao_original') and self._dados_classificacao_original:
                classificacao_data.update({
                    "classificacao_original": self._dados_classificacao_original
                })

            dados_extraidos = {
                "classificacao": classificacao_data,
                "extracao_dados": {
                    "dados_extraidos": resultado_extracao_dados.dados_extraidos,
                    "confianca": resultado_extracao_dados.confianca,
                    "metadados": resultado_extracao_dados.metadados
                } if resultado_extracao_dados else None,
                # ADICIONAR: Dados da extração do Docling
                "extracao_docling": {
                    "texto_extraido": resultado_extracao.texto,
                    "qualidade": resultado_extracao.qualidade,
                    "provedor": resultado_extracao.provedor,
                    "tempo_processamento": resultado_extracao.tempo_processamento,
                    "metadados": resultado_extracao.metadados
                },
                # ADICIONAR: Extração qualificada (resposta da LLM com prompts específicos)
                "extracao_qualificada": resultado_extracao_dados.dados_extraidos if resultado_extracao_dados else {}
            }

            # Obter confiança da classificação original
            confianca_classificacao = 0.0
            if hasattr(self, '_dados_classificacao_original') and self._dados_classificacao_original:
                confianca_classificacao = self._dados_classificacao_original.get(
                    'confianca', 0.0)

            self.documento_repo.atualizar(
                db, documento_id,
                tipo_documento=resultado_classificacao.resposta,  # CORREÇÃO: usar tipo correto
                texto_extraido=resultado_extracao.texto,
                dados_extraidos=dados_extraidos,
                # CORREÇÃO: usar confiança correta
                confianca_classificacao=confianca_classificacao,
                provider_extracao=resultado_extracao.provedor,
                qualidade_extracao=resultado_extracao.qualidade,
                tempo_processamento=resultado_extracao.tempo_processamento,
                custo_processamento=resultado_extracao.custo,
                status_processamento="concluido",  # CORREÇÃO: status correto
                data_processamento=datetime.utcnow()
            )

            await self._log_operacao(
                db, documento_id=documento_id,
                cliente_id=cliente_id,
                operacao="processamento_concluido",
                status="sucesso",
                detalhes={
                    "tempo_total": time.time() - inicio_processamento,
                    "custo_total": resultado_extracao.custo + resultado_classificacao.custo + (resultado_extracao_dados.metadados.get('custo', 0) if resultado_extracao_dados else 0)
                }
            )

            return self.documento_repo.obter_por_id(db, documento_id)

        except Exception as e:
            self.logger.error(
                f"Erro no processamento do documento {documento_id}: {e}")
            await self._finalizar_com_erro(db, documento_id, cliente_id, str(e))
            return await self._criar_resposta_erro(documento_id, str(e))

    async def _extrair_texto(
        self,
        arquivo_bytes: bytes,
        nome_arquivo: str,
        documento_id: str,
        cliente_id: str,
        metadados: Optional[Dict[str, Any]] = None
    ) -> ResultadoExtracao:
        """Extrai texto do documento com fallback automático"""
        extensao = self._obter_extensao(nome_arquivo)

        self.logger.debug(
            f"DEBUG: Iniciando extração de texto para documento {documento_id}")
        self.logger.debug(f"DEBUG: - Nome arquivo: {nome_arquivo}")
        self.logger.debug(f"DEBUG: - Extensão: {extensao}")
        self.logger.debug(f"DEBUG: - Tamanho: {len(arquivo_bytes)} bytes")
        self.logger.debug(f"DEBUG: - Cliente ID: {cliente_id}")

        # Para arquivos .txt, usar Azure diretamente (Docling não suporta)
        if extensao == ".txt":
            self.logger.info(
                f"Arquivo .txt detectado, usando Azure diretamente")

            # Procurar Azure provider
            azure_provider = None
            for provider in self.gerenciador_providers.provedores_extracao:
                if provider.nome == "azure_document_intelligence":
                    azure_provider = provider
                    break

            if azure_provider and azure_provider.validar_configuracao():
                try:
                    self.logger.debug(
                        f"DEBUG: Tentando Azure para arquivo .txt")
                    resultado_azure = await azure_provider.extrair_texto(arquivo_bytes, nome_arquivo, metadados)

                    # Log completo da resposta Azure
                    self.logger.debug(
                        f"DEBUG: RESPOSTA COMPLETA AZURE PARA .TXT:")
                    self.logger.debug(
                        f"DEBUG: - Sucesso: {resultado_azure.sucesso}")
                    self.logger.debug(
                        f"DEBUG: - Qualidade: {resultado_azure.qualidade}")
                    self.logger.debug(
                        f"DEBUG: - Tempo: {resultado_azure.tempo_processamento}s")
                    self.logger.debug(
                        f"DEBUG: - Custo: R$ {resultado_azure.custo:.4f}")
                    self.logger.debug(
                        f"DEBUG: - Provedor: {resultado_azure.provedor}")
                    self.logger.debug(
                        f"DEBUG: - Texto extraído (tamanho): {len(resultado_azure.texto)} chars")
                    self.logger.debug(
                        f"DEBUG: - Texto (primeiros 500 chars): {resultado_azure.texto[:500]}...")
                    self.logger.debug(
                        f"DEBUG: - Metadados: {resultado_azure.metadados}")
                    if resultado_azure.erro:
                        self.logger.debug(
                            f"DEBUG: - Erro: {resultado_azure.erro}")

                    if resultado_azure.sucesso:
                        self.logger.info(
                            f"Azure extraiu .txt com sucesso (qualidade: {resultado_azure.qualidade:.2f})")
                        return resultado_azure
                    else:
                        self.logger.warning(
                            f"Azure falhou para .txt: {resultado_azure.erro}")
                except Exception as e:
                    self.logger.error(f"Erro no Azure para .txt: {e}")
                    self.logger.debug(
                        f"DEBUG: EXCEÇÃO COMPLETA AZURE: {str(e)}")

            # Se Azure falhou, retornar erro específico para .txt
            raise ValueError(f"Nenhum provider disponível para arquivos .txt")

        # Para outros formatos, usar lógica normal (Docling primeiro, depois fallback)
        # 1. SEMPRE tentar Docling primeiro (provedor padrão)
        docling_provider = None
        for provider in self.gerenciador_providers.provedores_extracao:
            if provider.nome == "docling":
                docling_provider = provider
                break

        if docling_provider and docling_provider.validar_configuracao():
            self.logger.info(f"Tentando extração com Docling para {extensao}")
            self.logger.debug(f"DEBUG: Docling provider encontrado e válido")

            resultado_docling = await docling_provider.extrair_texto(arquivo_bytes, nome_arquivo, metadados)

            # Log completo da resposta Docling
            self.logger.debug(f"DEBUG: RESPOSTA COMPLETA DOCLING:")
            self.logger.debug(f"DEBUG: - Sucesso: {resultado_docling.sucesso}")
            self.logger.debug(
                f"DEBUG: - Qualidade: {resultado_docling.qualidade}")
            self.logger.debug(
                f"DEBUG: - Tempo: {resultado_docling.tempo_processamento}s")
            self.logger.debug(
                f"DEBUG: - Custo: R$ {resultado_docling.custo:.6f}")
            self.logger.debug(
                f"DEBUG: - Provedor: {resultado_docling.provedor}")
            self.logger.debug(
                f"DEBUG: - Texto extraído (tamanho): {len(resultado_docling.texto)} chars")
            self.logger.debug(
                f"DEBUG: - Texto (primeiros 1000 chars): {resultado_docling.texto[:1000]}...")
            self.logger.debug(
                f"DEBUG: - Metadados completos: {resultado_docling.metadados}")
            if resultado_docling.erro:
                self.logger.debug(f"DEBUG: - Erro: {resultado_docling.erro}")

            # Se Docling foi bem-sucedido e qualidade é boa, usar resultado
            if resultado_docling and resultado_docling.sucesso and resultado_docling.qualidade >= 0.7:
                self.logger.info(
                    f"Docling extraiu com sucesso (qualidade: {resultado_docling.qualidade:.2f})")
                self.logger.debug(
                    f"DEBUG: Usando resultado Docling (qualidade >= 0.7)")
                return resultado_docling

            # Se Docling falhou ou qualidade é baixa, tentar fallback
            if resultado_docling and resultado_docling.sucesso:
                self.logger.warning(
                    f"Docling extraiu mas qualidade baixa ({resultado_docling.qualidade:.2f}), tentando fallback")
                self.logger.debug(
                    f"DEBUG: Qualidade Docling baixa, iniciando fallback")
            else:
                self.logger.warning(
                    f"Docling falhou: {getattr(resultado_docling, 'erro', 'erro desconhecido')}, tentando fallback")
                self.logger.debug(
                    f"DEBUG: Docling falhou completamente, iniciando fallback")

        # 2. Fallback: tentar Azure ou AWS Textract
        fallback_providers = []
        for provider in self.gerenciador_providers.provedores_extracao:
            if provider.nome in ["azure_document_intelligence", "aws_textract"] and provider.validar_configuracao():
                if provider.suporta_formato(extensao):
                    fallback_providers.append(provider)

        self.logger.debug(
            f"DEBUG: Fallback providers disponíveis: {[p.nome for p in fallback_providers]}")

        if fallback_providers:
            # Tentar cada provider de fallback
            for provider in fallback_providers:
                try:
                    self.logger.info(
                        f"Tentando fallback com {provider.nome} para {extensao}")
                    self.logger.debug(
                        f"DEBUG: Iniciando fallback com {provider.nome}")

                    resultado_fallback = await provider.extrair_texto(arquivo_bytes, nome_arquivo, metadados)

                    # Log completo da resposta do fallback
                    self.logger.debug(
                        f"DEBUG: RESPOSTA COMPLETA {provider.nome.upper()}:")
                    self.logger.debug(
                        f"DEBUG: - Sucesso: {resultado_fallback.sucesso}")
                    self.logger.debug(
                        f"DEBUG: - Qualidade: {resultado_fallback.qualidade}")
                    self.logger.debug(
                        f"DEBUG: - Tempo: {resultado_fallback.tempo_processamento}s")
                    self.logger.debug(
                        f"DEBUG: - Custo: R$ {resultado_fallback.custo:.4f}")
                    self.logger.debug(
                        f"DEBUG: - Provedor: {resultado_fallback.provedor}")
                    self.logger.debug(
                        f"DEBUG: - Texto extraído (tamanho): {len(resultado_fallback.texto)} chars")
                    self.logger.debug(
                        f"DEBUG: - Texto (primeiros 1000 chars): {resultado_fallback.texto[:1000]}...")
                    self.logger.debug(
                        f"DEBUG: - Metadados completos: {resultado_fallback.metadados}")
                    if resultado_fallback.erro:
                        self.logger.debug(
                            f"DEBUG: - Erro: {resultado_fallback.erro}")

                    if resultado_fallback.sucesso:
                        self.logger.info(
                            f"Fallback {provider.nome} extraiu com sucesso (qualidade: {resultado_fallback.qualidade:.2f})")
                        self.logger.debug(
                            f"DEBUG: Usando resultado do fallback {provider.nome}")
                        return resultado_fallback
                    else:
                        self.logger.warning(
                            f"Fallback {provider.nome} falhou: {resultado_fallback.erro}")
                        self.logger.debug(
                            f"DEBUG: Fallback {provider.nome} falhou, tentando próximo")

                except Exception as e:
                    self.logger.error(f"Erro no fallback {provider.nome}: {e}")
                    self.logger.debug(
                        f"DEBUG: EXCEÇÃO COMPLETA {provider.nome}: {str(e)}")

        # 3. Se nenhum provider funcionou, retornar erro
        if docling_provider and docling_provider.validar_configuracao():
            # Retornar resultado do Docling mesmo que tenha falhado
            if 'resultado_docling' in locals():
                self.logger.debug(
                    f"DEBUG: Retornando resultado Docling mesmo com falha/qualidade baixa")
                return resultado_docling

        # Último recurso: erro genérico
        self.logger.debug(f"DEBUG: Nenhum provider funcionou para {extensao}")
        raise ValueError(
            f"Nenhum provider disponível ou funcionando para o formato {extensao}")

    async def _classificar_documento(
        self,
        texto: str,
        documento_id: str,
        cliente_id: str
    ) -> ResultadoLLM:
        """Classifica o tipo do documento"""
        self.logger.debug(
            f"DEBUG: Iniciando classificação do documento {documento_id}")
        self.logger.debug(
            f"DEBUG: - Texto para classificação (tamanho): {len(texto)} chars")
        self.logger.debug(
            f"DEBUG: - Texto (primeiros 300 chars): {texto[:300]}...")

        from app.services.classification_service import ClassificationService
        from app.services.vector_service import VectorStoreService

        # Inicializar o serviço de vetores
        vector_service = VectorStoreService()

        # Inicializar o classificador com o serviço de vetores
        classificador = ClassificationService(vector_service)

        # Chamar o método correto
        resultado = await classificador.classify_document(
            document_text=texto,
            use_adaptive=True,
            confidence_threshold=0.7
        )

        # Log completo da resposta de classificação
        self.logger.debug(f"DEBUG: RESPOSTA COMPLETA CLASSIFICAÇÃO:")
        self.logger.debug(
            f"DEBUG: - Tipo documento: {resultado.tipo_documento}")
        self.logger.debug(f"DEBUG: - Confiança: {resultado.confianca}")
        self.logger.debug(f"DEBUG: - Método: {resultado.metodo}")
        self.logger.debug(f"DEBUG: - Provedor LLM: {resultado.provedor_llm}")
        self.logger.debug(f"DEBUG: - Modelo LLM: {resultado.modelo_llm}")
        self.logger.debug(
            f"DEBUG: - Tempo processamento: {resultado.tempo_processamento}s")
        self.logger.debug(
            f"DEBUG: - Metadados completos: {resultado.metadados}")

        # CORREÇÃO: Preservar dados da classificação originais
        # Converter para ResultadoLLM mas manter dados importantes
        resultado_llm = ResultadoLLM(
            resposta=resultado.tipo_documento,
            tokens_input=resultado.metadados.get(
                'input_tokens', 0) if resultado.metadados else 0,
            tokens_output=resultado.metadados.get(
                'output_tokens', 0) if resultado.metadados else 0,
            custo=resultado.metadados.get(
                'cost', 0.0) if resultado.metadados else 0.0,
            tempo_resposta=resultado.tempo_processamento,
            provedor=resultado.provedor_llm,
            modelo=resultado.modelo_llm,
            sucesso=resultado.tipo_documento != "Documento Não Classificado"
        )

        # Armazenar dados da classificação original em uma variável separada
        # que será usada na atualização do documento
        self._dados_classificacao_original = {
            "tipo_documento": resultado.tipo_documento,
            "confianca": resultado.confianca,
            "metodo": resultado.metodo,
            "provedor_llm": resultado.provedor_llm,
            "modelo_llm": resultado.modelo_llm,
            "tempo_processamento": resultado.tempo_processamento,
            "documentos_similares": resultado.documentos_similares,
            "erro": resultado.erro,
            "metadados": resultado.metadados
        }

        self.logger.debug(
            f"DEBUG: ResultadoLLM criado: {resultado_llm.resposta} (sucesso: {resultado_llm.sucesso})")
        return resultado_llm

    async def _extrair_dados_estruturados(
        self,
        texto: str,
        tipo_documento: str,
        documento_id: str,
        db: Session
    ) -> "ResultadoExtracaoDados":
        """Extrai dados estruturados do documento usando prompts específicos do tipo classificado"""
        from app.services.extraction_service import ServicoExtracaoUnificado, ResultadoExtracaoDados
        from app.services.vector_service import VectorStoreService
        from app.services.cost_service import CostTrackingService

        self.logger.info(
            f"🎯 Iniciando extração QUALIFICADA para tipo: {tipo_documento}")
        self.logger.debug(
            f"DEBUG: Texto para extração (tamanho): {len(texto)} chars")

        try:
            # Inicializar serviços necessários
            vector_service = VectorStoreService()
            cost_service = CostTrackingService()

            # Inicializar o serviço de extração unificado
            servico_extracao = ServicoExtracaoUnificado(
                vector_service=vector_service,
                cost_service=cost_service
            )

            # Usar o método completo de extração de dados estruturados
            # que já tem todos os prompts específicos implementados
            resultado = await servico_extracao.extrair_dados_estruturados(
                texto_documento=texto,
                tipo_documento=tipo_documento,
                document_id=documento_id,
                db_session=db
            )

            self.logger.info(
                f"✅ Extração qualificada concluída: {len(resultado.dados_extraidos)} campos extraídos")
            self.logger.debug(
                f"DEBUG: Dados extraídos: {resultado.dados_extraidos}")
            self.logger.debug(f"DEBUG: Confiança: {resultado.confianca}")
            self.logger.debug(f"DEBUG: Metadados: {resultado.metadados}")

            return resultado

        except Exception as e:
            self.logger.error(f"❌ Erro na extração qualificada: {e}")
            self.logger.debug(f"DEBUG: ERRO COMPLETO EXTRAÇÃO: {str(e)}")

            # Fallback: retornar dados básicos se a extração completa falhar
            self.logger.warning(
                "⚠️ Usando fallback de dados básicos devido ao erro")

        dados_basicos = {
            "tipo_documento": tipo_documento,
            "texto_analisado": len(texto),
            "timestamp_extracao": datetime.utcnow().isoformat(),
                "status": "extraido_com_fallback",
                "erro_extracao_completa": str(e)
        }

        return ResultadoExtracaoDados(
            dados_extraidos=dados_basicos,
                confianca=0.3,  # Confiança baixa para fallback
            metadados={
                "custo": 0.001,
                "tempo_processamento": 0.1,
                    "metodo": "fallback_basico",
                    "erro_original": str(e)
            }
        )

    async def _log_operacao(
        self,
        db: Session,
        documento_id: str,
        cliente_id: str,
        operacao: str,
        status: str,
        provider: Optional[str] = None,
        detalhes: Optional[Dict[str, Any]] = None
    ):
        """Registra log de operação"""
        try:
            log_data = {
                "documento_id": documento_id,
                "cliente_id": cliente_id,
                "operacao": operacao,
                "provider": provider,
                "status": status,
                "detalhes": detalhes or {}
            }
            self.log_repo.criar(db, **log_data)
        except Exception as e:
            self.logger.error(f"Erro ao registrar log: {e}")

    async def _finalizar_com_erro(self, db: Session, documento_id: str, cliente_id: str, erro: str):
        """Finaliza processamento com erro"""
        try:
            self.documento_repo.atualizar(
                db, documento_id,
                status_processamento=ProcessamentoStatus.ERRO,
                data_processamento=datetime.utcnow()
            )

            await self._log_operacao(
                db, documento_id=documento_id,
                cliente_id=cliente_id,
                operacao="processamento_erro",
                status="erro",
                detalhes={"erro": erro}
            )
        except Exception as e:
            self.logger.error(f"Erro ao finalizar com erro: {e}")

    async def _criar_resposta_erro(self, documento_id: str, erro: str) -> DocumentoResponse:
        """Cria resposta de erro"""
        return DocumentoResponse(
            id=documento_id,
            nome_arquivo="",
            tipo_documento="",
            extensao_arquivo="",
            tamanho_arquivo=0,
            cliente_id="",
            data_upload=datetime.utcnow(),
            status_processamento=ProcessamentoStatus.ERRO,
            erro=erro
        )

    def _obter_extensao(self, nome_arquivo: str) -> str:
        """Obtém extensão do arquivo"""
        import os
        return os.path.splitext(nome_arquivo)[1].lower()

    async def obter_status_processamento(self, documento_id: str) -> Dict[str, Any]:
        """Obtém status do processamento"""
        try:
            # Precisamos de uma sessão do banco para obter o documento
            from app.database.connection import get_db
            db = next(get_db())

            documento = self.documento_repo.obter_por_id(db, documento_id)
            logs = self.log_repo.get_by_documento(db, documento_id)

            return {
                "documento": documento,
                "logs": logs,
                "status": documento.status_processamento if documento else "nao_encontrado"
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter status: {e}")
            return {"status": "erro", "erro": str(e)}
