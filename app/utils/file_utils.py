"""
Utilitários para manipulação de arquivos
"""
import os
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
import mimetypes
from app.core.config import settings
from app.core.exceptions import FileProcessingError, ValidationError
from app.core.logging import obter_logger

logger = obter_logger(__name__)


def gerar_id_arquivo() -> str:
    """Gera um ID único para arquivo"""
    return str(uuid.uuid4())


def calcular_hash_arquivo(conteudo: bytes) -> str:
    """Calcula hash SHA-256 do conteúdo do arquivo"""
    return hashlib.sha256(conteudo).hexdigest()


def validar_extensao_arquivo(nome_arquivo: str) -> bool:
    """Valida se a extensão do arquivo é suportada"""
    extensao = Path(nome_arquivo).suffix.lower()
    return extensao in settings.storage.allowed_extensions


def obter_extensao_arquivo(nome_arquivo: str) -> str:
    """Obtém a extensão do arquivo"""
    return Path(nome_arquivo).suffix.lower()


def obter_nome_arquivo_sem_extensao(nome_arquivo: str) -> str:
    """Obtém o nome do arquivo sem extensão"""
    return Path(nome_arquivo).stem


def obter_tipo_mime(extensao: str) -> str:
    """Obtém o tipo MIME baseado na extensão"""
    mime_type, _ = mimetypes.guess_type(f"arquivo{extensao}")
    return mime_type or "application/octet-stream"


def validar_tamanho_arquivo(tamanho: int) -> bool:
    """Valida se o tamanho do arquivo está dentro do limite"""
    return tamanho <= settings.storage.max_file_size


def criar_caminho_arquivo(documento_id: str, extensao: str) -> Path:
    """Cria caminho para salvar arquivo"""
    data_atual = datetime.now()
    ano_mes = data_atual.strftime("%Y/%m")

    caminho = Path(settings.storage.upload_dir) / \
        ano_mes / f"{documento_id}{extensao}"
    caminho.parent.mkdir(parents=True, exist_ok=True)

    return caminho


def salvar_arquivo(conteudo: bytes, documento_id: str, extensao: str) -> Path:
    """Salva arquivo no sistema de arquivos"""
    caminho = criar_caminho_arquivo(documento_id, extensao)

    with open(caminho, 'wb') as f:
        f.write(conteudo)

    return caminho


def ler_arquivo(caminho: Path) -> bytes:
    """Lê conteúdo de um arquivo"""
    with open(caminho, 'rb') as f:
        return f.read()


def deletar_arquivo(caminho: Path) -> bool:
    """Deleta um arquivo do sistema"""
    try:
        if caminho.exists():
            caminho.unlink()
            return True
        return False
    except Exception:
        return False


def obter_informacoes_arquivo(caminho: Path) -> dict:
    """Obtém informações detalhadas de um arquivo"""
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    stat = caminho.stat()

    return {
        "nome": caminho.name,
        "extensao": caminho.suffix,
        "tamanho": stat.st_size,
        "tipo_mime": obter_tipo_mime(caminho.suffix),
        "data_criacao": datetime.fromtimestamp(stat.st_ctime),
        "data_modificacao": datetime.fromtimestamp(stat.st_mtime),
        "hash": calcular_hash_arquivo(ler_arquivo(caminho))
    }


def limpar_arquivos_temporarios(diretorio: Path, max_idade_horas: int = 24) -> int:
    """Remove arquivos temporários mais antigos que o limite"""
    if not diretorio.exists():
        return 0

    agora = datetime.now()
    arquivos_removidos = 0

    for arquivo in diretorio.rglob("*"):
        if arquivo.is_file():
            idade = agora - datetime.fromtimestamp(arquivo.stat().st_mtime)
            if idade.total_seconds() > max_idade_horas * 3600:
                try:
                    arquivo.unlink()
                    arquivos_removidos += 1
                except Exception:
                    continue

    return arquivos_removidos


