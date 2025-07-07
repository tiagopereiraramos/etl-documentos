"""
Validadores para o sistema ETL Documentos
"""
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from app.models.enums import TipoDocumento, FormatoArquivo
from app.core.exceptions import ValidacaoException


def validar_email(email: str) -> bool:
    """Valida formato de email"""
    if not email:
        return False

    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(padrao, email))


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ"""
    if not cnpj:
        return False

    # Remove caracteres não numéricos
    cnpj_limpo = re.sub(r'[^\d]', '', cnpj)

    # Verifica se tem 14 dígitos
    if len(cnpj_limpo) != 14:
        return False

    # Verifica se todos os dígitos são iguais
    if len(set(cnpj_limpo)) == 1:
        return False

    # Validação dos dígitos verificadores
    def calcular_digito(cnpj: str, posicao: int) -> int:
        peso = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        if posicao == 2:
            peso = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        soma = sum(int(cnpj[i]) * peso[i] for i in range(len(peso)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    # Calcula primeiro dígito verificador
    digito1 = calcular_digito(cnpj_limpo[:12], 1)
    if int(cnpj_limpo[12]) != digito1:
        return False

    # Calcula segundo dígito verificador
    digito2 = calcular_digito(cnpj_limpo[:13], 2)
    if int(cnpj_limpo[13]) != digito2:
        return False

    return True


def validar_cpf(cpf: str) -> bool:
    """Valida CPF"""
    if not cpf:
        return False

    # Remove caracteres não numéricos
    cpf_limpo = re.sub(r'[^\d]', '', cpf)

    # Verifica se tem 11 dígitos
    if len(cpf_limpo) != 11:
        return False

    # Verifica se todos os dígitos são iguais
    if len(set(cpf_limpo)) == 1:
        return False

    # Validação dos dígitos verificadores
    def calcular_digito_cpf(cpf: str, posicao: int) -> int:
        peso = [10, 9, 8, 7, 6, 5, 4, 3, 2]
        if posicao == 2:
            peso = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]

        soma = sum(int(cpf[i]) * peso[i] for i in range(len(peso)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    # Calcula primeiro dígito verificador
    digito1 = calcular_digito_cpf(cpf_limpo[:9], 1)
    if int(cpf_limpo[9]) != digito1:
        return False

    # Calcula segundo dígito verificador
    digito2 = calcular_digito_cpf(cpf_limpo[:10], 2)
    if int(cpf_limpo[10]) != digito2:
        return False

    return True


def validar_cep(cep: str) -> bool:
    """Valida CEP"""
    if not cep:
        return False

    # Remove caracteres não numéricos
    cep_limpo = re.sub(r'[^\d]', '', cep)

    # Verifica se tem 8 dígitos
    return len(cep_limpo) == 8


def validar_telefone(telefone: str) -> bool:
    """Valida telefone brasileiro"""
    if not telefone:
        return False

    # Remove caracteres não numéricos
    telefone_limpo = re.sub(r'[^\d]', '', telefone)

    # Verifica se tem 10 ou 11 dígitos
    return len(telefone_limpo) in [10, 11]


def validar_data(data: str, formato: str = "%d/%m/%Y") -> bool:
    """Valida formato de data"""
    if not data:
        return False

    try:
        datetime.strptime(data, formato)
        return True
    except ValueError:
        return False


def validar_valor_monetario(valor: str) -> bool:
    """Valida valor monetário brasileiro"""
    if not valor:
        return False

    # Padrões para valores monetários
    padroes = [
        r'^R\$\s*\d+(?:[.,]\d{3})*(?:[.,]\d{2})?$',  # R$ 1.234,56
        r'^R\$\s*\d+(?:[.,]\d{2})?$',  # R$ 1234,56
        r'^\d+(?:[.,]\d{3})*(?:[.,]\d{2})?\s*reais?$',  # 1.234,56 reais
        r'^\d+(?:[.,]\d{2})?\s*reais?$',  # 1234,56 reais
    ]

    for padrao in padroes:
        if re.match(padrao, valor, re.IGNORECASE):
            return True

    return False


def validar_tipo_documento(tipo: str) -> bool:
    """Valida tipo de documento"""
    if not tipo:
        return False

    tipos_validos = TipoDocumento.get_all_types()
    return tipo in tipos_validos


def validar_extensao_arquivo(extensao: str) -> bool:
    """Valida extensão de arquivo"""
    if not extensao:
        return False

    extensoes_validas = FormatoArquivo.get_all_extensions()
    return extensao.lower() in extensoes_validas


def validar_tamanho_arquivo(tamanho: int, max_tamanho: int) -> bool:
    """Valida tamanho de arquivo"""
    return 0 < tamanho <= max_tamanho


def validar_json_schema(dados: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Valida dados contra um schema JSON"""
    erros = []

    for campo, regras in schema.items():
        valor = dados.get(campo)

        # Verifica se campo é obrigatório
        if regras.get('obrigatorio', False) and valor is None:
            erros.append(f"Campo '{campo}' é obrigatório")
            continue

        # Se valor é None e não é obrigatório, pula validação
        if valor is None:
            continue

        # Valida tipo
        tipo_esperado = regras.get('tipo')
        if tipo_esperado and not isinstance(valor, tipo_esperado):
            erros.append(
                f"Campo '{campo}' deve ser do tipo {tipo_esperado.__name__}")
            continue

        # Validações específicas por tipo
        if isinstance(valor, str):
            erros.extend(_validar_string(valor, campo, regras))
        elif isinstance(valor, int):
            erros.extend(_validar_inteiro(valor, campo, regras))
        elif isinstance(valor, float):
            erros.extend(_validar_float(valor, campo, regras))
        elif isinstance(valor, list):
            erros.extend(_validar_lista(valor, campo, regras))
        elif isinstance(valor, dict):
            erros.extend(_validar_dict(valor, campo, regras))

    return erros


