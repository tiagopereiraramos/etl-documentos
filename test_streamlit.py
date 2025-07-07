import streamlit as st
import requests

st.title("🧪 Teste de Conectividade")

# Teste da API
try:
    response = requests.get(
        "http://localhost:8000/api/v1/health/detailed", timeout=5)
    if response.status_code == 200:
        st.success("✅ API está funcionando!")
        st.json(response.json())
    else:
        st.error(f"❌ API retornou erro: {response.status_code}")
except Exception as e:
    st.error(f"❌ Erro ao conectar com a API: {e}")

st.info("Se você vê esta página, o Streamlit está funcionando!")
