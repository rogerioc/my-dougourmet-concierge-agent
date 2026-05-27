import sys
import os
# Garante que a raiz do MyDuoConcierge está no PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import datetime
from agent.agent_core import DuoConciergeAgent
from agent.location_picker import render_gps_picker

# ── Configuração da página ──────────────────────────────────
st.set_page_config(
    page_title="Duo Concierge",
    page_icon="🍽️",
    layout="wide"
)

# ── Inicialização do estado ──────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "steps" not in st.session_state:
    st.session_state.steps = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "gps_prompt_shown" not in st.session_state:
    st.session_state.gps_prompt_shown = False
if "gps_active_toast_shown" not in st.session_state:
    st.session_state.gps_active_toast_shown = False

# ── Custom CSS para alinhar tipografia e marca com DuoList ───
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"], .stApp {
            font-family: 'Outfit', sans-serif !important;
        }
        /* Ajustar borda dos inputs */
        .stTextInput input, .stChatInput textarea {
            border-color: rgba(255, 255, 255, 0.08) !important;
        }
        .stTextInput input:focus, .stChatInput textarea:focus {
            border-color: #fbcd4b !important;
            box-shadow: 0 0 0 3px rgba(251, 205, 75, 0.15) !important;
        }
        /* Esconde footer padrão do Streamlit */
        footer {
            visibility: hidden;
            display: none !important;
        }
        /* Ajusta o input do chat para subir e dar espaço ao footer */
        div[data-testid="stChatInput"] {
            bottom: 30px !important;
        }
        /* Estilo do footer fixo abaixo do input */
        .custom-footer {
            position: fixed;
            bottom: 8px;
            left: 0;
            right: 0;
            text-align: center;
            font-size: 11px;
            color: #64748b;
            z-index: 999999;
            background: transparent;
        }
    </style>
""", unsafe_allow_html=True)
st.sidebar.title("ℹ️ Sobre o Duo Gourmet")
st.sidebar.markdown("""
O **Duo Gourmet** é um benefício que permite pedir um prato
principal e ganhar outro de igual ou menor valor.

