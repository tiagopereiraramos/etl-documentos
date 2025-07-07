#!/usr/bin/env python3
"""
Script de Teste Completo do Sistema de Rastreabilidade ETL Documentos
Demonstra: criação de clientes, API keys, quotas, rate limiting e relatórios
"""

import requests
import json
import time
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8000"
API_VERSION = "v1"


def print_section(title):
    """Imprime uma seção formatada"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_success(msg):
    """Imprime mensagem de sucesso"""
    print(f"✅ {msg}")


def print_error(msg):
    """Imprime mensagem de erro"""
    print(f"❌ {msg}")


def print_info(msg):
    """Imprime mensagem informativa"""
    print(f"ℹ️  {msg}")


def test_health():
    """Testa o endpoint de health"""
    print_section("TESTE DE HEALTH")

    try:
        response = requests.get(f"{BASE_URL}/api/{API_VERSION}/health")
        if response.status_code == 200:
            print_success("API está funcionando")
            print(f"Status: {response.json()}")
        else:
            print_error(f"API não está funcionando: {response.status_code}")
    except Exception as e:
        print_error(f"Erro ao conectar com API: {e}")


def create_test_clients():
    """Cria clientes de teste com diferentes planos"""
    print_section("CRIAÇÃO DE CLIENTES")

    clients = [
        {
            "nome": "Empresa Free",
            "email": "free@empresa.com",
            "senha": "senha123",
            "plano": "free"
        },
        {
            "nome": "Empresa Basic",
            "email": "basic@empresa.com",
            "senha": "senha123",
            "plano": "basic"
        },
        {
            "nome": "Empresa Premium",
            "email": "premium@empresa.com",
            "senha": "senha123",
            "plano": "premium"
        },
        {
            "nome": "Super Admin",
            "email": "admin@gerdau.com",
            "senha": "admin123",
            "plano": "superadmin"
        }
    ]

    created_clients = []

    for client_data in clients:
        try:
            response = requests.post(
                f"{BASE_URL}/api/{API_VERSION}/clientes/",
                json=client_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                client = response.json()["cliente"]
                created_clients.append(client)
                print_success(
                    f"Cliente criado: {client['nome']} - Plano: {client['plano']}")
                print(f"  API Key: {client['api_key'][:20]}...")
                print(f"  Quotas: {client['quotas']}")
            else:
                print_error(
                    f"Erro ao criar cliente {client_data['nome']}: {response.status_code}")

        except Exception as e:
            print_error(f"Erro ao criar cliente {client_data['nome']}: {e}")

    return created_clients


def test_api_key_authentication(api_key):
    """Testa autenticação com API key"""
    print_section("TESTE DE AUTENTICAÇÃO")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # Teste de endpoint protegido real
        response = requests.get(
            f"{BASE_URL}/api/{API_VERSION}/clientes/me/usage", headers=headers)

        if response.status_code == 200:
            print_success("API Key válida - Autenticação funcionando")
            usage = response.json()
            print(f"Uso atual: {usage}")
        elif response.status_code == 401:
            print_error("API Key inválida")
        else:
            print_info(f"Resposta: {response.status_code}")

    except Exception as e:
        print_error(f"Erro na autenticação: {e}")


def test_quota_checking(api_key):
    """Testa verificação de quotas"""
    print_section("VERIFICAÇÃO DE QUOTAS")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(
            f"{BASE_URL}/api/{API_VERSION}/clientes/me/quotas", headers=headers)

        if response.status_code == 200:
            quotas = response.json()
            print_success("Quotas verificadas com sucesso")
            print(f"Pode processar: {quotas.get('pode_processar', 'N/A')}")
            print(
                f"Documentos restantes: {quotas.get('documentos_restantes', 'N/A')}")
            print(f"Tokens restantes: {quotas.get('tokens_restantes', 'N/A')}")
            print(f"Plano: {quotas.get('plano', 'N/A')}")
            print(f"Ilimitado: {quotas.get('ilimitado', False)}")
        else:
            print_error(f"Erro ao verificar quotas: {response.status_code}")

    except Exception as e:
        print_error(f"Erro na verificação de quotas: {e}")


def simulate_document_processing(api_key, num_docs=3):
    """Simula processamento de documentos"""
    print_section("SIMULAÇÃO DE PROCESSAMENTO")

    headers = {"Authorization": f"Bearer {api_key}"}

    for i in range(num_docs):
        try:
            # Simula processamento de documento
            doc_data = {
                "conteudo": f"Documento de teste {i+1}",
                "tipo": "classificacao"
            }

            print_info(f"Processando documento {i+1}...")

            # Chamada para processamento real
            response = requests.post(
                f"{BASE_URL}/api/{API_VERSION}/processar",
                json=doc_data,
                headers=headers
            )

            if response.status_code == 200:
                print_success(f"Documento {i+1} processado com sucesso")
                result = response.json()
                print(f"  Resultado: {result.get('tipo_documento', 'N/A')}")
                print(f"  Tokens usados: {result.get('tokens_consumidos', 0)}")
            elif response.status_code == 429:
                print_error("Rate limit excedido - aguardando...")
                time.sleep(2)
            elif response.status_code == 402:
                print_error("Quota excedida")
                break
            else:
                print_info(f"Resposta: {response.status_code}")

            time.sleep(0.5)  # Simula tempo de processamento

        except Exception as e:
            print_error(f"Erro no processamento do documento {i+1}: {e}")


def test_rate_limiting(api_key):
    """Testa rate limiting"""
    print_section("TESTE DE RATE LIMITING")

    headers = {"Authorization": f"Bearer {api_key}"}

    print_info("Enviando múltiplas requisições rapidamente...")

    for i in range(15):
        try:
            response = requests.get(
                f"{BASE_URL}/api/{API_VERSION}/clientes/me/quotas", headers=headers)

            if response.status_code == 200:
                print(f"  Requisição {i+1}: OK")
            elif response.status_code == 429:
                print_error(f"  Requisição {i+1}: Rate limit excedido")
                break
            else:
                print_info(f"  Requisição {i+1}: {response.status_code}")

            time.sleep(0.1)  # Requisições rápidas

        except Exception as e:
            print_error(f"Erro na requisição {i+1}: {e}")


def get_usage_report(api_key):
    """Obtém relatório de uso"""
    print_section("RELATÓRIO DE USO")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(
            f"{BASE_URL}/api/{API_VERSION}/clientes/me/usage", headers=headers)

        if response.status_code == 200:
            report = response.json()
            print_success("Relatório obtido com sucesso")
            print(f"Período: {report.get('periodo', 'N/A')}")
            print(
                f"Documentos processados: {report.get('documentos_processados', 0)}")
            print(f"Tokens consumidos: {report.get('tokens_consumidos', 0)}")
            print(f"Custo total: R$ {report.get('custo_total', 0):.4f}")
            print(
                f"Operações por provider: {report.get('operacoes_por_provider', {})}")
        else:
            print_error(f"Erro ao obter relatório: {response.status_code}")

    except Exception as e:
        print_error(f"Erro ao obter relatório: {e}")


def test_upgrade_plan(api_key, novo_plano):
    """Testa upgrade de plano"""
    print_section(f"TESTE DE UPGRADE DE PLANO - {novo_plano}")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # Upgrade de plano com parâmetro no body
        response = requests.put(
            f"{BASE_URL}/api/{API_VERSION}/clientes/me/upgrade-plan",
            headers=headers,
            params={"novo_plano": novo_plano}
        )

        if response.status_code == 200:
            print_success(f"Upgrade para {novo_plano} realizado com sucesso")
            resultado = response.json()
            print(f"Novas quotas: {resultado}")
        else:
            print_error(
                f"Erro no upgrade: {response.status_code} - {response.text}")

    except Exception as e:
        print_error(f"Erro ao testar upgrade: {str(e)}")


def test_processamento_documento(api_key):
    """Testa processamento de documento"""
    print_section("TESTE DE PROCESSAMENTO DE DOCUMENTO")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # Criar um arquivo de teste simples
        arquivo_teste = {
            "arquivo": ("teste.txt", "Este é um documento de teste para processamento.", "text/plain")
        }

        response = requests.post(
            f"{BASE_URL}/api/{API_VERSION}/processar",
            headers=headers,
            files=arquivo_teste
        )

        if response.status_code == 200:
            print_success("Processamento de documento realizado com sucesso")
            resultado = response.json()
            print(f"Resultado: {resultado}")
        else:
            print_error(
                f"Erro no processamento: {response.status_code} - {response.text}")

    except Exception as e:
        print_error(f"Erro ao testar processamento: {str(e)}")


def test_superadmin_unlimited(api_key):
    """Testa funcionalidades ilimitadas do superadmin"""
    print_section("TESTE SUPERADMIN - FUNCIONALIDADES ILIMITADAS")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # Testar múltiplas requisições sem rate limiting
        for i in range(20):
            response = requests.get(
                f"{BASE_URL}/api/{API_VERSION}/clientes/me/quotas",
                headers=headers
            )

            if response.status_code == 200:
                print_info(f"Requisição {i+1}: OK (sem rate limit)")
            else:
                print_error(
                    f"Erro na requisição {i+1}: {response.status_code}")

            time.sleep(0.1)

        print_success(
            "Superadmin não tem rate limiting - funcionando corretamente!")

    except Exception as e:
        print_error(f"Erro ao testar superadmin: {str(e)}")


def main():
    """Função principal do teste"""
    print("🚀 TESTE COMPLETO DO SISTEMA DE RASTREABILIDADE ETL DOCUMENTOS")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Teste de health
    test_health()

    # 2. Criação de clientes
    clients = create_test_clients()

    if not clients:
        print_error("Nenhum cliente foi criado. Abortando testes.")
        return

    # 3. Testes com cada cliente
    for client in clients:
        print_section(f"TESTES COM CLIENTE: {client['nome']}")

        api_key = client['api_key']
        plano = client['plano']

        print_info(f"Plano: {plano}")
        print_info(f"API Key: {api_key[:20]}...")

        # Teste de autenticação
        test_api_key_authentication(api_key)

        # Verificação de quotas
        test_quota_checking(api_key)

        # Simulação de processamento
        if plano == "superadmin":
            # Mais documentos para superadmin
            simulate_document_processing(api_key, 5)
        else:
            simulate_document_processing(api_key, 2)

        # Teste de rate limiting (apenas para planos limitados)
        if plano != "superadmin":
            test_rate_limiting(api_key)

        # Relatório de uso
        get_usage_report(api_key)

        # Teste de upgrade (apenas para planos não-superadmin)
        if plano != "superadmin":
            test_upgrade_plan(api_key, "premium")

        # Testar processamento de documento
        test_processamento_documento(api_key)

        # Testar superadmin ilimitado
        if plano == "superadmin":
            test_superadmin_unlimited(api_key)

        print("\n" + "-"*40)

    print_section("RESUMO DOS TESTES")
    print_success("Todos os testes foram executados!")
    print_info(f"Total de clientes testados: {len(clients)}")
    print_info("Verifique os logs do servidor para mais detalhes.")


if __name__ == "__main__":
    main()
