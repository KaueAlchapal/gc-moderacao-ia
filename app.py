import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import random
import tempfile

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (WIDE)
# ==========================================
st.set_page_config(
    page_title="Zeus AI - Moderação",
    page_icon="⚡",
    layout="wide"
)

# ==========================================
# 2. GERENCIAMENTO DE MEMÓRIA (CORRIGIDO)
# ==========================================
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
# 3. BACKEND E IA
# ==========================================
CSV_FILE = "casos.csv"

@st.cache_data
def carregar_csv():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=[
        "Exemplos de ocorridos nos reports (Falas/Chats)",
        "Punição aplicada",
        "Assinante?"
    ])

df_casos = carregar_csv()

def salvar_feedback(texto, punicao):
    arquivo_treino = "treinamento.csv"
    novo_dado = pd.DataFrame([{
        "Exemplos de ocorridos nos reports (Falas/Chats)": texto,
        "Punição aplicada": punicao
    }])
    if os.path.exists(arquivo_treino):
        novo_dado.to_csv(arquivo_treino, mode='a', header=False, index=False)
    else:
        novo_dado.to_csv(arquivo_treino, index=False)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ GEMINI_API_KEY não encontrada.")
    st.stop()

genai.configure(api_key=api_key)

filtros_seguranca = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

# Usando o 3.1 Flash Lite para contornar o limite de requisições do plano gratuito
model_zeus = genai.GenerativeModel("gemini-3.1-flash-lite")
model_escrivao = genai.GenerativeModel("gemini-3.1-flash-lite")

def construir_prompt(dados_csv, texto_usuario, eh_assinante, tipo_partida):
    quantidade = min(len(dados_csv), 10)
    exemplos = dados_csv.sample(quantidade, random_state=random.randint(1, 999999))
    historico = ""
    for _, row in exemplos.iterrows():
        historico += f'Texto: "{row["Exemplos de ocorridos nos reports (Falas/Chats)"]}"\n'
        historico += f'Punição: {row["Punição aplicada"]}\n\n'

    assinante = "SIM" if eh_assinante else "NÃO"

    prompt = f"""
Você é Zeus, um classificador linguístico e forense sênior focado em logs de Counter-Strike 2 (CS2).
Sua função é identificar a infração MAIS GRAVE contida no log e recomendar UMA ÚNICA punição principal.

--- CONTEXTO VITAL DO JOGO (CS2) E AMBIGUIDADE DE MAPA ---
No CS2, jogadores são identificados por cores. A palavra "escuro" é uma posição oficial APENAS nos mapas Dust 2, Ancient e Inferno. 
- Se for ataque pessoal direto (Ex: "seu escuro"), é BAN imediato por racismo.
- Se for usado indicando local ou direção (Ex: "vai escuro"), VOCÊ É OBRIGADO a usar a estrutura da Regra 5.

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- DIRETRIZES DE CLASSIFICAÇÃO (SIGA ESTRITAMENTE) ---
1. TOXICIDADE COMUM E ESTEREÓTIPOS INDIRETOS: Palavrões genéricos ou estereótipos indiretos: ALERTA. Repetição: CARTÃO 1.
2. HOMOFOBIA E RAGE SEXUAL: Termos homofóbicos ou rage sexual ("estuprado"): CARTÃO 2. Extrema agressividade repetida: CARTÃO 3.
3. XENOFOBIA E PRECONCEITO SOCIAL: Um termo isolado: CARTÃO 3. Dois termos/combo: CARTÃO 4. Repetição massiva (3x+): CARTÃO 5.
4. RACISMO E ATRIBUTOS FÍSICOS: Ofensa a cor branca/físico: CARTÃO 1. Menção isolada a macaco: CARTÃO 5. Macaco + xingamento ou Ódio a cor negra: BAN. Capacitismo: CARTÃO 2.
5. REGRA DE AMBIGUIDADE ("ESCURO"):
     Recomendo **BAN** pois o termo configura racismo camuflado se usado fora do contexto geográfico.
     Entretanto, caso a partida tenha ocorrido nos mapas Dust 2, Ancient ou Inferno, **NÃO RECOMENDO PUNIÇÃO** pelo termo.
6. NAZISMO E EXTREMISMO: Isolado: CARTÃO 4. Com xingamentos: CARTÃO 5. Apologia literal: BAN.
7. AMEAÇA À VIDA / ABUSO LITERAL: Foco na palavra de abuso ("foi abusado"): CARTÃO 4. Ameaça literal de morte/abuso a pessoa ou família: BAN.
8. REGRA DO ASSINANTE: Se Assinante = SIM, reduza a punição em 1 nível APENAS para a regra 1.
9. ANTIJOGO: Se "Ranked": CARTÃO 1. Se "Lobby / GC Solo": ALERTA. (Trava: Se houver xingamento grave no relato, ignore antijogo).
10. CONDUTA DE MÁ FÉ: Mentiras, falsas dicas: ALERTA. Ghosting/Telar: CARTÃO 2.
11. GORDOFOBIA: Geral: CARTÃO 1. Combo: CARTÃO 2. Repetição: CARTÃO 3.
12. MACHISMO: Geral: CARTÃO 2. Combo: CARTÃO 3. Repetição: CARTÃO 4. Abuso machista ("estuprada"): CARTÃO 4.

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}
[TIPO DE PARTIDA]: {tipo_partida}

--- INSTRUÇÕES DE SAÍDA ---
Não cite os palavrões na sua justificativa. Não use palavras de ligação soltas. 
Responda RIGOROSAMENTE em uma única linha, neste formato exato (salvo regra 5):
Recomendo **[PUNIÇÃO]** pois [justificativa técnica].
"""
    return prompt

