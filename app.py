import streamlit as st
import pandas as pd
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
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

# --- BLINDAGEM CONTRA CENSURA (Zera os filtros na entrada e na saída da API) ---
filtros_seguranca = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# O modelo recebe os filtros aqui para nunca mais dar o erro de "blocked prompt"
model = genai.GenerativeModel(
    "gemini-3.1-flash-lite",
    safety_settings=filtros_seguranca
)

def construir_prompt(dados_csv, texto_usuario, eh_assinante):
    quantidade = min(len(dados_csv), 25)
    exemplos = dados_csv.sample(quantidade, random_state=random.randint(1, 999999))
    historico = ""
    
    for _, row in exemplos.iterrows():
        historico += f'Texto: "{row["Exemplos de ocorridos nos reports (Falas/Chats)"]}"\n'
        historico += f'Punição: {row["Punição aplicada"]}\n\n'

    assinante = "SIM" if eh_assinante else "NÃO"

    prompt = f"""
Você é Zeus, analista sênior de moderação da Gamers Club.
Sua função é analisar condutas reportadas e aplicar UMA ÚNICA punição correta baseada nas regras abaixo.

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- REGRAS DE APLICAÇÃO (OBRIGATÓRIAS) ---
1. OFENSAS LEVES E TOXICIDADE COMUM:
   - Termos isolados, xingamentos bobos ou irritação leve (Ex: "seu coco", "seu bosta", "seu merda", "seu verme imundo", "seu imundo", "lixo"): A punição deve ser obrigatoriamente **Alerta**.
   - Se o jogador repetir esses termos de toxicidade comum várias vezes no mesmo log (uma sequência de xingamentos leves ou reclamações agressivas repetidas): Suba a punição para **Cartão 1**.

2. XENOFOBIA E REGIONALISMO: 
   - Leve e Isolada (Ofensa com o termo regional sozinho, curto e sem xingamentos agressivos. Ex: "seu nordestino", "seu baiano", "baiano"): CARTÃO 2.
   - Agressiva ou Repetitiva (Termo regional acompanhado de xingamentos ou repetido. Ex: "baiano de merda", "seu nordestino lixo", "seu nordestino, baiano de merda"): CARTÃO 3.
   - Extrema repetição (Ofensas à região repetidas mais de 4 vezes no mesmo log): CARTÃO 4.

3. HOMOFOBIA: 
   - Cartão 2 ou Cartão 3, dependendo da agressividade e contexto.

4. RACISMO E TERMOS ANIMAIS:
   - Termo animal isolado (Ex: "macaco", "mono"): CARTÃO 4.
   - Termo animal acompanhado de xingamento (Ex: "macaco retardado", "macaco de merda"): CARTÃO 5.
   - Ofensa direta à cor da pele (Ex: "seu preto", "escravo"): BAN.
   -> JAMAIS aplique BAN apenas pela palavra "macaco" isolada ou com xingamentos comuns, siga estritamente a escala (C4 ou C5).

5. NAZISMO E IDEOLOGIAS EXTREMAS:
   - Acusação ou ofensa isolada usando o termo (Ex: "seu nazista"): CARTÃO 4.
   - Ofensa usando o termo somada a outros xingamentos pesados e agressivos (Ex: "seu nazista, você é racista seu lixo seu merda"): CARTÃO 5.
   - Apologia real, adoração a Adolf Hitler, saudações nazistas ou propagação ativa da ideologia: BAN.

6. REGRA DO ASSINANTE:
   - Assinante (SIM) reduz a punição em 1 nível APENAS para os casos da Regra 1 (Rage/Toxicidade comum). Se a punição original calculada era Cartão 1, vira Alerta. Se era Alerta, permanece Alerta.
   - JAMAIS reduza a punição para os casos de Xenofobia, Homofobia, Racismo ou Nazismo.

--- HISTÓRICO DE CASOS ---
{historico}

--- CASO ATUAL ---
Texto: "{texto_usuario}"
Assinante: {assinante}

--- INSTRUÇÕES DE RESPOSTA ---
Não repita os palavrões ou termos ofensivos literais do usuário na sua justificativa para evitar alertas no sistema. Use termos técnicos e formais (ex: apologia ideológica extrema, acusação ideológica isolada, ofensa regional somada a xingamento, ofensa regional isolada, etc).

Responda EXATAMENTE e APENAS neste formato:
Recomendo **[PUNIÇÃO]** pois [sua justificativa técnica curta].
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
                    generation_config={
                        "temperature": 0.0
                    }
                )

                if not response.candidates or len(response.candidates) == 0:
                    st.warning("⚠️ A análise foi contida pelos filtros de segurança da API. Tente reescrever o caso removendo palavras excessivamente pesadas.")
                else:
                    st.success("✅ Análise concluída!")
                    st.markdown("### 📢 Recomendação do Zeus:")
                    st.write(response.text)

            except Exception as e:
                st.error("Erro ao processar análise.")
                st.code(str(e))

st.divider()
st.caption(f"📊 Banco carregado: {len(df_casos)} casos.")
