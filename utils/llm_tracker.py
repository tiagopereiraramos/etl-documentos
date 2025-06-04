import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from utils.logging import get_logger

# Obter logger configurado para este módulo
logger = get_logger("llm_tracker")

class LLMUsageTracker:
    """
    Rastreador de uso e custos de modelos LLM.
    Mantém contadores, estatísticas de tokens e logs detalhados para análise de custos.
    """
    
    # Preços atualizados conforme a página de pricing da OpenAI
    PRICING = {
        # GPT-4
        "gpt-4o": {"input": 0.01, "output": 0.03},
        "gpt-4o-mini": {"input": 0.005, "output": 0.015},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-32k": {"input": 0.06, "output": 0.12},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-4-vision-preview": {"input": 0.01, "output": 0.03},
        
        # GPT-3.5
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
        "gpt-3.5-turbo-instruct": {"input": 0.0015, "output": 0.002},
        
        # Fine-tuned models
        "ft:gpt-3.5-turbo": {"input": 0.003, "output": 0.006},
        "ft:gpt-4": {"input": 0.06, "output": 0.12},
        "ft:gpt-4-turbo": {"input": 0.03, "output": 0.06},
        
        # Azure OpenAI (mesmos preços que OpenAI, mas pode ser personalizado)
        "azure-gpt-4": {"input": 0.03, "output": 0.06},
        "azure-gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        
        # Claude (Anthropic)
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "claude-2": {"input": 0.01, "output": 0.03},
        "claude-instant-1": {"input": 0.0015, "output": 0.0015},
        
        # Embedding Models
        "text-embedding-3-small": {"input": 0.00013, "output": 0.0},
        "text-embedding-3-large": {"input": 0.00075, "output": 0.0},
        "text-embedding-ada-002": {"input": 0.0001, "output": 0.0},
        
        # Llama (Meta)
        "llama-3": {"input": 0.0007, "output": 0.0007},
        "llama-2": {"input": 0.0005, "output": 0.0005},
        
        # Mistral
        "mistral-medium": {"input": 0.002, "output": 0.006},
        "mistral-small": {"input": 0.0008, "output": 0.0024},
        "mistral-large": {"input": 0.008, "output": 0.024},
        
        # Defaults
        "default": {"input": 0.0015, "output": 0.002}
    }
    
    # Aproximação de custo para modelos locais por 1k tokens
    # Baseado em hardware típico para execução
    LOCAL_MODEL_COSTS = {
        "local-small": 0.0001,  # ~1B params
        "local-medium": 0.0005, # ~7B params
        "local-large": 0.002,   # ~13B+ params
        "default": 0.001
    }
    
    def __init__(self, log_dir: str = "./logs", persist_interval: int = 60):
        """
        Inicializa o rastreador de uso de LLMs.
        
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
        self.usage_dir = self.log_dir / "llm_usage"
        self.usage_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo para métricas agregadas
        self.metrics_file = self.usage_dir / "llm_usage_metrics.json"
        
        # Inicializar contadores
        self.usage = {
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "success_calls": 0,
            "failed_calls": 0,
            "models_used": {},
            "estimated_cost": 0.0,
            "calls_log": [],
            "last_update": datetime.now().isoformat()
        }
        
        # Carregar contadores existentes se disponíveis
        self.load_metrics()
        
        logger.info(f"LLMUsageTracker inicializado. Session ID: {self.session_id}")
    
    def load_metrics(self) -> None:
        """Carrega métricas existentes do disco se disponíveis."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    saved_metrics = json.load(f)
                    
                    # Atualizar apenas contadores agregados, mantendo calls_log da sessão atual
                    calls_current = self.usage.get("calls_log", [])
                    self.usage.update(saved_metrics)
                    self.usage["calls_log"] = calls_current
                    
                    logger.info(f"Métricas de uso de LLMs carregadas: {self.usage['total_calls']} chamadas, " +
                             f"{self.usage['total_tokens']} tokens, ${self.usage['estimated_cost']:.2f} custo estimado")
        except Exception as e:
            logger.error(f"Erro ao carregar métricas de uso de LLMs: {str(e)}")
    
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
                metrics_to_save["calls_log"] = f"{len(self.usage['calls_log'])} chamadas"
                
                with open(self.metrics_file, 'w') as f:
                    json.dump(metrics_to_save, f, indent=2)
                
                # Salvar detalhes de chamadas em arquivo da sessão atual
                session_file = self.usage_dir / f"llm_usage_session_{self.session_id}.json"
                with open(session_file, 'w') as f:
                    json.dump({
                        "session_id": self.session_id,
                        "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                        "calls": self.usage["calls_log"]
                    }, f, indent=2)
                
                self.last_persist_time = current_time
                logger.debug(f"Métricas de uso de LLMs persistidas em {self.metrics_file}")
            except Exception as e:
                logger.error(f"Erro ao persistir métricas de uso de LLMs: {str(e)}")
    
    def record_usage(self, 
                     call_id: str, 
                     model: str, 
                     input_tokens: int, 
                     output_tokens: int,
                     success: bool, 
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra o uso de uma chamada LLM.
        
        Args:
            call_id: ID da chamada LLM
            model: Nome do modelo usado (ex: "gpt-4")
            input_tokens: Número de tokens de entrada (prompt)
            output_tokens: Número de tokens de saída (completions)
            success: Se a chamada foi bem-sucedida
            metadata: Metadados adicionais da chamada
        """
        # Normalizar nome do modelo para cálculos de custo
        model_key = model.lower()
        
        # Atualizar contadores
        self.usage["total_calls"] += 1
        self.usage["total_input_tokens"] += input_tokens
        self.usage["total_output_tokens"] += output_tokens
        self.usage["total_tokens"] += (input_tokens + output_tokens)
        
        if success:
            self.usage["success_calls"] += 1
        else:
            self.usage["failed_calls"] += 1
        
        # Atualizar contadores de modelo
        if model_key in self.usage["models_used"]:
            self.usage["models_used"][model_key]["count"] += 1
            self.usage["models_used"][model_key]["input_tokens"] += input_tokens
            self.usage["models_used"][model_key]["output_tokens"] += output_tokens
        else:
            self.usage["models_used"][model_key] = {
                "count": 1, 
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        
        # Calcular custo estimado
        estimated_cost = 0
        if "local" in model_key:
            # Modelo local
            local_model_type = "default"
            for key in self.LOCAL_MODEL_COSTS.keys():
                if key in model_key:
                    local_model_type = key
                    break
            
            price_per_1k = self.LOCAL_MODEL_COSTS.get(local_model_type, self.LOCAL_MODEL_COSTS["default"])
            estimated_cost = (input_tokens + output_tokens) * price_per_1k / 1000
        else:
            # Modelo API
            price_model = "default"
            for key in self.PRICING.keys():
                if key in model_key:
                    price_model = key
                    break
            
            prices = self.PRICING.get(price_model, self.PRICING["default"])
            input_cost = input_tokens * prices["input"] / 1000
            output_cost = output_tokens * prices["output"] / 1000
            estimated_cost = input_cost + output_cost
        
        self.usage["estimated_cost"] += estimated_cost
        
        # Registrar detalhes da chamada
        call_record = {
            "call_id": call_id,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "success": success,
            "estimated_cost": round(estimated_cost, 4),
            "session_id": self.session_id
        }
        
        # Adicionar metadados se fornecidos
        if metadata:
            call_record["metadata"] = metadata
            
        self.usage["calls_log"].append(call_record)
        
        # Log da chamada com emoji para visualização rápida
        status = "sucesso" if success else "falha"
        emoji = "🟢" if success else "🔴"
        
        # Extrair ID do documento se existir nos metadados
        doc_info = ""
        if metadata and "doc_id" in metadata and "doc_name" in metadata:
            doc_info = f" | Doc: {metadata['doc_name']} ({metadata['doc_id']})"
        
        logger.info(
            f"{emoji} LLM {model} | {status} | {input_tokens} in | " + 
            f"{output_tokens} out | Custo: ${estimated_cost:.4f}{doc_info}"
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
        success_rate = (self.usage["success_calls"] / self.usage["total_calls"] * 100) if self.usage["total_calls"] > 0 else 0
        avg_input = self.usage["total_input_tokens"] / self.usage["total_calls"] if self.usage["total_calls"] > 0 else 0
        avg_output = self.usage["total_output_tokens"] / self.usage["total_calls"] if self.usage["total_calls"] > 0 else 0
        avg_tokens = (avg_input + avg_output)
        
        # Resumo de uso por modelo
        models_summary = []
        for model, data in self.usage["models_used"].items():
            # Calcular custo para este modelo específico
            if "local" in model:
                local_model_type = "default"
                for key in self.LOCAL_MODEL_COSTS.keys():
                    if key in model:
                        local_model_type = key
                        break
                
                price_per_1k = self.LOCAL_MODEL_COSTS.get(local_model_type, self.LOCAL_MODEL_COSTS["default"])
                cost = (data["input_tokens"] + data["output_tokens"]) * price_per_1k / 1000
            else:
                price_model = "default"
                for key in self.PRICING.keys():
                    if key in model:
                        price_model = key
                        break
                
                prices = self.PRICING.get(price_model, self.PRICING["default"])
                input_cost = data["input_tokens"] * prices["input"] / 1000
                output_cost = data["output_tokens"] * prices["output"] / 1000
                cost = input_cost + output_cost
                
            models_summary.append({
                "model": model,
                "calls": data["count"],
                "input_tokens": data["input_tokens"],
                "output_tokens": data["output_tokens"],
                "total_tokens": data["input_tokens"] + data["output_tokens"],
                "cost": round(cost, 2)
            })
        
        # Ordenar modelos por custo
        models_summary.sort(key=lambda x: x["cost"], reverse=True)
        
        return {
            "summary": {
                "total_calls": self.usage["total_calls"],
                "success_calls": self.usage["success_calls"],
                "failed_calls": self.usage["failed_calls"],
                "success_rate": f"{success_rate:.1f}%",
                "total_input_tokens": self.usage["total_input_tokens"],
                "total_output_tokens": self.usage["total_output_tokens"],
                "total_tokens": self.usage["total_tokens"],
                "average_input_tokens": round(avg_input, 1),
                "average_output_tokens": round(avg_output, 1),
                "average_tokens_per_call": round(avg_tokens, 1),
                "total_cost_usd": round(self.usage["estimated_cost"], 2)
            },
            "models": models_summary,
            "recent_calls": self.usage["calls_log"][-10:] if self.usage["calls_log"] else [],
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
        
        # Filtrar chamadas recentes
        recent_calls = [call for call in self.usage["calls_log"] 
                      if call["timestamp"] > cutoff_iso]
        
        # Criar CSV
        csv_path = self.usage_dir / f"llm_usage_export_{datetime.now().strftime('%Y%m%d')}.csv"
        try:
            with open(csv_path, 'w') as f:
                f.write("call_id,timestamp,model,input_tokens,output_tokens,total_tokens,success,cost,session_id\n")
                for call in recent_calls:
                    f.write(f"{call['call_id']},{call['timestamp']},{call['model']}," + 
                           f"{call['input_tokens']},{call['output_tokens']},{call['total_tokens']}," + 
                           f"{call['success']},{call['estimated_cost']},{call['session_id']}\n")
            
            logger.info(f"Dados de uso de LLMs exportados para {csv_path}")
            return str(csv_path)
        except Exception as e:
            logger.error(f"Erro ao exportar dados para CSV: {str(e)}")
            return ""
    
    def close(self):
        """Finaliza o rastreador de uso, persistindo métricas finais."""
        duration = time.time() - self.start_time
        logger.info(
            f"📊 Sessão LLM finalizada | Duração: {duration:.1f}s | " + 
            f"Chamadas: {self.usage['total_calls']} | " + 
            f"Tokens: {self.usage['total_tokens']} | " +
            f"Custo: ${self.usage['estimated_cost']:.2f}"
        )
        self.persist_metrics(force=True)