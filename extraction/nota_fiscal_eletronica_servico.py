from .extraction_base import BaseExtractor

class NotaFiscalServicoExtractor(BaseExtractor):
    """Extractor for Nota Fiscal de Serviços Eletrônica documents."""
    
    def _get_document_type(self) -> str:
        return "Nota Fiscal de Serviços Eletrônica"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente que extrai informações de documentos de **{document_type}**. 
Extraia os seguintes campos formatando no encoding UTF-8:

- Número da NFS-e
- Código de verificação
- Data e hora de emissão
- Competência
- Valor total da nota
- Valor dos impostos (ISS, PIS, COFINS, IR, CSLL, INSS)
- Nome do prestador de serviços
- CNPJ do prestador
- Endereço do prestador
- Nome do tomador de serviços
- CPF/CNPJ do tomador
- Endereço do tomador
- Descrição dos serviços
- Código do serviço (conforme lista de serviços)
- Alíquota (%)
- Situação da nota (ex: normal, cancelada, substituída)

Caso um campo não esteja presente, retorne "Não foi possível localizar este campo".

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "numero_nfse": "...",
  "codigo_verificacao": "...",
  "data_hora_emissao": "...",
  "competencia": "...",
  "valor_total": "...",
  "impostos": {{
    "iss": "...",
    "pis": "...",
    "cofins": "...",
    "ir": "...",
    "csll": "...",
    "inss": "..."
  }},
  "prestador": {{
    "nome": "...",
    "cnpj": "...",
    "endereco": "..."
  }},
  "tomador": {{
    "nome": "...",
    "cpf_cnpj": "...",
    "endereco": "..."
  }},
  "servico": {{
    "descricao": "...",
    "codigo": "...",
    "aliquota": "..."
  }},
  "situacao": "..."
}}
"""