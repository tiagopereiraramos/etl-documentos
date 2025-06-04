from .extraction_base import BaseExtractor

class ContratoSocialExtractor(BaseExtractor):
    """Extractor for Contrato Social documents."""
    
    def _get_document_type(self) -> str:
        return "Contrato Social"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente especializado em extrair informações precisas de **{document_type}** brasileiros.
Extraia os seguintes campos formatando no encoding UTF-8:

- Razão social (nome completo da empresa)
- Nome fantasia (se disponível)
- CNPJ (se disponível, em documentos de alteração contratual)
- Endereço completo da sede
- Objeto social (atividades da empresa)
- Capital social total (valor em R$)
- Data de constituição ou alteração
- Lista de sócios com:
  * Nome completo
  * CPF
  * Valor ou percentual de participação
  * Função na empresa (se administrador, sócio cotista, etc)
- Administradores (quem representa a empresa)
- Tipo de documento (se é contrato inicial ou alteração contratual)
- Número da alteração contratual (se aplicável)
- Cláusulas alteradas (em caso de alteração contratual)
- Sócios ingressantes (em caso de alteração)
- Sócios retirantes (em caso de alteração)

Caso um campo não esteja presente ou não se aplique ao documento, retorne "Não aplicável" ou "Não informado".

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "subtipo": "...", // "Contrato Inicial" ou "Alteração Contratual"
  "numero_alteracao": "...", // Se for alteração contratual
  "razao_social": "...",
  "nome_fantasia": "...",
  "cnpj": "...",
  "endereco_sede": "...",
  "objeto_social": "...",
  "capital_social_total": "...",
  "data_constituicao_alteracao": "...",
  "socios": [
    {{
      "nome": "...",
      "cpf": "...",
      "participacao": "...", // Valor ou percentual
      "funcao": "..." // Ex: "Sócio Administrador", "Sócio"
    }},
    // Repita para todos os sócios
  ],
  "administradores": [
    "..." // Lista de nomes dos administradores
  ],
  "clausulas_alteradas": [
    {{
      "clausula": "...", // Ex: "Cláusula Terceira - Endereço"
      "alteracao": "..." // Descrição da alteração
    }}
    // Repita para todas as cláusulas alteradas
  ],
  "socios_ingressantes": [
    "..." // Lista de nomes dos sócios ingressantes
  ],
  "socios_retirantes": [
    "..." // Lista de nomes dos sócios retirantes
  ],
  "representacao_empresa": "..." // Forma como a empresa é representada
}}
"""