def obter_estatisticas_diretorio(diretorio: Path) -> dict:
    """Obtém estatísticas de um diretório"""
    if not diretorio.exists():
        return {
            "total_arquivos": 0,
            "tamanho_total": 0,
            "extensoes": {},
            "arquivos_por_data": {}
        }

    total_arquivos = 0
    tamanho_total = 0
    extensoes = {}
    arquivos_por_data = {}

    for arquivo in diretorio.rglob("*"):
        if arquivo.is_file():
            total_arquivos += 1
            tamanho_total += arquivo.stat().st_size

            # Contar extensões
            extensao = arquivo.suffix.lower()
            extensoes[extensao] = extensoes.get(extensao, 0) + 1

            # Contar por data
            data = datetime.fromtimestamp(arquivo.stat().st_mtime).date()
            data_str = data.isoformat()
            arquivos_por_data[data_str] = arquivos_por_data.get(
                data_str, 0) + 1

    return {
        "total_arquivos": total_arquivos,
        "tamanho_total": tamanho_total,
        "tamanho_total_mb": round(tamanho_total / (1024 * 1024), 2),
        "extensoes": extensoes,
        "arquivos_por_data": arquivos_por_data
    }


def criar_backup_arquivo(caminho_original: Path, sufixo: str = ".backup") -> Path:
    """Cria backup de um arquivo"""
    if not caminho_original.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_original}")

    caminho_backup = caminho_original.with_suffix(
        caminho_original.suffix + sufixo)

    # Copiar arquivo
    with open(caminho_original, 'rb') as src, open(caminho_backup, 'wb') as dst:
        dst.write(src.read())

    return caminho_backup


def restaurar_backup_arquivo(caminho_backup: Path) -> Path:
    """Restaura arquivo a partir do backup"""
    if not caminho_backup.exists():
        raise FileNotFoundError(f"Backup não encontrado: {caminho_backup}")

    # Remove sufixo .backup
    caminho_original = caminho_backup.with_suffix(
        caminho_backup.suffix.replace('.backup', ''))

    # Copiar backup para original
    with open(caminho_backup, 'rb') as src, open(caminho_original, 'wb') as dst:
        dst.write(src.read())

    return caminho_original


def validar_integridade_arquivo(caminho: Path, hash_esperado: str) -> bool:
    """Valida integridade de um arquivo comparando hashes"""
    if not caminho.exists():
        return False

    hash_atual = calcular_hash_arquivo(ler_arquivo(caminho))
    return hash_atual == hash_esperado


def obter_arquivos_por_tipo(diretorio: Path, extensao: str) -> List[Path]:
    """Obtém lista de arquivos por extensão"""
    if not diretorio.exists():
        return []

    return list(diretorio.rglob(f"*{extensao}"))


def compactar_diretorio(diretorio: Path, arquivo_saida: Path) -> bool:
    """Compacta um diretório em arquivo ZIP"""
    try:
        import zipfile

        with zipfile.ZipFile(arquivo_saida, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for arquivo in diretorio.rglob("*"):
                if arquivo.is_file():
                    # Adiciona arquivo relativo ao diretório base
                    zipf.write(arquivo, arquivo.relative_to(diretorio))

        return True
    except Exception:
        return False


def descompactar_arquivo(arquivo_zip: Path, diretorio_destino: Path) -> bool:
    """Descompacta arquivo ZIP"""
    try:
        import zipfile

        diretorio_destino.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(arquivo_zip, 'r') as zipf:
            zipf.extractall(diretorio_destino)

        return True
    except Exception:
        return False


def generate_file_id() -> str:
    """Gera um ID único para arquivo"""
    return str(uuid.uuid4())


def generate_file_hash(content: bytes) -> str:
    """Gera hash SHA-256 do conteúdo do arquivo"""
    return hashlib.sha256(content).hexdigest()


def get_file_extension(filename: str) -> str:
    """Extrai a extensão do arquivo"""
    return Path(filename).suffix.lower()


def is_allowed_extension(filename: str) -> bool:
    """Verifica se a extensão do arquivo é permitida"""
    extension = get_file_extension(filename)
    return extension in settings.storage.allowed_extensions


def validate_file_size(content: bytes) -> bool:
    """Valida se o tamanho do arquivo está dentro do limite"""
    return len(content) <= settings.storage.max_file_size


def get_file_mime_type(filename: str, content: Optional[bytes] = None) -> str:
    """Determina o tipo MIME do arquivo"""
    # Tentar por extensão primeiro
    mime_type, _ = mimetypes.guess_type(filename)

    if mime_type:
        return mime_type

    # Fallback para tipos comuns
    extension = get_file_extension(filename)
    mime_mapping = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.tiff': 'image/tiff',
        '.bmp': 'image/bmp',
        '.txt': 'text/plain',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword'
    }

    return mime_mapping.get(extension, 'application/octet-stream')


