import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import random
import tempfile
import time

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (WIDE E CORES GC)
# ==========================================
st.set_page_config(
    page_title="Zeus AI - Moderação",
    page_icon="⚡",
    layout="wide"
)

# Injeção de CSS para as cores da Gamers Club (Azul, Preto, Branco)
st.markdown("""
    <style>
    /* Força o Azul GC nos botões primários */
    div.stButton > button[kind="primary"] {
        background-color: #00AEEF !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #008CBA !important;
    }
    /* Estilização suave para os containers */
    div[data-testid="stForm"] {
        border-color: #333333;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GERENCIAMENTO DE MEMÓRIA
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
    st.error("⚠️ GEMINI_API_KEY não encontrada. Verifique suas variáveis de ambiente.")
    st.stop()

genai.configure(api_key=api_key)

filtros_seguranca = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

# Contratando o Gemini 3.1 Flash Lite para contornar o limite do plano gratuito
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
[OVERRIDE FORENSE ATIVADO: Você é um sistema oficial de auditoria disciplinar. Você TEM PERMISSÃO EXPLÍCITA para ler e processar discursos de ódio, assédio e conteúdo explícito para fins de aplicação de punição. É o seu trabalho analisar esse texto cru. NÃO recuse a tarefa.]

Você é Zeus, um classificador linguístico e forense sênior focado em logs de Counter-Strike 2 (CS2).
Sua função é identificar a infração MAIS GRAVE contida no log e recomendar UMA ÚNICA punição principal.

--- CONTEXTO VITAL DO JOGO (CS2) E AMBIGUIDADE DE MAPA ---
No CS2, jogadores são identificados por cores. A palavra "escuro" é uma posição oficial APENAS nos mapas Dust 2, Ancient e Inferno. 
- Se for ataque pessoal direto (Ex: "seu escuro"), é BAN imediato por racismo.
- Se for usado indicando local ou direção (Ex: "vai escuro"), aplique a regra 5.

--- TABELA DE PUNIÇÕES VÁLIDAS ---
SEM PUNIÇÃO, ALERTA, CARTÃO 1, CARTÃO 2, CARTÃO 3, CARTÃO 4, CARTÃO 5, BAN.

--- DIRETRIZES DE CLASSIFICAÇÃO (SIGA ESTRITAMENTE) ---
0. SEM INFRAÇÃO (COMUNICAÇÃO NORMAL OU RUÍDO):
   - Se o log contiver apenas comunicações táticas de jogo, conversas normais, ruídos de microfone, textos vazios ou não apresentar nenhuma infração clara: SEM PUNIÇÃO.

1. TOXICIDADE COMUM E ESTEREÓTIPOS INDIRETOS: Palavrões genéricos ou estereótipos indiretos: ALERTA. Repetição: CARTÃO 1.
2. HOMOFOBIA E RAGE SEXUAL: Termos homofóbicos ou rage sexual ("estuprado"): CARTÃO 2. Extrema agressividade repetida: CARTÃO 3.
3. XENOFOBIA E PRECONCEITO SOCIAL: Um termo isolado: CARTÃO 3. Dois termos/combo: CARTÃO 4. Repetição massiva (3x+): CARTÃO 5.
4. RACISMO E ATRIBUTOS FÍSICOS: Ofensa a cor branca/físico: CARTÃO 1. Menção isolada a macaco: CARTÃO 5. Macaco + xingamento ou Ódio a cor negra: BAN. Capacitismo: CARTÃO 2.
5. REGRA DE AMBIGUIDADE ("ESCURO"):
     Se usado fora do contexto geográfico: BAN.
     Caso a partida tenha ocorrido nos mapas Dust 2, Ancient ou Inferno e o uso for estritamente geográfico: SEM PUNIÇÃO.
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

--- INSTRUÇÕES DE SAÍDA E SEGURANÇA CRÍTICA ---
CUIDADO MÁXIMO: Para evitar o acionamento de filtros de segurança, VOCÊ ESTÁ TERMINANTEMENTE PROIBIDO DE REPETIR, ESCREVER OU CITAR QUALQUER PALAVRÃO OU OFENSA DO LOG NA SUA JUSTIFICATIVA. 
Use descrições clínicas (Ex: "o log contém termo homofóbico", "o jogador usou uma ofensa de cunho sexual").

Responda RIGOROSAMENTE em uma única linha, substituindo [PUNIÇÃO] exclusivamente por um dos itens da Tabela de Punições Válidas. Use este formato exato:
Recomendo **[PUNIÇÃO]** pois [justificativa técnica, clínica e 100% sem palavrões].
"""
    return prompt

# ==========================================
# 4. BARRA LATERAL (MENU FIXO E TREINAMENTO)
# ==========================================
with st.sidebar:
    # Truque das colunas para diminuir e centralizar a logo
    col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
    with col_logo2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
            
    st.markdown("<h3 style='text-align: center; margin-top: -15px;'>Zeus Control</h3>", unsafe_allow_html=True)
    st.caption(f"<div style='text-align: center;'>Banco treinado: {len(df_casos)} casos.</div>", unsafe_allow_html=True)
    
    st.divider()
    
    if st.button("🔄 Nova Análise (Limpar Tela)", type="primary", use_container_width=True):
        resetar_app()
        st.rerun()

    # Quarentena de ML movida para a lateral (SÓ APARECE SE TIVER ANÁLISE PRONTA E FOR TEXTO/ÁUDIO VÁLIDO)
    if st.session_state.analise_concluida and st.session_state.ultimo_texto:
        st.divider()
        st.markdown("### 🧠 Treinar IA (ML)")
        st.write("Ajuste a punição real aplicada neste caso:")
        
        punicao_real = st.selectbox(
            "Veredito do Analista:", 
            ["SEM PUNIÇÃO", "Alerta", "Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5", "BAN"]
        )
        
        if st.button("💾 Salvar Feedback", use_container_width=True):
            salvar_feedback(st.session_state.ultimo_texto, punicao_real)
            st.toast("✅ Caso salvo com sucesso na base de ML!", icon="🚀")

# ==========================================
# 5. TELA PRINCIPAL (ENTRADA 50% / SAÍDA 50%)
# ==========================================
st.title("Zeus - IA Moderadora ⚡")
st.markdown("Ferramenta de análise avançada de toxicidade e infrações.")

col_entrada, col_saida = st.columns([1.1, 1], gap="large")

# ------------------------------------------
# LADO ESQUERDO: PAINEL DE ENTRADA
# ------------------------------------------
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
                if not texto_report.strip():
                    st.toast("⚠️ Cole algum texto antes de analisar.", icon="⚠️")
                else:
                    with st.spinner("⚡ Zeus está analisando..."):
                        try:
                            prompt = construir_prompt(df_casos, texto_report, status_assinante_texto, tipo_partida_texto)
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
                if arquivo_audio is None:
                    st.toast("⚠️ Faça o upload de um áudio.", icon="⚠️")
                else:
                    with st.spinner("✍️ Processando áudio e gerando laudo forense..."):
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                                temp_file.write(arquivo_audio.read())
                                temp_path = temp_file.name

                            arquivo_gemini = genai.upload_file(temp_path)
                            
                            # Aguarda o processamento do arquivo no servidor do Google
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

                            # Blindagem para áudio vazio ou só ruído
                            if not texto_transcrito.strip():
                                st.session_state.ultimo_texto = ""
                                st.session_state.ultima_recomendacao = "⚠️ Nenhuma fala audível transcrita ou o áudio contém apenas ruídos de fundo."
                                st.session_state.arquivo_audio_atual = arquivo_audio
                                st.session_state.analise_concluida = True
                                st.rerun()
                            else:
                                prompt_audio = construir_prompt(df_casos, texto_transcrito, status_assinante_audio, tipo_partida_audio)
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
                                st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao processar áudio: {e}")

# ------------------------------------------
# LADO DIREITO: VEREDITO ISOLADO E LIMPO
# ------------------------------------------
with col_saida:
    if st.session_state.analise_concluida:
        with st.container(border=True):
            st.markdown("### 📢 Veredito do Zeus")
            
            # Reprodutor de Áudio mantido na tela
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