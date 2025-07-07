
#!/usr/bin/env python3
"""
Script para configurar o banco PostgreSQL do sistema ETL Documentos
"""
import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys

# Adicionar o diretório app ao path
sys.path.append('.')

from app.core.config import DATABASE_URL
from app.models.database import Base
from app.core.logging import obter_logger

logger = obter_logger(__name__)

def verificar_conexao():
    """Verifica se consegue conectar ao PostgreSQL"""
    try:
        # Garantir que a URL use o driver correto
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ Conexão PostgreSQL bem-sucedida!")
            logger.info(f"Versão: {version}")
            return True
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao PostgreSQL: {e}")
        return False

def criar_tabelas():
    """Cria todas as tabelas no PostgreSQL"""
    try:
        logger.info("🔧 Criando tabelas no PostgreSQL...")
        
        # Garantir que a URL use o driver correto
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(db_url, echo=True)
        
        # Criar todas as tabelas
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Tabelas criadas com sucesso!")
        
        # Verificar tabelas criadas
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tabelas = [row[0] for row in result.fetchall()]
            logger.info(f"📋 Tabelas criadas: {tabelas}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
        return False

def inserir_dados_iniciais():
    """Insere dados iniciais no banco"""
    try:
        logger.info("📥 Inserindo dados iniciais...")
        
        # Garantir que a URL use o driver correto
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with SessionLocal() as session:
            # Verificar se já existem clientes
            result = session.execute(text("SELECT COUNT(*) FROM clientes"))
            count = result.fetchone()[0]
            
            if count == 0:
                # Inserir cliente padrão
                session.execute(text("""
                    INSERT INTO clientes (id, name, email, is_active, created_at, plan_type, rate_limit_per_minute)
                    VALUES (
                        'cliente-default',
                        'Cliente Padrão',
                        'admin@etldocumentos.com',
                        true,
                        NOW(),
                        'premium',
                        1000
                    )
                """))
                session.commit()
                logger.info("✅ Cliente padrão criado!")
            else:
                logger.info("ℹ️  Dados iniciais já existem")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao inserir dados iniciais: {e}")
        return False

def main():
    """Função principal"""
    logger.info("🚀 Configurando PostgreSQL para ETL Documentos...")
    
    # Verificar conexão
    if not verificar_conexao():
        logger.error("❌ Falha na conexão. Verifique as credenciais.")
        return False
    
    # Criar tabelas
    if not criar_tabelas():
        logger.error("❌ Falha ao criar tabelas.")
        return False
    
    # Inserir dados iniciais
    if not inserir_dados_iniciais():
        logger.error("❌ Falha ao inserir dados iniciais.")
        return False
    
    logger.info("🎉 PostgreSQL configurado com sucesso!")
    logger.info("📊 Sistema pronto para uso!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
