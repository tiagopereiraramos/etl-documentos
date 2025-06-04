# ETL de Documentos - Sistema de Processamento e Extração

[![Status](https://img.shields.io/badge/status-em%20desenvolvimento-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/fastapi-0.100.0-green)]()
[![Licença](https://img.shields.io/badge/licença-proprietária-red)]()

Sistema completo de ETL (Extração, Transformação e Carga) para documentos empresariais, utilizando técnicas avançadas de OCR (Reconhecimento Óptico de Caracteres) via Docling, classificação automática baseada em LLMs, e extração estruturada de dados.

## 🚀 Funcionalidades

- 📄 **OCR Avançado**: Extração de texto de documentos PDF e imagens usando Docling
- 🧠 **Classificação Automática**: Identifica automaticamente o tipo de documento
- 🔍 **Extração Estruturada**: Extrai campos específicos por tipo de documento
- 💾 **Armazenamento Vetorial**: Armazena documentos para consulta e reprocessamento
- 🌐 **API RESTful**: Interfaces simples para integração com outros sistemas

## 📋 Tipos de Documentos Suportados

- Comprovante Bancário
- CEI da Obra
- Inscrição Municipal
- Termo de Responsabilidade
- Alvará Municipal
- Contrato Social
- Fatura Telefônica
- Nota Fiscal de Serviços Eletrônica

Consulte a [documentação completa de tipos de documentos](docs/document-types.md) para detalhes sobre cada tipo.

## 🛠️ Instalação e Configuração

### Pré-requisitos

- Python 3.8 ou superior
- Acesso a API da OpenAI (para os modelos LLM)
- Docling instalado e configurado

### Instalação

```bash
# Criar e ativar ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações