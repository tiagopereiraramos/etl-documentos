#!/usr/bin/env python3
"""
Teste de inicialização do DocumentProcessor
"""
from app.core.logging import obter_logger
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


logger = obter_logger(__name__)


def test_document_processor():
    """Testa a inicialização do DocumentProcessor"""
    try:
        logger.info("Tentando importar DocumentProcessorService...")
        from app.services.document_processor import DocumentProcessorService

        logger.info("Criando instância do DocumentProcessorService...")
        processor = DocumentProcessorService()

        logger.info("✅ DocumentProcessorService inicializado com sucesso!")
        logger.info(
            f"Providers de extração: {len(processor.gerenciador_providers.listar_provedores_extracao())}")
        logger.info(
            f"Providers de LLM: {len(processor.gerenciador_providers.listar_provedores_llm())}")

        return True

    except Exception as e:
        logger.error(f"❌ Erro ao inicializar DocumentProcessorService: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_providers():
    """Testa a inicialização dos providers individualmente"""
    try:
        logger.info("Testando providers...")

        # Testar Docling
        try:
            from app.providers.docling_provider import DoclingProvider
            docling = DoclingProvider()
            logger.info("✅ Docling provider inicializado")
        except Exception as e:
            logger.error(f"❌ Erro no Docling provider: {e}")

        # Testar Azure
        try:
            from app.providers.azure_provider import AzureDocumentIntelligenceProvider
            from app.core.config import settings
            if settings.azure_endpoint and settings.azure_key:
                azure = AzureDocumentIntelligenceProvider(
                    endpoint=settings.azure_endpoint,
                    api_key=settings.azure_key
                )
                logger.info("✅ Azure provider inicializado")
            else:
                logger.info("⚠️ Azure não configurado")
        except Exception as e:
            logger.error(f"❌ Erro no Azure provider: {e}")

    except Exception as e:
        logger.error(f"❌ Erro geral nos providers: {e}")


if __name__ == "__main__":
    print("=== Teste de Inicialização do DocumentProcessor ===")

    print("\n1. Testando providers...")
    test_providers()

    print("\n2. Testando DocumentProcessor completo...")
    success = test_document_processor()

    if success:
        print("\n✅ Todos os testes passaram!")
    else:
        print("\n❌ Alguns testes falharam!")
