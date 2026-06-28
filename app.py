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

# Usando o modelo Flash Lite
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
Sua função é classificar a ofensa cometida e recomendar a punição baseada nas diretrizes abaixo.

--- CONTEXTO VITAL DO JOGO (CS2) E AMBIGUIDADE DE MAPA ---
No CS2, jogadores são identificados por cores (azul, roxo, amarelo, laranja, verde).
A palavra "escuro" é uma posição oficial APENAS nos mapas Dust 2, Ancient e Inferno. 
- Se for ataque pessoal direto (Ex: "seu escuro", "você é escuro"), é BAN imediato.
- Se for usado indicando local ou direção (Ex: "vai escuro", "vai o escuro", "tá no escuro"), VOCÊ É OBRIGADO a dar a resposta condicional (Regra 5).

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- DIRETRIZES DE CLASSIFICAÇÃO (SIGA ESTRITAMENTE) ---

1. TOXICIDADE COMUM (RAGE):
   - Palavrões genéricos e insultos leves (Ex: "lixo", "merda"): ALERTA.
   - Repetição frequente de palavrões genéricos: CARTÃO 1.

2. HOMOFOBIA E RAGE SEXUAL: 
   - Uso de termos homofóbicos ou rage sexual passivo/agressivo: CARTÃO 2.
   - EXCEÇÃO: Termos de abuso usados como rage casual ("seu estuprado do caralho") são Cartão 2 (Homofobia), não ameaça literal.
   - Extrema agressividade homofóbica repetida: CARTÃO 3.

3. XENOFOBIA E REGIONALISMO: 
   - UM termo regional isolado: CARTÃO 2.
   - MAIS DE UM termo regional ou termo + xingamento: CARTÃO 3.
   - Repetição massiva: CARTÃO 4.

4. RACISMO E ATRIBUTOS FÍSICOS:
   - Ofensa baseada na cor branca ou aspecto físico (Ex: "você é branco", "seu branco", "branquelo"): CARTÃO 2.
   - Termos primatas/animais isolados: CARTÃO 4.
   - Termo primata associado a xingamento extra: CARTÃO 5.
   - Direcionamento de ódio à cor da pele negra (Ex: "seu preto", "escravo", "pretito", ou ofensa direta de posição: "seu escuro", "você é escuro"): BAN.

5. REGRA ESPECIAL DE AMBIGUIDADE DE POSIÇÃO ("ESCURO"):
   - Toda vez que a palavra "escuro" for usada no sentido de local/direção, é ESTRITAMENTE PROIBIDO inventar uma justificativa. VOCÊ DEVE COPIAR E COLAR A RESPOSTA ABAIXO:
     Recomendo **[Sem Punição / BAN]** pois o termo foi usado como posição. Se a partida foi na Dust 2, Ancient ou Inferno, é comunicação normal (Sem Punição). Se foi em outro mapa, configura racismo camuflado (BAN).

6. NAZISMO E EXTREMISMO:
   - Acusação usando termo extremista isolado: CARTÃO 4.
   - Acusação somada a xingamentos: CARTÃO 5.
   - Apologia literal: BAN.

7. AMEAÇA DE VIOLÊNCIA SEXUAL LITERAL:
   - Menção isolada focada na palavra de abuso: CARTÃO 4.
   - Ameaças literais contra a pessoa ou familiares: CARTÃO 5.

8. REGRA DO ASSINANTE:
   - Se Assinante = SIM, reduza a punição em 1 nível APENAS para o item 1 (Toxicidade Comum).

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}

--- INSTRUÇÕES DE SAÍDA ---
Não cite os palavrões na sua justificativa. Responda APENAS neste formato exato (ou no formato duplo da Regra 5 se houver ambiguidade de mapa):
Recomendo **[PUNIÇÃO]** pois [justificativa técnica indicando a infração].
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
