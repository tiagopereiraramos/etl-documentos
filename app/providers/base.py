"""
Classes base para provedores de extração e LLM
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from datetime import datetime
import logging

from app.core.logging import obter_logger


@dataclass
class ResultadoExtracao:
    """Resultado da extração de texto de um documento"""
    texto: str
    qualidade: float
    metadados: Dict[str, Any]
    provedor: str
    tempo_processamento: float = 0.0
    custo: float = 0.0
    sucesso: bool = True
    erro: Optional[str] = None

    def __post_init__(self):
        # Validar qualidade entre 0 e 1
        if not 0 <= self.qualidade <= 1:
            raise ValueError("Qualidade deve estar entre 0 e 1")

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "texto": self.texto,
            "qualidade": self.qualidade,
            "metadados": self.metadados,
            "provedor": self.provedor,
            "tempo_processamento": self.tempo_processamento,
            "custo": self.custo,
            "sucesso": self.sucesso,
            "erro": self.erro,
            "timestamp": datetime.utcnow().isoformat()
        }


@dataclass
class ResultadoLLM:
    """Resultado de uma chamada para LLM"""
    resposta: str
    tokens_input: int
    tokens_output: int
    custo: float
    tempo_resposta: float
    provedor: str
    modelo: str
    sucesso: bool = True
    erro: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "resposta": self.resposta,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "custo": self.custo,
            "tempo_resposta": self.tempo_resposta,
            "provedor": self.provedor,
            "modelo": self.modelo,
            "sucesso": self.sucesso,
            "erro": self.erro,
            "timestamp": datetime.utcnow().isoformat()
        }


class ProvedorExtracaoBase(ABC):
    """Classe base para todos os provedores de extração"""

    def __init__(self, nome: str, configuracoes: Optional[Dict[str, Any]] = None):
        self.nome = nome
        self.configuracoes = configuracoes or {}
        self.ativo = True
        self.logger = obter_logger(f"{__name__}.{nome}")

    @abstractmethod
    async def extrair_texto(
        self,
        arquivo_bytes: bytes,
        nome_arquivo: str,
        metadados: Optional[Dict[str, Any]] = None
    ) -> ResultadoExtracao:
        """
        Extrai texto de um arquivo

        Args:
            arquivo_bytes: Bytes do arquivo
            nome_arquivo: Nome do arquivo original
            metadados: Metadados adicionais

        Returns:
            ResultadoExtracao com o texto extraído
        """
        pass

    @abstractmethod
    def suporta_formato(self, extensao: str) -> bool:
        """Verifica se o provedor suporta determinado formato"""
        pass

    @abstractmethod
    def formatos_suportados(self) -> List[str]:
        """Lista de formatos suportados pelo provedor"""
        pass

    @abstractmethod
    def validar_configuracao(self) -> bool:
        """Valida se o provedor está configurado corretamente"""
        pass

    def obter_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o provedor"""
        return {
            "nome": self.nome,
            "ativo": self.ativo,
            "formatos_suportados": self.formatos_suportados(),
            "configurado": self.validar_configuracao()
        }

    def calcular_custo_estimado(self, tamanho_arquivo: int) -> float:
        """Calcula custo estimado para processamento"""
        return 0.0


class ProvedorLLMBase(ABC):
    """Classe base para provedores de LLM"""

    def __init__(self, nome: str, api_key: str, modelo: Optional[str] = None):
        self.nome = nome
        self.api_key = api_key
        self.modelo = modelo
        self.logger = obter_logger(f"{__name__}.{nome}")

    @abstractmethod
    async def gerar_resposta(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> ResultadoLLM:
        """
        Gera resposta usando LLM

        Args:
            prompt: Texto de entrada
            temperature: Temperatura para geração
            max_tokens: Máximo de tokens de saída

        Returns:
            ResultadoLLM com a resposta gerada
        """
        pass

    @abstractmethod
    async def calcular_custo(
        self,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """
        Calcula custo da operação

        Args:
            tokens_input: Tokens de entrada
            tokens_output: Tokens de saída

        Returns:
            Custo em reais
        """
        pass

    @abstractmethod
    def validar_configuracao(self) -> bool:
        """Valida se o provedor está configurado corretamente"""
        pass

    def obter_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o provedor"""
        return {
            "nome": self.nome,
            "modelo": self.modelo if self.modelo else "não especificado",
            "configurado": self.validar_configuracao()
        }


class GerenciadorProvedores:
    """Gerenciador de provedores de extração e LLM"""

    def __init__(self):
        self.provedores_extracao: List[ProvedorExtracaoBase] = []
        self.provedores_llm: List[ProvedorLLMBase] = []
        self.logger = obter_logger(__name__)

    def adicionar_provedor_extracao(self, provedor: ProvedorExtracaoBase):
        """Adiciona um provedor de extração"""
        if provedor.validar_configuracao():
            self.provedores_extracao.append(provedor)
            self.logger.info(
                f"Provedor de extração {provedor.nome} adicionado com sucesso")
        else:
            self.logger.warning(
                f"Provedor de extração {provedor.nome} não foi adicionado - configuração inválida")

    def adicionar_provedor_llm(self, provedor: ProvedorLLMBase):
        """Adiciona um provedor de LLM"""
        if provedor.validar_configuracao():
            self.provedores_llm.append(provedor)
            self.logger.info(
                f"Provedor LLM {provedor.nome} adicionado com sucesso")
        else:
            self.logger.warning(
                f"Provedor LLM {provedor.nome} não foi adicionado - configuração inválida")

    def obter_provedor_extracao_disponivel(self, extensao: str) -> Optional[ProvedorExtracaoBase]:
        """Retorna o primeiro provedor de extração disponível para o formato"""
        for provedor in self.provedores_extracao:
            if provedor.ativo and provedor.validar_configuracao() and provedor.suporta_formato(extensao):
                return provedor
        return None

    def obter_provedor_llm_disponivel(self) -> Optional[ProvedorLLMBase]:
        """Retorna o primeiro provedor LLM disponível"""
        for provedor in self.provedores_llm:
            if provedor.validar_configuracao():
                return provedor
        return None

    def listar_provedores_extracao(self) -> List[str]:
        """Lista nomes dos provedores de extração disponíveis"""
        return [p.nome for p in self.provedores_extracao if p.ativo and p.validar_configuracao()]

    def listar_provedores_llm(self) -> List[str]:
        """Lista nomes dos provedores LLM disponíveis"""
        return [p.nome for p in self.provedores_llm if p.validar_configuracao()]

    def obter_info_provedores(self) -> Dict[str, Any]:
        """Retorna informações de todos os provedores"""
        return {
            "extracao": [p.obter_info() for p in self.provedores_extracao],
            "llm": [p.obter_info() for p in self.provedores_llm]
        }
