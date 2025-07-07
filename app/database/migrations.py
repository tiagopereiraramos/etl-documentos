"""
Sistema de migrações para o banco de dados
"""
import os
from typing import List, Optional
from sqlalchemy import text, inspect
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.logging import obter_logger
from app.database.connection import db_manager
from app.models.database import Base

logger = obter_logger(__name__)


class DatabaseMigrator:
    """Gerenciador de migrações do banco de dados"""

    def __init__(self):
        self.settings = db_manager.settings
        self.alembic_cfg = None
        self._setup_alembic()

    def _setup_alembic(self):
        """Configura o Alembic para migrações"""
        try:
            # Criar diretório de migrações se não existir
            migrations_dir = os.path.join(os.getcwd(), "migrations")
            os.makedirs(migrations_dir, exist_ok=True)

            # Configurar Alembic
            self.alembic_cfg = Config()
            self.alembic_cfg.set_main_option("script_location", migrations_dir)
            self.alembic_cfg.set_main_option(
                "sqlalchemy.url", db_manager._get_database_url())

            # Configurações adicionais
            self.alembic_cfg.set_main_option(
                "file_template", "%(year)d_%(month).2d_%(day).2d_%(hour).2d%(minute).2d_%(rev)s_%(slug)s")

            logger.info("Alembic configurado para migrações")

        except Exception as e:
            logger.error(f"Erro ao configurar Alembic: {e}")
            self.alembic_cfg = None

    def create_initial_migration(self) -> bool:
        """Cria migração inicial baseada nos modelos atuais"""
        if not self.alembic_cfg:
            logger.error("Alembic não configurado")
            return False

        try:
            logger.info("Criando migração inicial...")

            # Gerar migração automática
            command.revision(
                self.alembic_cfg,
                message="Initial migration",
                autogenerate=True
            )

            logger.info("Migração inicial criada com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao criar migração inicial: {e}")
            return False

    def run_migrations(self, target: Optional[str] = None) -> bool:
        """Executa migrações pendentes"""
        if not self.alembic_cfg:
            logger.error("Alembic não configurado")
            return False

        try:
            logger.info("Executando migrações...")

            if target:
                command.upgrade(self.alembic_cfg, target)
            else:
                command.upgrade(self.alembic_cfg, "head")

            logger.info("Migrações executadas com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao executar migrações: {e}")
            return False

    def create_migration(self, message: str) -> bool:
        """Cria uma nova migração vazia"""
        if not self.alembic_cfg:
            logger.error("Alembic não configurado")
            return False

        try:
            logger.info(f"Criando migração: {message}")
            command.revision(self.alembic_cfg, message=message)
            logger.info("Migração criada com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao criar migração: {e}")
            return False

    def get_migration_history(self) -> List[dict]:
        """Obtém histórico de migrações"""
        if not self.alembic_cfg:
            return []

        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = script_dir.walk_revisions()

            history = []
            for rev in revisions:
                history.append({
                    "revision": rev.revision,
                    "down_revision": rev.down_revision,
                    "message": rev.message,
                    "date": rev.date
                })

            return history

        except Exception as e:
            logger.error(f"Erro ao obter histórico de migrações: {e}")
            return []

    def get_current_revision(self) -> Optional[str]:
        """Obtém a revisão atual do banco"""
        if not self.alembic_cfg:
            return None

        try:
            from alembic.migration import MigrationContext
            from sqlalchemy import create_engine

            engine = create_engine(db_manager._get_database_url())
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                return context.get_current_revision()

        except Exception as e:
            logger.error(f"Erro ao obter revisão atual: {e}")
            return None

    def rollback_migration(self, target_revision: str) -> bool:
        """Faz rollback para uma revisão específica"""
        if not self.alembic_cfg:
            logger.error("Alembic não configurado")
            return False

        try:
            logger.info(f"Fazendo rollback para revisão: {target_revision}")
            command.downgrade(self.alembic_cfg, target_revision)
            logger.info("Rollback executado com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao fazer rollback: {e}")
            return False


def create_tables_simple():
    """Cria tabelas de forma simples (sem Alembic)"""
    try:
        logger.info("Criando tabelas usando SQLAlchemy...")

        # Inicializar banco
        db_manager.initialize()

        # Criar tabelas
        Base.metadata.create_all(bind=db_manager.engine)

        # Verificar tabelas criadas
        inspector = inspect(db_manager.engine)
        tabelas = inspector.get_table_names()
        logger.info(f"Tabelas criadas: {tabelas}")

        return True

    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")
        return False


def check_database_health() -> dict:
    """Verifica a saúde do banco de dados"""
    try:
        db_manager.initialize()

        # Testar conexão
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT 1"))
            result.fetchone()

        # Verificar tabelas
        inspector = inspect(db_manager.engine)
        tabelas = inspector.get_table_names()

        # Verificar se tabelas essenciais existem
        tabelas_essenciais = [
            "clientes", "documentos", "logs_processamento",
            "sessoes_uso", "consumo_llm"
        ]

        tabelas_faltando = [t for t in tabelas_essenciais if t not in tabelas]

        return {
            "status": "healthy" if not tabelas_faltando else "degraded",
            "tabelas_existentes": len(tabelas),
            "tabelas_faltando": tabelas_faltando,
            "tipo_banco": db_manager.settings.database.type.value,
            "conexao_ativa": True
        }

    except Exception as e:
        logger.error(f"Erro ao verificar saúde do banco: {e}")
        return {
            "status": "unhealthy",
            "erro": str(e),
            "conexao_ativa": False
        }


def seed_initial_data():
    """Popula o banco com dados iniciais"""
    try:
        from app.database.repositories import cliente_repo
        from app.core.security import hash_password

        logger.info("Populando banco com dados iniciais...")

        with db_manager.get_session() as session:
            # Verificar se já existe cliente admin
            admin = cliente_repo.get_by_email(
                session, "admin@etl-documentos.com")

            if not admin:
                # Criar cliente admin
                admin = cliente_repo.create(
                    session,
                    nome="Administrador",
                    email="admin@etl-documentos.com",
                    senha_hash=hash_password("admin123"),
                    ativo=True
                )
                logger.info("Cliente admin criado")

            # Adicionar mais dados de exemplo se necessário
            logger.info("Dados iniciais populados com sucesso")

    except Exception as e:
        logger.error(f"Erro ao popular dados iniciais: {e}")


# Funções de conveniência
def initialize_database():
    """Inicializa o banco de dados completo"""
    try:
        logger.info("Inicializando banco de dados...")

        # Criar tabelas
        if not create_tables_simple():
            return False

        # Popular dados iniciais
        seed_initial_data()

        logger.info("Banco de dados inicializado com sucesso")
        return True

    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        return False


def reset_database():
    """Reseta o banco de dados (CUIDADO!)"""
    try:
        logger.warning(
            "RESETANDO BANCO DE DADOS - TODOS OS DADOS SERÃO PERDIDOS!")

        # Dropar todas as tabelas
        Base.metadata.drop_all(bind=db_manager.engine)
        logger.info("Tabelas removidas")

        # Recriar tabelas
        Base.metadata.create_all(bind=db_manager.engine)
        logger.info("Tabelas recriadas")

        # Popular dados iniciais
        seed_initial_data()

        logger.info("Banco de dados resetado com sucesso")
        return True

    except Exception as e:
        logger.error(f"Erro ao resetar banco de dados: {e}")
        return False
