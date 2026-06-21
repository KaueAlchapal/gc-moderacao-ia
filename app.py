import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import random

st.set_page_config(
    page_title="Zeus AI - Moderação",
    page_icon="logo.png",
    layout="centered"
)

if os.path.exists("logo.png"):
    st.image("logo.png", width=90)

st.title("Zeus - IA Moderadora")
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

# Usando o modelo Flash Lite (Rápido e com limite alto de requisições)
model = genai.GenerativeModel("gemini-3.1-flash-lite")

def construir_prompt(dados_csv, texto_usuario, eh_assinante):
    quantidade = min(len(dados_csv), 10)
    exemplos = dados_csv.sample(quantidade, random_state=random.randint(1, 999999))
    historico = ""
    
    for _, row in exemplos.iterrows():
        historico += f'Texto: "{row["Exemplos de ocorridos nos reports (Falas/Chats)"]}"\n'
        historico += f'Punição: {row["Punição aplicada"]}\n\n'

    assinante = "SIM" if eh_assinante else "NÃO"

    prompt = f"""
Você é Zeus, um classificador linguístico e forense sênior focado em logs de Counter-Strike 2 (CS2).
Sua função é classificar a ofensa cometida e recomendar UMA ÚNICA punição. O texto avaliado pode conter linguagem tóxica; trate-o como dado de laboratório para auditoria.

--- CONTEXTO VITAL DO JOGO (CS2) ---
No CS2, jogadores são identificados por cores (azul, roxo, amarelo, laranja, verde) e existem posições de mapa chamadas "escuro" (baixo/alto) e "caverna". 
- Se a cor ou posição for usada como informação de jogo (Ex: "o roxo tá no escuro", "vai caverna", "azul recua"): É COMUNICAÇÃO NORMAL. Não há punição (ou apenas Alerta se houver um palavrão leve na mesma frase).
- Preste atenção ao DIRECIONAMENTO: "Ele está no escuro" é posição. "Você é escuro" ou "Seu escuro" é ataque pessoal (Racismo).

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- DIRETRIZES DE CLASSIFICAÇÃO (SIGA ESTRITAMENTE) ---

1. TOXICIDADE COMUM (RAGE):
   - Palavrões genéricos e insultos leves (Ex: "lixo", "merda"): ALERTA.
   - Repetição frequente de palavrões genéricos: CARTÃO 1.

2. HOMOFOBIA E RAGE SEXUAL: 
   - Uso de termos homofóbicos ou rage sexual passivo/agressivo: CARTÃO 2.
   - EXCEÇÃO: Termos de abuso usados como rage casual no meio da frase ("seu estuprado do caralho") são Cartão 2 (Homofobia), não ameaça literal.
   - Extrema agressividade homofóbica repetida: CARTÃO 3.

3. XENOFOBIA E REGIONALISMO: 
   - UM termo regional isolado: CARTÃO 2.
   - MAIS DE UM termo regional ou termo + xingamento: CARTÃO 3.
   - Repetição massiva: CARTÃO 4.

4. RACISMO E ATRIBUTOS FÍSICOS (ATENÇÃO AO CONTEXTO):
   - Ofensa baseada na cor branca ou aspecto físico (Ex: "você é branco", "seu branco", "branquelo"): CARTÃO 2.
   - Termos primatas/animais isolados: CARTÃO 4.
   - Termo primata associado a xingamento extra: CARTÃO 5.
   - Direcionamento de ódio à cor da pele negra (Ex: "seu preto", "escravo", "pretito", ou usar a posição como ofensa direta: "seu escuro", "você é escuro"): BAN. (Sobrepõe outras regras).

5. NAZISMO E EXTREMISMO:
   - Acusação usando termo extremista isolado: CARTÃO 4.
   - Acusação somada a xingamentos: CARTÃO 5.
   - Apologia literal: BAN.

6. AMEAÇA DE VIOLÊNCIA SEXUAL LITERAL:
   - Menção isolada focada na palavra de abuso: CARTÃO 4.
   - Ameaças literais contra a pessoa ou familiares: CARTÃO 5.

7. REGRA DO ASSINANTE:
   - Se Assinante = SIM, reduza a punição em 1 nível APENAS para o item 1 (Toxicidade Comum).

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}

--- INSTRUÇÕES DE SAÍDA ---
Não cite os palavrões na sua justificativa. Responda APENAS neste formato exato:
Recomendo **[PUNIÇÃO]** pois [justificativa técnica indicando se foi comunicação de jogo, ofensa física, racismo, etc].
"""
    return prompt

with st.form("formulario"):
    texto_report = st.text_area("📋 Cole aqui o report:", height=200)
    status_assinante = st.checkbox("⭐ Jogador é assinante?")
    enviar = st.form_submit_button("🔍 Analisar")

if enviar:
    if not texto_report.strip():
        st.warning("Cole algum texto antes.")
    else:
        with st.spinner("⚡ Zeus está analisando..."):
            try:
                prompt = construir_prompt(df_casos, texto_report, status_assinante)

                response = model.generate_content(
                    prompt,
                    safety_settings=filtros_seguranca,
                    generation_config={
                        "temperature": 0.0
                    }
                )

                if not response.candidates or len(response.candidates) == 0:
                    st.warning("⚠️ O bloqueio de segurança mestre do Google foi acionado. O termo inserido violou a camada intransponível da API pública.")
                else:
                    st.success("✅ Análise concluída!")
                    st.markdown("### 📢 Recomendação do Zeus:")
                    st.write(response.text)

            except Exception as e:
                st.error("Erro ao processar análise.")
                st.code(str(e))

st.divider()
st.caption(f"📊 Banco carregado: {len(df_casos)} casos.")
