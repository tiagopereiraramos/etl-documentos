#!/bin/bash

# Script para rodar ETL Documentos com Docker

echo "🐳 Iniciando ETL Documentos com Docker..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Instale o Docker primeiro."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Instale o Docker Compose primeiro."
    exit 1
fi

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose down

# Construir e iniciar containers
echo "🔨 Construindo containers..."
docker-compose build

echo "🚀 Iniciando serviços..."
docker-compose up -d

# Aguardar API ficar pronta
echo "⏳ Aguardando API ficar pronta..."
sleep 10

# Verificar se API está funcionando
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ API está funcionando em http://localhost:8000"
else
    echo "⚠️  API ainda não está pronta. Aguarde mais alguns segundos..."
fi

echo "✅ Streamlit está disponível em http://localhost:8501"
echo ""
echo "📋 Comandos úteis:"
echo "  - Ver logs: docker-compose logs -f"
echo "  - Parar: docker-compose down"
echo "  - Reiniciar: docker-compose restart"
echo ""
echo "🎉 Sistema pronto para uso!" 