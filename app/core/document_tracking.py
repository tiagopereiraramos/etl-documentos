
"""
Sistema Unificado de Rastreamento de Documentos
Consolida todos os logs de processamento com persistência em banco
"""
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import uuid
from sqlalchemy.orm import Session

from app.core.logging import obter_logger
from app.models.database import (
    Documento, LogProcessamento, SessaoUso, ConsumoLLM, 
    MetricasPerformance, Cliente
)

logger = obter_logger(__name__)

class DocumentTracker:
    """Sistema unificado de rastreamento de processamento de documentos"""
    
    @staticmethod
    def generate_doc_id() -> str:
        """Gera ID único para documento"""
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def log_processing_start(
        doc_id: str, 
        doc_name: str, 
        file_size: int, 
        client_id: str,
        session_id: str,
        doc_type: str = "unknown",
        db_session: Optional[Session] = None
    ) -> None:
        """Registra início do processamento com persistência em banco"""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "doc_name": doc_name,
                "file_size_bytes": file_size,
                "file_size_kb": round(file_size / 1024, 2),
                "doc_type": doc_type,
                "client_id": client_id,
                "session_id": session_id,
                "status": "processing_started"
            }
            
            logger.info(f"INICIO: Processamento iniciado | ID: {doc_id} | Cliente: {client_id} | "
                       f"Arquivo: {doc_name} | Tamanho: {log_data['file_size_kb']}KB | Tipo: {doc_type}")
            
            # Salvar em arquivo
            DocumentTracker._save_processing_log(doc_id, "start", log_data)
            
            # Salvar em banco de dados
            if db_session:
                DocumentTracker._save_to_database(
                    db_session, doc_id, client_id, doc_name, file_size, doc_type, "start", log_data
                )
            
        except Exception as e:
            logger.error(f"Erro ao registrar início do processamento: {str(e)}")
    
    @staticmethod
    def log_extraction_step(doc_id: str, method: str, success: bool, 
                          extracted_text_length: int = 0, execution_time: float = 0.0,
                          quality_score: float = 0.0, details: Dict[str, Any] = None) -> None:
        """Registra passo de extração"""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "extraction_method": method,
                "success": success,
                "extracted_chars": extracted_text_length,
                "extracted_lines": extracted_text_length // 80 if extracted_text_length > 0 else 0,
                "execution_time_seconds": round(execution_time, 3),
                "quality_score": round(quality_score, 2),
                "details": details or {}
            }
            
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"EXTRAÇÃO {status}: {method} | ID: {doc_id} | "
                       f"Texto: {extracted_text_length} chars | "
                       f"Qualidade: {quality_score:.2f} | Tempo: {execution_time:.3f}s")
            
            DocumentTracker._save_processing_log(doc_id, f"extraction_{method.lower()}", log_data)
            
        except Exception as e:
            logger.error(f"Erro ao registrar extração: {str(e)}")
    
    @staticmethod
    def log_classification_step(doc_id: str, predicted_type: str, confidence: float,
                              method: str, execution_time: float = 0.0,
                              similar_docs: list = None) -> None:
        """Registra classificação"""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "predicted_type": predicted_type,
                "confidence": round(confidence, 3),
                "classification_method": method,
                "execution_time_seconds": round(execution_time, 3),
                "similar_documents_count": len(similar_docs) if similar_docs else 0
            }
            
            logger.info(f"CLASSIFICAÇÃO: {predicted_type} | ID: {doc_id} | "
                       f"Confiança: {confidence:.3f} | Método: {method} | Tempo: {execution_time:.3f}s")
            
            DocumentTracker._save_processing_log(doc_id, "classification", log_data)
            
        except Exception as e:
            logger.error(f"Erro ao registrar classificação: {str(e)}")
    
    @staticmethod
    def log_data_extraction_step(doc_id: str, doc_type: str, extracted_fields: Dict[str, Any],
                               required_fields: list, execution_time: float = 0.0,
                               extraction_quality: float = 0.0) -> None:
        """Registra extração de dados estruturados"""
        try:
            missing_fields = [field for field in required_fields if field not in extracted_fields]
            present_fields = [field for field in required_fields if field in extracted_fields]
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "document_type": doc_type,
                "total_fields_extracted": len(extracted_fields),
                "required_fields_present": len(present_fields),
                "required_fields_missing": len(missing_fields),
                "missing_fields": missing_fields,
                "present_fields": present_fields,
                "extraction_quality": round(extraction_quality, 3),
                "execution_time_seconds": round(execution_time, 3)
            }
            
            logger.info(f"EXTRAÇÃO DADOS: {doc_type} | ID: {doc_id} | "
                       f"Campos: {len(present_fields)}/{len(required_fields)} | "
                       f"Qualidade: {extraction_quality:.3f} | Tempo: {execution_time:.3f}s")
            
            DocumentTracker._save_processing_log(doc_id, "data_extraction", log_data)
            
        except Exception as e:
            logger.error(f"Erro ao registrar extração de dados: {str(e)}")
    
    @staticmethod
    def log_processing_complete(
        doc_id: str, 
        doc_name: str, 
        total_time: float,
        final_method: str, 
        metrics: Dict[str, Any],
        client_id: str = None,
        db_session: Optional[Session] = None
    ) -> None:
        """Registra conclusão do processamento"""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "doc_name": doc_name,
                "status": "completed",
                "total_processing_time": round(total_time, 3),
                "final_extraction_method": final_method,
                "final_metrics": metrics,
                "client_id": client_id
            }
            
            logger.info(f"CONCLUÍDO: Processamento finalizado | ID: {doc_id} | "
                       f"Cliente: {client_id} | Arquivo: {doc_name} | "
                       f"Tempo total: {total_time:.3f}s | Método: {final_method}")
            
            DocumentTracker._save_processing_log(doc_id, "complete", log_data)
            
            # Atualizar banco de dados
            if db_session and client_id:
                DocumentTracker._update_document_completion(
                    db_session, doc_id, total_time, final_method, metrics
                )
            
        except Exception as e:
            logger.error(f"Erro ao registrar conclusão: {str(e)}")
    
    @staticmethod
    def _update_document_completion(
        db_session: Session,
        doc_id: str,
        total_time: float,
        final_method: str,
        metrics: Dict[str, Any]
    ) -> None:
        """Atualiza documento com informações de conclusão"""
        try:
            documento = db_session.query(Documento).filter(Documento.id == doc_id).first()
            
            if documento:
                documento.status_processamento = "sucesso"
                documento.data_processamento = datetime.utcnow()
                documento.tempo_processamento = total_time
                documento.provider_extracao = final_method
                documento.dados_extraidos = metrics.get("extracted_data", {})
                documento.confianca_classificacao = metrics.get("classification_confidence", 0.0)
                documento.qualidade_extracao = metrics.get("extraction_quality", 0.0)
                documento.custo_processamento = metrics.get("cost_info", {}).get("custo_total", 0.0)
                documento.texto_extraido = metrics.get("texto_extraido", "")
                
                # Atualizar sessão
                session_id = metrics.get("session_id")
                if session_id:
                    sessao = db_session.query(SessaoUso).filter(
                        SessaoUso.session_id == session_id
                    ).first()
                    if sessao:
                        sessao.documentos_sucesso += 1
                        sessao.custo_total += documento.custo_processamento or 0.0
                        
                db_session.commit()
                logger.info(f"Documento {doc_id} atualizado no banco com sucesso")
                
        except Exception as e:
            logger.error(f"Erro ao atualizar documento no banco: {str(e)}")
            db_session.rollback()
    
    @staticmethod
    def log_error(doc_id: str, doc_name: str, error_message: str, 
                 elapsed_time: float = 0.0, error_stage: str = "unknown") -> None:
        """Registra erro no processamento"""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "doc_name": doc_name,
                "status": "error",
                "error_message": error_message,
                "error_stage": error_stage,
                "elapsed_time": round(elapsed_time, 3)
            }
            
            logger.error(f"ERRO: Processamento falhou | ID: {doc_id} | "
                        f"Arquivo: {doc_name} | Estágio: {error_stage} | "
                        f"Tempo: {elapsed_time:.3f}s | Erro: {error_message}")
            
            DocumentTracker._save_processing_log(doc_id, "error", log_data)
            
        except Exception as e:
            logger.error(f"Erro ao registrar erro de processamento: {str(e)}")
    
    @staticmethod
    def _save_processing_log(doc_id: str, operation: str, data: Dict[str, Any]) -> None:
        """Salva log em arquivo para auditoria"""
        try:
            logs_dir = Path("logs/document_processing")
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Log por data
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = logs_dir / f"processing_{date_str}.jsonl"
            
            log_entry = {
                "operation": operation,
                "data": data
            }
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"Erro ao salvar log de processamento: {str(e)}")
    
    @staticmethod
    def _save_to_database(
        db_session: Session,
        doc_id: str,
        client_id: str,
        doc_name: str,
        file_size: int,
        doc_type: str,
        operation: str,
        data: Dict[str, Any]
    ) -> None:
        """Salva informações no banco de dados"""
        try:
            # Verificar se documento já existe
            documento = db_session.query(Documento).filter(Documento.id == doc_id).first()
            
            if not documento and operation == "start":
                # Criar novo documento
                documento = Documento(
                    id=doc_id,
                    cliente_id=client_id,
                    nome_arquivo=doc_name,
                    tipo_documento=doc_type,
                    extensao_arquivo=Path(doc_name).suffix.lower(),
                    tamanho_arquivo=file_size,
                    status_processamento="processando",
                    data_upload=datetime.utcnow()
                )
                db_session.add(documento)
                db_session.flush()
            
            # Criar log de processamento
            log_entry = LogProcessamento(
                documento_id=doc_id,
                operacao=operation,
                provider=data.get("provider"),
                status=data.get("status", "success"),
                detalhes=data,
                tempo_execucao=data.get("execution_time", 0.0),
                timestamp=datetime.utcnow()
            )
            db_session.add(log_entry)
            
            # Atualizar sessão de uso
            DocumentTracker._update_session_usage(db_session, client_id, data.get("session_id"))
            
            db_session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao salvar no banco de dados: {str(e)}")
            db_session.rollback()
    
    @staticmethod
    def _update_session_usage(db_session: Session, client_id: str, session_id: str = None) -> None:
        """Atualiza ou cria sessão de uso"""
        try:
            if not session_id:
                return
                
            sessao = db_session.query(SessaoUso).filter(
                SessaoUso.session_id == session_id
            ).first()
            
            if not sessao:
                sessao = SessaoUso(
                    session_id=session_id,
                    cliente_id=client_id,
                    inicio_sessao=datetime.utcnow(),
                    documentos_processados=1
                )
                db_session.add(sessao)
            else:
                sessao.documentos_processados += 1
                
        except Exception as e:
            logger.error(f"Erro ao atualizar sessão de uso: {str(e)}")
    
    @staticmethod
    def get_document_history(doc_id: str) -> list:
        """Recupera histórico completo de um documento"""
        try:
            logs_dir = Path("logs/document_processing")
            if not logs_dir.exists():
                return []
            
            history = []
            
            # Buscar em todos os arquivos de log recentes (últimos 30 dias)
            for log_file in logs_dir.glob("processing_*.jsonl"):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                entry = json.loads(line.strip())
                                if entry.get("data", {}).get("doc_id") == doc_id:
                                    history.append(entry)
                except Exception:
                    continue
            
            # Ordenar por timestamp
            history.sort(key=lambda x: x.get("data", {}).get("timestamp", ""))
            return history
            
        except Exception as e:
            logger.error(f"Erro ao recuperar histórico do documento: {str(e)}")
            return []
