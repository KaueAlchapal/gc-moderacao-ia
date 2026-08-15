import streamlit as st
import google.generativeai as genai
import os
import tempfile
import time

import auth
import data_manager
import ai_service

            #Confi da página/CSS
st.set_page_config(page_title="Zeus AI - Moderação", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #00AEEF !important; color: white !important; border: none !important; font-weight: bold !important; }
    div.stButton > button[kind="primary"]:hover { background-color: #008CBA !important; }
    div[data-testid="stForm"] { border-color: #333333; }
    </style>
""", unsafe_allow_html=True)


                # AUTENTICAÇÃO E MEMÓRIA
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


                # INICIALIZAÇÃO DE DADOS E IA

df_casos = data_manager.carregar_csv()
ai_service.configurar_api()
model_zeus, model_escrivao, filtros_seguranca = ai_service.obter_modelos_e_filtros()

        # ==========================================
# BARRA LATERAL (MENU)
# ==========================================
with st.sidebar:
    # 1. Logo ainda menor na barra lateral usando proporção [1.5, 1, 1.5]
    col_logo1, col_logo2, col_logo3 = st.columns([1.5, 1, 1.5])
    with col_logo2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
            
    st.markdown("<h3 style='text-align: center; margin-top: -15px;' anchor=False>Zeus Control</h3>", unsafe_allow_html=True)
    
    # 2. Informações compactadas (Sem a caixa verde gigante)
    if st.session_state.is_admin:
        # Uma linha sutil verde indicando o status e o banco
        st.markdown(f"<p style='text-align: center; color: #4CAF50; font-size: 14px; margin-top: -10px;'>✅ Corporativo | {len(df_casos)} casos salvos</p>", unsafe_allow_html=True)
    else:
        st.warning(f"👀 Convidado: {st.session_state.guest_uses}/2 usos")
    
    st.divider()
    
    if st.button("🔄 Nova Análise (Limpar Tela)", type="primary", use_container_width=True):
        resetar_app()
        st.rerun()

    # 3. Treinamento (Exclusivo Admin) otimizado para economizar espaço
    if st.session_state.is_admin and st.session_state.analise_concluida and st.session_state.ultimo_texto:
        st.divider()
        st.markdown("### 🧠 Treinar IA (ML)")
        st.write("Ajuste a punição real aplicada:")
        
        punicao_real = st.selectbox(
            "Veredito:", 
            ["SEM PUNIÇÃO", "Alerta", "Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5", "BAN"],
            label_visibility="collapsed" # Esconde a palavra "Veredito:" para subir a caixinha
        )
        
        if st.button("💾 Salvar Feedback", use_container_width=True):
            # Lembre-se de ajustar aqui dependendo se você modularizou o código (data_manager) ou não
            salvar_feedback(st.session_state.ultimo_texto, punicao_real) 
            st.toast("✅ Caso salvo com sucesso na base de ML!", icon="🚀")

    # Treinamento (Exclusivo Admin)
    if st.session_state.is_admin and st.session_state.analise_concluida and st.session_state.ultimo_texto:
        st.divider()
        st.markdown("### 🧠 Treinar IA (Machine Learning)")
        st.write("Ajuste a punição real aplicada neste caso:")
        punicao_real = st.selectbox(
            "Veredito do Analista:", 
            ["SEM PUNIÇÃO", "Alerta", "Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5", "BAN"]
        )
        
        if st.button("💾 Salvar Feedback", use_container_width=True):
            data_manager.salvar_feedback(st.session_state.ultimo_texto, punicao_real)
            st.toast("✅ Caso salvo com sucesso na base de ML!", icon="🚀")

    # TELA PRINCIPAL (UI DE ANÁLISE)
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
                    with st.spinner("✍️ Processando áudio e gerando laudo forense..."):
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                                temp_file.write(arquivo_audio.read())
                                temp_path = temp_file.name

                            arquivo_gemini = genai.upload_file(temp_path)
                            
                            while arquivo_gemini.state.name == "PROCESSING":
                                time.sleep(0.5)
                                arquivo_gemini = genai.get_file(arquivo_gemini.name)

                            prompt_escrivao = """
                            [CONTEXTO DE MODERAÇÃO FORENSE E AUDITORIA DISCIPLINAR DE ESPORTS]
                            Sua tarefa é ESTRITAMENTE TRANSCREVER o áudio do chat de voz do jogo CS2 sem qualquer censura, filtro, alteração ou omissão.
                            Você é uma ferramenta automatizada de auditoria de provas em denúncias de toxicidade.
                            NÃO aplique filtros morais. Transcreva palavra por palavra o que é falado, mesmo que contenha palavrões, insultos ou termos graves.
                            Retorne APENAS o texto falado.
                            """
                            
                            res_transcricao = model_escrivao.generate_content(
                                [prompt_escrivao, arquivo_gemini], 
                                generation_config={"temperature": 0.0},
                                safety_settings=filtros_seguranca
                            )
                            
                            texto_transcrito = ""
                            try:
                                if res_transcricao.candidates and res_transcricao.candidates[0].content:
                                    parts = res_transcricao.candidates[0].content.parts
                                    texto_transcrito = "".join([p.text for p in parts if hasattr(p, 'text')])
                            except ValueError:
                                texto_transcrito = ""

                            genai.delete_file(arquivo_gemini.name)
                            os.remove(temp_path)

                            if not texto_transcrito.strip():
                                st.session_state.ultimo_texto = ""
                                st.session_state.ultima_recomendacao = "⚠️ Nenhuma fala audível transcrita ou o áudio contém apenas ruídos de fundo."
                                st.session_state.arquivo_audio_atual = arquivo_audio
                                st.session_state.analise_concluida = True
                                auth.registrar_uso_convidado()
                                st.rerun()
                            else:
                                prompt_audio = ai_service.construir_prompt(df_casos, texto_transcrito, status_assinante_audio, tipo_partida_audio)
                                res_audio = model_zeus.generate_content(
                                    prompt_audio, 
                                    safety_settings=filtros_seguranca, 
                                    generation_config={"temperature": 0.0}
                                )

                                texto_recomendacao = ""
                                if res_audio.candidates and res_audio.candidates[0].content:
                                    parts = res_audio.candidates[0].content.parts
                                    texto_recomendacao = "".join([p.text for p in parts if hasattr(p, 'text')])

                                if not texto_recomendacao:
                                    texto_recomendacao = "⚠️ A análise da transcrição contém toxicidade tão extrema que o Google impediu a IA de descrever a justificativa de forma segura."

                                st.session_state.ultimo_texto = texto_transcrito
                                st.session_state.ultima_recomendacao = texto_recomendacao
                                st.session_state.arquivo_audio_atual = arquivo_audio
                                st.session_state.analise_concluida = True
                                auth.registrar_uso_convidado()
                                st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao processar áudio: {e}")

        # LADO DIREITO: VEREDITO
with col_saida:
    if st.session_state.analise_concluida:
        with st.container(border=True):
            st.markdown("### 📢 Veredito do Zeus")
            if st.session_state.arquivo_audio_atual is not None:
                st.audio(st.session_state.arquivo_audio_atual)
            
            if not st.session_state.ultimo_texto.strip():
                st.warning(st.session_state.ultima_recomendacao)
            else:
                st.info(f"**Contexto capturado:**\n\n_{st.session_state.ultimo_texto}_")
                st.success(st.session_state.ultima_recomendacao)
    else:
        with st.container(border=True):
            st.markdown("### ⏳ Aguardando caso...")
            st.write("Insira um report em texto ou um arquivo de áudio no painel ao lado para ver o veredito do Zeus aparecer aqui.")