import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import tempfile
import time

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
auth.verificar_acesso() # Se não passar, a tela de login bloqueia aqui

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

def limpar_arquivos_antigos_gemini():
    """Varre e deleta arquivos travados na API para evitar lentidão e limite de cota."""
    try:
        for f in genai.list_files():
            genai.delete_file(f.name)
    except Exception:
        pass

# ==========================================
# INICIALIZAÇÃO DE DADOS E IA
# ==========================================
df_casos = data_manager.carregar_csv()
ai_service.configurar_api()
model_zeus, model_escrivao, _ = ai_service.obter_modelos_e_filtros()

# Filtros completamente desligados
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
    
    # É ESTE BOTÃO QUE VAI LIMPAR A TELA AGORA
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
            # RETORNEI PARA FALSE PARA O ÁUDIO NÃO SUMIR DA TELA
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
                        # ETAPA 0: FAXINA DE ARQUIVOS PRESOS
                        with st.spinner("0/3 🧹 Limpando cache de uploads antigos..."):
                            limpar_arquivos_antigos_gemini()

                        # ETAPA 1: UPLOAD
                        with st.spinner("1/3 📤 Subindo arquivo seguro para o Google..."):
                            arquivo_audio.seek(0) 
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                                temp_file.write(arquivo_audio.read())
                                temp_path = temp_file.name

                            tipo_mime = arquivo_audio.type if arquivo_audio.type else "audio/wav"
                            arquivo_gemini = genai.upload_file(temp_path, mime_type=tipo_mime)
                        
                        # ETAPA 2: PROCESSAMENTO RESILIENTE
                        with st.spinner("2/3 ⏳ Aguardando Google processar..."):
                            tentativas = 0
                            # Tenta até 60 vezes pausando 5 segundos = 5 minutos de tolerância na fila
                            while arquivo_gemini.state.name == "PROCESSING" and tentativas < 60:
                                time.sleep(5)
                                arquivo_gemini = genai.get_file(arquivo_gemini.name)
                                tentativas += 1

                            if arquivo_gemini.state.name == "FAILED":
                                st.error("❌ Erro interno da API: O Google rejeitou este arquivo na entrada.")
                                st.stop()
                            elif arquivo_gemini.state.name == "PROCESSING":
                                st.error("❌ Timeout: O Google levou mais de 5 minutos na fila de processamento e estourou o tempo.")
                                st.stop()

                        # ETAPA 3: TRANSCRIÇÃO (COM DIAGNÓSTICO EXATO E TEMPERATURA MAIS ALTA)
                        with st.spinner("3/3 ✍️ Extraindo falas e aplicando regras..."):
                            
                            # PROMPT AJUSTADO para não engatilhar o modelo com discursos problemáticos muito repetitivos
                            prompt_escrivao = """
                            Sua tarefa é transcrever o arquivo de áudio. 
                            Gere uma transcrição descritiva do que está sendo dito pelos participantes, sem alterar o sentido original das palavras. 
                            Ignore sons não verbais e ruídos de fundo (como sons de jogo, tiros, assobios prolongados e ruídos de estática). 
                            Retorne apenas o texto correspondente à fala humana transcrita.
                            """
                            
                            # MUDANÇA CRUCIAL: Aumentei a temperature para 0.8 para evitar que o modelo trave em loops infinitos com a repetição de palavras
                            res_transcricao = model_escrivao.generate_content(
                                [prompt_escrivao, arquivo_gemini], 
                                generation_config={"temperature": 0.8, "max_output_tokens": 8192},
                                safety_settings=filtros_seguranca,
                                request_options={"timeout": 600}
                            )
                            
                            texto_transcrito = ""
                            motivo_bloqueio = ""

                            # CAPTURA DE DIAGNÓSTICO PARA SABERMOS PORQUE ELE PAROU
                            if res_transcricao.prompt_feedback and res_transcricao.prompt_feedback.block_reason:
                                motivo_bloqueio = f"Google bloqueou todo o comando. Motivo: {res_transcricao.prompt_feedback.block_reason.name}"
                            elif res_transcricao.candidates:
                                razao_parada = res_transcricao.candidates[0].finish_reason.name
                                if razao_parada != "STOP":
                                    motivo_bloqueio = f"Geração cortada pelo Filtro de Segurança Interno: {razao_parada}"
                                elif res_transcricao.candidates[0].content:
                                    parts = res_transcricao.candidates[0].content.parts
                                    texto_transcrito = "".join([p.text for p in parts if hasattr(p, 'text')])

                            # Limpa arquivos para não encher a cota
                            genai.delete_file(arquivo_gemini.name)
                            os.remove(temp_path)

                            if not texto_transcrito.strip():
                                st.session_state.ultimo_texto = ""
                                if motivo_bloqueio:
                                    st.session_state.ultima_recomendacao = f"⚠️ Falha de Transcrição!\n\n**Detalhe:** {motivo_bloqueio}\n\n*Nota: Áudios com extrema repetição de discursos problemáticos ou distorcidos podem acionar filtros irremovíveis da API.*"
                                else:
                                    st.session_state.ultima_recomendacao = "⚠️ O Google não encontrou nenhuma voz audível/inteligível neste arquivo após desconsiderar os ruídos."
                            else:
                                prompt_audio = ai_service.construir_prompt(df_casos, texto_transcrito, status_assinante_audio, tipo_partida_audio)
                                
                                # Análise final com temperature baixa para focar na lógica, mas com alto limite de tokens
                                res_audio = model_zeus.generate_content(
                                    prompt_audio, 
                                    safety_settings=filtros_seguranca, 
                                    generation_config={"temperature": 0.0, "max_output_tokens": 8192},
                                    request_options={"timeout": 600}
                                )

                                texto_recomendacao = ""
                                if res_audio.candidates and res_audio.candidates[0].content:
                                    parts = res_audio.candidates[0].content.parts
                                    texto_recomendacao = "".join([p.text for p in parts if hasattr(p, 'text')])

                                if not texto_recomendacao:
                                    texto_recomendacao = "⚠️ A IA transcreveu o áudio com sucesso, mas a resposta final da regra de negócio foi bloqueada pelos filtros."

                                st.session_state.ultimo_texto = texto_transcrito
                                st.session_state.ultima_recomendacao = texto_recomendacao
                            
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