def _validar_string(valor: str, campo: str, regras: Dict[str, Any]) -> List[str]:
    """Validações específicas para strings"""
    erros = []

    # Comprimento mínimo
    min_len = regras.get('min_len')
    if min_len and len(valor) < min_len:
        erros.append(
            f"Campo '{campo}' deve ter pelo menos {min_len} caracteres")

    # Comprimento máximo
    max_len = regras.get('max_len')
    if max_len and len(valor) > max_len:
        erros.append(
            f"Campo '{campo}' deve ter no máximo {max_len} caracteres")

    # Padrão regex
    padrao = regras.get('padrao')
    if padrao and not re.match(padrao, valor):
        erros.append(f"Campo '{campo}' não está no formato esperado")

    # Validações específicas
    if regras.get('email') and not validar_email(valor):
        erros.append(f"Campo '{campo}' deve ser um email válido")

    if regras.get('cnpj') and not validar_cnpj(valor):
        erros.append(f"Campo '{campo}' deve ser um CNPJ válido")

    if regras.get('cpf') and not validar_cpf(valor):
        erros.append(f"Campo '{campo}' deve ser um CPF válido")

    if regras.get('cep') and not validar_cep(valor):
        erros.append(f"Campo '{campo}' deve ser um CEP válido")

    if regras.get('telefone') and not validar_telefone(valor):
        erros.append(f"Campo '{campo}' deve ser um telefone válido")

    if regras.get('data') and not validar_data(valor):
        erros.append(f"Campo '{campo}' deve ser uma data válida")

    if regras.get('valor_monetario') and not validar_valor_monetario(valor):
        erros.append(f"Campo '{campo}' deve ser um valor monetário válido")

    return erros


def _validar_inteiro(valor: int, campo: str, regras: Dict[str, Any]) -> List[str]:
    """Validações específicas para inteiros"""
    erros = []

    # Valor mínimo
    min_valor = regras.get('min')
    if min_valor is not None and valor < min_valor:
        erros.append(f"Campo '{campo}' deve ser maior ou igual a {min_valor}")

    # Valor máximo
    max_valor = regras.get('max')
    if max_valor is not None and valor > max_valor:
        erros.append(f"Campo '{campo}' deve ser menor ou igual a {max_valor}")

    return erros


def _validar_float(valor: float, campo: str, regras: Dict[str, Any]) -> List[str]:
    """Validações específicas para floats"""
    erros = []

    # Valor mínimo
    min_valor = regras.get('min')
    if min_valor is not None and valor < min_valor:
        erros.append(f"Campo '{campo}' deve ser maior ou igual a {min_valor}")

    # Valor máximo
    max_valor = regras.get('max')
    if max_valor is not None and valor > max_valor:
        erros.append(f"Campo '{campo}' deve ser menor ou igual a {max_valor}")

    return erros


