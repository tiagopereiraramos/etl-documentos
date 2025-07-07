"""
Provider Azure Document Intelligence para extração de texto
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError

from app.providers.base import (
    ProvedorExtracaoBase,
    ResultadoExtracao,
    ProvedorLLMBase,
    ResultadoLLM
)
from app.core.config import settings


class AzureDocumentIntelligenceProvider(ProvedorExtracaoBase):
    """Provider para Azure Document Intelligence"""

    def __init__(self, endpoint: str, api_key: str):
        super().__init__("azure_document_intelligence")
        self.endpoint = endpoint
        self.api_key = api_key
        self.client = None
        self._inicializar_cliente()

    def _inicializar_cliente(self):
        """Inicializa o cliente Azure Document Intelligence"""
        try:
            credential = AzureKeyCredential(self.api_key)
            self.client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=credential
            )
            self.logger.info(
                "Cliente Azure Document Intelligence inicializado")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar cliente Azure: {e}")
            self.client = None

    def validar_configuracao(self) -> bool:
        """Valida se o provedor está configurado corretamente"""
        return (
            bool(self.endpoint) and
            bool(self.api_key) and
            self.client is not None
        )

    def formatos_suportados(self) -> List[str]:
        """Lista de formatos suportados pelo Azure Document Intelligence"""
        return [
            ".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff",
            ".heic", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"
        ]

    def suporta_formato(self, extensao: str) -> bool:
        """Verifica se o provedor suporta determinado formato"""
        return extensao.lower() in self.formatos_suportados()

    async def extrair_texto(
        self,
        arquivo_bytes: bytes,
        nome_arquivo: str,
        metadados: Optional[Dict[str, Any]] = None
    ) -> ResultadoExtracao:
        """
        Extrai texto usando Azure Document Intelligence

        Args:
            arquivo_bytes: Bytes do arquivo
            nome_arquivo: Nome do arquivo original
            metadados: Metadados adicionais

        Returns:
            ResultadoExtracao com o texto extraído
        """
        inicio = time.time()

        try:
            if not self.validar_configuracao() or self.client is None:
                raise ValueError(
                    "Provider Azure não está configurado corretamente")

            # Executar análise do documento
            poller = await asyncio.to_thread(
                self.client.begin_analyze_document,
                "prebuilt-document",
                arquivo_bytes
            )

            # Aguardar resultado
            result = await asyncio.to_thread(poller.result)

            # Extrair texto
            texto_extraido = ""
            if result.content:
                texto_extraido = result.content

            # Calcular qualidade baseada na confiança
            qualidade = self._calcular_qualidade(result)

            # Calcular custo
            custo = self._calcular_custo(len(arquivo_bytes))

            tempo_processamento = time.time() - inicio

            # Preparar metadados
            metadados_resultado = {
                "azure_result": {
                    "pages": len(result.pages) if result.pages else 0,
                    "tables": len(result.tables) if result.tables else 0,
                    "key_value_pairs": len(result.key_value_pairs) if result.key_value_pairs else 0,
                    "styles": len(result.styles) if result.styles else 0,
                    "languages": [lang.language_code for lang in result.languages] if result.languages else []
                },
                "arquivo_original": nome_arquivo,
                "tamanho_bytes": len(arquivo_bytes)
            }

            if metadados:
                metadados_resultado.update(metadados)

            return ResultadoExtracao(
                texto=texto_extraido,
                qualidade=qualidade,
                metadados=metadados_resultado,
                provedor=self.nome,
                tempo_processamento=tempo_processamento,
                custo=custo,
                sucesso=True
            )

        except AzureError as e:
            tempo_processamento = time.time() - inicio
            self.logger.error(f"Erro Azure Document Intelligence: {e}")
            return ResultadoExtracao(
                texto="",
                qualidade=0.0,
                metadados={"erro_azure": str(e)},
                provedor=self.nome,
                tempo_processamento=tempo_processamento,
                custo=0.0,
                sucesso=False,
                erro=f"Erro Azure: {e}"
            )

        except Exception as e:
            tempo_processamento = time.time() - inicio
            self.logger.error(
                f"Erro inesperado no Azure Document Intelligence: {e}")
            return ResultadoExtracao(
                texto="",
                qualidade=0.0,
                metadados={"erro": str(e)},
                provedor=self.nome,
                tempo_processamento=tempo_processamento,
                custo=0.0,
                sucesso=False,
                erro=f"Erro inesperado: {e}"
            )

    def _calcular_qualidade(self, result) -> float:
        """Calcula qualidade da extração baseada na confiança do Azure"""
        try:
            # Calcular confiança média das páginas
            confiancas = []
            if result.pages:
                for page in result.pages:
                    if hasattr(page, 'confidence') and page.confidence:
                        confiancas.append(page.confidence)

            # Se não há confiança específica, usar valor padrão
            if not confiancas:
                return 0.85  # Valor padrão para Azure

            return sum(confiancas) / len(confiancas)

        except Exception:
            return 0.85

    def _calcular_custo(self, tamanho_bytes: int) -> float:
        """Calcula custo estimado do Azure Document Intelligence"""
        # Preços aproximados do Azure Document Intelligence (por 1K páginas)
        # Prebuilt-document: ~$1.50 por 1K páginas
        # Assumindo ~1MB = ~1 página
        tamanho_mb = tamanho_bytes / (1024 * 1024)
        custo_por_pagina = 0.0015  # $1.50 / 1000 páginas
        return tamanho_mb * custo_por_pagina

    def calcular_custo_estimado(self, tamanho_arquivo: int) -> float:
        """Calcula custo estimado para processamento"""
        return self._calcular_custo(tamanho_arquivo)


class AzureOpenAIProvider(ProvedorLLMBase):
    """Provider para Azure OpenAI"""

    def __init__(self, endpoint: str, api_key: str, modelo: str = "gpt-4"):
        super().__init__("azure_openai", api_key, modelo)
        self.endpoint = endpoint
        self.deployment_name = modelo
        self._inicializar_cliente()

    def _inicializar_cliente(self):
        """Inicializa o cliente Azure OpenAI"""
        try:
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version="2024-02-15-preview"
            )
            self.logger.info("Cliente Azure OpenAI inicializado")
        except ImportError:
            self.logger.error(
                "OpenAI não está instalado. Execute: pip install openai")
            self.client = None
        except Exception as e:
            self.logger.error(f"Erro ao inicializar cliente Azure OpenAI: {e}")
            self.client = None

    def validar_configuracao(self) -> bool:
        """Valida se o provedor está configurado corretamente"""
        return (
            bool(self.endpoint) and
            bool(self.api_key) and
            self.client is not None
        )

    async def gerar_resposta(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> ResultadoLLM:
        """
        Gera resposta usando Azure OpenAI

        Args:
            prompt: Texto de entrada
            temperature: Temperatura para geração
            max_tokens: Máximo de tokens de saída

        Returns:
            ResultadoLLM com a resposta gerada
        """
        inicio = time.time()

        try:
            if not self.validar_configuracao() or self.client is None:
                raise ValueError(
                    "Provider Azure OpenAI não está configurado corretamente")

            # Preparar parâmetros
            params = {
                "model": self.deployment_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Executar chamada
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                **params
            )

            # Extrair dados da resposta
            resposta = response.choices[0].message.content
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens

            tempo_resposta = time.time() - inicio

            # Calcular custo
            custo = await self.calcular_custo(tokens_input, tokens_output)

            return ResultadoLLM(
                resposta=resposta,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                custo=custo,
                tempo_resposta=tempo_resposta,
                provedor=self.nome,
                modelo=self.modelo or "desconhecido",
                sucesso=True
            )

        except Exception as e:
            tempo_resposta = time.time() - inicio
            self.logger.error(f"Erro Azure OpenAI: {e}")
            return ResultadoLLM(
                resposta="",
                tokens_input=0,
                tokens_output=0,
                custo=0.0,
                tempo_resposta=tempo_resposta,
                provedor=self.nome,
                modelo=self.modelo or "desconhecido",
                sucesso=False,
                erro=f"Erro Azure OpenAI: {e}"
            )

    async def calcular_custo(
        self,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """
        Calcula custo da operação Azure OpenAI

        Args:
            tokens_input: Tokens de entrada
            tokens_output: Tokens de saída

        Returns:
            Custo em reais (aproximado)
        """
        # Preços aproximados do Azure OpenAI GPT-4 (por 1K tokens)
        # Input: ~$0.03 por 1K tokens
        # Output: ~$0.06 por 1K tokens

        custo_input = (tokens_input / 1000) * 0.03
        custo_output = (tokens_output / 1000) * 0.06

        # Converter para reais (aproximado: 1 USD = 5 BRL)
        return (custo_input + custo_output) * 5.0
