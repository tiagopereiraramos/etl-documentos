#!/bin/bash

# Script para iniciar API e Streamlit simultaneamente
echo "🚀 Iniciando ETL Documentos - Multi-Service Container"

# Função para aguardar a API estar pronta
wait_for_api() {
    echo "⏳ Aguardando API estar pronta..."
    while ! curl -s http://localhost:8000/docs > /dev/null 2>&1; do
        sleep 2
    done
    echo "✅ API está pronta!"
}

# Iniciar API em background
echo "🔧 Iniciando API FastAPI na porta 8000..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300 --timeout-graceful-shutdown 300 &
API_PID=$!

# Aguardar API estar pronta
wait_for_api

# Iniciar Streamlit em background
echo "🌐 Iniciando Streamlit na porta 8501..."
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
STREAMLIT_PID=$!

# Função para cleanup quando o container parar
cleanup() {
    echo "🛑 Parando serviços..."
    kill $API_PID $STREAMLIT_PID
    wait $API_PID $STREAMLIT_PID
    echo "✅ Serviços parados"
    exit 0
}

# Capturar sinais de parada
trap cleanup SIGTERM SIGINT

echo "✅ Ambos os serviços iniciados:"
echo "   📡 API: http://localhost:8000"
echo "   🌐 Streamlit: http://localhost:8501"

# Aguardar ambos os processos
wait $API_PID $STREAMLIT_PID 