def _validar_lista(valor: List, campo: str, regras: Dict[str, Any]) -> List[str]:
    """Validações específicas para listas"""
    erros = []

    # Tamanho mínimo
    min_len = regras.get('min_len')
    if min_len and len(valor) < min_len:
        erros.append(f"Campo '{campo}' deve ter pelo menos {min_len} itens")

    # Tamanho máximo
    max_len = regras.get('max_len')
    if max_len and len(valor) > max_len:
        erros.append(f"Campo '{campo}' deve ter no máximo {max_len} itens")

    # Validação de itens
    schema_item = regras.get('schema_item')
    if schema_item:
        for i, item in enumerate(valor):
            if isinstance(item, dict):
                erros_item = validar_json_schema(item, schema_item)
                for erro in erros_item:
                    erros.append(f"Campo '{campo}[{i}]': {erro}")

    return erros


def _validar_dict(valor: Dict, campo: str, regras: Dict[str, Any]) -> List[str]:
    """Validações específicas para dicionários"""
    erros = []

    # Schema aninhado
    schema = regras.get('schema')
    if schema:
        erros.extend(validar_json_schema(valor, schema))

    return erros


def validar_dados_documento(dados: Dict[str, Any], tipo_documento: str) -> List[str]:
    """Valida dados extraídos de documento baseado no tipo"""
    if not validar_tipo_documento(tipo_documento):
        return [f"Tipo de documento '{tipo_documento}' não é válido"]

    # Schemas específicos por tipo de documento
    schemas = {
        "Comprovante Bancário": {
            "razao_social": {"tipo": str, "obrigatorio": True, "min_len": 2},
            "agencia": {"tipo": str, "obrigatorio": False},
            "conta": {"tipo": str, "obrigatorio": False},
            "nome_banco": {"tipo": str, "obrigatorio": True, "min_len": 2},
            "codigo_banco": {"tipo": str, "obrigatorio": False},
            "valor": {"tipo": str, "obrigatorio": True, "valor_monetario": True},
            "data_transacao": {"tipo": str, "obrigatorio": True, "data": True},
            "tipo_operacao": {"tipo": str, "obrigatorio": False},
            "numero_comprovante": {"tipo": str, "obrigatorio": False},
            "cnpj_cpf": {"tipo": str, "obrigatorio": False}
        },
        "CNH": {
            "nome": {"tipo": str, "obrigatorio": True, "min_len": 2},
            "cpf": {"tipo": str, "obrigatorio": True, "cpf": True},
            "numero_registro": {"tipo": str, "obrigatorio": True},
            "categoria": {"tipo": str, "obrigatorio": True},
            "data_emissao": {"tipo": str, "obrigatorio": True, "data": True},
            "data_vencimento": {"tipo": str, "obrigatorio": True, "data": True}
        },
        "Cartão CNPJ": {
            "razao_social": {"tipo": str, "obrigatorio": True, "min_len": 2},
            "cnpj": {"tipo": str, "obrigatorio": True, "cnpj": True},
            "nome_fantasia": {"tipo": str, "obrigatorio": False},
            "data_abertura": {"tipo": str, "obrigatorio": True, "data": True},
            "cnae": {"tipo": str, "obrigatorio": False},
            "natureza_juridica": {"tipo": str, "obrigatorio": False},
            "endereco": {"tipo": str, "obrigatorio": False},
            "situacao": {"tipo": str, "obrigatorio": False}
        }
    }

    schema = schemas.get(tipo_documento, {})
    return validar_json_schema(dados, schema)


def validar_configuracao(config: Dict[str, Any]) -> List[str]:
    """Valida configuração do sistema"""
    erros = []

    # Validações básicas
    if not config.get('api'):
        erros.append("Configuração da API é obrigatória")

    if not config.get('database'):
        erros.append("Configuração do banco de dados é obrigatória")

    if not config.get('llm'):
        erros.append("Configuração de LLM é obrigatória")

    # Validações específicas
    api_config = config.get('api', {})
    if not api_config.get('secret_key'):
        erros.append("SECRET_KEY é obrigatória")

    llm_config = config.get('llm', {})
    if not llm_config.get('openai_api_key'):
        erros.append("OPENAI_API_KEY é obrigatória")

    return erros


def validar_upload_arquivo(nome_arquivo: str, tamanho: int, extensao: str) -> List[str]:
    """Valida upload de arquivo"""
    erros = []

    if not nome_arquivo:
        erros.append("Nome do arquivo é obrigatório")

    if not validar_extensao_arquivo(extensao):
        erros.append(f"Extensão '{extensao}' não é suportada")

    if not validar_tamanho_arquivo(tamanho, 10 * 1024 * 1024):  # 10MB
        erros.append("Tamanho do arquivo excede o limite de 10MB")

    return erros