Use este assistente para encontrar o restaurante ideal.
""")

if st.sidebar.button("🔄 Nova Conversa"):
    st.session_state.messages = []
    st.session_state.steps = {}
    st.session_state.chat_history = []
    st.rerun()

st.sidebar.markdown("---")
# ── Sidebar ─────────────────────────────────────────────────
api_key = st.sidebar.text_input("🔑 Gemini API Key", type="password")

with st.sidebar.popover("ℹ️ Como obter sua API Key?"):
    st.markdown("""
    💡 **O que é a API do Gemini?**
    É a interface que conecta este assistente à IA do Google, permitindo analisar restaurantes de forma personalizada.
    
    🔑 **Como conseguir sua chave (API Key)?**
    1. Acesse o **[Google AI Studio](https://aistudio.google.com/)**.
    2. Clique em **"Get API Key"**.
    3. Crie uma chave gratuita.
    
    👉 Veja mais no **[Guia do Gemini API](https://ai.google.dev/gemini-api/docs/quickstart?hl=pt-br)**.
    """)

st.sidebar.markdown("---")
st.sidebar.title("🧪 Simulação de Contexto")

# Permite simular diferentes dias e horários para fins de teste do schedule do Duo Gourmet
usar_data_atual = st.sidebar.checkbox(
    "Usar data/hora atual", 
    value=True,
    help="Desmarque para simular outro dia/horário. Isso serve para testar a validade dos horários do Duo Gourmet em dias específicos (ex: finais de semana ou jantares de terça-feira)."
)

if not usar_data_atual:
    dia_simulado = st.sidebar.selectbox(
        "Dia da Semana",
        ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    )
    hora_simulada = st.sidebar.time_input("Horário da visita", datetime.time(20, 0))
    periodo_simulado = st.sidebar.selectbox("Refeição", ["almoco", "jantar"])
    
    contexto_tempo = f"Hoje é {dia_simulado}, às {hora_simulada.strftime('%H:%M')}. Período: {periodo_simulado}."
else:
    # Mapeamento do dia da semana em português
    dias_semana_pt = {
        0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
        3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
    }
    agora = datetime.datetime.now()
    dia_pt = dias_semana_pt[agora.weekday()]
    hora_str = agora.strftime("%H:%M")
    periodo = "almoco" if agora.hour < 17 else "jantar"
    
    contexto_tempo = f"Hoje é {dia_pt}, às {hora_str}. Período: {periodo}."

# ── Localização do Usuário ───────────────────────────────
st.sidebar.markdown("---")
st.sidebar.title("📍 Localização do Usuário")

modo_localizacao = st.sidebar.radio(
    "Como definir sua posição?",
    ["Desativada", "Usar GPS do Navegador (Leaflet)", "Simular Ponto de Referência"],
    help="O agente usará sua localização para calcular a distância física em KM de cada restaurante e priorizar os mais próximos."
)

lat_usuario = None
lon_usuario = None
opcao_bairro = None

if modo_localizacao == "Desativada":
    st.session_state.gps_active_toast_shown = False
    if not st.session_state.gps_prompt_shown:
        with st.container(border=True):
            st.markdown("""
                <style>
                    div[data-testid="stVerticalBlockBorderWrapper"]:has(.gps-popup-class) {
                        position: fixed !important;
                        bottom: 80px !important;
                        left: 24px !important;
                        width: 320px !important;
                        background-color: #1e293b !important;
                        border: 1px solid rgba(251, 205, 75, 0.6) !important;
                        border-radius: 12px !important;
                        padding: 16px !important;
                        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.7) !important;
                        z-index: 999999 !important;
                    }
                    .gps-popup-class {
                        color: #f8fafc;
                        font-family: 'Outfit', sans-serif;
                        font-size: 13.5px;
                        line-height: 1.5;
                        margin-bottom: 12px;
                    }
                    .gps-popup-title {
                        font-weight: 700;
                        color: #fbcd4b;
                        margin-bottom: 6px;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }
                    div[data-testid="stVerticalBlockBorderWrapper"]:has(.gps-popup-class) button {
                        background-color: #fbcd4b !important;
                        color: #0f172a !important;
                        border: none !important;
                        font-weight: 600 !important;
                    }
                    div[data-testid="stVerticalBlockBorderWrapper"]:has(.gps-popup-class) button:hover {
                        background-color: #fbd668 !important;
                        color: #0f172a !important;
                    }
                </style>
                <div class="gps-popup-class">
                    <div class="gps-popup-title">🧭 Ative seu GPS</div>
                    Para uma melhor experiência, ative a geolocalização na barra lateral. Isso permite calcular a distância e ver os restaurantes mais próximos!
                </div>
            """, unsafe_allow_html=True)
            if st.button("Entendi", key="close_gps_popup", use_container_width=True):
                st.session_state.gps_prompt_shown = True
                st.rerun()

elif modo_localizacao == "Usar GPS do Navegador (Leaflet)":
    st.session_state.gps_prompt_shown = False
    st.sidebar.caption("Permita o acesso ao GPS na janela do mapa abaixo:")
    gps_data = render_gps_picker(key="main_gps_picker")
    if gps_data:
        lat_usuario = gps_data.get("lat")
        lon_usuario = gps_data.get("lon")
        st.sidebar.success(f"GPS Ativo: {lat_usuario:.4f}, {lon_usuario:.4f}")
        if not st.session_state.gps_active_toast_shown:
            st.toast("📍 GPS Ativado com sucesso! O assistente agora calculará a distância até os restaurantes.", icon="✅")
            st.session_state.gps_active_toast_shown = True
    else:
        st.sidebar.info("Aguardando coordenadas do GPS...")
        
elif modo_localizacao == "Simular Ponto de Referência":
    st.session_state.gps_prompt_shown = False
    st.session_state.gps_active_toast_shown = False
    opcao_bairro = st.sidebar.selectbox(
        "Selecione um ponto em BH",
        [
            "Savassi (Praça Diogo de Vasconcelos)",
            "Lourdes (Praça Marília de Dirceu)",
            "Centro (Praça da Estação)",
            "Buritis (Parque Aggeo Pio Sobrinho)",
            "Pampulha (Igrejinha)"
        ]
    )
    coords = {
        "Savassi (Praça Diogo de Vasconcelos)": (-19.9386, -43.9359),
        "Lourdes (Praça Marília de Dirceu)": (-19.9348, -43.9455),
        "Centro (Praça da Estação)": (-19.9169, -43.9346),
        "Buritis (Parque Aggeo Pio Sobrinho)": (-19.9723, -43.9686),
        "Pampulha (Igrejinha)": (-19.8519, -43.9793)
    }
    lat_usuario, lon_usuario = coords[opcao_bairro]
    st.sidebar.caption(f"Simulando Lat: {lat_usuario} / Lon: {lon_usuario}")

# ── Cabeçalho principal com Branding do DuoList ──────────────
st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-top: -20px; margin-bottom: 5px;">
        <span style="font-size: 28px; color: #fbcd4b;">🍽️</span>
        <h1 style="font-size: 26px; font-weight: 700; margin: 0; color: #f8fafc; font-family: 'Outfit', sans-serif;">
            Duo<span style="color: #fbcd4b;">Concierge</span>
        </h1>
    </div>
    <p style="font-size: 13px; color: #94a3b8; margin-top: -6px; margin-bottom: 20px; font-weight: 300;">
        Seu assistente inteligente de gastronomia integrado com o mapa DuoList BH
    </p>
""", unsafe_allow_html=True)