def sanitize_filename(filename: str) -> str:
    """Sanitiza o nome do arquivo removendo caracteres perigosos"""
    # Remover caracteres perigosos
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    sanitized = filename

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')

    # Remover espaços em branco no início e fim
    sanitized = sanitized.strip()

    # Limitar tamanho
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext

    return sanitized


def create_file_path(filename: str, user_id: Optional[str] = None) -> str:
    """Cria o caminho completo para o arquivo"""
    # Sanitizar nome do arquivo
    safe_filename = sanitize_filename(filename)

    # Criar estrutura de diretórios
    timestamp = datetime.now().strftime("%Y/%m/%d")
    if user_id:
        file_path = Path(settings.storage.upload_dir) / \
            user_id / timestamp / safe_filename
    else:
        file_path = Path(settings.storage.upload_dir) / \
            timestamp / safe_filename

    # Criar diretórios se não existirem
    file_path.parent.mkdir(parents=True, exist_ok=True)

    return str(file_path)


def save_file(content: bytes, filename: str, user_id: Optional[str] = None) -> Tuple[str, str]:
    """Salva o arquivo e retorna o caminho e hash"""
    try:
        # Validar arquivo
        if not is_allowed_extension(filename):
            raise ValidationError(
                message=f"Extensão não permitida: {get_file_extension(filename)}",
                error_code="INVALID_FILE_EXTENSION",
                details={"filename": filename,
                         "extension": get_file_extension(filename)}
            )

        if not validate_file_size(content):
            raise ValidationError(
                message="Arquivo muito grande",
                error_code="FILE_TOO_LARGE",
                details={
                    "file_size": len(content),
                    "max_size": settings.storage.max_file_size
                }
            )

        # Gerar hash
        file_hash = generate_file_hash(content)

        # Criar caminho do arquivo
        file_path = create_file_path(filename, user_id)

        # Salvar arquivo
        with open(file_path, 'wb') as f:
            f.write(content)

        logger.info(
            f"Arquivo salvo com sucesso: {filename}",
            operation="file_save",
            status="success",
            metadata={
                "filename": filename,
                "file_path": file_path,
                "file_size": len(content),
                "file_hash": file_hash,
                "user_id": user_id
            }
        )

        return file_path, file_hash

    except Exception as e:
        logger.error(
            f"Erro ao salvar arquivo: {filename}",
            operation="file_save",
            status="error",
            metadata={
                "filename": filename,
                "error": str(e),
                "user_id": user_id
            }
        )
        raise FileProcessingError(
            message=f"Erro ao salvar arquivo: {str(e)}",
            error_code="FILE_SAVE_ERROR",
            details={"filename": filename}
        )


