
"""
Testes para os serviços principais do sistema
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionService
from app.services.cost_service import CostService

class TestClassificationService:
    """Testes para o serviço de classificação"""
    
    @pytest.fixture
    def service(self):
        return ClassificationService()
    
    @pytest.mark.asyncio
    async def test_classificar_documento_bancario(self, service, sample_document_text):
        """Testa classificação de comprovante bancário"""
        with patch.object(service, '_chamar_openai') as mock_openai:
            mock_openai.return_value = ("Comprovante Bancário", 0.95, {})
            
            resultado = await service.classificar_documento(sample_document_text)
            
            assert resultado["tipo"] == "Comprovante Bancário"
            assert resultado["confianca"] >= 0.9
    
    @pytest.mark.asyncio
    async def test_classificar_documento_vazio(self, service):
        """Testa classificação com texto vazio"""
        resultado = await service.classificar_documento("")
        assert resultado["tipo"] == "Documento Não Classificado"

class TestExtractionService:
    """Testes para o serviço de extração"""
    
    @pytest.fixture
    def service(self):
        return ExtractionService()
    
    @pytest.mark.asyncio
    async def test_extrair_dados_bancario(self, service, sample_document_text):
        """Testa extração de dados de comprovante bancário"""
        with patch.object(service, '_chamar_openai') as mock_openai:
            mock_openai.return_value = ({
                "tipo_documento": "Comprovante Bancário",
                "valor": "R$ 1.500,00",
                "razao_social": "João Silva"
            }, {})
            
            resultado = await service.extrair_dados(
                sample_document_text, 
                "Comprovante Bancário"
            )
            
            assert resultado["tipo_documento"] == "Comprovante Bancário"
            assert "valor" in resultado

class TestCostService:
    """Testes para o serviço de custos"""
    
    @pytest.fixture
    def service(self):
        return CostService()
    
    def test_calcular_custo_openai(self, service):
        """Testa cálculo de custo OpenAI"""
        custo = service.calcular_custo_openai(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4o-mini"
        )
        assert custo > 0
        assert isinstance(custo, float)
    
    def test_calcular_custo_azure(self, service):
        """Testa cálculo de custo Azure"""
        custo = service.calcular_custo_azure(paginas=5)
        assert custo > 0
        assert isinstance(custo, float)
