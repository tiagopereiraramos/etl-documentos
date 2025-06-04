from typing import Dict, Any, Optional, List, Union
import json
from datetime import datetime

from utils.logging import get_logger

# Usar o logger do Loguru em vez do logging padrão
logger = get_logger("document_processor")

class DocumentTracker:
    """
    Classe para rastreamento visual e detalhado do processamento de documentos,
    fornecendo indicadores claros de onde cada documento está sendo processado.
    """
    
    @staticmethod
    def log_processing_start(doc_id: str, doc_name: str, doc_type: str = None) -> None:
        """Log de início do processamento de um documento"""
        doc_type_str = f"| Tipo: {doc_type}" if doc_type else ""
        logger.info(f"🔄 INÍCIO PROCESSAMENTO | ID: {doc_id} | Documento: {doc_name} {doc_type_str}")
    
    @staticmethod
    def log_docling_processing(doc_id: str, doc_name: str, model_name: str = None, doc_type: str = None) -> None:
        """Log quando um documento é processado pelo Docling"""
        doc_type_str = f"| Tipo: {doc_type}" if doc_type else ""
        model_str = f"| Modelo: {model_name}" if model_name else ""
        logger.info(f"🟢 DOCLING LOCAL | ID: {doc_id} | Documento: {doc_name} {doc_type_str} {model_str}")
    
    @staticmethod
    def log_azure_processing(doc_id: str, doc_name: str, service_name: str = None, reason: str = None, doc_type: str = None) -> None:
        """Log quando um documento é processado pelo Azure"""
        doc_type_str = f"| Tipo: {doc_type}" if doc_type else ""
        service_str = f"| Serviço: {service_name}" if service_name else ""
        reason_str = f"| Motivo: {reason}" if reason else ""
        logger.warning(f"🔵 AZURE API | ID: {doc_id} | Documento: {doc_name} {doc_type_str} {service_str} {reason_str}")
    
    @staticmethod
    def log_extraction_result(doc_id: str, doc_name: str, extracted_text: str, method: str, quality_score: float = None) -> None:
        """Log do resultado da extração de texto"""
        quality_str = f"| Qualidade: {quality_score:.2f}" if quality_score is not None else ""
        chars_count = len(extracted_text) if extracted_text else 0
        lines_count = extracted_text.count('\n') + 1 if extracted_text else 0
        
        # Emoji baseado no método
        emoji = "🟢" if method.lower() == "docling" else "🔵" if method.lower() == "azure" else "📄"
        
        logger.info(
            f"{emoji} EXTRAÇÃO {method.upper()} | ID: {doc_id} | Documento: {doc_name} | "
            f"Caracteres: {chars_count} | Linhas: {lines_count} {quality_str}"
        )
    
    @staticmethod
    def log_extraction_quality(doc_id: str, doc_name: str, quality_score: float, metrics: Dict[str, Any], method: str) -> None:
        """Log detalhado da qualidade da extração"""
        method_emoji = "🟢" if method.lower() == "docling" else "🔵" if method.lower() == "azure" else "📊"
        logger.info(
            f"{method_emoji} QUALIDADE {method.upper()} | ID: {doc_id} | Documento: {doc_name} | "
            f"Score: {quality_score:.2f} | Métricas: {json.dumps(metrics)}"
        )
    
    @staticmethod
    def log_fallback(doc_id: str, doc_name: str, from_method: str, to_method: str, reason: str) -> None:
        """Log de fallback entre métodos de processamento"""
        logger.warning(
            f"⚠️ FALLBACK | ID: {doc_id} | Documento: {doc_name} | "
            f"De: {from_method} → Para: {to_method} | Motivo: {reason}"
        )
    
    @staticmethod
    def log_processing_complete(doc_id: str, doc_name: str, elapsed_time: float, method: str, stats: Dict[str, Any]) -> None:
        """Log de conclusão do processamento"""
        method_emoji = "🟢" if method.lower() == "docling" else "🔵" if method.lower() == "azure" else "✅"
        logger.info(
            f"{method_emoji} PROCESSAMENTO CONCLUÍDO | ID: {doc_id} | Documento: {doc_name} | "
            f"Método: {method} | Tempo: {elapsed_time:.3f}s | Estatísticas: {json.dumps(stats)}"
        )
    
    @staticmethod
    def log_error(doc_id: str, doc_name: str, error_message: str, elapsed_time: float = None) -> None:
        """Log de erro no processamento"""
        time_str = f"| Tempo: {elapsed_time:.3f}s" if elapsed_time is not None else ""
        logger.error(f"❌ ERRO | ID: {doc_id} | Documento: {doc_name} {time_str} | {error_message}")

    # Método adicional para rastrear APIs/endpoints
    @staticmethod
    def log_api_call(endpoint: str, method: str, doc_id: str = None, doc_name: str = None) -> None:
        """Log de chamada à API"""
        doc_info = f"| ID: {doc_id} | Documento: {doc_name}" if doc_id and doc_name else ""
        logger.info(f"🌐 API {method} | Endpoint: {endpoint} {doc_info}")
        
    # Método para logging de classificação de documentos
    @staticmethod
    def log_classification(doc_id: str, doc_name: str, doc_type: str, confidence: float = None, elapsed_time: float = None) -> None:
        """Log de classificação de documento"""
        conf_str = f"| Confiança: {confidence:.2f}" if confidence is not None else ""
        time_str = f"| Tempo: {elapsed_time:.3f}s" if elapsed_time is not None else ""
        logger.info(f"🏷️ CLASSIFICAÇÃO | ID: {doc_id} | Documento: {doc_name} | Tipo: {doc_type} {conf_str} {time_str}")