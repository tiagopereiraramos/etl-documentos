
#!/usr/bin/env python3
"""
Script para debug e teste do sistema de analytics
"""
import asyncio
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.logging import obter_logger
from app.services.analytics_service import AnalyticsService
from app.services.cost_service import CostService
from app.database.connection import inicializar_banco

logger = obter_logger(__name__)

async def debug_analytics():
    """Debug do serviço de analytics"""
    logger.info("📊 Testando Serviço de Analytics")
    
    # Inicializar banco
    await inicializar_banco()
    
    analytics = AnalyticsService()
    
    # Testar estatísticas por tipo
    stats_tipos = await analytics.obter_estatisticas_por_tipo()
    logger.info(f"Estatísticas por tipo: {stats_tipos}")
    
    # Testar tempos de processamento
    stats_tempo = await analytics.obter_tempos_processamento()
    logger.info(f"Tempos de processamento: {stats_tempo}")
    
    # Testar custos
    stats_custos = await analytics.obter_estatisticas_custos()
    logger.info(f"Estatísticas de custos: {stats_custos}")

async def debug_cost_service():
    """Debug do serviço de custos"""
    logger.info("💰 Testando Serviço de Custos")
    
    cost_service = CostService()
    
    # Simular custos
    custo_openai = cost_service.calcular_custo_openai(
        input_tokens=1000,
        output_tokens=500,
        model="gpt-4o-mini"
    )
    logger.info(f"Custo OpenAI simulado: ${custo_openai:.4f}")
    
    custo_azure = cost_service.calcular_custo_azure(paginas=3)
    logger.info(f"Custo Azure simulado: ${custo_azure:.4f}")

async def main():
    """Função principal de debug analytics"""
    logger.info("🚀 Iniciando Debug do Sistema de Analytics")
    
    try:
        await debug_cost_service()
        await debug_analytics()
        
        logger.info("✅ Debug Analytics concluído!")
        
    except Exception as e:
        logger.error(f"❌ Erro durante debug analytics: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
