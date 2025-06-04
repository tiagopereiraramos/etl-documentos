import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from utils.logging import get_logger
from utils.document_logging import DocumentTracker

# Obter logger contextualizado
logger = get_logger("azure_tracker")

class AzureUsageTracker:
    """
    Rastreador de uso e custos de APIs Azure, com foco em Document Intelligence.
    Mantém contadores, estatísticas e logs detalhados para análise de custos.
    """
    
    # Preços por página para os serviços do Azure Document Intelligence
    # Valores em USD por página (ou para serviços específicos, conforme especificado)
    PRICING = {
        "prebuilt-layout": 0.005,      # Preço por página para Layout
        "prebuilt-read": 0.005,        # Preço por página para OCR padrão
        "prebuilt-document": 0.05,     # Preço por página para modelo General Document
        "prebuilt-invoice": 0.05,      # Preço por página para modelo de Notas Fiscais
        "prebuilt-receipt": 0.05,      # Preço por página para modelo de Recibos
        "prebuilt-idDocument": 0.05,   # Preço por página para modelo de Documentos de ID
        "prebuilt-businessCard": 0.05, # Preço por página para modelo de Cartões de Visita
        "prebuilt-tax.us.w2": 0.05,    # Preço por página para modelo de W2 (EUA)
        "custom": 0.05,                # Preço por página para modelos personalizados
        "default": 0.005               # Preço padrão (OCR básico)
    }
    
    def __init__(self, log_dir: str = "./logs", persist_interval: int = 60):
        """
        Inicializa o rastreador de uso do Azure.
        
        Args:
            log_dir: Diretório para armazenar logs de uso
            persist_interval: Intervalo em segundos para persistir contadores em disco
        """
        self.session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.start_time = time.time()
        self.log_dir = Path(log_dir)
        self.persist_interval = persist_interval
        self.last_persist_time = time.time()
        
        # Criar diretórios se não existirem
        self.usage_dir = self.log_dir / "azure_usage"
        self.usage_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo para métricas agregadas
        self.metrics_file = self.usage_dir / "azure_usage_metrics.json"
        
        # Inicializar contadores
        self.usage = {
            "total_requests": 0,
            "total_pages": 0,
            "total_size_mb": 0,
            "success_requests": 0,
            "failed_requests": 0,
            "models_used": {},
            "estimated_cost": 0.0,
            "requests_log": [],
            "last_update": datetime.now().isoformat()
        }
        
        # Carregar contadores existentes se disponíveis
        self.load_metrics()
        
        logger.info(f"AzureUsageTracker inicializado. Session ID: {self.session_id}")
    
    def load_metrics(self) -> None:
        """Carrega métricas existentes do disco se disponíveis."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    saved_metrics = json.load(f)
                    
                    # Atualizar apenas contadores agregados, mantendo requests_log da sessão atual
                    requests_current = self.usage.get("requests_log", [])
                    self.usage.update(saved_metrics)
                    self.usage["requests_log"] = requests_current
                    
                    logger.info(
                        f"Métricas de uso do Azure carregadas: {self.usage['total_requests']} solicitações, " +
                        f"{self.usage['total_pages']} páginas, ${self.usage['estimated_cost']:.2f} custo estimado"
                    )
        except Exception as e:
            logger.error(f"Erro ao carregar métricas de uso do Azure: {str(e)}")
    
    def persist_metrics(self, force: bool = False) -> None:
        """
        Persiste métricas em disco.
        
        Args:
            force: Se True, força persistência independente do intervalo
        """
        current_time = time.time()
        if force or (current_time - self.last_persist_time > self.persist_interval):
            try:
                self.usage["last_update"] = datetime.now().isoformat()
                
                # Criar cópia sem logs detalhados para o arquivo de métricas principal
                metrics_to_save = self.usage.copy()
                metrics_to_save["requests_log"] = f"{len(self.usage['requests_log'])} solicitações"
                
                with open(self.metrics_file, 'w') as f:
                    json.dump(metrics_to_save, f, indent=2)
                
                # Salvar detalhes de solicitações em arquivo da sessão atual
                session_file = self.usage_dir / f"azure_usage_session_{self.session_id}.json"
                with open(session_file, 'w') as f:
                    json.dump({
                        "session_id": self.session_id,
                        "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                        "requests": self.usage["requests_log"]
                    }, f, indent=2)
                
                self.last_persist_time = current_time
                logger.debug(f"Métricas de uso do Azure persistidas em {self.metrics_file}")
            except Exception as e:
                logger.error(f"Erro ao persistir métricas de uso do Azure: {str(e)}")
    
    def record_usage(self, 
                     document_id: str, 
                     model: str, 
                     pages: int, 
                     size_bytes: int,
                     success: bool, 
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra o uso de uma chamada ao Azure Document Intelligence.
        
        Args:
            document_id: ID do documento processado
            model: Nome do modelo usado (ex: "prebuilt-layout")
            pages: Número de páginas processadas
            size_bytes: Tamanho do documento em bytes
            success: Se a chamada foi bem-sucedida
            metadata: Metadados adicionais da chamada
        """
        # Normalizar nome do modelo para cálculos de custo
        model_key = model.lower()
        size_mb = size_bytes / (1024 * 1024)
        
        # Atualizar contadores
        self.usage["total_requests"] += 1
        self.usage["total_pages"] += pages
        self.usage["total_size_mb"] += size_mb
        
        if success:
            self.usage["success_requests"] += 1
        else:
            self.usage["failed_requests"] += 1
        
        # Atualizar contadores de modelo
        if model_key in self.usage["models_used"]:
            self.usage["models_used"][model_key]["count"] += 1
            self.usage["models_used"][model_key]["pages"] += pages
            self.usage["models_used"][model_key]["size_mb"] += size_mb
        else:
            self.usage["models_used"][model_key] = {
                "count": 1, 
                "pages": pages,
                "size_mb": size_mb
            }
        
        # Calcular custo estimado
        price_model = "default"
        for key in self.PRICING.keys():
            if key in model_key:
                price_model = key
                break
        
        price_per_page = self.PRICING.get(price_model, self.PRICING["default"])
        estimated_cost = pages * price_per_page
        
        self.usage["estimated_cost"] += estimated_cost
        
        # Registrar detalhes da chamada
        request_record = {
            "document_id": document_id,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "pages": pages,
            "size_mb": round(size_mb, 2),
            "success": success,
            "estimated_cost": round(estimated_cost, 4),
            "session_id": self.session_id
        }
        
        # Adicionar metadados se fornecidos
        if metadata:
            request_record["metadata"] = metadata
            
        self.usage["requests_log"].append(request_record)
        
        # Log da chamada com emoji para visualização rápida
        status = "sucesso" if success else "falha"
        emoji = "🔵" if success else "🔴"
        
        # Extrair nome do documento se existir nos metadados
        doc_name = metadata.get("document_name", document_id) if metadata else document_id
        operation = metadata.get("operation", "processamento") if metadata else "processamento"
        
        logger.info(
            f"{emoji} AZURE {model} | {status} | {operation} | " + 
            f"Doc: {doc_name} | {pages} página(s) | {size_mb:.2f}MB | ${estimated_cost:.4f}"
        )
        
        # Persistir métricas periodicamente
        self.persist_metrics()
    
    def get_usage_report(self) -> Dict[str, Any]:
        """
        Gera um relatório de uso formatado.
        
        Returns:
            Dicionário com estatísticas de uso
        """
        # Calcular métricas adicionais
        success_rate = (self.usage["success_requests"] / self.usage["total_requests"] * 100) if self.usage["total_requests"] > 0 else 0
        avg_pages = self.usage["total_pages"] / self.usage["total_requests"] if self.usage["total_requests"] > 0 else 0
        avg_size = self.usage["total_size_mb"] / self.usage["total_requests"] if self.usage["total_requests"] > 0 else 0
        
        # Resumo de uso por modelo
        models_summary = []
        for model, data in self.usage["models_used"].items():
            # Calcular custo para este modelo específico
            price_model = "default"
            for key in self.PRICING.keys():
                if key in model:
                    price_model = key
                    break
            
            price_per_page = self.PRICING.get(price_model, self.PRICING["default"])
            cost = data["pages"] * price_per_page
                
            models_summary.append({
                "model": model,
                "requests": data["count"],
                "pages": data["pages"],
                "size_mb": round(data["size_mb"], 2),
                "cost": round(cost, 2)
            })
        
        # Ordenar modelos por custo
        models_summary.sort(key=lambda x: x["cost"], reverse=True)
        
        return {
            "summary": {
                "total_requests": self.usage["total_requests"],
                "success_requests": self.usage["success_requests"],
                "failed_requests": self.usage["failed_requests"],
                "success_rate": f"{success_rate:.1f}%",
                "total_pages": self.usage["total_pages"],
                "total_size_mb": round(self.usage["total_size_mb"], 2),
                "average_pages_per_request": round(avg_pages, 1),
                "average_size_mb_per_request": round(avg_size, 2),
                "total_cost_usd": round(self.usage["estimated_cost"], 2)
            },
            "models": models_summary,
            "recent_requests": self.usage["requests_log"][-10:] if self.usage["requests_log"] else [],
            "last_update": self.usage["last_update"]
        }
    
    def export_csv(self, days: int = 30) -> str:
        """
        Exporta dados de uso para CSV.
        
        Args:
            days: Número de dias para incluir no relatório
            
        Returns:
            Caminho para o arquivo CSV
        """
        # Implementação básica para exportação CSV
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()
        
        # Filtrar solicitações recentes
        recent_requests = [req for req in self.usage["requests_log"] 
                        if req["timestamp"] > cutoff_iso]
        
        # Criar CSV
        csv_path = self.usage_dir / f"azure_usage_export_{datetime.now().strftime('%Y%m%d')}.csv"
        try:
            with open(csv_path, 'w') as f:
                f.write("document_id,timestamp,model,pages,size_mb,success,cost,session_id\n")
                for req in recent_requests:
                    f.write(f"{req['document_id']},{req['timestamp']},{req['model']}," + 
                           f"{req['pages']},{req['size_mb']},{req['success']},{req['estimated_cost']},{req['session_id']}\n")
            
            logger.info(f"Dados de uso do Azure exportados para {csv_path}")
            return str(csv_path)
        except Exception as e:
            logger.error(f"Erro ao exportar dados para CSV: {str(e)}")
            return ""
    
    def close(self):
        """Finaliza o rastreador de uso, persistindo métricas finais."""
        duration = time.time() - self.start_time
        logger.info(
            f"📊 Sessão Azure finalizada | Duração: {duration:.1f}s | " + 
            f"Solicitações: {self.usage['total_requests']} | " + 
            f"Páginas: {self.usage['total_pages']} | " +
            f"Custo: ${self.usage['estimated_cost']:.2f}"
        )
        self.persist_metrics(force=True)