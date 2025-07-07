#!/usr/bin/env python3
"""
Script de teste para o serviço de classificação com múltiplos LLMs
"""
from app.core.logging import obter_logger
from app.core.config import settings
from app.services.vector_service import VectorStoreService
from app.services.classification_service import ClassificationService
import asyncio
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))


logger = obter_logger(__name__)


async def test_classification_service():
    """Testa o serviço de classificação"""

    print("🚀 Iniciando teste do serviço de classificação...")

    try:
        # Inicializar serviços
        print("📦 Inicializando serviços...")
        vector_service = VectorStoreService()
        classification_service = ClassificationService(vector_service)

        # Verificar provedores LLM configurados
        providers_info = classification_service.get_llm_providers_info()
        print(f"✅ Provedores LLM configurados: {len(providers_info)}")
        for provider in providers_info:
            print(
                f"   - {provider['nome']}: {provider['modelo']} ({'✅' if provider['configurado'] else '❌'})")

        # Testar classificação com diferentes tipos de documentos
        test_documents = [
            {
                "texto": """
                COMPROVANTE DE TRANSFERÊNCIA
                Banco: Banco do Brasil
                Agência: 1234-5
                Conta: 12345-6
                Valor: R$ 1.500,00
                Data: 15/03/2024
                Tipo: PIX
                Código de Autenticação: ABC123456
                """,
                "tipo_esperado": "Comprovante Bancário"
            },
            {
                "texto": """
                CARTÃO CNPJ
                CNPJ: 12.345.678/0001-95
                Razão Social: EMPRESA TESTE LTDA
                Nome Fantasia: EMPRESA TESTE
                Data de Abertura: 01/01/2020
                CNAE Principal: 6201-5/01
                Natureza Jurídica: 206-2 - LTDA
                Endereço: Rua das Flores, 123, Centro, São Paulo, SP
                Situação Cadastral: ATIVA
                """,
                "tipo_esperado": "Cartão CNPJ"
            },
            {
                "texto": """
                CEI DA OBRA
                Matrícula CEI: 123456789
                Endereço da Obra: Rua da Construção, 456, Bairro Industrial
                Proprietário: João Silva
                CNPJ: 98.765.432/0001-10
                Responsável Técnico: Eng. Maria Santos
                ART: 123456
                Data de Registro: 10/02/2024
                """,
                "tipo_esperado": "CEI da Obra"
            },
            {
                "texto": """
                INSCRIÇÃO MUNICIPAL
                Número: IM-123456
                Razão Social: EMPRESA MUNICIPAL LTDA
                CNPJ: 11.222.333/0001-44
                Endereço: Av. Municipal, 789, Centro
                Atividade Principal: Comércio de Produtos Eletrônicos
                Data de Inscrição: 05/01/2024
                Situação: ATIVA
                """,
                "tipo_esperado": "Inscrição Municipal"
            }
        ]

        print("\n🔍 Testando classificação de documentos...")

        for i, doc in enumerate(test_documents, 1):
            print(f"\n--- Documento {i}: {doc['tipo_esperado']} ---")

            # Classificar documento
            resultado = await classification_service.classify_document(
                document_text=doc['texto'],
                use_adaptive=True,
                confidence_threshold=0.7
            )

            # Exibir resultados
            print(f"   Tipo predito: {resultado.tipo_documento}")
            print(f"   Confiança: {resultado.confianca:.2f}")
            print(f"   Método: {resultado.metodo}")
            print(f"   Provedor: {resultado.provedor_llm}")
            print(f"   Modelo: {resultado.modelo_llm}")
            print(f"   Tempo: {resultado.tempo_processamento:.2f}s")

            # Verificar acerto
            acerto = resultado.tipo_documento == doc['tipo_esperado']
            print(f"   ✅ Acerto: {'SIM' if acerto else 'NÃO'}")

            if resultado.metadados:
                print(f"   Metadados: {resultado.metadados}")

        # Testar tipos suportados
        print(
            f"\n📋 Tipos de documentos suportados ({len(classification_service.get_supported_types())}):")
        for doc_type in classification_service.get_supported_types():
            desc = classification_service.get_type_description(doc_type)
            print(f"   - {doc_type}: {desc[:50]}...")

        print("\n✅ Teste concluído com sucesso!")

    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        logger.error(f"Erro no teste: {e}", exc_info=True)
        return False

    return True


async def test_feedback_system():
    """Testa o sistema de feedback"""

    print("\n🔄 Testando sistema de feedback...")

    try:
        vector_service = VectorStoreService()
        classification_service = ClassificationService(vector_service)

        # Simular feedback
        await classification_service.add_feedback(
            document_text="Este é um documento de teste para feedback",
            predicted_type="Documento Não Classificado",
            correct_type="Comprovante Bancário",
            confidence=0.3
        )

        print("✅ Feedback adicionado com sucesso!")

    except Exception as e:
        print(f"❌ Erro no feedback: {e}")
        logger.error(f"Erro no feedback: {e}", exc_info=True)


if __name__ == "__main__":
    print("🧪 TESTE DO SERVIÇO DE CLASSIFICAÇÃO COM MÚLTIPLOS LLMs")
    print("=" * 60)

    # Verificar configuração
    print(f"🔧 Ambiente: {settings.env}")
    print(f"🔧 Debug: {settings.debug}")

    if settings.llm:
        print(f"🔧 OpenAI Model: {settings.llm.classification_model}")

    if settings.azure_openai_endpoint:
        print(f"🔧 Azure OpenAI: {settings.azure_openai_model}")

    if settings.aws_access_key_id:
        print(f"🔧 AWS Bedrock: {settings.aws_bedrock_model}")

    print("=" * 60)

    # Executar testes
    success = asyncio.run(test_classification_service())
    asyncio.run(test_feedback_system())

    if success:
        print("\n🎉 Todos os testes passaram!")
        sys.exit(0)
    else:
        print("\n💥 Alguns testes falharam!")
        sys.exit(1)
