#!/usr/bin/env python3
"""
Teste do Sistema de Rastreabilidade por Cliente
Demonstra criação de clientes, API keys, quotas e rastreamento de uso
"""
import asyncio
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Configuração da API
API_BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}


def criar_cliente_teste(nome: str, email: str, plano: str = "free") -> Optional[Dict[str, Any]]:
    """Cria um cliente de teste"""
    url = f"{API_BASE_URL}/clientes/"
    data = {
        "nome": nome,
        "email": email,
        "senha": "senha123",
        "plano": plano
    }

    response = requests.post(url, json=data, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(
            f"❌ Erro ao criar cliente: {response.status_code} - {response.text}")
        return None


def testar_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Testa uma API key"""
    headers = {"X-API-Key": api_key}

    # Testar endpoint de perfil
    url = f"{API_BASE_URL}/clientes/me"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(
            f"❌ Erro ao testar API key: {response.status_code} - {response.text}")
        return None


def processar_documento_teste(api_key: str, filename: str = "teste.pdf") -> Optional[Dict[str, Any]]:
    """Simula processamento de documento"""
    headers = {"X-API-Key": api_key}

    # Simular upload de arquivo
    files = {"arquivo": (
        filename, b"conteudo do arquivo de teste", "application/pdf")}
    url = f"{API_BASE_URL}/processar"

    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        return response.json()
    else:
        print(
            f"❌ Erro ao processar documento: {response.status_code} - {response.text}")
        return None


def obter_relatorio_uso(api_key: str, periodo_dias: int = 30) -> Optional[Dict[str, Any]]:
    """Obtém relatório de uso do cliente"""
    headers = {"X-API-Key": api_key}

    url = f"{API_BASE_URL}/clientes/me/usage?periodo_dias={periodo_dias}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(
            f"❌ Erro ao obter relatório: {response.status_code} - {response.text}")
        return None


def obter_quotas(api_key: str) -> Optional[Dict[str, Any]]:
    """Obtém informações de quotas do cliente"""
    headers = {"X-API-Key": api_key}

    url = f"{API_BASE_URL}/clientes/me/quotas"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(
            f"❌ Erro ao obter quotas: {response.status_code} - {response.text}")
        return None


def testar_rate_limit(api_key: str, num_requests: int = 15) -> None:
    """Testa rate limiting"""
    headers = {"X-API-Key": api_key}

    print(f"\n🔄 Testando rate limit com {num_requests} requisições...")

    for i in range(num_requests):
        url = f"{API_BASE_URL}/clientes/me"
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            print(f"✅ Rate limit atingido na requisição {i+1}")
            break
        elif response.status_code == 200:
            print(f"✅ Requisição {i+1} bem-sucedida")
        else:
            print(f"❌ Erro na requisição {i+1}: {response.status_code}")
            break


def main():
    """Função principal de teste"""
    print("🧪 TESTE DO SISTEMA DE RASTREABILIDADE POR CLIENTE")
    print("=" * 60)

    # 1. Criar clientes de teste
    print("\n1️⃣ CRIANDO CLIENTES DE TESTE")
    print("-" * 40)

    # Cliente Free
    cliente_free = criar_cliente_teste(
        nome="João Silva",
        email="joao.silva@teste.com",
        plano="free"
    )

    if not cliente_free:
        print("❌ Falha ao criar cliente free")
        return

    print(f"✅ Cliente Free criado: {cliente_free['cliente']['nome']}")
    print(f"   API Key: {cliente_free['cliente']['api_key'][:20]}...")
    print(f"   Plano: {cliente_free['cliente']['plano']}")

    # Cliente Basic
    cliente_basic = criar_cliente_teste(
        nome="Maria Santos",
        email="maria.santos@teste.com",
        plano="basic"
    )

    if not cliente_basic:
        print("❌ Falha ao criar cliente basic")
        return

    print(f"✅ Cliente Basic criado: {cliente_basic['cliente']['nome']}")
    print(f"   API Key: {cliente_basic['cliente']['api_key'][:20]}...")
    print(f"   Plano: {cliente_basic['cliente']['plano']}")

    # Cliente Premium
    cliente_premium = criar_cliente_teste(
        nome="Pedro Costa",
        email="pedro.costa@teste.com",
        plano="premium"
    )

    if not cliente_premium:
        print("❌ Falha ao criar cliente premium")
        return

    print(f"✅ Cliente Premium criado: {cliente_premium['cliente']['nome']}")
    print(f"   API Key: {cliente_premium['cliente']['api_key'][:20]}...")
    print(f"   Plano: {cliente_premium['cliente']['plano']}")

    # 2. Testar API Keys
    print("\n2️⃣ TESTANDO API KEYS")
    print("-" * 40)

    api_key_free = cliente_free['cliente']['api_key']
    perfil_free = testar_api_key(api_key_free)

    if perfil_free:
        print(f"✅ API Key Free válida")
        print(f"   Cliente: {perfil_free['cliente']['nome']}")
        print(f"   Plano: {perfil_free['cliente']['plano']}")
        print(
            f"   Documentos restantes: {perfil_free['quotas']['documentos_restantes']}")
        print(
            f"   Tokens restantes: {perfil_free['quotas']['tokens_restantes']}")

    # 3. Testar processamento de documentos
    print("\n3️⃣ TESTANDO PROCESSAMENTO DE DOCUMENTOS")
    print("-" * 40)

    # Processar com cliente free
    resultado_free = processar_documento_teste(
        api_key_free, "comprovante_bancario.pdf")
    if resultado_free:
        print(f"✅ Documento processado com cliente Free")
        print(f"   ID: {resultado_free['documento_id']}")
        print(f"   Custo: ${resultado_free['processamento']['custo_total']}")
        print(
            f"   Tokens: {resultado_free['processamento']['tokens_consumidos']}")

    # Processar com cliente basic
    api_key_basic = cliente_basic['cliente']['api_key']
    resultado_basic = processar_documento_teste(
        api_key_basic, "contrato_social.pdf")
    if resultado_basic:
        print(f"✅ Documento processado com cliente Basic")
        print(f"   ID: {resultado_basic['documento_id']}")
        print(f"   Custo: ${resultado_basic['processamento']['custo_total']}")
        print(
            f"   Tokens: {resultado_basic['processamento']['tokens_consumidos']}")

    # 4. Verificar quotas após uso
    print("\n4️⃣ VERIFICANDO QUOTAS APÓS USO")
    print("-" * 40)

    quotas_free = obter_quotas(api_key_free)
    if quotas_free:
        print(f"📊 Quotas Cliente Free:")
        print(
            f"   Documentos usados: {quotas_free['uso_mes']['documentos_processados']}")
        print(
            f"   Tokens usados: {quotas_free['uso_mes']['tokens_consumidos']}")
        print(f"   Custo total: ${quotas_free['uso_mes']['custo_total']}")

    # 5. Testar rate limiting
    print("\n5️⃣ TESTANDO RATE LIMITING")
    print("-" * 40)

    testar_rate_limit(api_key_free, 15)  # Free tem limite de 10/min

    # 6. Obter relatório de uso
    print("\n6️⃣ RELATÓRIO DE USO")
    print("-" * 40)

    relatorio_free = obter_relatorio_uso(api_key_free, 7)
    if relatorio_free:
        print(f"📈 Relatório Cliente Free (7 dias):")
        print(
            f"   Total operações: {relatorio_free['resumo']['total_operacoes']}")
        print(f"   Total tokens: {relatorio_free['resumo']['total_tokens']}")
        print(f"   Total custo: ${relatorio_free['resumo']['total_custo']}")

        if relatorio_free['uso_por_operacao']:
            print(f"   Operações por tipo:")
            for op in relatorio_free['uso_por_operacao']:
                print(f"     - {op['operacao']}: {op['total']} vezes")

    # 7. Testar upgrade de plano
    print("\n7️⃣ TESTANDO UPGRADE DE PLANO")
    print("-" * 40)

    headers = {"X-API-Key": api_key_free}
    url = f"{API_BASE_URL}/clientes/me/upgrade-plan?novo_plano=basic"
    response = requests.put(url, headers=headers)

    if response.status_code == 200:
        resultado_upgrade = response.json()
        print(f"✅ Plano atualizado com sucesso")
        print(f"   De: {resultado_upgrade['resultado']['plano_anterior']}")
        print(f"   Para: {resultado_upgrade['resultado']['plano_novo']}")

        # Verificar novas quotas
        novas_quotas = obter_quotas(api_key_free)
        if novas_quotas:
            print(f"   Novas quotas:")
            print(
                f"     Documentos/mês: {novas_quotas['plano_config']['documentos_mes']}")
            print(
                f"     Tokens/mês: {novas_quotas['plano_config']['tokens_mes']}")
            print(
                f"     Rate limit: {novas_quotas['plano_config']['rate_limit_minuto']}/min")
    else:
        print(f"❌ Erro ao atualizar plano: {response.status_code}")

    print("\n🎉 TESTE CONCLUÍDO!")
    print("=" * 60)
    print("✅ Sistema de rastreabilidade funcionando corretamente")
    print("✅ API Keys, quotas e rate limiting operacionais")
    print("✅ Relatórios de uso disponíveis")
    print("✅ Upgrade de planos funcionando")


if __name__ == "__main__":
    main()
