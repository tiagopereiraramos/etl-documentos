#!/usr/bin/env python3
"""
Teste do Docling com suporte a imagens e fallback
"""
import requests
import json
import time
import os
from pathlib import Path

# Configurações
API_BASE_URL = "http://localhost:8000"
API_KEY = "etl_90Vob9jH5yGzPQj-gTj51Hk71YESMO3nM-mJrWdCSrg"  # Chave do superadmin


def test_docling_imagens():
    """Testa o Docling com diferentes tipos de arquivo incluindo imagens"""

    print("🧪 Testando Docling com suporte a imagens e fallback")
    print("=" * 60)

    # 1. Verificar se a API está funcionando
    print("1️⃣ Verificando status da API...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health")
        if response.status_code == 200:
            print("✅ API está funcionando")
        else:
            print(f"❌ API não está funcionando: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao conectar com a API: {e}")
        return False

    # 2. Verificar providers disponíveis
    print("\n2️⃣ Verificando providers disponíveis...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health/detailed")
        if response.status_code == 200:
            data = response.json()
            providers = data.get("providers_status", {})
            print("📋 Providers disponíveis:")
            for provider, status in providers.items():
                print(f"   - {provider}: {'✅' if status else '❌'}")
        else:
            print(f"❌ Erro ao obter detalhes da API: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao verificar providers: {e}")

    # 3. Testar com arquivo de texto (deve funcionar com Docling)
    print("\n3️⃣ Testando com arquivo de texto (.txt)...")
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
            print("✅ Arquivo .txt processado com sucesso!")
            print(f"📊 Status: {result.get('status_processamento')}")
            print(f"🆔 ID: {result.get('id')}")
            print(f"🔧 Provider: {result.get('provider_extracao', 'N/A')}")

            if result.get('texto_extraido'):
                print(f"📄 Texto extraído: {result['texto_extraido'][:100]}...")
            else:
                print("⚠️ Nenhum texto extraído")
        else:
            print(f"❌ Erro no processamento .txt: {response.status_code}")
            print(f"Resposta: {response.text}")

    except Exception as e:
        print(f"❌ Erro ao processar arquivo .txt: {e}")

    # 4. Testar com arquivo PDF (deve funcionar com Docling)
    print("\n4️⃣ Testando com arquivo PDF (.pdf)...")

    # Criar um PDF simples para teste
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        pdf_path = "teste_docling.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "Documento PDF de Teste")
        c.drawString(100, 730, "Este é um PDF criado para testar o Docling")
        c.drawString(100, 710, "Data: 2025-06-26")
        c.drawString(100, 690, "Tipo: Teste de Funcionamento")
        c.save()

        with open(pdf_path, "rb") as f:
            files = {"arquivo": (pdf_path, f, "application/pdf")}
            headers = {"Authorization": f"Bearer {API_KEY}"}

            response = requests.post(
                f"{API_BASE_URL}/api/v1/processar",
                files=files,
                headers=headers
            )

        if response.status_code == 200:
            result = response.json()
            print("✅ Arquivo .pdf processado com sucesso!")
            print(f"📊 Status: {result.get('status_processamento')}")
            print(f"🆔 ID: {result.get('id')}")
            print(f"🔧 Provider: {result.get('provider_extracao', 'N/A')}")

            if result.get('texto_extraido'):
                print(f"📄 Texto extraído: {result['texto_extraido'][:100]}...")
            else:
                print("⚠️ Nenhum texto extraído")
        else:
            print(f"❌ Erro no processamento .pdf: {response.status_code}")
            print(f"Resposta: {response.text}")

    except ImportError:
        print("⚠️ reportlab não instalado, pulando teste PDF")
    except Exception as e:
        print(f"❌ Erro ao processar arquivo .pdf: {e}")

    # 5. Testar com arquivo de imagem (deve funcionar com Docling)
    print("\n5️⃣ Testando com arquivo de imagem (.png)...")

    # Criar uma imagem simples para teste
    try:
        from PIL import Image, ImageDraw, ImageFont

        img_path = "teste_docling.png"
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)

        # Adicionar texto à imagem
        try:
            font = ImageFont.truetype("Arial", 20)
        except:
            font = ImageFont.load_default()

        draw.text((20, 20), "Documento de Imagem de Teste",
                  fill='black', font=font)
        draw.text((20, 50), "Este é um PNG criado para testar o Docling",
                  fill='black', font=font)
        draw.text((20, 80), "Data: 2025-06-26", fill='black', font=font)
        draw.text((20, 110), "Tipo: Teste de Funcionamento",
                  fill='black', font=font)

        img.save(img_path)

        with open(img_path, "rb") as f:
            files = {"arquivo": (img_path, f, "image/png")}
            headers = {"Authorization": f"Bearer {API_KEY}"}

            response = requests.post(
                f"{API_BASE_URL}/api/v1/processar",
                files=files,
                headers=headers
            )

        if response.status_code == 200:
            result = response.json()
            print("✅ Arquivo .png processado com sucesso!")
            print(f"📊 Status: {result.get('status_processamento')}")
            print(f"🆔 ID: {result.get('id')}")
            print(f"🔧 Provider: {result.get('provider_extracao', 'N/A')}")

            if result.get('texto_extraido'):
                print(f"📄 Texto extraído: {result['texto_extraido'][:100]}...")
            else:
                print("⚠️ Nenhum texto extraído")
        else:
            print(f"❌ Erro no processamento .png: {response.status_code}")
            print(f"Resposta: {response.text}")

    except ImportError:
        print("⚠️ PIL não instalado, pulando teste de imagem")
    except Exception as e:
        print(f"❌ Erro ao processar arquivo .png: {e}")

    # 6. Limpar arquivos de teste
    print("\n6️⃣ Limpando arquivos de teste...")
    for file_path in ["teste_docling.txt", "teste_docling.pdf", "teste_docling.png"]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ Removido: {file_path}")
            except Exception as e:
                print(f"⚠️ Erro ao remover {file_path}: {e}")

    print("\n✅ Teste concluído!")
    return True


if __name__ == "__main__":
    test_docling_imagens()
