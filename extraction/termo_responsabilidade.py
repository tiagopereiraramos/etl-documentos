from .extraction_base import BaseExtractor

class TermoResponsabilidadeExtractor(BaseExtractor):
    """Extractor for Termo de Responsabilidade documents."""
    
    def _get_document_type(self) -> str:
        return "Termo de Responsabilidade"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente que extrai informações de documentos de **{document_type}**. 
Extraia os seguintes campos formatando no encoding UTF-8:

- Razão Social: Nome oficial da empresa registrado para fins legais e fiscais.
  Geralmente aparece como "NOME EMPRESARIAL", "RAZÃO SOCIAL" ou similar no documento.

- CNPJ: Cadastro Nacional da Pessoa Jurídica com 14 dígitos numéricos, com ou sem formatação.
  Exemplos válidos: '12.345.678/0001-95' ou '12345678000195'.
  O CNPJ deve estar diretamente vinculado à Razão Social da empresa e não ao de outra entidade.
  Priorize a extração do CNPJ que aparece próximo à Razão Social no documento.

- Nome do Responsável: Pessoa física que está assumindo responsabilidade conforme o termo.
  Geralmente aparece após expressões como "eu", "declaro", "responsável" ou junto a assinaturas.

- CPF do Responsável: Número do CPF da pessoa responsável, quando disponível.
  Deve conter 11 dígitos numéricos, formatado como '123.456.789-00' ou sem formatação '12345678900'.

- Objeto de Responsabilidade: Descrição do assunto, serviço, equipamento ou situação para a qual a responsabilidade está sendo assumida.
  Pode aparecer após expressões como "responsabilizo-me por", "referente a", ou similar.

- Data do Termo: Data em que o termo de responsabilidade foi assinado ou emitido.
  Deve ser fornecida no formato "DD/MM/AAAA" quando disponível.

- Assinatura Detectada: Verifique se há indícios de que o documento foi efetivamente assinado.
  - Se encontrar informações que indiquem assinatura eletrônica, digital, ou certificado digital aplicado ao documento, defina como "true".
  - Ignore menções genéricas ou instruções sobre aceitação de assinaturas que não indiquem que o documento específico já foi assinado.
  - Caso não encontre indícios de assinatura aplicada, defina como "false".

Caso um campo não esteja presente no documento, retorne "Não foi possível localizar este campo".

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "razao_social": "...",
  "cnpj": "...",
  "nome_responsavel": "...",
  "cpf_responsavel": "...",
  "objeto_responsabilidade": "...",
  "data_termo": "...",
  "assinatura_detectada": "..." 
}}
"""