#!/usr/bin/env python3
"""
Teste do Docling no Docker
"""
import requests
import json
import time
import os
from pathlib import Path

# Configurações
API_BASE_URL = "http://localhost:8000"
API_KEY = "etl_90Vob9jH5yGzPQj-gTj51Hk71YESMO3nM-mJrWdCSrg"


def test_docling_docker():
    """Testa o Docling no ambiente Docker"""

    print("🐳 Testando Docling no Docker")
    print("=" * 50)

    # 1. Verificar se a API está funcionando
    print("1️⃣ Verificando status da API...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health")
        if response.status_code == 200:
            print("✅ API está funcionando")
        else:
            print(f"❌ API não está funcionando: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Erro ao conectar com API: {e}")
        return

    # 2. Criar arquivo de teste
    print("2️⃣ Criando arquivo de teste...")
    with open("teste_docker.txt", "w", encoding="utf-8") as f:
        f.write("Este é um documento de teste para verificar se o Docling está funcionando no Docker sem segmentation fault.")

    # 3. Testar processamento
    print("3️⃣ Testando processamento...")

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    with open("teste_docker.txt", "rb") as f:
        files = {"arquivo": ("teste_docker.txt", f, "text/plain")}

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/processar",
                headers=headers,
                files=files
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                resultado = response.json()
                print("✅ Processamento bem-sucedido!")
                print(
                    f"Texto extraído: {resultado.get('texto_extraido', 'N/A')[:100]}...")
                print(f"Provedor: {resultado.get('provider_extracao', 'N/A')}")
                print(
                    f"Qualidade: {resultado.get('qualidade_extracao', 'N/A')}")
            else:
                print(f"❌ Erro no processamento: {response.text}")

        except Exception as e:
            print(f"❌ Erro na requisição: {e}")

    # 4. Limpar arquivo de teste
    if os.path.exists("teste_docker.txt"):
        os.remove("teste_docker.txt")

    print("4️⃣ Teste concluído!")


if __name__ == "__main__":
    test_docling_docker()
