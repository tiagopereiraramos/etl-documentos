from .extraction_base import BaseExtractor

class CNHExtractor(BaseExtractor):
    """Extractor for Carteira Nacional de Habilitação (CNH) documents."""
    
    def _get_document_type(self) -> str:
        return "CNH"
    
    def _get_prompt_template(self) -> str:
      return """
Você é um agente especializado na extração de informações de documentos oficiais do tipo **{document_type}** (Carteira Nacional de Habilitação — CNH física ou CNH-e).

Extraia com precisão os seguintes campos, mesmo que estejam fora de ordem ou formatados de maneira incomum. Os dados devem estar em codificação UTF-8.

- Nome completo do condutor
- Número de registro/CNH (11 dígitos numéricos)
- CPF do condutor (com ou sem formatação)
- Data de nascimento (formato DD/MM/AAAA)
- Data da primeira habilitação (formato DD/MM/AAAA)
- Data de validade da CNH (formato DD/MM/AAAA)
- Categoria da CNH (ex: A, B, AB, C, D, E, ACC)
- Observações ou restrições (descrições ou códigos, se houver)
- UF (estado) emissor da CNH
- Local de nascimento (cidade e UF)
- Filiação (nome dos pais ou responsáveis legais)
- RG (número do documento de identidade, se disponível)

Se algum campo não estiver presente ou legível, retorne exatamente: `"Não foi possível localizar este campo"`.

Texto do documento:
{document_text}

Responda exclusivamente no seguinte formato JSON, respeitando a estrutura abaixo:

{{
  "tipo_documento": "{document_type}",
  "nome": "...",
  "numero_registro": "...",
  "cpf": "...",
  "data_nascimento": "...",
  "data_primeira_habilitacao": "...",
  "validade": "...",
  "categoria": "...",
  "restricoes": "...",
  "uf_emissor": "...",
  "local_nascimento": "...",
  "filiacao": "...",
  "rg": "..."
}}
"""