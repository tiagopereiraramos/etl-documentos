#!/usr/bin/env python3
"""
Script para executar a interface Streamlit
"""
import subprocess
import sys
import os


def run_streamlit():
    """Executa o Streamlit com as configurações corretas"""
    cmd = [
        sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port=8501"
    ]

    print("🚀 Iniciando interface Streamlit...")
    print(f"📡 Acesse: http://localhost:8501")
    print("⚠️  Certifique-se de que a API está rodando em http://localhost:8000")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Interface Streamlit encerrada.")
    except Exception as e:
        print(f"❌ Erro ao executar Streamlit: {e}")


if __name__ == "__main__":
    run_streamlit()
