#!/usr/bin/env python3
"""
Script de teste para diagnosticar problemas com a chave OpenAI
"""
import os
import json
from openai import OpenAI


def test_openai_key():
    """Testa a chave OpenAI com diferentes cenários"""

    # Obter chave do ambiente
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ ERRO: Variável OPENAI_API_KEY não encontrada")
        return False

    print(f"🔑 Testando chave: {api_key[:20]}...")
    print()

    # Inicializar cliente OpenAI
    client = OpenAI(api_key=api_key)

    # Teste 1: Chamada básica simples
    print("1️⃣ TESTE BÁSICO - Chamada simples")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Olá, este é um teste simples"}],
            temperature=0
        )
        print(f"✅ SUCESSO: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

    print()

    # Teste 2: Chamada similar à classificação
    print("2️⃣ TESTE CLASSIFICAÇÃO - Simulando classificação de documento")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": "Classifique este documento: 'Nota Fiscal de Serviços - Empresa XYZ'"
            }],
            temperature=0
        )
        print(f"✅ SUCESSO: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

    print()

    # Teste 3: Chamada similar à extração qualificada (payload maior)
    print("3️⃣ TESTE EXTRAÇÃO - Simulando extração qualificada")

    prompt_longo = """
    Você é um agente que extrai informações de documentos de **Nota Fiscal de Serviços Eletrônica**. 
    Extraia os seguintes campos formatando no encoding UTF-8:

    - Número da Nota Fiscal: Número sequencial da nota fiscal.
    - Data de Emissão: Data de emissão da nota fiscal.
    - Prestador do Serviço: Dados completos da empresa prestadora.

    Texto do documento:
    NOTA FISCAL DE SERVIÇOS ELETRÔNICA
    Número: 00000039
    Data: 30/06/2025 08:20:48
    Prestador: TPS AUTOMACAO E TECNOLOGIA LTDA
    CNPJ: 50.282.533/0001-81
    
    Responda no seguinte formato JSON:
    {
      "tipo_documento": "Nota Fiscal de Serviços Eletrônica",
      "numero_nota": "...",
      "data_emissao": "...",
      "prestador_servico": {
        "razao_social": "...",
        "cnpj": "..."
      }
    }
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_longo}],
            temperature=0
        )
        print(f"✅ SUCESSO: {response.choices[0].message.content[:200]}...")
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

    print()

    # Teste 4: Teste com HumanMessage (formato usado na extração)
    print("4️⃣ TESTE FORMATO LANGCHAIN - Simulando formato usado no código")
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0
        )

        response = llm.invoke(
            [HumanMessage(content="Teste formato LangChain")])
        print(f"✅ SUCESSO: {response.content}")
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

    print()
    print("🎉 TODOS OS TESTES PASSARAM! A chave OpenAI está funcionando corretamente.")
    return True


def test_environment():
    """Testa o ambiente e configurações"""
    print("🔍 DIAGNÓSTICO DO AMBIENTE")
    print(f"📁 CWD: {os.getcwd()}")
    print(
        f"🔑 OPENAI_API_KEY presente: {'✅' if os.environ.get('OPENAI_API_KEY') else '❌'}")

    # Tentar carregar settings
    try:
        from app.core.config import settings
        print(f"⚙️ Settings carregado: ✅")
        print(f"🤖 Classification model: {settings.llm.classification_model}")
        print(f"🎯 Extraction model: {settings.llm.extraction_model}")
        print(
            f"🔑 Settings API key: {settings.llm.openai_api_key.get_secret_value()[:20]}...")
    except Exception as e:
        print(f"⚙️ Erro ao carregar settings: {e}")

    print()


if __name__ == "__main__":
    print("🧪 TESTE DIAGNÓSTICO DA CHAVE OPENAI")
    print("=" * 50)
    print()

    test_environment()
    test_openai_key()
