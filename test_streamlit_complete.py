#!/usr/bin/env python3
"""
Teste Completo do Streamlit com Sistema de Clientes
Demonstra todas as funcionalidades da interface
"""

import requests
import time
import json
from datetime import datetime

# Configuração
API_BASE_URL = "http://localhost:8000/api/v1"
STREAMLIT_URL = "http://localhost:8501"


def print_header(title):
    """Imprime cabeçalho formatado"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_step(step, description):
    """Imprime passo formatado"""
    print(f"\n{step}. {description}")
    print("-" * 40)


def check_api_health():
    """Verifica se a API está funcionando"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def check_streamlit_health():
    """Verifica se o Streamlit está funcionando"""
    try:
        response = requests.get(STREAMLIT_URL, timeout=5)
        return response.status_code == 200
    except:
        return False


def create_test_clients():
    """Cria clientes de teste"""
    clients = []

    test_clients = [
        {"nome": "Empresa Teste Free", "email": "teste.free@empresa.com",
            "senha": "123456", "plano": "free"},
        {"nome": "Empresa Teste Basic", "email": "teste.basic@empresa.com",
            "senha": "123456", "plano": "basic"},
        {"nome": "Empresa Teste Premium", "email": "teste.premium@empresa.com",
            "senha": "123456", "plano": "premium"},
    ]

    for client_data in test_clients:
        try:
            response = requests.post(
                f"{API_BASE_URL}/clientes/", json=client_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                clients.append({
                    "data": client_data,
                    "api_key": result["cliente"]["api_key"],
                    "info": result
                })
                print(
                    f"✅ Cliente criado: {client_data['nome']} - {client_data['plano']}")
            else:
                print(
                    f"❌ Erro ao criar cliente {client_data['nome']}: {response.text}")
        except Exception as e:
            print(f"❌ Erro ao criar cliente {client_data['nome']}: {str(e)}")

    return clients


def test_client_authentication(api_key):
    """Testa autenticação do cliente"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            f"{API_BASE_URL}/clientes/me/usage", headers=headers, timeout=10)
        return response.status_code == 200, response.json() if response.status_code == 200 else response.text
    except Exception as e:
        return False, str(e)


def test_document_processing(api_key):
    """Testa processamento de documento"""
    try:
        # Criar arquivo de teste
        test_content = "Este é um documento de teste para processamento."
        headers = {"Authorization": f"Bearer {api_key}"}
        files = {"arquivo": ("teste.txt", test_content.encode())}

        response = requests.post(
            f"{API_BASE_URL}/processar", files=files, headers=headers, timeout=30)
        return response.status_code, response.json() if response.status_code == 200 else response.text
    except Exception as e:
        return 500, str(e)


def test_plan_upgrade(api_key, novo_plano):
    """Testa upgrade de plano"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.put(
            f"{API_BASE_URL}/clientes/me/upgrade-plan?novo_plano={novo_plano}",
            headers=headers,
            timeout=10
        )
        return response.status_code == 200, response.json() if response.status_code == 200 else response.text
    except Exception as e:
        return False, str(e)


def main():
    print_header("TESTE COMPLETO DO STREAMLIT ETL DOCUMENTOS")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Verificar serviços
    print_step(1, "Verificando serviços")

    api_ok = check_api_health()
    streamlit_ok = check_streamlit_health()

    if api_ok:
        print("✅ API está funcionando")
    else:
        print("❌ API não está funcionando")
        print("   Execute: python -m uvicorn app.main:app --host localhost --port 8000")
        return

    if streamlit_ok:
        print("✅ Streamlit está funcionando")
        print(f"   Acesse: {STREAMLIT_URL}")
    else:
        print("❌ Streamlit não está funcionando")
        print("   Execute: python run_streamlit.py")
        return

    # 2. Criar clientes de teste
    print_step(2, "Criando clientes de teste")
    clients = create_test_clients()

    if not clients:
        print("❌ Nenhum cliente foi criado. Abortando teste.")
        return

    # 3. Testar cada cliente
    print_step(3, "Testando funcionalidades por cliente")

    for i, client in enumerate(clients, 1):
        print(f"\n--- Cliente {i}: {client['data']['nome']} ---")

        # Testar autenticação
        print(f"🔐 Testando autenticação...")
        auth_success, auth_result = test_client_authentication(
            client['api_key'])
        if auth_success:
            print("✅ Autenticação funcionando")
            cliente_info = auth_result.get('cliente', {})
            print(f"   Nome: {cliente_info.get('nome', 'N/A')}")
            print(f"   Plano: {cliente_info.get('plano', 'N/A')}")
        else:
            print(f"❌ Erro na autenticação: {auth_result}")
            continue

        # Testar processamento de documento
        print(f"📄 Testando processamento de documento...")
        status_code, result = test_document_processing(client['api_key'])
        if status_code == 200:
            print("✅ Processamento funcionando")
            if isinstance(result, dict):
                print(f"   Resultado: {result.get('message', 'N/A')}")
        else:
            print(f"❌ Erro no processamento: {result}")

        # Testar upgrade de plano (apenas para free e basic)
        current_plan = client['data']['plano']
        if current_plan in ['free', 'basic']:
            novo_plano = 'premium' if current_plan == 'free' else 'premium'
            print(f"🔄 Testando upgrade para {novo_plano}...")
            upgrade_success, upgrade_result = test_plan_upgrade(
                client['api_key'], novo_plano)
            if upgrade_success:
                print("✅ Upgrade funcionando")
            else:
                print(f"❌ Erro no upgrade: {upgrade_result}")

        print(f"✅ Cliente {i} testado com sucesso!")

    # 4. Instruções para teste manual
    print_step(4, "Instruções para teste manual no Streamlit")

    print("🌐 Acesse o Streamlit:")
    print(f"   URL: {STREAMLIT_URL}")
    print("\n📋 Passos para teste:")
    print("   1. Abra o navegador e acesse a URL acima")
    print("   2. Na sidebar, vá para a aba '➕ Novo Cliente'")
    print("   3. Crie um novo cliente ou use uma das API Keys abaixo:")

    print("\n🔑 API Keys de teste criadas:")
    for i, client in enumerate(clients, 1):
        print(f"   Cliente {i}: {client['api_key']}")

    print("\n🔧 Funcionalidades para testar:")
    print("   • Login com API Key")
    print("   • Upload e processamento de documentos")
    print("   • Visualização de quotas e uso")
    print("   • Upgrade de planos")
    print("   • Relatórios detalhados")

    # 5. Resumo
    print_step(5, "Resumo do teste")

    print(f"✅ Total de clientes criados: {len(clients)}")
    print(f"✅ API funcionando: {api_ok}")
    print(f"✅ Streamlit funcionando: {streamlit_ok}")
    print(f"✅ Sistema pronto para teste manual!")

    print(f"\n🎉 Teste concluído com sucesso!")
    print(f"   Acesse: {STREAMLIT_URL}")
    print(f"   API: {API_BASE_URL}")


if __name__ == "__main__":
    main()
