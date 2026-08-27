import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import tempfile
import time
from groq import Groq

import auth
import data_manager
import ai_service

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="Zeus AI - Moderação", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #00AEEF !important; color: white !important; border: none !important; font-weight: bold !important; }
    div.stButton > button[kind="primary"]:hover { background-color: #008CBA !important; }
    div[data-testid="stForm"] { border-color: #333333; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# AUTENTICAÇÃO E MEMÓRIA
# ==========================================
auth.inicializar_autenticacao()
auth.verificar_acesso()

if 'analise_concluida' not in st.session_state:
    st.session_state.analise_concluida = False
    st.session_state.ultimo_texto = ""
    st.session_state.ultima_recomendacao = ""
    st.session_state.arquivo_audio_atual = None

def resetar_app():
    st.session_state.analise_concluida = False
    st.session_state.ultimo_texto = ""
    st.session_state.ultima_recomendacao = ""
    st.session_state.arquivo_audio_atual = None

# ==========================================
# INICIALIZAÇÃO DE DADOS E IA
# ==========================================
df_casos = data_manager.carregar_csv()
ai_service.configurar_api()

# Carrega o Zeus (ignoramos o Escrivão antigo do Gemini usando _)
model_zeus, _, _ = ai_service.obter_modelos_e_filtros()

# Cliente Groq inicializado com a sua chave gratuita
groq_client = Groq(api_key="GROQ_API_KEY")

filtros_seguranca = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ==========================================
# BARRA LATERAL (MENU)
# ==========================================
with st.sidebar:
    col_logo1, col_logo2, col_logo3 = st.columns([1.5, 1, 1.5])
    with col_logo2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
            
    st.markdown("<h3 style='text-align: center; margin-top: -15px;' anchor=False>Zeus Control</h3>", unsafe_allow_html=True)
    
    if st.session_state.is_admin:
        st.markdown(f"<p style='text-align: center; color: #4CAF50; font-size: 14px; margin-top: -10px;'>✅ Corporativo | {len(df_casos)} casos salvos</p>", unsafe_allow_html=True)
    else:
        st.warning(f"👀 Convidado: {st.session_state.guest_uses}/2 usos")
    
    st.divider()
    
    if st.button("🔄 Nova Análise (Limpar Tela)", type="primary", use_container_width=True):
        resetar_app()
        st.rerun()

    if st.session_state.is_admin and st.session_state.analise_concluida and st.session_state.ultimo_texto:
        st.divider()
        st.markdown("### 🧠 Treinar IA (ML)")
        st.write("Ajuste a punição real aplicada:")
        
        punicao_real = st.selectbox(
            "Veredito:", 
            ["SEM PUNIÇÃO", "Alerta", "Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5", "BAN"],
            label_visibility="collapsed"
        )
        
        if st.button("💾 Salvar Feedback", use_container_width=True):
            data_manager.salvar_feedback(st.session_state.ultimo_texto, punicao_real)
            st.toast("✅ Caso salvo com sucesso na base de ML!", icon="🚀")

# ==========================================
# TELA PRINCIPAL (UI DE ANÁLISE)
# ==========================================
st.title("Zeus - IA Moderadora ⚡", anchor=False)
st.markdown("Ferramenta de análise avançada de toxicidade e infrações.")

col_entrada, col_saida = st.columns([1.1, 1], gap="large")

with col_entrada:
    aba_texto, aba_audio = st.tabs(["📝 Analisar Chat/Log", "🎧 Transcrever Áudio"])

    with aba_texto:
        with st.container(border=True):
            with st.form("form_texto", clear_on_submit=False):
                texto_report = st.text_area("📋 Cole o report recebido:", height=150)
                
                c1, c2 = st.columns(2)
                with c1:
                    status_assinante_texto = st.toggle("⭐ Jogador é assinante?", key="ass_t")
                with c2:
                    tipo_partida_texto = st.selectbox(
                        "🎮 Partida (Antijogo):", 
                        ["Não se aplica", "Ranked", "Lobby / GC Solo"], key="part_t"
                    )
                submit_texto = st.form_submit_button("🔍 Executar Análise", use_container_width=True)

            if submit_texto:
                if auth.bloqueio_limite_convidado():
                    pass 
                elif not texto_report.strip():
                    st.toast("⚠️ Cole algum texto antes de analisar.", icon="⚠️")
                else:
                    with st.spinner("⚡ Zeus está analisando..."):
                        try:
                            prompt = ai_service.construir_prompt(df_casos, texto_report, status_assinante_texto, tipo_partida_texto)
                            response = model_zeus.generate_content(prompt, safety_settings=filtros_seguranca, generation_config={"temperature": 0.0})
                            
                            texto_resposta = ""
                            if response.candidates and response.candidates[0].content:
                                parts = response.candidates[0].content.parts
                                texto_resposta = "".join([p.text for p in parts if hasattr(p, 'text')])

                            if not texto_resposta:
                                st.error("⚠️ O filtro de segurança da API impediu a exibição desta análise.")
                            else:
                                st.session_state.ultimo_texto = texto_report
                                st.session_state.ultima_recomendacao = texto_resposta
                                st.session_state.arquivo_audio_atual = None
                                st.session_state.analise_concluida = True
                                auth.registrar_uso_convidado()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao analisar texto: {e}")

    with aba_audio:
        with st.container(border=True):
            with st.form("form_audio", clear_on_submit=False):
                arquivo_audio = st.file_uploader("🎧 Selecione o áudio (.wav, .mp3)", type=["wav", "mp3", "m4a", "ogg"])
                
                c3, c4 = st.columns(2)
                with c3:
                    status_assinante_audio = st.toggle("⭐ Jogador é assinante?", key="ass_a")
                with c4:
                    tipo_partida_audio = st.selectbox(
                        "🎮 Partida (Antijogo):", 
                        ["Não se aplica", "Ranked", "Lobby / GC Solo"], key="part_a"
                    )
                submit_audio = st.form_submit_button("🎧 Transcrever e Julgar", use_container_width=True)

            if submit_audio:
                if auth.bloqueio_limite_convidado():
                    pass
                elif arquivo_audio is None:
                    st.toast("⚠️ Faça o upload de um áudio.", icon="⚠️")
                else:
                    try:
                        # ETAPA 1: TRANSCRIÇÃO ULTRA RÁPIDA COM GROQ (WHISPER)
                        with st.spinner("1/2 ⚡ Transcrevendo áudio em alta velocidade com Groq..."):
                            arquivo_audio.seek(0)
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                                temp_file.write(arquivo_audio.read())
                                temp_path = temp_file.name

                            # Acionando a Groq diretamente no arquivo temporário
                            with open(temp_path, "rb") as file:
                                transcricao = groq_client.audio.transcriptions.create(
                                  file=(temp_path, file.read()),
                                  model="whisper-large-v3",
                                  prompt="CS2, gaming, toxicidade, palavrões, ofensa, gameplay, report, ban.",
                                  temperature=0.0
                                )
                            
                            texto_transcrito = transcricao.text
                            os.remove(temp_path)

                        # ETAPA 2: ANÁLISE DE REGRAS COM GEMINI (ZEUS)
                        with st.spinner("2/2 🧠 Aplicando regras corporativas..."):
                            if not texto_transcrito.strip():
                                st.session_state.ultimo_texto = ""
                                st.session_state.ultima_recomendacao = "⚠️ A transcrição falhou ou não identificou voz inteligível no áudio."
                            else:
                                prompt_audio = ai_service.construir_prompt(df_casos, texto_transcrito, status_assinante_audio, tipo_partida_audio)
                                
                                res_audio = model_zeus.generate_content(
                                    prompt_audio, 
                                    safety_settings=filtros_seguranca, 
                                    generation_config={"temperature": 0.0, "max_output_tokens": 1500}
                                )

                                texto_recomendacao = ""
                                if res_audio.candidates and res_audio.candidates[0].content:
                                    parts = res_audio.candidates[0].content.parts
                                    texto_recomendacao = "".join([p.text for p in parts if hasattr(p, 'text')])

                                st.session_state.ultimo_texto = texto_transcrito
                                st.session_state.ultima_recomendacao = texto_recomendacao if texto_recomendacao else "⚠️ A análise final foi bloqueada pelos filtros internos."
                            
                            st.session_state.arquivo_audio_atual = arquivo_audio
                            st.session_state.analise_concluida = True
                            auth.registrar_uso_convidado()
                            st.rerun()

                    except Exception as e:
                        st.error(f"Erro fatal ao processar áudio: {e}")

# ==========================================
# LADO DIREITO: VEREDITO
# ==========================================
with col_saida:
    if st.session_state.analise_concluida:
        with st.container(border=True):
            st.markdown("### 📢 Veredito do Zeus")
            if st.session_state.arquivo_audio_atual is not None:
                st.audio(st.session_state.arquivo_audio_atual)
            
            if not st.session_state.ultimo_texto.strip():
                st.warning(st.session_state.ultima_recomendacao)
            else:
                st.info(f"**Contexto capturado:**\n\n{st.session_state.ultimo_texto}")
                st.success(st.session_state.ultima_recomendacao)
    else:
        with st.container(border=True):
            st.markdown("### ⏳ Aguardando caso...")
            st.write("Insira um report em texto ou um arquivo de áudio no painel ao lado para ver o veredito do Zeus aparecer aqui.")