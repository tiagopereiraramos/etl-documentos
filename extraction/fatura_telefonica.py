from .extraction_base import BaseExtractor

class FaturaTelefonicaExtractor(BaseExtractor):
    """Extractor for Fatura Telefônica documents."""
    
    def _get_document_type(self) -> str:
        return "Fatura Telefônica"
    
    def _get_prompt_template(self) -> str:
        return """
Você é um agente que extrai informações de documentos de **{document_type}**. 
Extraia os seguintes campos formatando no encoding UTF-8:

- Nome do cliente
- CPF/CNPJ do cliente (manter formato original do documento)
- Operadora de telefonia (ex: Vivo, Claro, Tim, Oi)
- Número da linha telefônica (com DDD)
- Número da fatura/conta
- Mês de referência da fatura
- Período de cobrança (data inicial e final)
- Valor total da fatura (em R$)
- Data de vencimento
- Código de barras (se disponível)
- Consumo detalhado (resumo de ligações, internet, serviços adicionais)

Caso um campo não esteja presente, retorne "Não foi possível localizar este campo".

Texto do documento:
{document_text}

Responda no seguinte formato JSON:
{{
  "tipo_documento": "{document_type}",
  "nome_cliente": "...",
  "cpf_cnpj": "...",
  "operadora": "...",
  "numero_telefone": "...",
  "numero_fatura": "...",
  "mes_referencia": "...",
  "periodo_cobranca": "...",
  "valor_total": "...",
  "data_vencimento": "...",
  "codigo_barras": "...",
  "consumo_detalhado": {{
    "ligacoes": "...",
    "internet": "...",
    "mensagens": "...",
    "servicos_adicionais": "..."
  }}
}}
"""