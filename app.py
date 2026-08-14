import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import random
import tempfile

st.set_page_config(
    page_title="Zeus AI - Moderação",
    page_icon="logo.png",
    layout="centered"
)

# ==========================================
# GERENCIAMENTO DE MEMÓRIA (SESSION STATE)
# ==========================================
if 'analise_texto_concluida' not in st.session_state:
    st.session_state.analise_texto_concluida = False
    st.session_state.texto_infrator_texto = ""
    st.session_state.recomendacao_texto = ""

if 'analise_audio_concluida' not in st.session_state:
    st.session_state.analise_audio_concluida = False
    st.session_state.texto_infrator_audio = ""
    st.session_state.recomendacao_audio = ""

if os.path.exists("logo.png"):
    st.image("logo.png", width=90)

st.title("Zeus - IA Moderadora ⚡")
st.subheader("Assistente de Análise de Reports")
st.write("Ferramenta de apoio à tomada de decisão baseada no histórico interno de moderação.")

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

# ==========================================
# FUNÇÃO DE MACHINE LEARNING (QUARENTENA)
# ==========================================
def salvar_feedback(texto, punicao):
    arquivo_treino = "treinamento.csv"
    novo_dado = pd.DataFrame([{
        "Exemplos de ocorridos nos reports (Falas/Chats)": texto,
        "Punição aplicada": punicao
    }])
    
    # Se o arquivo já existir, insere no final. Se não, cria com cabeçalho.
    if os.path.exists(arquivo_treino):
        novo_dado.to_csv(arquivo_treino, mode='a', header=False, index=False)
    else:
        novo_dado.to_csv(arquivo_treino, index=False)

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ GEMINI_API_KEY não encontrada.")
    st.stop()

genai.configure(api_key=api_key)

# Filtros desligados na entrada da API
filtros_seguranca = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

# CONTRATANDO OS DOIS FUNCIONÁRIOS (Limitados a 3.1 Flash Lite para economizar a API)
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
No CS2, jogadores são identificados por cores (azul, roxo, amarelo, laranja, verde).
A palavra "escuro" é uma posição oficial APENAS nos mapas Dust 2, Ancient e Inferno. 
- Se for ataque pessoal direto (Ex: "seu escuro", "você é escuro"), é BAN imediato por racismo.
- Se for usado indicando local ou direção (Ex: "vai escuro", "tá no escuro"), VOCÊ É OBRIGADO a usar o formato de resposta conectada da Regra 5.

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- DIRETRIZES DE CLASSIFICAÇÃO (SIGA ESTRITAMENTE) ---

1. TOXICIDADE COMUM (RAGE) E ESTEREÓTIPOS INDIRETOS:
   - Palavrões genéricos e insultos leves (Ex: "lixo", "merda", "bundão", "horrível", "bot", "babaca", "filho da puta", "vai toma no cu"): ALERTA.
   - Frases com estereótipos culturais/regionais INDIRETOS, SEM citar o nome do estado/região (Ex: "vai quebrar coco", "caçar camaleão", "comer calango", "comer pão de queijo"): ALERTA.
   - Repetição frequente desses termos (xingamentos ou estereótipos indiretos): CARTÃO 1.

2. HOMOFOBIA E RAGE SEXUAL: 
   - Uso de termos homofóbicos ou rage sexual passivo/agressivo: CARTÃO 2.
   - EXCEÇÃO: Termos de abuso usados como rage casual ("seu estuprado do caralho","estuprado") são Cartão 2 (Homofobia), não ameaça literal. Mesmo que venha acompanhado de xingamentos comuns (como filho da puta), a punição unificada deve ser CARTÃO 2.
   - Extrema agressividade homofóbica repetida: CARTÃO 3.

3. XENOFOBIA, REGIONALISMO E PRECONCEITO SOCIAL (OFENSAS EXPLÍCITAS): 
   - Requer ofensa EXPLÍCITA a regiões (nordestino, baiano, paulista) ou termos de preconceito social/classe (Ex: favelado, faveladinha).
   - UM termo isolado e explícito: CARTÃO 3.
   - DOIS termos ou termo associado a xingamento comum (Ex: "favelado de merda", "favelado do caralho", "seu nordestino de merda", "nordestino sem agua", "sulista pobre"): CARTÃO 4.
   - REPETIÇÃO MASSIVA (O termo é repetido 3 ou mais vezes no mesmo log) ou associação direta com falas de supremacia (Ex: "raça inferior", "sub-raça"): CARTÃO 5.

