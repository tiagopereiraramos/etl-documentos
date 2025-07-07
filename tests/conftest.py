
"""
Configurações e fixtures globais para testes
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(scope="session")
def event_loop():
    """Cria um event loop para toda a sessão de testes"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_document_text():
    """Texto de documento de exemplo para testes"""
    return """
    BANCO DO BRASIL S.A.
    Comprovante de Transferência
    
    Data: 15/01/2024
    Valor: R$ 1.500,00
    Beneficiário: João Silva
    CPF: 123.456.789-00
    Conta Destino: 98765-4
    Agência: 5678
    Código de Autenticação: ABC123456789
    """

@pytest.fixture
def sample_file_bytes():
    """Bytes de arquivo de exemplo"""
    return b"Content of test document file"

@pytest.fixture
def mock_openai_response():
    """Mock de resposta da OpenAI"""
    return {
        "choices": [
            {
                "message": {
                    "content": "Comprovante Bancário"
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }
