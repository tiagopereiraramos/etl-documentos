FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências
COPY requirements.txt pyproject.toml ./

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY . .

# Copiar e dar permissão ao script de inicialização
COPY start-services.sh /app/start-services.sh
RUN chmod +x /app/start-services.sh

# Criar diretórios necessários
RUN mkdir -p data/uploads data/output logs vector_store_db

# Expor ambas as portas
EXPOSE 8000 8501

# Variáveis de ambiente
ENV PYTHONPATH=/app
ENV DOCLING_DEVICE=cpu
ENV PYTORCH_ENABLE_MPS_FALLBACK=1
ENV CUDA_VISIBLE_DEVICES=""

# Comando padrão - usar o script multi-service
CMD ["/app/start-services.sh"] 