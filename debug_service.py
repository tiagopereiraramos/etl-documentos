
#!/usr/bin/env python3
"""
Script para debug e teste de serviços específicos
"""
import asyncio
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

import app.core.config as config
from app.core.logging import obter_logger
from app.services.document_processor import DocumentProcessor
from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionService
from app.providers.docling_provider import ProvedorDocling
from app.providers.azure_provider import ProvedorAzure

logger = obter_logger(__name__)

async def debug_classification_service():
    """Debug do serviço de classificação"""
    logger.info("🔍 Testando Serviço de Classificação")
    
    service = ClassificationService()
    
    # Texto de teste
    texto_teste = """
    BANCO DO BRASIL S.A.
    Comprovante de Transferência
    
    Data: 15/01/2024
    Valor: R$ 1.500,00
    Conta Origem: 12345-6
    Agência: 1234
    """
    
    resultado = await service.classificar_documento(texto_teste)
    logger.info(f"Resultado da classificação: {resultado}")
    
    return resultado

async def debug_extraction_service():
    """Debug do serviço de extração"""
    logger.info("🔍 Testando Serviço de Extração")
    
    service = ExtractionService()
    
    # Teste com documento fictício
    texto_teste = """
    BANCO DO BRASIL S.A.
    Comprovante de Transferência
    
    Data: 15/01/2024
    Valor: R$ 1.500,00
    Beneficiário: João Silva
    CPF: 123.456.789-00
    Conta Destino: 98765-4
    Agência: 5678
    Código de Autenticação: ABC123456789
    """
    
    resultado = await service.extrair_dados(
        texto_documento=texto_teste,
        tipo_documento="Comprovante Bancário"
    )
    
    logger.info(f"Dados extraídos: {resultado}")
    return resultado

async def debug_providers():
    """Debug dos provedores de extração"""
    logger.info("🔍 Testando Provedores de Extração")
    
    # Teste Docling
    if config.DOCLING_ENABLED:
        logger.info("Testando Provedor Docling...")
        docling = ProvedorDocling()
        logger.info(f"Docling configurado: {docling.nome}")
    
    # Teste Azure
    if config.AZURE_ENABLED:
        logger.info("Testando Provedor Azure...")
        azure = ProvedorAzure()
        logger.info(f"Azure configurado: {azure.nome}")r.info(f"Azure configurado: {azure.nome}")

async def debug_full_pipeline():
    """Debug do pipeline completo"""
    logger.info("🔍 Testando Pipeline Completo")
    
    processor = DocumentProcessor()
    
    # Simular arquivo de teste
    arquivo_teste = "test_document.txt"
    conteudo_teste = b"""
    BANCO DO BRASIL S.A.
    Comprovante de Transferencia
    
    Data da Operacao: 15/01/2024
    Valor: R$ 2.500,00
    Beneficiario: Maria Santos
    CPF: 987.654.321-00
    Conta Destino: 11111-2
    Agencia: 3333
    Codigo Autenticacao: XYZ987654321
    """
    
    resultado = await processor.processar_documento(
        arquivo_bytes=conteudo_teste,
        nome_arquivo=arquivo_teste
    )
    
    logger.info(f"Resultado do pipeline: {resultado}")
    return resultado

async def main():
    """Função principal de debug"""
    logger.info("🚀 Iniciando Debug do Sistema ETL Documentos")
    
    try:
        # Debug de cada serviço
        await debug_providers()
        await debug_classification_service()
        await debug_extraction_service()
        await debug_full_pipeline()
        
        logger.info("✅ Debug concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro durante debug: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
