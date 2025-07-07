#!/usr/bin/env python3
"""
Script de teste para verificar se o Docling está funcionando com CPU
"""
import requests
import json
import os
from pathlib import Path

# Configurações
API_BASE_URL = "http://localhost:8000"
API_KEY = "etl_90Vob9jH5yGzPQj-gTj51Hk71YESMO3nM-mJrWdCSrg"  # Chave do superadmin


def test_docling_cpu():
    """Testa o processamento com Docling usando CPU"""

    print("🧪 Testando Docling com CPU...")

    # 1. Verificar se a API está rodando
    print("🔍 Verificando se a API está rodando...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health")
        if response.status_code == 200:
            print("✅ API está rodando")
        else:
            print("❌ API não está respondendo")
            return False
    except Exception as e:
        print(f"❌ Erro ao conectar com a API: {e}")
        return False

    # 2. Verificar se o Document Processor está funcionando
    print("🔍 Verificando Document Processor...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health/detailed")
        if response.status_code == 200:
            health_data = response.json()
            if health_data.get("services", {}).get("document_processor") == "healthy":
                print("✅ Document Processor está funcionando")
            else:
                print("❌ Document Processor não está funcionando")
                return False
        else:
            print("❌ Erro ao verificar health detailed")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar health: {e}")
        return False

    # 3. Criar um arquivo de teste simples
    print("📝 Criando arquivo de teste...")
    test_content = """
    Este é um documento de teste para verificar se o Docling está funcionando.
    
    Informações importantes:
    - Nome: Documento de Teste
    - Data: 2025-06-26
    - Tipo: Teste de Funcionamento
    - Status: Em processamento
    
    Este documento contém texto simples para testar a extração.
    """

    test_file_path = "teste_docling.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_content)

    print(f"✅ Arquivo de teste criado: {test_file_path}")

    # 4. Fazer upload e processar o documento
    print("📤 Fazendo upload do documento...")
    try:
        with open(test_file_path, "rb") as f:
            files = {"arquivo": (test_file_path, f, "text/plain")}
            headers = {"Authorization": f"Bearer {API_KEY}"}

            response = requests.post(
                f"{API_BASE_URL}/api/v1/processar",
                files=files,
                headers=headers
            )

        if response.status_code == 200:
            result = response.json()
            print("✅ Documento processado com sucesso!")
            print(f"📊 Status: {result.get('status')}")
            print(f"🆔 ID: {result.get('id')}")

            if result.get('texto_extraido'):
                print(f"📄 Texto extraído: {result['texto_extraido'][:100]}...")
            else:
                print("⚠️ Nenhum texto extraído")

            if result.get('tipo_documento'):
                print(f"🏷️ Tipo: {result['tipo_documento']}")
            else:
                print("⚠️ Tipo não identificado")

        else:
            print(f"❌ Erro no processamento: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Erro ao processar documento: {e}")
        return False

    # 5. Limpar arquivo de teste
    try:
        os.remove(test_file_path)
        print(f"🧹 Arquivo de teste removido: {test_file_path}")
    except:
        pass

    print("\n🎉 Teste concluído com sucesso!")
    print("✅ Docling está funcionando com CPU!")
    return True


if __name__ == "__main__":
    test_docling_cpu()
