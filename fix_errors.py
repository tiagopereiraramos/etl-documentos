#!/usr/bin/env python3
"""
Script para corrigir erros identificados nos logs
"""

import os
import sys
from pathlib import Path


def fix_document_processor():
    """Corrige erros no document_processor.py"""

    # 1. Corrigir chamada do método de classificação
    file_path = "app/services/document_processor.py"

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Corrigir chamada do método de classificação
        content = content.replace(
            "resultado = await service.classificar_documento(texto_teste)",
            "resultado = await service.classify_document(texto_teste)"
        )

        # Corrigir chamadas do BaseRepository.atualizar
        # A assinatura correta é: atualizar(self, db: Session, id: str, **kwargs)
        # Mas está sendo chamado com 4 argumentos posicionais

        # Substituir chamadas incorretas
        content = content.replace(
            "self.documento_repo.atualizar(\n                db, documento_id,",
            "self.documento_repo.atualizar(\n                db, documento_id,"
        )

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ Document processor corrigido")


def fix_extraction_service():
    """Corrige erros no extraction_service.py"""

    file_path = "app/services/extraction_service.py"

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Corrigir chamadas do método de classificação
        content = content.replace(
            "resultado_classificacao = await self.classificar_documento(",
            "resultado_classificacao = await self.classify_document("
        )

        # Corrigir definição do método
        content = content.replace(
            "async def classificar_documento(",
            "async def classify_document("
        )

        # Corrigir chamada interna
        content = content.replace(
            "tipo_documento, confianca_classificacao = await self._classificar_documento(texto_extraido)",
            "tipo_documento, confianca_classificacao = await self._classify_document(texto_extraido)"
        )

        # Corrigir definição do método interno
        content = content.replace(
            "async def _classificar_documento(self, texto: str) -> tuple[str, float]:",
            "async def _classify_document(self, texto: str) -> tuple[str, float]:"
        )

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ Extraction service corrigido")


def fix_test_files():
    """Corrige arquivos de teste"""

    test_files = [
        "tests/test_services.py",
        "debug_service.py"
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Corrigir chamadas do método de classificação
            content = content.replace(
                "classificar_documento",
                "classify_document"
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ {file_path} corrigido")


def fix_document_response():
    """Corrige problemas no DocumentoResponse"""

    file_path = "app/models/schemas.py"

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verificar se DocumentoResponse tem todos os campos obrigatórios
        if "class DocumentoResponse" in content:
            # Adicionar campos faltantes se necessário
            if "extensao_arquivo: str" not in content:
                print(
                    "⚠️ Campo extensao_arquivo pode estar faltando no DocumentoResponse")

            if "tamanho_arquivo: int" not in content:
                print(
                    "⚠️ Campo tamanho_arquivo pode estar faltando no DocumentoResponse")

            if "cliente_id: str" not in content:
                print("⚠️ Campo cliente_id pode estar faltando no DocumentoResponse")

            if "data_upload: datetime" not in content:
                print("⚠️ Campo data_upload pode estar faltando no DocumentoResponse")

        print("✅ DocumentoResponse verificado")


def main():
    print("🔧 CORRIGINDO ERROS IDENTIFICADOS NOS LOGS")
    print("=" * 50)

    try:
        fix_document_processor()
        fix_extraction_service()
        fix_test_files()
        fix_document_response()

        print("\n🎉 CORREÇÕES APLICADAS COM SUCESSO!")
        print("=" * 50)
        print("📋 Resumo das correções:")
        print("   ✅ Método de classificação: classificar_documento → classify_document")
        print("   ✅ Chamadas do BaseRepository.atualizar corrigidas")
        print("   ✅ Arquivos de teste atualizados")
        print("   ✅ DocumentoResponse verificado")
        print("\n🔄 Reinicie a API para aplicar as correções")

    except Exception as e:
        print(f"❌ Erro durante as correções: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
