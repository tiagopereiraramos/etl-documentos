"""
Utilitários para processamento de texto
"""
import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json


def normalizar_texto(texto: str) -> str:
    """Normaliza texto removendo caracteres especiais e normalizando espaços"""
    if not texto:
        return ""

    # Remove acentos
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))

    # Converte para minúsculas
    texto = texto.lower()

    # Remove caracteres especiais, mantendo apenas letras, números e espaços
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)

    # Normaliza espaços (remove múltiplos espaços)
    texto = re.sub(r'\s+', ' ', texto)

    return texto.strip()


def extrair_numeros(texto: str) -> List[str]:
    """Extrai números de um texto"""
    if not texto:
        return []

    # Padrão para números (inteiros e decimais)
    padrao = r'\d+(?:[.,]\d+)?'
    return re.findall(padrao, texto)


def extrair_datas(texto: str) -> List[str]:
    """Extrai datas de um texto"""
    if not texto:
        return []

    # Padrões comuns de data
    padroes = [
        r'\d{2}/\d{2}/\d{4}',  # DD/MM/AAAA
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-AAAA
        r'\d{4}-\d{2}-\d{2}',  # AAAA-MM-DD
        r'\d{2}/\d{2}/\d{2}',  # DD/MM/AA
    ]

    datas = []
    for padrao in padroes:
        datas.extend(re.findall(padrao, texto))

    return datas


def extrair_valores_monetarios(texto: str) -> List[str]:
    """Extrai valores monetários de um texto"""
    if not texto:
        return []

    # Padrões para valores monetários
    padroes = [
        r'R\$\s*\d+(?:[.,]\d{3})*(?:[.,]\d{2})?',  # R$ 1.234,56
        r'R\$\s*\d+(?:[.,]\d{2})?',  # R$ 1234,56
        r'\d+(?:[.,]\d{3})*(?:[.,]\d{2})?\s*reais?',  # 1.234,56 reais
        r'\d+(?:[.,]\d{2})?\s*reais?',  # 1234,56 reais
    ]

    valores = []
    for padrao in padroes:
        valores.extend(re.findall(padrao, texto, re.IGNORECASE))

    return valores


def extrair_cnpj_cpf(texto: str) -> List[str]:
    """Extrai CNPJ e CPF de um texto"""
    if not texto:
        return []

    # Remove caracteres não numéricos
    texto_limpo = re.sub(r'[^\d]', '', texto)

    documentos = []

    # Procura por CNPJ (14 dígitos)
    cnpjs = re.findall(r'\d{14}', texto_limpo)
    documentos.extend(cnpjs)

    # Procura por CPF (11 dígitos)
    cpfs = re.findall(r'\d{11}', texto_limpo)
    documentos.extend(cpfs)

    return documentos


def extrair_emails(texto: str) -> List[str]:
    """Extrai emails de um texto"""
    if not texto:
        return []

    padrao = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(padrao, texto)


def extrair_telefones(texto: str) -> List[str]:
    """Extrai números de telefone de um texto"""
    if not texto:
        return []

    # Remove caracteres não numéricos
    texto_limpo = re.sub(r'[^\d]', '', texto)

    # Padrões para telefones brasileiros
    padroes = [
        r'\d{10}',  # 10 dígitos (DDD + número)
        r'\d{11}',  # 11 dígitos (DDD + número com 9)
    ]

    telefones = []
    for padrao in padroes:
        telefones.extend(re.findall(padrao, texto_limpo))

    return telefones


def extrair_ceps(texto: str) -> List[str]:
    """Extrai CEPs de um texto"""
    if not texto:
        return []

    # Remove caracteres não numéricos
    texto_limpo = re.sub(r'[^\d]', '', texto)

    # CEP tem 8 dígitos
    padrao = r'\d{8}'
    return re.findall(padrao, texto_limpo)


def calcular_similaridade_texto(texto1: str, texto2: str) -> float:
    """Calcula similaridade entre dois textos usando Jaccard"""
    if not texto1 or not texto2:
        return 0.0

    # Normaliza textos
    texto1_norm = set(normalizar_texto(texto1).split())
    texto2_norm = set(normalizar_texto(texto2).split())

    if not texto1_norm or not texto2_norm:
        return 0.0

    # Calcula similaridade Jaccard
    intersecao = len(texto1_norm.intersection(texto2_norm))
    uniao = len(texto1_norm.union(texto2_norm))

    return intersecao / uniao if uniao > 0 else 0.0


def dividir_texto_em_chunks(texto: str, tamanho_chunk: int = 1000,
                            sobreposicao: int = 100) -> List[str]:
    """Divide texto em chunks menores"""
    if not texto:
        return []

    if len(texto) <= tamanho_chunk:
        return [texto]

    chunks = []
    inicio = 0

    while inicio < len(texto):
        fim = inicio + tamanho_chunk

        # Se não é o último chunk, tenta quebrar em uma palavra
        if fim < len(texto):
            # Procura o último espaço antes do fim
            ultimo_espaco = texto.rfind(' ', inicio, fim)
            if ultimo_espaco > inicio:
                fim = ultimo_espaco

        chunk = texto[inicio:fim].strip()
        if chunk:
            chunks.append(chunk)

        inicio = fim - sobreposicao
        if inicio >= len(texto):
            break

    return chunks


