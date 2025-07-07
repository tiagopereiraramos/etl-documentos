
"""
Extractors Específicos por Tipo de Documento
Baseado no sistema legado mas integrado à nova arquitetura
"""
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import obter_logger

logger = obter_logger(__name__)

class DocumentExtractors:
    """Extractors específicos para cada tipo de documento"""
    
    @staticmethod
    def extract_comprovante_bancario(text: str) -> Dict[str, Any]:
        """Extrator específico para Comprovante Bancário"""
        result = {}
        
        # Padrões específicos para comprovante bancário
        patterns = {
            "valor": [
                r"(?:valor|quantia|importância)[\s:]*r?\$?\s*([\d.,]+)",
                r"r\$\s*([\d.,]+)",
                r"([\d]+\.[\d]{3},[\d]{2})"
            ],
            "data_transacao": [
                r"(?:data|em)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
                r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
            ],
            "agencia": [
                r"(?:agência|ag)[\s:]*(\d{3,5}[\-]?\d?)",
                r"ag[\.:]\s*(\d{3,5}[\-]?\d?)"
            ],
            "conta": [
                r"(?:conta|cc)[\s:]*(\d{4,12}[\-]?\d?)",
                r"cc[\.:]\s*(\d{4,12}[\-]?\d?)"
            ],
            "nome_banco": [
                r"(banco\s+[\w\s]+)",
                r"(caixa\s+econômica)",
                r"(itaú|bradesco|santander|bb|banco do brasil)"
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    break
        
        return result
    
    @staticmethod
    def extract_cartao_cnpj(text: str) -> Dict[str, Any]:
        """Extrator específico para Cartão CNPJ"""
        result = {}
        
        patterns = {
            "cnpj": [
                r"(\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2})",
                r"cnpj[\s:]*(\d{14})"
            ],
            "razao_social": [
                r"(?:razão social|nome empresarial)[\s:]*([^\n\r]+)",
                r"^([A-Z][A-Z\s&]+(?:LTDA|S\.A\.|ME|EPP))"
            ],
            "situacao_cadastral": [
                r"(?:situação|status)[\s:]*([^\n\r]+)",
                r"(ativa|suspensa|baixada|inapta)"
            ],
            "data_abertura": [
                r"(?:abertura|constituição)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    break
        
        return result
    
    @staticmethod
    def extract_cei_obra(text: str) -> Dict[str, Any]:
        """Extrator específico para CEI da Obra"""
        result = {}
        
        patterns = {
            "numero_cei": [
                r"(?:cei|matrícula)[\s:]*(\d{11,12})",
                r"(\d{3}\.?\d{5}\.?\d{2}\-?\d{1})"
            ],
            "cnpj": [
                r"(\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2})"
            ],
            "endereco_completo": [
                r"(?:endereço|local)[\s:]*([^\n\r]+(?:rua|av|avenida|praça)[^\n\r]*)"
            ],
            "data_registro": [
                r"(?:registro|cadastro)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    break
        
        return result
    
    @staticmethod
    def extract_cnh(text: str) -> Dict[str, Any]:
        """Extrator específico para CNH"""
        result = {}
        
        patterns = {
            "numero_cnh": [
                r"(?:registro|nº)[\s:]*(\d{11})",
                r"(\d{11})"
            ],
            "cpf": [
                r"(\d{3}\.?\d{3}\.?\d{3}\-?\d{2})"
            ],
            "categoria": [
                r"(?:categoria)[\s:]*([A-E]+)",
                r"\b([ABCDE]{1,3})\b"
            ],
            "data_validade": [
                r"(?:validade|válida até)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
            ],
            "data_primeira_habilitacao": [
                r"(?:primeira habilitação)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    break
        
        return result
    
    @staticmethod
    def extract_contrato_social(text: str) -> Dict[str, Any]:
        """Extrator específico para Contrato Social"""
        result = {}
        
        patterns = {
            "razao_social": [
                r"(?:denominação|razão social)[\s:]*([^\n\r]+)",
                r"^([A-Z][A-Z\s&]+(?:LTDA|S\.A\.|ME|EPP))"
            ],
            "cnpj": [
                r"(\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2})"
            ],
            "capital_social": [
                r"(?:capital social)[\s:]*r?\$?\s*([\d.,]+)",
                r"capital[\s:]*r?\$?\s*([\d.,]+)"
            ],
            "objeto_social": [
                r"(?:objeto social|atividade)[\s:]*([^\n\r]+(?:\n[^\n\r]+){0,3})"
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    break
        
        return result
    
    @staticmethod
    def extract_fatura_telefonica(text: str) -> Dict[str, Any]:
        """Extrator específico para Fatura Telefônica"""
        result = {}
        
        patterns = {
            "operadora": [
                r"(vivo|tim|claro|oi|nextel)",
                r"operadora[\s:]*([^\n\r]+)"
            ],
            "numero_telefone": [
                r"(\(\d{2}\)\s*\d{4,5}\-?\d{4})",
                r"(\d{2}\s*\d{4,5}\-?\d{4})"
            ],
            "valor_total": [
                r"(?:total|valor final)[\s:]*r?\$?\s*([\d.,]+)",
                r"r\$\s*([\d.,]+)"
            ],
            "data_vencimento": [
                r"(?:vencimento)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
            ],
            "periodo_cobranca": [
                r"(?:período|referência)[\s:]*([^\n\r]+)"
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    break
        
        return result
    
    @staticmethod
    def extract_nota_fiscal(text: str) -> Dict[str, Any]:
        """Extrator específico para Nota Fiscal de Serviços"""
        result = {}
        
        patterns = {
            "numero_nota": [
                r"(?:número|nº)[\s:]*(\d+)",
                r"nota[\s:]*(\d+)"
            ],
            "valor_servicos": [
                r"(?:valor dos serviços)[\s:]*r?\$?\s*([\d.,]+)",
                r"serviços[\s:]*r?\$?\s*([\d.,]+)"
            ],
            "valor_iss": [
                r"(?:iss)[\s:]*r?\$?\s*([\d.,]+)"
            ],
            "data_emissao": [
                r"(?:emissão|emitida em)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    break
        
        return result
    
    @staticmethod
    def get_extractor_for_type(document_type: str):
        """Retorna o extrator específico para o tipo de documento"""
        extractors = {
            "Comprovante Bancário": DocumentExtractors.extract_comprovante_bancario,
            "Cartão CNPJ": DocumentExtractors.extract_cartao_cnpj,
            "CEI da Obra": DocumentExtractors.extract_cei_obra,
            "CNH": DocumentExtractors.extract_cnh,
            "Contrato Social": DocumentExtractors.extract_contrato_social,
            "Fatura Telefônica": DocumentExtractors.extract_fatura_telefonica,
            "Nota Fiscal de Serviços Eletrônica": DocumentExtractors.extract_nota_fiscal
        }
        
        return extractors.get(document_type)
    
    @staticmethod
    def combine_extractions(llm_data: Dict[str, Any], regex_data: Dict[str, Any]) -> Dict[str, Any]:
        """Combina dados extraídos por LLM e regex, priorizando dados mais confiáveis"""
        combined = {}
        
        # Começar com dados do LLM
        for key, value in llm_data.items():
            if value and value != "Não foi possível localizar este campo":
                combined[key] = value
        
        # Sobrescrever com dados de regex quando disponíveis (mais confiáveis)
        for key, value in regex_data.items():
            if value and value.strip():
                # Limpar dados de regex
                cleaned_value = value.strip()
                if cleaned_value and len(cleaned_value) > 1:
                    combined[key] = cleaned_value
        
        return combined
