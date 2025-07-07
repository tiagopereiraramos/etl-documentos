
"""
Testes para as rotas da API
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_health_check():
    """Testa endpoint de health check"""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_upload_documento():
    """Testa upload de documento"""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock do processamento
        with patch("app.api.routes.DocumentProcessor") as mock_processor:
            mock_processor.return_value.processar_documento.return_value = {
                "document_type": "Comprovante Bancário",
                "classification_confidence": 0.95,
                "extracted_data": {"teste": "valor"}
            }
            
            files = {"file": ("test.txt", b"conteudo teste", "text/plain")}
            response = await client.post("/api/v1/documents/upload", files=files)
            
            assert response.status_code == 200
            data = response.json()
            assert "document_type" in data
