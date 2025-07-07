import streamlit as st
import requests
import json
from datetime import datetime
import os
import time
import subprocess

# Configuração da página
st.set_page_config(
    page_title="ETL Documentos - Sistema Completo",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URLs da API
# Detecta se está rodando no Docker
if os.path.exists('/.dockerenv'):
    # Se está no Docker, usa o nome do serviço
    API_BASE_URL = "http://etl-api:8000/api/v1"
else:
    # Se está local, usa localhost
    API_BASE_URL = "http://localhost:8000/api/v1"

# Inicializar session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'cliente_info' not in st.session_state:
    st.session_state.cliente_info = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'live_logs' not in st.session_state:
    st.session_state.live_logs = []


def add_log(message, level="INFO"):
    """Adiciona log à sessão"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    st.session_state.logs.append(log_entry)
    # Manter apenas os últimos 100 logs
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]


def add_live_log(message, level="INFO"):
    """Adiciona log em tempo real"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_entry = f"[{timestamp}] {level}: {message}"
    st.session_state.live_logs.append(log_entry)
    # Manter apenas os últimos 50 logs para a tela
    if len(st.session_state.live_logs) > 50:
        st.session_state.live_logs = st.session_state.live_logs[-50:]


def get_docker_logs():
    """Captura logs do container da API em tempo real"""
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", "10",
                "--since", "5s", "etl-documentos-api"],
            capture_output=True,
            text=True,
            timeout=3
        )

        if result.returncode == 0:
            logs = result.stdout + result.stderr
            parsed_logs = []

            for log in logs.split('\n'):
                if not log.strip():
                    continue

                # Extrair mensagens importantes
                if '"message":' in log:
                    try:
                        log_data = json.loads(log)
                        message = log_data.get('message', '')
                        level = log_data.get('level', 'INFO')

                        # Filtra mensagens importantes
                        important_keywords = [
                            'tentando extração', 'docling', 'azure', 'fallback',
                            'classificação', 'processamento', 'converting document',
                            'finished converting', 'erro azure', 'openai'
                        ]

                        if any(keyword.lower() in message.lower() for keyword in important_keywords):
                            timestamp = log_data.get('timestamp', '')
                            if timestamp:
                                timestamp = timestamp.split(
                                    'T')[1][:8]  # HH:MM:SS
                            parsed_logs.append(
                                f"[{timestamp}] {level}: {message}")

                    except json.JSONDecodeError:
                        continue
                elif 'Processing document' in log:
                    doc_name = log.split('Processing document')[1].strip()
                    parsed_logs.append(f"🔄 Processando: {doc_name}")
                elif 'Finished converting' in log and 'in' in log:
                    time_info = log.split('in')[-1].strip()
                    parsed_logs.append(f"✅ Conversão concluída em {time_info}")

            return parsed_logs
        return []
    except Exception as e:
        return [f"Erro ao capturar logs: {str(e)}"]


def clear_logs():
    """Limpa os logs"""
    st.session_state.logs = []


def clear_live_logs():
    """Limpa os logs em tempo real"""
    st.session_state.live_logs = []


def check_api_health():
    """Verifica se a API está online"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        return response.status_code == 200
    except:
        return False


def create_client(nome, email, senha, plano):
    """Cria um novo cliente"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/clientes/",
            json={"nome": nome, "email": email,
                  "senha": senha, "plano": plano},
            timeout=15
        )
        return response.status_code == 201, response.json()
    except Exception as e:
        return False, str(e)


def authenticate_client(api_key):
    """Autentica cliente e retorna dados de uso"""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(
            f"{API_BASE_URL}/clientes/me/usage", headers=headers, timeout=15)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)


def get_client_quotas(api_key):
    """Obtém quotas do cliente"""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(
            f"{API_BASE_URL}/clientes/me/quotas", headers=headers, timeout=15)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)