def delete_file(file_path: str) -> bool:
    """Deleta um arquivo do sistema"""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info(
                f"Arquivo deletado: {file_path}",
                operation="file_delete",
                status="success"
            )
            return True
        else:
            logger.warning(
                f"Arquivo não encontrado para deletar: {file_path}",
                operation="file_delete",
                status="warning"
            )
            return False

    except Exception as e:
        logger.error(
            f"Erro ao deletar arquivo: {file_path}",
            operation="file_delete",
            status="error",
            metadata={"error": str(e)}
        )
        raise FileProcessingError(
            message=f"Erro ao deletar arquivo: {str(e)}",
            error_code="FILE_DELETE_ERROR",
            details={"file_path": file_path}
        )


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Obtém informações detalhadas do arquivo"""
    try:
        path = Path(file_path)

        if not path.exists():
            raise FileProcessingError(
                message="Arquivo não encontrado",
                error_code="FILE_NOT_FOUND",
                details={"file_path": file_path}
            )

        stat = path.stat()

        # Ler conteúdo para gerar hash
        with open(file_path, 'rb') as f:
            content = f.read()
            file_hash = generate_file_hash(content)

        return {
            "filename": path.name,
            "file_path": str(path),
            "file_size": stat.st_size,
            "file_hash": file_hash,
            "mime_type": get_file_mime_type(path.name),
            "extension": get_file_extension(path.name),
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "is_readable": os.access(file_path, os.R_OK),
            "is_writable": os.access(file_path, os.W_OK)
        }

    except Exception as e:
        logger.error(
            f"Erro ao obter informações do arquivo: {file_path}",
            operation="file_info",
            status="error",
            metadata={"error": str(e)}
        )
        raise FileProcessingError(
            message=f"Erro ao obter informações do arquivo: {str(e)}",
            error_code="FILE_INFO_ERROR",
            details={"file_path": file_path}
        )


def validate_upload_file(filename: str, content: bytes) -> Dict[str, Any]:
    """Valida um arquivo de upload"""
    errors = []
    warnings = []

    # Validar extensão
    if not is_allowed_extension(filename):
        errors.append(
            f"Extensão não permitida: {get_file_extension(filename)}")

    # Validar tamanho
    if not validate_file_size(content):
        errors.append(f"Arquivo muito grande: {len(content)} bytes")

    # Validar nome do arquivo
    if len(filename) > 255:
        errors.append("Nome do arquivo muito longo")

    # Verificar se é um arquivo vazio
    if len(content) == 0:
        warnings.append("Arquivo vazio")

    # Verificar tipo MIME
    mime_type = get_file_mime_type(filename, content)
    if mime_type == 'application/octet-stream':
        warnings.append("Tipo MIME não reconhecido")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "file_info": {
            "filename": filename,
            "size": len(content),
            "extension": get_file_extension(filename),
            "mime_type": mime_type,
            "hash": generate_file_hash(content)
        }
    }


def cleanup_temp_files(directory: Optional[str] = None, max_age_hours: int = 24) -> int:
    """Remove arquivos temporários antigos"""
    if directory is None:
        directory = settings.storage.upload_dir

    try:
        path = Path(directory)  # type: ignore
        if not path.exists():
            return 0

        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        deleted_count = 0

        for file_path in path.rglob("*"):
            if file_path.is_file():
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(
                            f"Arquivo temporário removido: {file_path}")
                    except Exception as e:
                        logger.warning(
                            f"Erro ao remover arquivo temporário {file_path}: {e}")

        logger.info(
            f"Limpeza de arquivos temporários concluída: {deleted_count} arquivos removidos",
            operation="temp_cleanup",
            status="success",
            metadata={"deleted_count": deleted_count, "directory": directory}
        )

        return deleted_count

    except Exception as e:
        logger.error(
            f"Erro na limpeza de arquivos temporários: {e}",
            operation="temp_cleanup",
            status="error",
            metadata={"error": str(e), "directory": directory}
        )
        return 0


def get_storage_usage() -> Dict[str, Any]:
    """Obtém informações de uso do armazenamento"""
    try:
        upload_dir = Path(settings.storage.upload_dir)
        output_dir = Path(settings.storage.output_dir)

        total_size = 0
        file_count = 0

        # Calcular tamanho dos diretórios
        for directory in [upload_dir, output_dir]:
            if directory.exists():
                for file_path in directory.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1

        return {
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "file_count": file_count,
            "upload_dir_size": sum(f.stat().st_size for f in upload_dir.rglob("*") if f.is_file()) if upload_dir.exists() else 0,
            "output_dir_size": sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file()) if output_dir.exists() else 0
        }

    except Exception as e:
        logger.error(
            f"Erro ao calcular uso do armazenamento: {e}",
            operation="storage_usage",
            status="error",
            metadata={"error": str(e)}
        )
        return {
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "file_count": 0,
            "error": str(e)
        }
