#!/usr/bin/env python3
"""
Script de teste para verificar a integração da nova camada de banco de dados
"""
from app.database.repositories import (
    cliente_repo, documento_repo, log_repo,
    sessao_repo, consumo_llm_repo, feedback_repo
)
from app.database.migrations import initialize_database, check_database_health
from app.database.connection import db_manager, inicializar_banco
from app.core.logging import obter_logger
import asyncio
import sys
import os
from sqlalchemy import text

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


logger = obter_logger(__name__)


def test_database_connection():
    """Testa a conexão com o banco de dados"""
    print("🔍 Testando conexão com banco de dados...")

    try:
        # Inicializar database manager
        db_manager.initialize()
        print("✅ Database manager inicializado")

        # Testar sessão
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Conexão com banco estabelecida")

        return True

    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False


def test_database_initialization():
    """Testa a inicialização do banco de dados"""
    print("\n🔍 Testando inicialização do banco...")

    try:
        success = initialize_database()
        if success:
            print("✅ Banco de dados inicializado com sucesso")
            return True
        else:
            print("❌ Falha na inicialização do banco")
            return False

    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        return False


def test_database_health():
    """Testa a verificação de saúde do banco"""
    print("\n🔍 Testando verificação de saúde...")

    try:
        health = check_database_health()
        print(f"Status: {health['status']}")
        print(f"Tabelas existentes: {health['tabelas_existentes']}")
        print(f"Tipo de banco: {health['tipo_banco']}")

        if health['tabelas_faltando']:
            print(f"Tabelas faltando: {health['tabelas_faltando']}")

        return health['status'] == 'healthy'

    except Exception as e:
        print(f"❌ Erro na verificação de saúde: {e}")
        return False


def test_repositories():
    """Testa os repositories"""
    print("\n🔍 Testando repositories...")

    try:
        with db_manager.get_session() as session:
            # Testar cliente repository
            print("  - Testando ClienteRepository...")
            clientes = cliente_repo.get_all(session, limit=5)
            print(f"    Clientes encontrados: {len(clientes)}")

            # Testar documento repository
            print("  - Testando DocumentoRepository...")
            documentos = documento_repo.get_all(session, limit=5)
            print(f"    Documentos encontrados: {len(documentos)}")

            # Testar log repository
            print("  - Testando LogProcessamentoRepository...")
            logs = log_repo.get_all(session, limit=5)
            print(f"    Logs encontrados: {len(logs)}")

            # Testar sessão repository
            print("  - Testando SessaoUsoRepository...")
            sessoes = sessao_repo.get_all(session, limit=5)
            print(f"    Sessões encontradas: {len(sessoes)}")

            # Testar consumo LLM repository
            print("  - Testando ConsumoLLMRepository...")
            consumos = consumo_llm_repo.get_all(session, limit=5)
            print(f"    Consumos encontrados: {len(consumos)}")

        print("✅ Todos os repositories funcionando")
        return True

    except Exception as e:
        print(f"❌ Erro nos repositories: {e}")
        return False


def test_create_sample_data():
    """Testa a criação de dados de exemplo"""
    print("\n🔍 Testando criação de dados de exemplo...")

    try:
        with db_manager.get_session() as session:
            # Criar um cliente de teste
            cliente = cliente_repo.create(
                session,
                nome="Cliente Teste",
                email="teste@exemplo.com",
                senha_hash="hash_teste",
                ativo=True
            )
            print(f"✅ Cliente criado: {cliente.id}")

            # Criar um documento de teste
            documento = documento_repo.create(
                session,
                cliente_id=cliente.id,
                nome_arquivo="teste.pdf",
                tipo_documento="Comprovante Bancário",
                extensao_arquivo=".pdf",
                tamanho_arquivo=1024,
                status_processamento="concluido"
            )
            print(f"✅ Documento criado: {documento.id}")

            # Criar um log de teste
            log = log_repo.create(
                session,
                documento_id=documento.id,
                cliente_id=cliente.id,
                operacao="extracao_texto",
                status="sucesso",
                detalhes={"provider": "docling"}
            )
            print(f"✅ Log criado: {log.id}")

            # Limpar dados de teste
            log_repo.delete(session, log.id)
            documento_repo.delete(session, documento.id)
            cliente_repo.delete(session, cliente.id)
            print("✅ Dados de teste removidos")

        return True

    except Exception as e:
        print(f"❌ Erro na criação de dados: {e}")
        return False


async def test_async_operations():
    """Testa operações assíncronas"""
    print("\n🔍 Testando operações assíncronas...")

    try:
        if db_manager.settings.database.type.value == "postgresql":
            async with db_manager.get_async_session() as session:
                result = await session.execute("SELECT 1")
                await result.fetchone()
            print("✅ Operações assíncronas funcionando")
            return True
        else:
            print("⚠️  Operações assíncronas não disponíveis para SQLite")
            return True

    except Exception as e:
        print(f"❌ Erro nas operações assíncronas: {e}")
        return False


def main():
    """Função principal de teste"""
    print("🚀 Iniciando testes de integração da camada de banco de dados")
    print("=" * 60)

    tests = [
        ("Conexão com banco", test_database_connection),
        ("Inicialização do banco", test_database_initialization),
        ("Verificação de saúde", test_database_health),
        ("Repositories", test_repositories),
        ("Criação de dados", test_create_sample_data),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro no teste '{test_name}': {e}")
            results.append((test_name, False))

    # Teste assíncrono
    try:
        result = asyncio.run(test_async_operations())
        results.append(("Operações assíncronas", result))
    except Exception as e:
        print(f"❌ Erro no teste assíncrono: {e}")
        results.append(("Operações assíncronas", False))

    # Resumo dos resultados
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nResultado: {passed}/{total} testes passaram")

    if passed == total:
        print(
            "🎉 Todos os testes passaram! A camada de banco está funcionando corretamente.")
        return True
    else:
        print("⚠️  Alguns testes falharam. Verifique os logs acima.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