# ==========================================
# 4. BARRA LATERAL (MENU FIXO)
# ==========================================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.caption(f"📊 Banco treinado: {len(df_casos)} casos.")
    
    st.divider()
    
    # Botão fixo e sempre visível para resetar a tela
    if st.button("🔄 Nova Análise (Limpar Tudo)", type="primary", use_container_width=True):
        resetar_app()
        st.rerun()

# ==========================================
# 5. TELA PRINCIPAL (DIVISÃO 50/50)
# ==========================================
st.title("Zeus - IA Moderadora ⚡")
st.markdown("Ferramenta de análise avançada de toxicidade e infrações.")

# Divisão de colunas: Esquerda (Entrada) | Direita (Saída)
col_entrada, col_saida = st.columns([1.1, 1], gap="large")

# ------------------------------------------
# LADO ESQUERDO: PAINEL DE ENTRADA
# ------------------------------------------
with col_entrada:
    aba_texto, aba_audio = st.tabs(["📝 Analisar Chat/Log", "🎧 Transcrever Áudio"])

    with aba_texto:
        with st.container(border=True):
            # Form sem o clear_on_submit para não apagar o que o analista digitou atoa
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
                if not texto_report.strip():
                    st.toast("⚠️ Cole algum texto antes de analisar.", icon="⚠️")
                else:
                    with st.spinner("⚡ Analisando..."):
                        try:
                            prompt = construir_prompt(df_casos, texto_report, status_assinante_texto, tipo_partida_texto)
                            response = model_zeus.generate_content(prompt, safety_settings=filtros_seguranca, generation_config={"temperature": 0.0})
                            if response.candidates:
                                st.session_state.ultimo_texto = texto_report
                                st.session_state.ultima_recomendacao = response.text
                                st.session_state.arquivo_audio_atual = None # Limpa áudio se for texto
                                st.session_state.analise_concluida = True
                                st.rerun() # Atualiza a tela instantaneamente
                        except Exception as e:
                            st.error(f"Erro: {e}")

    with aba_audio:
        with st.container(border=True):
            # Form sem clear_on_submit: MANTÉM O ÁUDIO NA TELA!
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
                if arquivo_audio is None:
                    st.toast("⚠️ Faça o upload de um áudio.", icon="⚠️")
                else:
                    with st.spinner("✍️ Escrivão transcrevendo e Zeus julgando..."):
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                                temp_file.write(arquivo_audio.read())
                                temp_path = temp_file.name

                            arquivo_gemini = genai.upload_file(temp_path)
                            prompt_escrivao = "Transcreva EXATAMENTE as palavras audíveis do áudio, sem adivinhar contexto."
                            
                            res_transcricao = model_escrivao.generate_content([prompt_escrivao, arquivo_gemini], generation_config={"temperature": 0.0})
                            texto_transcrito = res_transcricao.text
                            
                            genai.delete_file(arquivo_gemini.name)
                            os.remove(temp_path)

                            prompt_audio = construir_prompt(df_casos, texto_transcrito, status_assinante_audio, tipo_partida_audio)
                            res_audio = model_zeus.generate_content(prompt_audio, safety_settings=filtros_seguranca, generation_config={"temperature": 0.0})

                            if res_audio.candidates:
                                st.session_state.ultimo_texto = texto_transcrito
                                st.session_state.ultima_recomendacao = res_audio.text
                                st.session_state.arquivo_audio_atual = arquivo_audio # Salva o áudio na memória
                                st.session_state.analise_concluida = True
                                st.rerun() # Atualiza a tela instantaneamente
                        except Exception as e:
                            st.error(f"Erro: {e}")

# ------------------------------------------
# LADO DIREITO: RESULTADOS E MACHINE LEARNING
# ------------------------------------------
with col_saida:
    if st.session_state.analise_concluida:
        with st.container(border=True):
            st.markdown("### 📢 Veredito do Zeus")
            
            # Se for áudio, exibe um player de áudio elegante para o analista reouvir!
            if st.session_state.arquivo_audio_atual is not None:
                st.audio(st.session_state.arquivo_audio_atual)
            
            st.info(f"**Contexto capturado:**\n\n_{st.session_state.ultimo_texto}_")
            st.success(st.session_state.ultima_recomendacao)
            
        with st.container(border=True):
            st.markdown("### 🧠 Treinar Zeus (Machine Learning)")
            st.markdown("Ajuste a punição real para treinar a IA.")
            
            punicao_real = st.selectbox(
                "Veredito final aplicado:", 
                ["Alerta", "Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5", "BAN", "Sem Punição"]
            )
            
            if st.button("💾 Salvar Feedback no Banco de Treinamento", use_container_width=True):
                salvar_feedback(st.session_state.ultimo_texto, punicao_real)
                st.toast("✅ Salvo com sucesso! A IA ficará mais inteligente.", icon="🚀")
    else:
        # Mensagem de espera elegante
        with st.container(border=True):
            st.markdown("### ⏳ Aguardando caso...")
            st.write("Insira um report em texto ou um arquivo de áudio no painel ao lado para ver o veredito do Zeus aparecerá aqui.")