# Exibe contexto de simulação ativo
localizacao_texto = ""
if lat_usuario and lon_usuario:
    localizacao_texto = f" | 📍 Localização: {opcao_bairro or 'GPS do Navegador'} ({lat_usuario:.4f}, {lon_usuario:.4f})"
st.info(f"⚙️ **Contexto Ativo:** {contexto_tempo}{localizacao_texto}")

# ── Exibe histórico de mensagens ─────────────────────────────
avatars = {"human": "user", "ai": "assistant"}

for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(avatars[msg["role"]]):
        # Expanders para cada tool chamada (transparência do agente)
        for step in st.session_state.steps.get(str(idx), []):
            with st.expander(f"⚙️ **Ferramenta executada:** `{step['tool']}`"):
                st.write("**Parâmetros:**", step['args'])
                st.write("**Resultado retornado:**", step['result'])
        st.markdown(msg["content"])

# ── Input do usuário ─────────────────────────────────────────
if user_input := st.chat_input("Ex: Quero comer comida italiana hoje à noite 🍝"):

    if not api_key:
        st.warning("⚠️ Adicione sua Gemini API Key na barra lateral.")
        st.stop()

    # Exibe mensagem do usuário
    st.session_state.messages.append({"role": "human", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Executa o agente e captura steps intermediários
    with st.chat_message("assistant"):
        try:
            with st.spinner("🤖 Procurando o melhor restaurante para você..."):
                agent = DuoConciergeAgent(api_key=api_key)
                
                response, intermediate_steps, st.session_state.chat_history = agent.run(
                    user_input=user_input, 
                    time_context=contexto_tempo, 
                    lat_usuario=lat_usuario,
                    lon_usuario=lon_usuario,
                    history=st.session_state.chat_history
                )

            # Expanders dos passos intermediários
            for step in intermediate_steps:
                with st.expander(f"⚙️ **Ferramenta executada:** `{step['tool']}`"):
                    st.write("**Parâmetros:**", step['args'])
                    st.write("**Resultado retornado:**", step['result'])

            st.markdown(response)

            # Salva no histórico apenas em caso de sucesso
            idx = len(st.session_state.messages) - 1
            st.session_state.messages.append({"role": "ai", "content": response})
            st.session_state.steps[str(idx + 1)] = intermediate_steps

        except Exception as e:
            err_msg = str(e)
            # Remove a última mensagem enviada pelo usuário para não quebrar a UI
            if st.session_state.messages:
                st.session_state.messages.pop()
                
            if "API_KEY_INVALID" in err_msg or "INVALID_ARGUMENT" in err_msg or "400" in err_msg:
                st.error("🔑 **API Key Inválida!** A chave que você inseriu na barra lateral não é válida ou está inativa. Verifique se copiou a chave correta no [Google AI Studio](https://aistudio.google.com/).")
            else:
                st.error(f"⚠️ **Erro no Gemini:** Não foi possível processar sua mensagem. Detalhes: `{err_msg}`")

# ── Footer da Tela Principal ────────────────────────────────
st.markdown(
    """
    <div class="custom-footer">
        Created By <a href="https://rogerioc.github.io/about/" target="_blank" style="color: #fbcd4b; text-decoration: none; font-weight: 600;">Rogerio C.S</a> | 
        Dados extraídos de <a href="https://www.duogourmet.com.br" target="_blank" style="color: #fbcd4b; text-decoration: none;">Duo Gourmet</a> &copy;
    </div>
    """,
    unsafe_allow_html=True
)