def process_document_with_logs(api_key, file):
    """Processa documento com logs simples"""
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        add_live_log("🚀 Iniciando processamento...", "INFO")
        add_live_log(
            f"📁 Arquivo: {file.name} ({len(file.read())} bytes)", "INFO")
        file.seek(0)

        add_live_log("📤 Enviando arquivo para a API...", "INFO")

        files = {"arquivo": (file.name, file, "application/octet-stream")}
        start_time = time.time()

        response = requests.post(
            f"{API_BASE_URL}/processar",
            headers=headers,
            files=files,
            timeout=180
        )

        processing_time = time.time() - start_time
        add_live_log(
            f"⏱️ Processamento concluído em {processing_time:.2f}s", "SUCCESS")

        if response.status_code == 200:
            result = response.json()
            add_log("✅ Documento processado com sucesso!", "SUCCESS")
            add_live_log("✅ Processamento bem-sucedido!", "SUCCESS")
            return True, result
        else:
            error_msg = f"Erro {response.status_code}: {response.text}"
            add_log(f"❌ {error_msg}", "ERROR")
            add_live_log(f"❌ {error_msg}", "ERROR")
            return False, error_msg

    except requests.exceptions.Timeout:
        error_msg = "❌ Timeout: Processamento demorou muito tempo"
        add_log(error_msg, "ERROR")
        add_live_log(error_msg, "ERROR")
        return False, error_msg
    except Exception as e:
        error_msg = f"❌ Erro: {str(e)}"
        add_log(error_msg, "ERROR")
        add_live_log(error_msg, "ERROR")
        return False, error_msg


def display_live_logs():
    """Exibe logs em tempo real"""
    if st.session_state.live_logs:
        st.subheader("📡 Logs em Tempo Real")

        # Container com altura fixa e scroll
        logs_container = st.container(height=350)
        with logs_container:
            for log in st.session_state.live_logs[-20:]:  # Últimos 20 logs
                if "ERROR" in log:
                    st.error(log)
                elif "SUCCESS" in log:
                    st.success(log)
                elif "WARNING" in log:
                    st.warning(log)
                elif "🔄" in log or "📤" in log or "✅" in log:
                    st.info(log)
                else:
                    st.text(log)


def upgrade_plan(api_key, novo_plano):
    """Faz upgrade do plano do cliente"""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.put(
            f"{API_BASE_URL}/clientes/me/upgrade-plan",
            json={"novo_plano": novo_plano},
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)


