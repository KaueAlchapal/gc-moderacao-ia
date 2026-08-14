import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import random
import tempfile

# 1. LAYOUT WIDE (TELA CHEIA)
st.set_page_config(
    page_title="Zeus AI - Moderação",
    page_icon="⚡",
    layout="wide"
)

# ==========================================
# GERENCIAMENTO UNIFICADO DE MEMÓRIA
# ==========================================
if 'analise_concluida' not in st.session_state:
    st.session_state.analise_concluida = False
    st.session_state.ultimo_texto = ""
    st.session_state.ultima_recomendacao = ""
    st.session_state.aba_atual = "Texto"

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

# CONTRATANDO OS DOIS FUNCIONÁRIOS
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
Sua função é identificar a infração MAIS GRAVE contida no log e recomendar UMA ÚNICA punição principal (exceto no caso específico da Regra 5).

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
# BARRA LATERAL (SIDEBAR FLUTUANTE)
# ==========================================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    
    st.header("⚙️ Controle")
    st.caption(f"Banco: {len(df_casos)} casos.")
    
    # Só mostra os controles se houver uma análise pronta na tela
    if st.session_state.analise_concluida:
        if st.button("🔄 Nova Análise (Limpar Tela)", type="primary", use_container_width=True):
            st.session_state.analise_concluida = False
            st.rerun()
            
        st.divider()
        st.subheader("🧠 Quarentena ML")
        st.write("Ajuste a punição real para treinar a IA.")
        
        punicao_real = st.selectbox(
            "Veredito do Analista:", 
            ["Alerta", "Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5", "BAN", "Sem Punição"]
        )
        
        if st.button("💾 Salvar Feedback", use_container_width=True):
            salvar_feedback(st.session_state.ultimo_texto, punicao_real)
            st.toast("✅ Caso salvo com sucesso no banco de ML!", icon="🚀")

# ==========================================
# ÁREA PRINCIPAL
# ==========================================
st.title("Zeus - IA Moderadora ⚡")
st.markdown("Ferramenta de apoio à tomada de decisão baseada no histórico interno de moderação.")

aba_texto, aba_audio = st.tabs(["📝 Analisar Chat/Log", "🎧 Transcrever e Analisar Áudio"])

# --- ABA DE TEXTO ---
with aba_texto:
    with st.container(border=True):
        with st.form("formulario_texto", clear_on_submit=True):
            texto_report = st.text_area("📋 Cole o report recebido:", height=150, placeholder="Insira o log do chat ou descrição do antijogo...")
            
            col1, col2 = st.columns(2)
            with col1:
                status_assinante_texto = st.toggle("⭐ Jogador é assinante?", key="ass_texto")
            with col2:
                tipo_partida_texto = st.selectbox(
                    "🎮 Tipo de Partida (Antijogo):", 
                    ["Não se aplica", "Ranked", "Lobby / GC Solo"],
                    key="partida_texto"
                )
                
            enviar_texto = st.form_submit_button("🔍 Executar Análise de Texto", use_container_width=True)

        if enviar_texto:
            if not texto_report.strip():
                st.toast("⚠️ Cole algum texto antes de analisar.", icon="⚠️")
            else:
                with st.spinner("⚡ Zeus está analisando..."):
                    try:
                        prompt = construir_prompt(df_casos, texto_report, status_assinante_texto, tipo_partida_texto)
                        response = model_zeus.generate_content(
                            prompt,
                            safety_settings=filtros_seguranca,
                            generation_config={"temperature": 0.0}
                        )

                        if not response.candidates or len(response.candidates) == 0:
                            st.error("⚠️ Bloqueio de segurança mestre do Google acionado.")
                        else:
                            st.session_state.ultimo_texto = texto_report
                            st.session_state.ultima_recomendacao = response.text
                            st.session_state.analise_concluida = True
                            st.toast("✅ Análise concluída!", icon="✅")
                    except Exception as e:
                        st.error(f"Erro: {e}")

# --- ABA DE ÁUDIO ---
with aba_audio:
    with st.container(border=True):
        with st.form("formulario_audio", clear_on_submit=True):
            arquivo_audio = st.file_uploader("🎧 Selecione o áudio (.wav, .mp3)", type=["wav", "mp3", "m4a", "ogg"])
            
            col3, col4 = st.columns(2)
            with col3:
                status_assinante_audio = st.toggle("⭐ Jogador é assinante?", key="ass_audio")
            with col4:
                tipo_partida_audio = st.selectbox(
                    "🎮 Tipo de Partida (Antijogo):", 
                    ["Não se aplica", "Ranked", "Lobby / GC Solo"],
                    key="partida_audio"
                )
                
            enviar_audio = st.form_submit_button("🎧 Transcrever e Julgar Áudio", use_container_width=True)

        if enviar_audio:
            if arquivo_audio is None:
                st.toast("⚠️ Faça o upload de um áudio.", icon="⚠️")
            else:
                with st.spinner("✍️ Escrivão Neutro transcrevendo..."):
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                            temp_file.write(arquivo_audio.read())
                            temp_path = temp_file.name

                        arquivo_gemini = genai.upload_file(temp_path)
                        prompt_escrivao = "Você é um transcritor isento. Transcreva EXATAMENTE as palavras audíveis do áudio, sem adivinhar contexto."
                        
                        response_transcricao = model_escrivao.generate_content(
                            [prompt_escrivao, arquivo_gemini],
                            generation_config={"temperature": 0.0}
                        )
                        texto_transcrito = response_transcricao.text
                        
                        genai.delete_file(arquivo_gemini.name)
                        os.remove(temp_path)

                        # Julgamento
                        prompt_audio = construir_prompt(df_casos, texto_transcrito, status_assinante_audio, tipo_partida_audio)
                        response_audio = model_zeus.generate_content(
                            prompt_audio,
                            safety_settings=filtros_seguranca,
                            generation_config={"temperature": 0.0}
                        )

                        if not response_audio.candidates or len(response_audio.candidates) == 0:
                            st.error("⚠️ Bloqueio de segurança mestre acionado no julgamento.")
                        else:
                            st.session_state.ultimo_texto = texto_transcrito
                            st.session_state.ultima_recomendacao = response_audio.text
                            st.session_state.analise_concluida = True
                            st.toast("✅ Transcrição e Análise concluídas!", icon="✅")

                    except Exception as e:
                        st.error(f"Erro: {e}")

# ==========================================
# EXIBIÇÃO DE RESULTADOS (COMUM ÀS DUAS ABAS)
# ==========================================
if st.session_state.analise_concluida:
    with st.container(border=True):
        st.markdown("### 📢 Veredito do Zeus")
        st.info(f"**Contexto/Transcrição capturada:**\n\n_{st.session_state.ultimo_texto}_")
        st.success(st.session_state.ultima_recomendacao)