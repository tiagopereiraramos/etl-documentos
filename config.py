import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# MongoDB configuration
COLLECTIONS=os.getenv("COLLECTIONS")
ENV=os.getenv("ENV")
MODE=os.getenv("MODE")
LOCAL_MONGO_DATABASE_DEV=os.getenv("LOCAL_MONGO_DATABASE_DEV")
LOCAL_MONGO_DATABASE_PROD=os.getenv("LOCAL_MONGO_DATABASE_PROD")
MONGO_URI=os.getenv("MONGO_URI")

# API Keys and configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4-turbo")

# Vector store configuration
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./vector_store_db")
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "faiss")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "./logs/document_extractor.log")
LOG_ROTATION = os.getenv("LOG_ROTATION", "10 MB")
LOG_RETENTION = int(os.getenv("LOG_RETENTION", "5"))

DOCUMENT_TYPES = [
    "CNH",
    "Comprovante Bancário",
    "Cartão CNPJ",   # Novo tipo adicionado
    "CEI da Obra",
    "Inscrição Municipal",
    "Termo de Responsabilidade",
    "Alvará Municipal",
    "Contrato Social",
    "Fatura Telefônica",
    "Nota Fiscal de Serviços Eletrônica"
]

# Mapeamento de tipos de documentos para identificadores internos
DOCUMENT_TYPE_IDS = {
    "Alvará Municipal": "alvara_municipal",
    "Cartão CNPJ": "cartao_cnpj",  # Novo mapeamento adicionado
    "CEI da Obra": "cei_obra",
    "CNH": "cnh",
    "Comprovante Bancário": "comprovante_bancario",
    "Contrato Social": "contrato_social",
    "Fatura Telefônica": "fatura_telefonica",
    "Inscrição Municipal": "inscricao_municipal",
    "Nota Fiscal de Serviços Eletrônica": "nota_fiscal_servico",
    "Termo de Responsabilidade": "termo_responsabilidade"
}

# API configuration
API_PORT = int(os.getenv("API_PORT", 8000))
API_HOST = os.getenv("API_HOST", "0.0.0.0")