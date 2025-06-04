from .extraction_base import BaseExtractor

class CartaoCNPJExtractor(BaseExtractor):
    """Extractor for Cartão CNPJ documents."""
    
    def _get_document_type(self) -> str:
        return "Cartão CNPJ"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente que extrai informações de documentos de **{document_type}**. 
Extraia os seguintes campos formatando no encoding UTF-8:

- Razão Social: Nome oficial da empresa registrado para fins legais e fiscais.
  Geralmente aparece como "NOME EMPRESARIAL" ou "RAZÃO SOCIAL" no documento.

- Nome Fantasia: Nome comercial da empresa, pelo qual é conhecida no mercado.
  Geralmente aparece como "TÍTULO DO ESTABELECIMENTO (NOME FANTASIA)" ou "NOME DE FANTASIA".
  Se não houver, retorne "Não informado".

- CNPJ: Cadastro Nacional da Pessoa Jurídica com 14 dígitos numéricos, com ou sem formatação.
  Exemplos válidos: '12.345.678/0001-95' ou '12345678000195'.
  Geralmente aparece no topo do documento como "CNPJ" ou "NÚMERO DE INSCRIÇÃO".

- Data de Abertura: Data em que a empresa foi formalmente registrada.
  Deve ser fornecida no formato "DD/MM/AAAA" quando disponível.

- Atividades Econômicas Principais: Código CNAE e descrição da atividade principal da empresa.
  Exemplo: "47.51-2-01 - Comércio varejista especializado de equipamentos e suprimentos de informática" *Concatene todas elas separando por '|'*

- Natureza Jurídica: Classificação que indica o tipo jurídico da empresa.
  Exemplo: "206-2 - Sociedade Empresária Limitada"

- Endereço completo: Deve incluir logradouro, número, complemento (se houver), bairro, cidade, estado (UF) e CEP.
  Exemplo: 'Avenida Brasil, 1500, Sala 302, Centro, Rio de Janeiro, RJ, CEP: 20071-001'.

- Situação Cadastral: Status atual da empresa perante a Receita Federal.
  Geralmente aparece como "SITUAÇÃO CADASTRAL" com valores como "ATIVA", "SUSPENSA", "BAIXADA", etc.

- Data da Situação Cadastral: Data da última atualização do status cadastral.
  Deve ser fornecida no formato "DD/MM/AAAA" quando disponível.

Caso um campo não esteja presente no documento, retorne "Não foi possível localizar este campo".

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "razao_social": "...",
  "nome_fantasia": "...",
  "cnpj": "...",
  "data_abertura": "...",
  "atividades_principais": "...",
  "natureza_juridica": "...",
  "endereco": "...",
  "situacao_cadastral": "...",
  "data_situacao_cadastral": "..."
}}
"""