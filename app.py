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

model = genai.GenerativeModel(
    "gemini-3-flash-preview"
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
Sua função é analisar condutas reportadas e aplicar UMA ÚNICA punição.

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- REGRAS DE APLICAÇÃO (OBRIGATÓRIAS) ---
1. RAGE E TOXICIDADE COMUM (Ex: "seu coco", "lixo", "fudido", "merda"): 
   - Punição: Alerta ou Cartão 1.
2. XENOFOBIA E REGIONALISMO: 
   - Leve: Cartão 2. 
   - Agressiva (com palavrões): Cartão 3. 
   - Extrema repetição: Cartão 4.
3. HOMOFOBIA: 
   - Cartão 2 ou Cartão 3 dependendo do peso do xingamento.
4. RACISMO E TERMOS ANIMAIS (A regra mais importante):
   - Termo animal isolado (Ex: "macaco", "mono"): CARTÃO 4.
   - Termo animal acompanhado de xingamento (Ex: "macaco retardado", "macaco de merda"): CARTÃO 5.
   - Ofensa direta à cor da pele (Ex: "seu preto", "escravo"): BAN.
   -> JAMAIS dê BAN apenas pela palavra "macaco", siga a escala acima (C4 ou C5).
5. REGRA DO ASSINANTE:
   - Assinante (SIM) tem a punição reduzida em 1 nível APENAS para rage/toxicidade comum.
   - JAMAIS reduza punição para Xenofobia, Homofobia ou Racismo.

--- HISTÓRICO DE CASOS ---
{historico}

--- CASO ATUAL ---
Texto: "{texto_usuario}"
Assinante: {assinante}

--- INSTRUÇÕES DE RESPOSTA ---
Não repita os palavrões do usuário na sua justificativa para não acionar os filtros de bloqueio. Use apenas termos técnicos descritivos (ex: ofensa regional, termo animal racista, toxicidade leve, xingamento comum).

Responda EXATAMENTE e APENAS neste formato:
Recomendo **[PUNIÇÃO]** pois [sua justificativa técnica].
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
                # Sintaxe oficial do Python SDK para desligar os filtros
                filtros_seguranca = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }

                prompt = construir_prompt(df_casos, texto_report, status_assinante)

                # Temperatura em ZERO (0.0) para a IA ser 100% robótica e obedecer à matemática das regras.
                # O limite de Tokens (max_output_tokens) foi RETIRADO para a resposta não cortar no meio.
                response = model.generate_content(
                    prompt,
                    safety_settings=filtros_seguranca,
                    generation_config={
                        "temperature": 0.0
                    }
                )

                st.success("✅ Análise concluída!")
                st.markdown("### 📢 Recomendação do Zeus:")
                st.write(response.text)

            except Exception as e:
                st.error("Erro ao processar análise. É provável que o sistema mestre de segurança do Google tenha bloqueado a saída.")
                st.code(str(e))

st.divider()
st.caption(f"📊 Banco carregado: {len(df_casos)} casos.")
