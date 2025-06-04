from .extraction_base import BaseExtractor

class CEIObraExtractor(BaseExtractor):
    """Extractor for CEI da Obra documents."""
    
    def _get_document_type(self) -> str:
        return "CEI da Obra"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente que extrai informações de documentos de **{document_type}**. 
Extraia os seguintes campos formatando no encoding UTF-8:

- Razão Social do cliente: Nome oficial da empresa registrado para fins legais e fiscais.

- CNPJ: Cadastro Nacional da Pessoa Jurídica com 14 dígitos numéricos, com ou sem formatação.
  Exemplos válidos: '12.345.678/0001-95' ou '12345678000195'.
  O CNPJ deve estar diretamente vinculado à Razão Social da empresa e não ao da prefeitura ou outro órgão emissor.
  Priorize a extração do CNPJ que aparece próximo à Razão Social no documento.

- Endereço completo: Deve incluir rua, número, complemento (se houver), bairro, cidade, estado (UF) e CEP.
  Exemplo: 'Rua das Flores, 123, Apto 45, Bairro Centro, São Paulo, SP, CEP: 01234-567'.

- Número da matrícula CEI: Código único de identificação da obra perante o INSS.
  Geralmente possui formato numérico e é precedido por termos como "Matrícula CEI", "Matrícula", "CEI nº".

- Data de registro: Data em que o cadastro CEI foi efetuado junto ao INSS.
  Deve ser fornecida no formato "DD/MM/AAAA" quando disponível.

Caso um campo não esteja presente no documento, retorne "Não foi possível localizar este campo".

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "razao_social": "...",
  "cnpj": "...",
  "endereco": "...",
  "numero_cei": "...",
  "data_registro": "..."
}}
"""