def limpar_texto_html(texto: str) -> str:
    """Remove tags HTML de um texto"""
    if not texto:
        return ""

    # Remove tags HTML
    texto = re.sub(r'<[^>]+>', '', texto)

    # Remove entidades HTML
    texto = re.sub(r'&[a-zA-Z]+;', '', texto)
    texto = re.sub(r'&#\d+;', '', texto)

    # Normaliza espaços
    texto = re.sub(r'\s+', ' ', texto)

    return texto.strip()


def extrair_palavras_chave(texto: str, min_frequencia: int = 2) -> List[Tuple[str, int]]:
    """Extrai palavras-chave de um texto baseado na frequência"""
    if not texto:
        return []

    # Normaliza texto
    texto_norm = normalizar_texto(texto)

    # Remove palavras comuns (stop words)
    stop_words = {
        'a', 'o', 'e', 'de', 'do', 'da', 'em', 'um', 'para', 'com', 'não', 'na',
        'se', 'que', 'por', 'mais', 'as', 'como', 'mas', 'foi', 'ele', 'das',
        'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos',
        'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela',
        'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'suas',
        'minha', 'têm', 'naquele', 'essas', 'esses', 'pelos', 'elas', 'estava',
        'seja', 'qual', 'será', 'nós', 'tenho', 'lhe', 'deles', 'essas', 'esses',
        'pelas', 'este', 'fosse', 'dele', 'tu', 'te', 'você', 'vocês', 'lhes',
        'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'nosso', 'nossa',
        'nossos', 'nossas', 'dela', 'delas', 'esta', 'estes', 'estas', 'aquele',
        'aquela', 'aqueles', 'aquelas', 'isto', 'aquilo', 'estou', 'está',
        'estamos', 'estão', 'estive', 'esteve', 'estivemos', 'estiveram',
        'estava', 'estávamos', 'estavam', 'estivera', 'estivéramos', 'esteja',
        'estejamos', 'estejam', 'estivesse', 'estivéssemos', 'estivessem',
        'estiver', 'estivermos', 'estiverem', 'hei', 'há', 'havemos', 'hão',
        'houve', 'houvemos', 'houveram', 'houvera', 'houvéramos', 'haja',
        'hajamos', 'hajam', 'houvesse', 'houvéssemos', 'houvessem', 'houver',
        'houvermos', 'houverem', 'houverei', 'houverá', 'houveremos', 'houverão',
        'houveria', 'houveríamos', 'houveriam', 'sou', 'somos', 'são', 'era',
        'éramos', 'eram', 'fui', 'foi', 'fomos', 'foram', 'fora', 'fôramos',
        'seja', 'sejamos', 'sejam', 'fosse', 'fôssemos', 'fossem', 'for',
        'formos', 'forem', 'serei', 'será', 'seremos', 'serão', 'seria',
        'seríamos', 'seriam', 'tenho', 'tem', 'temos', 'têm', 'tinha',
        'tínhamos', 'tinham', 'tive', 'teve', 'tivemos', 'tiveram', 'tivera',
        'tivéramos', 'tenha', 'tenhamos', 'tenham', 'tivesse', 'tivéssemos',
        'tivessem', 'tiver', 'tivermos', 'tiverem', 'terei', 'terá', 'teremos',
        'terão', 'teria', 'teríamos', 'teriam'
    }

    # Divide em palavras
    palavras = texto_norm.split()

    # Filtra palavras comuns e muito curtas
    palavras_filtradas = [
        palavra for palavra in palavras
        if palavra not in stop_words and len(palavra) > 2
    ]

    # Conta frequência
    frequencia = {}
    for palavra in palavras_filtradas:
        frequencia[palavra] = frequencia.get(palavra, 0) + 1

    # Filtra por frequência mínima e ordena
    palavras_chave = [
        (palavra, freq) for palavra, freq in frequencia.items()
        if freq >= min_frequencia
    ]

    return sorted(palavras_chave, key=lambda x: x[1], reverse=True)


def validar_json(texto: str) -> bool:
    """Valida se um texto é um JSON válido"""
    try:
        json.loads(texto)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def extrair_json(texto: str) -> Optional[Dict[str, Any]]:
    """Extrai JSON de um texto"""
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return None


def formatar_texto_para_exibicao(texto: str, max_comprimento: int = 100) -> str:
    """Formata texto para exibição, truncando se necessário"""
    if not texto:
        return ""

    if len(texto) <= max_comprimento:
        return texto

    # Trunca e adiciona reticências
    return texto[:max_comprimento-3] + "..."


def contar_palavras(texto: str) -> int:
    """Conta o número de palavras em um texto"""
    if not texto:
        return 0

    return len(texto.split())


def contar_caracteres(texto: str, incluir_espacos: bool = True) -> int:
    """Conta o número de caracteres em um texto"""
    if not texto:
        return 0

    if incluir_espacos:
        return len(texto)
    else:
        return len(texto.replace(' ', ''))


def obter_resumo_texto(texto: str, max_palavras: int = 50) -> str:
    """Gera um resumo do texto com número máximo de palavras"""
    if not texto:
        return ""

    palavras = texto.split()

    if len(palavras) <= max_palavras:
        return texto

    return ' '.join(palavras[:max_palavras]) + "..."
