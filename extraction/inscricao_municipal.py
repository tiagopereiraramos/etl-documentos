from .extraction_base import BaseExtractor

class InscricaoMunicipalExtractor(BaseExtractor):
    """Extractor for Inscrição Municipal documents."""
    
    def _get_document_type(self) -> str:
        return "Inscrição Municipal"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente que extrai informações de documentos de **{document_type}**. 
Extraia os seguintes campos formatando no encoding UTF-8:

- Número da Inscrição: Identificador único da Inscrição Municipal, emitido pela prefeitura ou órgão municipal responsável.
  Também pode ser referenciado como CCM (Cadastro de Contribuinte Mobiliário) em alguns documentos.
  Geralmente composto por uma sequência de números, podendo conter pontos, barras ou traços.
  Pode variar de 6 a 20 caracteres numéricos, dependendo da cidade.
  Exemplos válidos: "123.456.789-0", "00123456789", "12.345.678/0001-99".

- Razão Social: Nome oficial da empresa registrado para fins legais e fiscais.
  Geralmente aparece como "NOME EMPRESARIAL", "RAZÃO SOCIAL" ou "TITULAR" no documento.

- CNPJ: Cadastro Nacional da Pessoa Jurídica com 14 dígitos numéricos, com ou sem formatação.
  Exemplos válidos: '12.345.678/0001-95' ou '12345678000195'.

- Data de Inscrição: Data em que a empresa foi inscrita no cadastro municipal.
  Deve ser fornecida no formato "DD/MM/AAAA" quando disponível.

- Município: Nome da cidade onde a inscrição municipal foi registrada.

- Endereço: Local registrado da empresa no município.
  Deve incluir logradouro, número, complemento (se houver), bairro e CEP quando disponíveis.

- Atividade Econômica: Descrição da atividade principal da empresa registrada na prefeitura.
  Pode incluir códigos e descrições de atividades.

Caso um campo não esteja presente no documento, retorne "Não foi possível localizar este campo".

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "numero_inscricao": "...",
  "razao_social": "...",
  "cnpj": "...",
  "data_inscricao": "...",
  "municipio": "...",
  "endereco": "...",
  "atividade_economica": "..."
}}
"""