4. RACISMO E ATRIBUTOS FÍSICOS:
   - Ofensa baseada exclusivamente e isoladamente na cor branca ou aspecto físico (Ex: "você é branco", "seu branco", "branquelo"): CARTÃO 1.
   - Termos primatas/animais relacionados a macacos isolados (Ex: "ta pulando igual um macaco", "você anda igual um macaco", "você pensa igual um macaco", "tá perdido igual um macaco", "joga igual um primata"): CARTÃO 5.
   - Termo primata associado a xingamento extra (Ex: "seu macaco do caralho", "macaquinho de merda", "macaco fodido", "mono de mierda", "monito de mierda", "macaco de mierda") : BAN.
   - Direcionamento de ódio à cor da pele negra (Ex: "seu preto", "escravo", "pretito", ou ofensa direta de posição: "seu escuro", "você é escuro"): BAN.
   - Capacitismo, menções a características físicas do jogador: CARTÃO 2.

5. REGRA ESPECIAL DE AMBIGUIDADE DE POSIÇÃO ("ESCURO"):
   - Toda vez que a palavra "escuro" for usada no sentido de local/direção, siga EXATAMENTE esta estrutura conectada em linhas separadas:
     Recomendo **BAN** pois o termo configura racismo camuflado se usado fora do contexto geográfico.
     Entretanto, caso a partida tenha ocorrido nos mapas Dust 2, Ancient ou Inferno, **NÃO RECOMENDO PUNIÇÃO** pelo termo, pois configura comunicação normal de jogo.
     [USE ESTA 3ª LINHA APENAS SE HOUVER OUTRO XINGAMENTO]: Ainda assim, recomendo **[PUNIÇÃO DO XINGAMENTO]** pois [justifique o outro xingamento extra].

6. NAZISMO E EXTREMISMO:
   - Acusação usando termo extremista isolado: CARTÃO 4.
   - Acusação somada a xingamentos: CARTÃO 5.
   - Apologia literal: BAN.

7. AMEAÇA DE VIOLÊNCIA SEXUAL LITERAL E AMEAÇA À VIDA:
   - Menção isolada focada na palavra de abuso (Ex: "seu pai deve ter te estuprado", "foi abusado quando era criança"): CARTÃO 4.
   - Ameaças literais contra a pessoa ou familiares (Ex: "sua irmãzinha vai ser abusada", "vou estuprar sua mãe", "vou te matar na vida real", "vou matar sua mãe na sua frente", "vou estuprar sua mãe na sua frente", "me passa seu endereço que vou ai te matar"): BAN.

8. REGRA DO ASSINANTE:
   - Se Assinante = SIM, reduza a punição em 1 nível APENAS para o item 1 (Toxicidade Comum).

9. REGRA DE ANTIJOGO (RELATOS DE ATITUDES):
   - Refere-se a ATITUDES descritas pelo analista (Ex: "descaso", "tk no aliado", "tk com he", "tk com arma", "tk com faca", "travando passagem", "cegando aliado").
   - A punição depende EXCLUSIVAMENTE do [TIPO DE PARTIDA]:
     * Se for "Ranked": CARTÃO 1.
     * Se for "Lobby / GC Solo": ALERTA.
   - TRAVA DE PRIORIDADE: Se o texto colado for um log de chat onde o jogador está xingando *enquanto reclama* de antijogo (Ex: "Seu preto macaco, você está dando tk"), IGNORE a regra de antijogo. A infração de chat (Racismo, Homofobia, etc.) é SEMPRE a mais grave e deve sobrepor o relato de antijogo.

10. CONDUTA DE MÁ FÉ:
   - Usar bind snap tap, inventar mentiras, afirmar vantagem em conhecer staff da GC, se passar por admin/suporte, figura pública ou tentar enganar jogadores com dicas falsas (Ex: "digita kill no console que você aumenta o som"), incitar atitudes ruins: ALERTA.
   - Telar jogadores, dar ghosting (Ex: "telando na partida", "dando ghosting"): CARTÃO 2.

11. GORDOFOBIA:
   - Termos gordofóbicos gerais (Ex: "seu gordo", "cala a boca gordão"): CARTÃO 1.
   - Termos gordofóbicos com adição de toxicidade comum: CARTÃO 2.
   - Repetição frequente desses termos (repetir mais de 4 vezes): CARTÃO 3.

