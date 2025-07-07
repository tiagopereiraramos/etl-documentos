#!/usr/bin/env python3
"""
Teste simples para verificar se os providers estão funcionando
"""
import asyncio
import os
from app.providers.base import GerenciadorProvedores
from app.providers.azure_provider import AzureDocumentIntelligenceProvider, AzureOpenAIProvider
from app.providers.aws_provider import AWSTextractProvider, AWSBedrockProvider
from app.providers.docling_provider import DoclingProvider
from app.core.config import settings


async def test_providers():
    """Testa a inicialização dos providers"""
    print("🚀 Testando inicialização dos providers")
    print("=" * 50)

    gerenciador = GerenciadorProvedores()

    # Testar Docling (local)
    print("\n🔍 Testando Docling...")
    try:
        docling = DoclingProvider()
        gerenciador.adicionar_provedor_extracao(docling)
        print(f"✅ Docling: {docling.validar_configuracao()}")
    except Exception as e:
        print(f"❌ Docling: {e}")

    # Testar Azure Document Intelligence
    print("\n🔍 Testando Azure Document Intelligence...")
    try:
        azure_extracao = AzureDocumentIntelligenceProvider(
            endpoint=os.getenv("AZURE_ENDPOINT", ""),
            api_key=os.getenv("AZURE_KEY", "")
        )
        gerenciador.adicionar_provedor_extracao(azure_extracao)
        print(
            f"✅ Azure Document Intelligence: {azure_extracao.validar_configuracao()}")
    except Exception as e:
        print(f"❌ Azure Document Intelligence: {e}")

    # Testar Azure OpenAI
    print("\n🔍 Testando Azure OpenAI...")
    try:
        azure_llm = AzureOpenAIProvider(
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_KEY", ""),
            modelo=os.getenv("AZURE_OPENAI_MODEL", "gpt-4")
        )
        gerenciador.adicionar_provedor_llm(azure_llm)
        print(f"✅ Azure OpenAI: {azure_llm.validar_configuracao()}")
    except Exception as e:
        print(f"❌ Azure OpenAI: {e}")

    # Testar AWS Textract
    print("\n🔍 Testando AWS Textract...")
    try:
        aws_extracao = AWSTextractProvider(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            region=os.getenv("AWS_REGION", "us-east-1")
        )
        gerenciador.adicionar_provedor_extracao(aws_extracao)
        print(f"✅ AWS Textract: {aws_extracao.validar_configuracao()}")
    except Exception as e:
        print(f"❌ AWS Textract: {e}")

    # Testar AWS Bedrock
    print("\n🔍 Testando AWS Bedrock...")
    try:
        aws_llm = AWSBedrockProvider(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            modelo=os.getenv("AWS_BEDROCK_MODEL",
                             "anthropic.claude-3-sonnet-20240229-v1:0"),
            region=os.getenv("AWS_REGION", "us-east-1")
        )
        gerenciador.adicionar_provedor_llm(aws_llm)
        print(f"✅ AWS Bedrock: {aws_llm.validar_configuracao()}")
    except Exception as e:
        print(f"❌ AWS Bedrock: {e}")

    # Mostrar informações dos providers
    print("\n📊 Informações dos providers:")
    print("=" * 50)
    info = gerenciador.obter_info_provedores()

    print("\n🔧 Providers de Extração:")
    for provider in info["extracao"]:
        status = "✅ Configurado" if provider['configurado'] else "❌ Não configurado"
        print(f"  - {provider['nome']}: {status}")
        if provider['configurado']:
            # Mostrar apenas os primeiros 5
            formatos = ', '.join(provider['formatos_suportados'][:5])
            if len(provider['formatos_suportados']) > 5:
                formatos += f" (+{len(provider['formatos_suportados']) - 5} mais)"
            print(f"    Formatos: {formatos}")

    print("\n🤖 Providers LLM:")
    for provider in info["llm"]:
        status = "✅ Configurado" if provider['configurado'] else "❌ Não configurado"
        print(f"  - {provider['nome']}: {status}")
        if provider['configurado']:
            print(f"    Modelo: {provider['modelo']}")

    print(f"\n📈 Total de providers:")
    print(f"  - Extração: {len(gerenciador.listar_provedores_extracao())}")
    print(f"  - LLM: {len(gerenciador.listar_provedores_llm())}")

    # Testar seleção de provider por formato
    print(f"\n🔍 Teste de seleção por formato:")
    formatos_teste = [".pdf", ".docx", ".jpg", ".txt"]
    for formato in formatos_teste:
        provider = gerenciador.obter_provedor_extracao_disponivel(formato)
        if provider:
            print(f"  - {formato}: {provider.nome}")
        else:
            print(f"  - {formato}: Nenhum provider disponível")


if __name__ == "__main__":
    asyncio.run(test_providers())
