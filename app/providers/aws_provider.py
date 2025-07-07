"""
Provider AWS Textract para extração de texto
"""
import time
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.providers.base import (
    ProvedorExtracaoBase,
    ResultadoExtracao,
    ProvedorLLMBase,
    ResultadoLLM
)
from app.core.config import settings


class AWSTextractProvider(ProvedorExtracaoBase):
    """Provider para AWS Textract"""

    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region: str = "us-east-1"):
        super().__init__("aws_textract")
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region = region
        self.client = None
        self._inicializar_cliente()

    def _inicializar_cliente(self):
        """Inicializa o cliente AWS Textract"""
        try:
            import boto3
            self.client = boto3.client(
                'textract',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region
            )
            self.logger.info("Cliente AWS Textract inicializado")
        except ImportError:
            self.logger.error(
                "boto3 não está instalado. Execute: pip install boto3")
            self.client = None
        except Exception as e:
            self.logger.error(f"Erro ao inicializar cliente AWS Textract: {e}")
            self.client = None

    def validar_configuracao(self) -> bool:
        """Valida se o provedor está configurado corretamente"""
        return (
            bool(self.aws_access_key_id) and
            bool(self.aws_secret_access_key) and
            self.client is not None
        )

    def formatos_suportados(self) -> List[str]:
        """Lista de formatos suportados pelo AWS Textract"""
        return [
            ".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"
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
        Extrai texto usando AWS Textract

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
                    "Provider AWS Textract não está configurado corretamente")

            # Executar análise do documento
            response = await asyncio.to_thread(
                self.client.detect_document_text,
                Document={'Bytes': arquivo_bytes}
            )

            # Extrair texto dos blocos
            texto_extraido = ""
            if 'Blocks' in response:
                for block in response['Blocks']:
                    if block['BlockType'] == 'LINE':
                        texto_extraido += block['Text'] + '\n'

            # Calcular qualidade baseada na confiança
            qualidade = self._calcular_qualidade(response)

            # Calcular custo
            custo = self._calcular_custo(len(arquivo_bytes))

            tempo_processamento = time.time() - inicio

            # Preparar metadados
            metadados_resultado = {
                "aws_textract_result": {
                    "blocks": len(response.get('Blocks', [])),
                    "pages": len([b for b in response.get('Blocks', []) if b.get('BlockType') == 'PAGE']),
                    "lines": len([b for b in response.get('Blocks', []) if b.get('BlockType') == 'LINE']),
                    "words": len([b for b in response.get('Blocks', []) if b.get('BlockType') == 'WORD'])
                },
                "arquivo_original": nome_arquivo,
                "tamanho_bytes": len(arquivo_bytes)
            }

            if metadados:
                metadados_resultado.update(metadados)

            return ResultadoExtracao(
                texto=texto_extraido.strip(),
                qualidade=qualidade,
                metadados=metadados_resultado,
                provedor=self.nome,
                tempo_processamento=tempo_processamento,
                custo=custo,
                sucesso=True
            )

        except Exception as e:
            tempo_processamento = time.time() - inicio
            self.logger.error(f"Erro AWS Textract: {e}")
            return ResultadoExtracao(
                texto="",
                qualidade=0.0,
                metadados={"erro_aws": str(e)},
                provedor=self.nome,
                tempo_processamento=tempo_processamento,
                custo=0.0,
                sucesso=False,
                erro=f"Erro AWS Textract: {e}"
            )

    def _calcular_qualidade(self, response) -> float:
        """Calcula qualidade da extração baseada na confiança do AWS Textract"""
        try:
            # Calcular confiança média dos blocos
            confiancas = []
            for block in response.get('Blocks', []):
                if 'Confidence' in block:
                    confiancas.append(block['Confidence'])

            # Se não há confiança específica, usar valor padrão
            if not confiancas:
                return 0.80  # Valor padrão para AWS Textract

            # Normalizar para 0-1
            return sum(confiancas) / len(confiancas) / 100.0

        except Exception:
            return 0.80

    def _calcular_custo(self, tamanho_bytes: int) -> float:
        """Calcula custo estimado do AWS Textract"""
        # Preços aproximados do AWS Textract (por 1K páginas)
        # Sync: ~$1.50 por 1K páginas
        # Assumindo ~1MB = ~1 página
        tamanho_mb = tamanho_bytes / (1024 * 1024)
        custo_por_pagina = 0.0015  # $1.50 / 1000 páginas
        return tamanho_mb * custo_por_pagina

    def calcular_custo_estimado(self, tamanho_arquivo: int) -> float:
        """Calcula custo estimado para processamento"""
        return self._calcular_custo(tamanho_arquivo)


class AWSBedrockProvider(ProvedorLLMBase):
    """Provider para AWS Bedrock"""

    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, modelo: str = "anthropic.claude-3-sonnet-20240229-v1:0", region: str = "us-east-1"):
        super().__init__("aws_bedrock", "dummy_key", modelo)
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region = region
        self.client = None
        self._inicializar_cliente()

    def _inicializar_cliente(self):
        """Inicializa o cliente AWS Bedrock"""
        try:
            import boto3
            self.client = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region
            )
            self.logger.info("Cliente AWS Bedrock inicializado")
        except ImportError:
            self.logger.error(
                "boto3 não está instalado. Execute: pip install boto3")
            self.client = None
        except Exception as e:
            self.logger.error(f"Erro ao inicializar cliente AWS Bedrock: {e}")
            self.client = None

    def validar_configuracao(self) -> bool:
        """Valida se o provedor está configurado corretamente"""
        return (
            bool(self.aws_access_key_id) and
            bool(self.aws_secret_access_key) and
            self.client is not None
        )

    async def gerar_resposta(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> ResultadoLLM:
        """
        Gera resposta usando AWS Bedrock

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
                    "Provider AWS Bedrock não está configurado corretamente")

            # Preparar payload para Claude
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens or 4096,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            # Executar chamada
            response = await asyncio.to_thread(
                self.client.invoke_model,
                modelId=self.modelo,
                body=json.dumps(payload)
            )

            # Processar resposta
            response_body = json.loads(response['body'].read())
            resposta = response_body['content'][0]['text']

            # Extrair informações de uso (se disponível)
            tokens_input = response_body.get(
                'usage', {}).get('input_tokens', 0)
            tokens_output = response_body.get(
                'usage', {}).get('output_tokens', 0)

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
            self.logger.error(f"Erro AWS Bedrock: {e}")
            return ResultadoLLM(
                resposta="",
                tokens_input=0,
                tokens_output=0,
                custo=0.0,
                tempo_resposta=tempo_resposta,
                provedor=self.nome,
                modelo=self.modelo or "desconhecido",
                sucesso=False,
                erro=f"Erro AWS Bedrock: {e}"
            )

    async def calcular_custo(
        self,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """
        Calcula custo da operação AWS Bedrock

        Args:
            tokens_input: Tokens de entrada
            tokens_output: Tokens de saída

        Returns:
            Custo em reais (aproximado)
        """
        # Preços aproximados do AWS Bedrock Claude-3 (por 1M tokens)
        # Input: ~$3.00 por 1M tokens
        # Output: ~$15.00 por 1M tokens

        custo_input = (tokens_input / 1_000_000) * 3.00
        custo_output = (tokens_output / 1_000_000) * 15.00

        # Converter para reais (aproximado: 1 USD = 5 BRL)
        return (custo_input + custo_output) * 5.0
