#!/bin/bash
set -e

# Parar servidor antigo
kill $(lsof -t -i:8000) 2>/dev/null || true

# Remover banco de dados
rm -f ./data/etl_documentos_dev.db

# Iniciar servidor FastAPI em background
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!

# Função para parar o servidor ao sair
function cleanup {
  echo "Parando servidor..."
  kill $SERVER_PID
}
trap cleanup EXIT

# Aguardar API estar pronta
echo "Aguardando API iniciar..."
for i in {1..20}; do
  sleep 1
  if curl -s http://localhost:8000/api/v1/health | grep -q 'healthy'; then
    echo "API pronta!"
    break
  fi
  if [ $i -eq 20 ]; then
    echo "Timeout ao aguardar API. Abortando."
    exit 1
  fi
done

# Rodar o teste completo
python test_sistema_completo.py 