from .extraction_base import BaseExtractor

class ComprovanteBancarioExtractor(BaseExtractor):
    """Extractor for Comprovante Bancário documents."""
    
    def _get_document_type(self) -> str:
        return "Comprovante Bancário"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente que extrai informações de documentos de **{document_type}**. 
Extraia os seguintes campos formatando no encoding UTF-8:

- Razão Social: Nome oficial da empresa ou pessoa registrada para fins legais e fiscais.
  Pode aparecer como "beneficiário", "favorecido", "cliente", "titular" ou similar.

- Agência: Código numérico que identifica a agência bancária onde a conta está registrada.
  Geralmente possui de 4 a 5 dígitos, podendo incluir um dígito verificador separado por hífen.
  Exemplos: "1234", "1234-5", "00123".

- Conta: Número único que identifica a conta do cliente na instituição financeira.
  Geralmente possui formato numérico, podendo incluir um dígito verificador separado por hífen.
  Exemplos: "12345-6", "123456-7", "00012345-X".

- Nome do Banco: Nome da instituição financeira onde a conta bancária está registrada.
  Exemplos: "Banco do Brasil", "Caixa Econômica Federal", "Itaú", "Bradesco", "Santander".

- Código do Banco: Código numérico de 3 dígitos que identifica a instituição financeira no sistema bancário.
  Exemplos: "001" (Banco do Brasil), "104" (Caixa), "341" (Itaú).
  Se não estiver explícito no documento, tente identificá-lo a partir do nome do banco.

- Valor: Quantia monetária envolvida na transação bancária.
  Deve incluir o valor numérico com separador decimal (vírgula ou ponto) e a moeda quando disponível.
  Exemplos: "R$ 1.234,56", "1.234,56", "R$ 1234.56".

- Data da Transação: Data em que a operação bancária foi realizada.
  Deve ser fornecida no formato "DD/MM/AAAA" quando disponível.

- Tipo de Transação: Natureza da operação bancária realizada.
  Exemplos: "Transferência", "TED", "DOC", "Pagamento", "Depósito", "PIX".


**Observação importante**:
- Caso não encontre qualquer um dos campos baseado nas características sugeridas acima, retorne o resulto para o campo como "Não foi possível localizar este campo.    
- Se o "Código do Banco" não estiver explicitamente presente no texto, utilize o "Nome do Banco" para pesquisá-lo na lista oficial de códigos de bancos brasileiros do Banco Central ou outra referência confiável.

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "razao_social": "...",
  "agencia": "...",
  "conta": "...",
  "nome_banco": "...",
  "codigo_banco": "...",
  "valor": "...",
  "data_transacao": "...",
  "tipo_transacao": "..."
}}
"""