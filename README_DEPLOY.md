# 🚀 Guia de Deploy - ETL Documentos

## 📋 Informações da Aplicação

- **Nome:** ETL Documentos / BRFlow CAS
- **Imagem Docker:** `svcdockers/brflow-cas:1.0.1`
- **Repositório:** https://github.com/tiagopereiraramos/etl-documentos

## 🐳 Deploy com Docker Compose

### 1. Usar o arquivo docker-compose.yml

O projeto já inclui um `docker-compose.yml` otimizado para produção que:
- Usa a imagem do Docker Hub do cliente
- Configura volumes persistentes
- Inclui health checks
- Configura restart automático

### 2. Variáveis de Ambiente Obrigatórias

Crie um arquivo `.env` com:

```env
# OBRIGATÓRIO - Chave da OpenAI
OPENAI_API_KEY=sk-proj-sua_chave_aqui

# OPCIONAL - Modelos (já tem defaults)
CLASSIFICATION_MODEL=gpt-4o-mini
EXTRACTION_MODEL=gpt-4o-mini
```

### 3. Executar

```bash
docker-compose up -d
```

## 🌐 Deploy no EasyPanel

### Opção 1: Via Docker Compose (Recomendado)

1. **Upload do Repositório:**
   - Conecte o repositório GitHub: `https://github.com/tiagopereiraramos/etl-documentos`
   - EasyPanel detectará automaticamente o `docker-compose.yml`

2. **Configurar Variáveis de Ambiente:**
   ```
   OPENAI_API_KEY=sk-proj-sua_chave_aqui
   ```

3. **Deploy Automático:**
   - EasyPanel criará automaticamente:
     - Serviço API (porta 8000)
     - Serviço Streamlit (porta 8501)
     - Volumes persistentes

### Opção 2: Via Imagem Docker Individual

Se preferir configurar manualmente:

#### Serviço 1: API Principal
- **Image:** `svcdockers/brflow-cas:1.0.1`
- **Port:** `8000`
- **Environment Variables:**
  ```
  OPENAI_API_KEY=sk-proj-sua_chave_aqui
  PYTHONPATH=/app
  DATABASE_URL=sqlite:///./data/etl_documentos.db
  DOCLING_DEVICE=cpu
  PYTORCH_ENABLE_MPS_FALLBACK=1
  CUDA_VISIBLE_DEVICES=""
  ```
- **Volumes:**
  ```
  /app/data
  /app/logs
  /app/vector_store_db
  ```

#### Serviço 2: Interface Streamlit (Opcional)
- **Image:** `svcdockers/brflow-cas:1.0.1`
- **Port:** `8501`
- **Command:** `streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0`
- **Same Environment Variables and Volumes**

## 🔍 Verificação de Deploy

### Health Checks

- **API:** `https://seu-dominio/docs` - Documentação FastAPI
- **Streamlit:** `https://seu-dominio:8501` - Interface web

### Endpoints Principais

```
GET  /docs                     - Documentação da API
POST /api/v1/process          - Upload e processamento de documentos
GET  /api/v1/documents        - Listar documentos processados
GET  /api/v1/documents/{id}   - Detalhes de um documento
```

### Teste Rápido

```bash
curl https://seu-dominio/docs
```

## 📊 Recursos Necessários

### Mínimo Recomendado:
- **CPU:** 2 vCores
- **RAM:** 4GB
- **Storage:** 20GB (para dados e modelo)

### Produção:
- **CPU:** 4+ vCores
- **RAM:** 8GB+
- **Storage:** 50GB+

## 🔒 Segurança

### Variáveis Sensíveis:
- `OPENAI_API_KEY` - Nunca commitar no código
- Use secrets do EasyPanel para variáveis sensíveis

### Volumes Persistentes:
- `/app/data` - Banco de dados e uploads
- `/app/logs` - Logs da aplicação
- `/app/vector_store_db` - Índices vetoriais (pode ser regenerado)

## 🐛 Troubleshooting

### Logs:
```bash
docker-compose logs -f etl-api
docker-compose logs -f etl-streamlit
```

### Problemas Comuns:

1. **Erro 401 OpenAI:** Verificar `OPENAI_API_KEY`
2. **Timeout na inicialização:** Aplicação demora ~60s para carregar modelos
3. **Falta de memória:** Aumentar RAM ou usar DOCLING_DEVICE=cpu

### Restart:
```bash
docker-compose restart etl-api
```

## 📞 Suporte

Para problemas ou dúvidas:
- Verificar logs da aplicação
- Consultar documentação em `/docs`
- Testar endpoints individualmente 