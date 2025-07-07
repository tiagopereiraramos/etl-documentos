#!/usr/bin/env python3
"""
Script para obter a API Key do Super Admin
"""

from app.services.client_management_service import ClientManagementService
from app.models.database import Cliente
from app.database.connection import get_db
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def get_or_create_superadmin():
    """Busca ou cria o super admin"""
    db = next(get_db())

    # Buscar super admin existente
    superadmin = db.query(Cliente).filter(
        Cliente.plano_tipo == "superadmin",
        Cliente.ativo == True
    ).first()

    if superadmin:
        print(f"✅ Super Admin encontrado:")
        print(f"   Nome: {superadmin.nome}")
        print(f"   Email: {superadmin.email}")
        print(f"   API Key: {superadmin.api_key}")
        print(f"   Plano: {superadmin.plano_tipo}")
        return superadmin.api_key
    else:
        print("❌ Super Admin não encontrado. Criando...")

        # Criar super admin
        client_service = ClientManagementService()
        try:
            result = client_service.create_client(
                nome="Super Admin",
                email="admin@gerdau.com",
                senha="admin123",
                plano="superadmin",
                db=db
            )

            if result["success"]:
                api_key = result["cliente"]["api_key"]
                print(f"✅ Super Admin criado com sucesso!")
                print(f"   Nome: {result['cliente']['nome']}")
                print(f"   Email: {result['cliente']['email']}")
                print(f"   API Key: {api_key}")
                print(f"   Plano: {result['cliente']['plano']}")
                return api_key
            else:
                print(f"❌ Erro ao criar Super Admin: {result['error']}")
                return None

        except Exception as e:
            print(f"❌ Erro ao criar Super Admin: {str(e)}")
            return None


def list_all_clients():
    """Lista todos os clientes"""
    db = next(get_db())
    clientes = db.query(Cliente).filter(Cliente.ativo == True).all()

    print(f"\n📋 Todos os clientes ({len(clientes)}):")
    print("-" * 60)

    for i, cliente in enumerate(clientes, 1):
        print(f"{i}. {cliente.nome}")
        print(f"   Email: {cliente.email}")
        print(f"   Plano: {cliente.plano_tipo}")
        print(f"   API Key: {cliente.api_key}")
        print()


def main():
    print("🔑 OBTENDO API KEY DO SUPER ADMIN")
    print("=" * 50)

    # Obter super admin
    api_key = get_or_create_superadmin()

    if api_key:
        print(f"\n🎯 API Key do Super Admin:")
        print(f"   {api_key}")
        print(f"\n📋 Para usar no Streamlit:")
        print(f"   1. Acesse: http://localhost:8501")
        print(f"   2. Na sidebar, vá para '🔑 Login'")
        print(f"   3. Cole a API Key acima")
        print(f"   4. Clique em '🔓 Entrar'")

        # Listar todos os clientes
        list_all_clients()
    else:
        print("❌ Não foi possível obter a API Key do Super Admin")


if __name__ == "__main__":
    main()
