from .extraction_base import BaseExtractor

class AlvaraMunicipalExtractor(BaseExtractor):
    """Extractor for Alvará Municipal documents."""
    
    def _get_document_type(self) -> str:
        return "Alvará Municipal"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente que extrai informações de documentos de **{document_type}**. 
Extraia os seguintes campos formatando no encoding UTF-8:

- Razão Social: Nome oficial da empresa registrado para fins legais e fiscais.
  Geralmente aparece como "NOME EMPRESARIAL", "RAZÃO SOCIAL" ou "TITULAR" no documento.

- CNPJ: Cadastro Nacional da Pessoa Jurídica com 14 dígitos numéricos, com ou sem formatação.
  Exemplos válidos: '12.345.678/0001-95' ou '12345678000195'.
  O CNPJ deve estar diretamente vinculado à Razão Social da empresa e não ao da prefeitura ou outro órgão emissor.
  Priorize a extração do CNPJ que aparece próximo à Razão Social no documento.

- Inscrição Municipal: Número de registro único atribuído pela prefeitura à empresa.
  Geralmente aparece como "INSCRIÇÃO MUNICIPAL", "INSCRIÇÃO" ou "Nº DE INSCRIÇÃO".
  Este é um número essencial no alvará que identifica o contribuinte perante a administração municipal.

- Número do Alvará: Código identificador único do documento de autorização.
  Geralmente aparece como "ALVARÁ Nº", "NÚMERO DO ALVARÁ" ou similar.

- Data de Emissão: Data em que o alvará foi emitido pela prefeitura.
  Deve ser fornecida no formato "DD/MM/AAAA" quando disponível.

- Validade: Data limite de validade do alvará ou período de vigência.
  Exemplo: "31/12/2025" ou "Válido até 31/12/2025".

- Endereço: Local autorizado para funcionamento da empresa.
  Deve incluir logradouro, número, complemento (se houver), bairro, cidade, estado (UF) e CEP quando disponíveis.
  Exemplo: 'Avenida Brasil, 1500, Sala 302, Centro, Rio de Janeiro, RJ, CEP: 20071-001'.

- Atividades Permitidas: Descrição das atividades econômicas autorizadas pelo alvará.
  Pode incluir códigos CNAE e descrições de atividades.

Caso um campo não esteja presente no documento, retorne "Não foi possível localizar este campo".

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "razao_social": "...",
  "cnpj": "...",
  "inscricao_municipal": "...",
  "numero_alvara": "...",
  "data_emissao": "...",
  "validade": "...",
  "endereco": "...",
  "atividades_permitidas": "..."
}}
"""