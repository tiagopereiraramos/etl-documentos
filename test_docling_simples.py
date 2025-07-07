#!/usr/bin/env python3
"""
Teste simples do Docling
"""
import requests
import json
import os
from pathlib import Path

# Configurações
API_BASE_URL = "http://localhost:8000"
API_KEY = "etl_90Vob9jH5yGzPQj-gTj51Hk71YESMO3nM-mJrWdCSrg"


def test_docling_simples():
    """Teste simples do Docling"""

    print("🧪 Teste simples do Docling")
    print("=" * 40)

    # 1. Criar arquivo de teste simples
    print("1️⃣ Criando arquivo de teste...")
    with open("teste_simples.txt", "w", encoding="utf-8") as f:
        f.write(
            "Este é um documento de teste para verificar se o Docling está funcionando.")

    # 2. Testar processamento
    print("2️⃣ Testando processamento...")

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    with open("teste_simples.txt", "rb") as f:
        files = {"arquivo": ("teste_simples.txt", f, "text/plain")}

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/processar",
                headers=headers,
                files=files
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("✅ Sucesso!")
                print(
                    f"Texto extraído: {result.get('texto_extraido', 'N/A')[:100]}...")
                print(f"Provedor: {result.get('provider_extracao', 'N/A')}")
                print(f"Qualidade: {result.get('qualidade_extracao', 'N/A')}")
            else:
                print(f"❌ Erro: {response.status_code}")
                print(f"Resposta: {response.text}")

        except Exception as e:
            print(f"❌ Erro na requisição: {e}")

    # 3. Limpar
    print("3️⃣ Limpando...")
    if os.path.exists("teste_simples.txt"):
        os.remove("teste_simples.txt")
        print("🗑️ Arquivo removido")

    print("✅ Teste concluído!")


if __name__ == "__main__":
    test_docling_simples()