12. MACHISMO:
   - Termos machistas gerais isolados (Ex: "vai lavar uma louça", "sua vagabunda", "sua puta", "piranha fodida", "cachorra do caralho", "safada putinha"): CARTÃO 2.
   - Termos machistas gerais com adição de toxicidade comum: CARTÃO 3.
   - Repetição frequente desses termos (repetir mais de 4 vezes): CARTÃO 4.
   - Termos de abuso focados no machismo (Ex: "sua estuprada do caralho", "seu pai abusou de você sua puta", "você é estuprada"): CARTÃO 4.

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}
[TIPO DE PARTIDA]: {tipo_partida}

--- INSTRUÇÕES DE SAÍDA ---
Não cite os palavrões na sua justificativa. Não use palavras de ligação soltas (como "Adicionalmente"). 
- Se o caso se enquadrar na REGRA 5 ("escuro" como posição): Você DEVE usar a estrutura conectada de 3 linhas ensinada na Regra 5.
- Para TODOS os outros casos (incluindo Antijogo definido pela interface): Você DEVE aplicar apenas a punição da infração MAIS GRAVE detectada. Responda RIGOROSAMENTE em uma única linha, neste formato exato:
  Recomendo **[PUNIÇÃO]** pois [justificativa técnica].
"""
    return prompt

aba_texto, aba_audio = st.tabs(["📝 Analisar Chat/Log", "🎧 Transcrever e Analisar Áudio"])

# ==========================================
# ABA 1: ANÁLISE DE TEXTO TRADICIONAL
# ==========================================
with aba_texto:
    # O clear_on_submit=True apaga o texto da caixa após o envio
    with st.form("formulario_texto", clear_on_submit=True):
        texto_report = st.text_area("📋 Cole aqui o report:", height=200)
        
        col1, col2 = st.columns(2)
        with col1:
            status_assinante_texto = st.checkbox("⭐ Jogador é assinante?", key="ass_texto")
        with col2:
            tipo_partida_texto = st.selectbox(
                "🎮 Tipo de Partida (Apenas para Antijogo):", 
                ["Não se aplica", "Ranked", "Lobby / GC Solo"],
                key="partida_texto"
            )
            
        enviar_texto = st.form_submit_button("🔍 Analisar Texto")

    if enviar_texto:
        if not texto_report.strip():
            st.warning("Cole algum texto antes.")
        else:
            with st.spinner("⚡ Zeus está analisando o texto..."):
                try:
                    prompt = construir_prompt(df_casos, texto_report, status_assinante_texto, tipo_partida_texto)
                    response = model_zeus.generate_content(
                        prompt,
                        safety_settings=filtros_seguranca,
                        generation_config={"temperature": 0.0}
                    )

                    if not response.candidates or len(response.candidates) == 0:
                        st.warning("⚠️ O bloqueio de segurança mestre do Google foi acionado.")
                    else:
                        # Salva o resultado na memória da sessão
                        st.session_state.texto_infrator_texto = texto_report
                        st.session_state.recomendacao_texto = response.text
                        st.session_state.analise_texto_concluida = True

                except Exception as e:
                    st.error("Erro ao processar análise.")
                    st.code(str(e))

    # Exibe os resultados e a Quarentena de ML se a análise estiver na memória
    if st.session_state.analise_texto_concluida:
        st.success("✅ Análise concluída!")
        st.markdown("### 📢 Recomendação do Zeus:")
        st.write(st.session_state.recomendacao_texto)
        
        st.markdown("---")
        st.markdown("### 🧠 Treinar Zeus (Machine Learning)")
        st.write("Qual foi a punição final aplicada pelo analista? Salve para treinar a IA no futuro.")
        
        punicao_real_texto = st.selectbox(
            "Punição aplicada de fato:", 
            ["Alerta", "Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5", "BAN", "Sem Punição"], 
            key="punicao_ml_texto"
        )
        
        col_fb1, col_fb2 = st.columns(2)
        with col_fb1:
            if st.button("💾 Salvar na Quarentena (ML)", key="salvar_texto"):
                salvar_feedback(st.session_state.texto_infrator_texto, punicao_real_texto)
                st.success("✅ Caso salvo com sucesso no arquivo treinamento.csv!")
        with col_fb2:
            if st.button("🔄 Limpar Tela e Nova Análise", key="reset_texto"):
                st.session_state.analise_texto_concluida = False
                st.rerun()

# ==========================================
# ABA 2: TRANSCRIÇÃO E ANÁLISE DE ÁUDIO
# ==========================================
with aba_audio:
    # O clear_on_submit=True descarta o arquivo de áudio pesado da memória RAM após o envio
    with st.form("formulario_audio", clear_on_submit=True):
        st.markdown("Faça o upload do áudio extraído da demo do CS2. O Zeus irá transcrever e julgar.")
        arquivo_audio = st.file_uploader("🎧 Selecione o arquivo (.wav, .mp3)", type=["wav", "mp3", "m4a", "ogg"])
        
        col3, col4 = st.columns(2)
        with col3:
            status_assinante_audio = st.checkbox("⭐ Jogador é assinante?", key="ass_audio")
        with col4:
            tipo_partida_audio = st.selectbox(
                "🎮 Tipo de Partida (Apenas para Antijogo):", 
                ["Não se aplica", "Ranked", "Lobby / GC Solo"],
                key="partida_audio"
            )
            
        enviar_audio = st.form_submit_button("🎧 Transcrever e Julgar")

    if enviar_audio:
        if arquivo_audio is None:
            st.warning("⚠️ Faça o upload de um arquivo de áudio antes de prosseguir.")
        else:
            with st.spinner("✍️ Escrivão Neutro ouvindo e transcrevendo o áudio..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                        temp_file.write(arquivo_audio.read())
                        temp_path = temp_file.name

                    arquivo_gemini = genai.upload_file(temp_path)

                    prompt_escrivao = """
                    Você é um transcritor profissional e isento. 
                    Sua única tarefa é ouvir este áudio extraído de um jogo e escrever EXATAMENTE as palavras que foram ditas.
                    Não assuma intenções, não procure por xingamentos específicos e não adivinhe contexto.
                    Se o áudio estiver ruidoso e você não tiver certeza absoluta de uma palavra, transcreva apenas o que for perfeitamente audível.
                    Escreva apenas a transcrição direta, sem comentários extras.
                    """

                    response_transcricao = model_escrivao.generate_content(
                        [prompt_escrivao, arquivo_gemini],
                        generation_config={"temperature": 0.0}
                    )
                    
                    texto_transcrito = response_transcricao.text
                    
                    # Limpando a memória do servidor
                    genai.delete_file(arquivo_gemini.name)
                    temp_file.close()
                    os.remove(temp_path)

                    # Passo 2: O Julgamento
                    prompt_audio = construir_prompt(df_casos, texto_transcrito, status_assinante_audio, tipo_partida_audio)
                    response_audio = model_zeus.generate_content(
                        prompt_audio,
                        safety_settings=filtros_seguranca,
                        generation_config={"temperature": 0.0}
                    )

                    if not response_audio.candidates or len(response_audio.candidates) == 0:
                        st.warning("⚠️ O bloqueio de segurança mestre do Google foi acionado no julgamento.")
                    else:
                        # Salva o resultado na memória da sessão
                        st.session_state.texto_infrator_audio = texto_transcrito
                        st.session_state.recomendacao_audio = response_audio.text
                        st.session_state.analise_audio_concluida = True

                except Exception as e:
                    st.error("Erro durante o processamento do áudio.")
                    st.code(str(e))

    # Exibe os resultados e a Quarentena de ML se a análise de áudio estiver na memória
    if st.session_state.analise_audio_concluida:
        st.info(f"**Transcrição bruta detectada:**\n\n\"{st.session_state.texto_infrator_audio}\"")
        st.success("✅ Análise de áudio concluída com sucesso!")
        st.markdown("### 📢 Recomendação Final do Zeus:")
        st.write(st.session_state.recomendacao_audio)
        
        st.markdown("---")
        st.markdown("### 🧠 Treinar Zeus (Machine Learning)")
        st.write("Qual foi a punição final aplicada pelo analista? Salve para treinar a IA no futuro.")
        
        punicao_real_audio = st.selectbox(
            "Punição aplicada de fato:", 
            ["Alerta", "Cartão 1", "Cartão 2", "Cartão 3", "Cartão 4", "Cartão 5", "BAN", "Sem Punição"], 
            key="punicao_ml_audio"
        )
        
        col_fb3, col_fb4 = st.columns(2)
        with col_fb3:
            if st.button("💾 Salvar na Quarentena (ML)", key="salvar_audio"):
                salvar_feedback(st.session_state.texto_infrator_audio, punicao_real_audio)
                st.success("✅ Caso de áudio salvo com sucesso no arquivo treinamento.csv!")
        with col_fb4:
            if st.button("🔄 Limpar Tela e Nova Análise", key="reset_audio"):
                st.session_state.analise_audio_concluida = False
                st.rerun()

st.divider()
st.caption(f"📊 Banco carregado: {len(df_casos)} casos.")