def main():
    st.title("🔍 ETL Documentos - Sistema Completo")
    st.markdown(
        "**Sistema de processamento inteligente com rastreabilidade de clientes**")

    # Verificar API
    api_ok = check_api_health()

    # Sidebar principal
    with st.sidebar:
        st.header("🔐 Autenticação")

        if not api_ok:
            st.error("❌ API Não Conectada")
            st.info("Certifique-se de que a API está rodando na porta 8000")
            return

        st.success("✅ API Conectada")

        # Tabs para autenticação
        auth_tab1, auth_tab2 = st.tabs(["🔑 Login", "➕ Novo Cliente"])

        with auth_tab1:
            st.subheader("Login com API Key")

            api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="etl_...",
                help="Cole sua API Key aqui"
            )

            if st.button("🔓 Entrar", type="primary", key="login_button"):
                if api_key:
                    with st.spinner("Autenticando..."):
                        add_log("Tentando autenticação...")
                        success, result = authenticate_client(api_key)
                        if success:
                            st.session_state.api_key = api_key
                            st.session_state.cliente_info = result
                            st.session_state.authenticated = True
                            add_log("✅ Autenticação bem-sucedida!", "SUCCESS")
                            st.success("✅ Autenticado com sucesso!")
                            st.rerun()
                        else:
                            add_log(
                                f"❌ Falha na autenticação: {result}", "ERROR")
                            st.error(f"❌ Erro na autenticação: {result}")
                else:
                    st.warning("⚠️ Digite uma API Key")

        with auth_tab2:
            st.subheader("Criar Novo Cliente")

            with st.form("novo_cliente"):
                nome = st.text_input("Nome da Empresa")
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                plano = st.selectbox(
                    "Plano",
                    ["free", "basic", "premium"],
                    format_func=lambda x: {
                        "free": "🆓 Free (10 docs/mês)",
                        "basic": "💼 Basic (100 docs/mês)",
                        "premium": "⭐ Premium (1000 docs/mês)"
                    }[x]
                )

                if st.form_submit_button("➕ Criar Cliente", type="primary"):
                    if nome and email and senha:
                        with st.spinner("Criando cliente..."):
                            add_log(f"Criando cliente: {nome}")
                            success, result = create_client(
                                nome, email, senha, plano)
                            if success:
                                add_log(
                                    f"✅ Cliente {nome} criado com sucesso!", "SUCCESS")
                                st.success("✅ Cliente criado com sucesso!")
                                st.json(result)
                            else:
                                add_log(
                                    f"❌ Erro ao criar cliente: {result}", "ERROR")
                                st.error(f"❌ Erro ao criar cliente: {result}")
                    else:
                        st.warning("⚠️ Preencha todos os campos")

        # Logout
        if st.session_state.authenticated:
            st.markdown("---")
            if st.button("🚪 Logout", key="logout_button"):
                add_log("Logout realizado")
                st.session_state.api_key = None
                st.session_state.cliente_info = None
                st.session_state.authenticated = False
                st.success("✅ Logout realizado!")
                st.rerun()

    # Área principal
    if not st.session_state.authenticated:
        st.info("👆 Use a sidebar para fazer login ou criar uma conta")
        return

    # Cliente autenticado
    if not st.session_state.cliente_info or 'cliente' not in st.session_state.cliente_info:
        st.error("❌ Dados do cliente não disponíveis")
        return

    cliente = st.session_state.cliente_info['cliente']

    # Header com informações do cliente
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.subheader(f"👤 {cliente.get('nome', 'N/A')}")
        st.caption(f"📧 {cliente.get('email', 'N/A')}")

    with col2:
        st.subheader(f"📋 Plano: {cliente.get('plano', 'N/A').title()}")

        # Obter quotas
        success, quotas = get_client_quotas(st.session_state.api_key)
        if success and isinstance(quotas, dict):
            quota_data = quotas.get('quotas', {})
            if quota_data.get('documentos_restantes') is not None:
                st.metric("📄 Documentos Restantes", quota_data.get(
                    'documentos_restantes', 'N/A'))
            else:
                st.metric("📄 Documentos", "∞ Ilimitado")
        else:
            st.warning("⚠️ Não foi possível carregar quotas")

    with col3:
        st.subheader("🔑 API Key")
        st.code(st.session_state.api_key[:20] + "...", language="text")

    # Tabs principais
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📤 Processar", "📊 Uso", "⚙️ Configurações", "📈 Relatórios", "📋 Logs"])

    with tab1:
        st.header("📤 Processar Documento")

        # Upload de arquivo
        uploaded_file = st.file_uploader(
            "Escolha um documento",
            type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'txt', 'docx'],
            help="Formatos suportados: PDF, imagens, TXT, DOCX"
        )

        if uploaded_file is not None:
            st.success(f"Arquivo carregado: {uploaded_file.name}")
            st.info(f"**Tamanho:** {len(uploaded_file.getvalue())} bytes")

            # Botão para processar
            if st.button("🚀 Processar Documento", type="primary", disabled=st.session_state.processing, key="process_button"):
                st.session_state.processing = True
                clear_live_logs()  # Limpar logs anteriores

                with st.spinner("🔄 Processando documento..."):
                    success, result = process_document_with_logs(
                        st.session_state.api_key, uploaded_file)

                    if success:
                        st.success("✅ Documento processado com sucesso!")

                        # Mostrar resultado
                        if isinstance(result, dict):
                            result_str = json.dumps(
                                result, indent=2, ensure_ascii=False)
                            result_lang = "json"
                        else:
                            result_str = str(result)
                            result_lang = "text"

                        # Exibir resultado formatado
                        st.subheader("📄 Resultado do Processamento")
                        if result_lang == "json":
                            st.json(result)
                        else:
                            st.code(result_str, language="text")
                    else:
                        st.error(f"❌ Erro ao processar: {result}")

                st.session_state.processing = False

        # Seção de logs sempre visível
        st.markdown("---")
        st.subheader("📡 Logs da API")

        # Botões de controle de logs
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 Capturar Logs", key="capture_logs"):
                add_live_log("🔍 Capturando logs da API...", "INFO")
                docker_logs = get_docker_logs()

                if docker_logs:
                    for log in docker_logs:
                        add_live_log(log, "API")
                    add_live_log(
                        f"✅ Capturados {len(docker_logs)} logs", "SUCCESS")
                else:
                    add_live_log("ℹ️ Nenhum log novo encontrado", "INFO")

                st.rerun()

        with col2:
            if st.button("🗑️ Limpar Logs", key="clear_live_logs"):
                clear_live_logs()
                st.rerun()

        with col3:
            if st.button("📊 Status API", key="api_status"):
                if check_api_health():
                    add_live_log("✅ API funcionando normalmente", "SUCCESS")
                else:
                    add_live_log("❌ API indisponível", "ERROR")
                st.rerun()

        # Exibir logs
        display_live_logs()

    with tab2:
        st.header("📊 Uso e Quotas")

        # Carregar dados de uso
        if st.button("🔄 Atualizar Dados", key="refresh_data_button"):
            with st.spinner("Carregando dados..."):
                add_log("Atualizando dados de uso...")
                success, usage_data = authenticate_client(
                    st.session_state.api_key)
                if success:
                    st.session_state.cliente_info = usage_data
                    add_log("✅ Dados de uso atualizados!", "SUCCESS")
                    st.success("✅ Dados atualizados!")
                    st.rerun()
                else:
                    add_log(
                        f"❌ Erro ao atualizar dados: {usage_data}", "ERROR")

        # Mostrar dados de uso
        if st.session_state.cliente_info:
            usage = st.session_state.cliente_info

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 Resumo")
                resumo = usage.get('resumo', {})
                st.metric("🔄 Total Operações",
                          resumo.get('total_operacoes', 0))
                st.metric("🧠 Tokens Consumidos",
                          f"{resumo.get('total_tokens', 0):,}")
                st.metric("💰 Custo Total",
                          f"R$ {resumo.get('total_custo', 0):.4f}")
                st.metric("⏱️ Tempo Médio",
                          f"{resumo.get('tempo_medio', 0):.2f}s")

            with col2:
                st.subheader("📋 Quotas")
                quotas = usage.get('quotas', {})
                st.metric("📄 Documentos Usados",
                          f"{quotas.get('documentos_usados', 0)}/{quotas.get('documentos_mes', '∞')}")
                st.metric(
                    "🧠 Tokens Usados", f"{quotas.get('tokens_usados', 0):,}/{quotas.get('tokens_mes', '∞'):,}")

                # Barra de progresso
                if quotas.get('documentos_mes') and quotas.get('documentos_mes') > 0:
                    progress = quotas.get(
                        'documentos_usados', 0) / quotas.get('documentos_mes', 1)
                    st.progress(progress)
                    st.caption(f"Progresso: {progress:.1%}")

    with tab3:
        st.header("⚙️ Configurações")

        # Upgrade de plano
        st.subheader("🔄 Upgrade de Plano")

        current_plan = cliente['plano']
        available_plans = {
            "free": ["basic", "premium"],
            "basic": ["premium"],
            "premium": []
        }

        if current_plan in available_plans and available_plans[current_plan]:
            upgrade_options = available_plans[current_plan]
            novo_plano = st.selectbox(
                "Escolha o novo plano:",
                upgrade_options,
                format_func=lambda x: {
                    "basic": "💼 Basic (100 docs/mês, 100k tokens)",
                    "premium": "⭐ Premium (1000 docs/mês, 1M tokens)"
                }[x]
            )

            if st.button("🔄 Fazer Upgrade", type="primary", key="upgrade_button"):
                with st.spinner("Fazendo upgrade..."):
                    add_log(f"Tentando upgrade para plano: {novo_plano}")
                    success, result = upgrade_plan(
                        st.session_state.api_key, novo_plano)
                    if success:
                        add_log(
                            f"✅ Upgrade para {novo_plano} realizado com sucesso!", "SUCCESS")
                        st.success("✅ Upgrade realizado com sucesso!")
                        st.json(result)
                        # Recarregar dados do cliente
                        time.sleep(1)
                        auth_success, new_data = authenticate_client(
                            st.session_state.api_key)
                        if auth_success:
                            st.session_state.cliente_info = new_data
                            st.rerun()
                    else:
                        add_log(f"❌ Erro no upgrade: {result}", "ERROR")
                        st.error(f"❌ Erro no upgrade: {result}")
        else:
            st.info("🎉 Você já está no plano mais alto disponível!")

    with tab4:
        st.header("📈 Relatórios Detalhados")

        if st.session_state.cliente_info:
            usage = st.session_state.cliente_info

            # Período
            periodo = usage.get('periodo', {})
            st.subheader("📅 Período de Análise")
            st.info(
                f"**Dias:** {periodo.get('dias', 0)} | **Início:** {periodo.get('inicio', 'N/A')} | **Fim:** {periodo.get('fim', 'N/A')}")

            # Uso por operação
            uso_por_operacao = usage.get('uso_por_operacao', [])
            if uso_por_operacao:
                st.subheader("🔄 Uso por Operação")
                for op in uso_por_operacao:
                    st.write(
                        f"• **{op.get('operacao', 'N/A')}:** {op.get('quantidade', 0)} operações")

            # Uso por provider
            uso_por_provider = usage.get('uso_por_provider', [])
            if uso_por_provider:
                st.subheader("🔧 Uso por Provider")
                for prov in uso_por_provider:
                    st.write(
                        f"• **{prov.get('provider', 'N/A')}:** {prov.get('quantidade', 0)} operações")

            if not uso_por_operacao and not uso_por_provider:
                st.info("📊 Nenhum dado de uso registrado ainda")

    with tab5:
        st.header("📋 Logs Históricos")

        # Controles de log
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Limpar Logs"):
                clear_logs()
                st.rerun()

        with col2:
            st.caption("Logs históricos das operações")

        # Exibir logs
        if st.session_state.logs:
            # Container com scroll
            logs_container = st.container(height=400)
            with logs_container:
                # Colorir logs por nível
                for log in st.session_state.logs:
                    if "ERROR" in log:
                        st.error(log)
                    elif "SUCCESS" in log:
                        st.success(log)
                    elif "WARNING" in log:
                        st.warning(log)
                    else:
                        st.info(log)

            # Estatísticas
            total_logs = len(st.session_state.logs)
            error_logs = len(
                [log for log in st.session_state.logs if "ERROR" in log])
            success_logs = len(
                [log for log in st.session_state.logs if "SUCCESS" in log])

            st.caption(
                f"📊 Total: {total_logs} | ✅ Sucessos: {success_logs} | ❌ Erros: {error_logs}")
        else:
            st.info(
                "📝 Nenhum log registrado ainda. Execute operações para ver os logs.")

    # Footer
    st.markdown("---")
    st.markdown(
        "**ETL Documentos v2.0** | Sistema de Rastreabilidade Completo | Feito com ❤️ e Streamlit")


if __name__ == "__main__":
    main()
