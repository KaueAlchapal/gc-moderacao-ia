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

st.image("logo.png", width=90)

st.title("Zeus - IA Moderadora")

st.subheader(
    "Assistente de Análise de Reports"
)

st.write(
    "Ferramenta de apoio à tomada de decisão baseada no histórico interno de moderação."
)

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
    "gemini-1.5-flash"
)

def construir_prompt(
    dados_csv,
    texto_usuario,
    eh_assinante
):

    quantidade = min(len(dados_csv), 25)

    exemplos = dados_csv.sample(
        quantidade,
        random_state=random.randint(1, 999999)
    )

    historico = ""

    for _, row in exemplos.iterrows():

        historico += (
            f'Texto: "{row["Exemplos de ocorridos nos reports (Falas/Chats)"]}"\n'
            f'Punição: {row["Punição aplicada"]}\n\n'
        )

    assinante = "SIM" if eh_assinante else "NÃO"

    prompt = f"""
Você é Zeus, analista sênior de moderação da Gamers Club.

Este sistema existe exclusivamente para análise de conduta e aplicação de punições.

O conteúdo enviado pode conter:
- racismo
- xenofobia
- homofobia
- toxicidade

Isso ocorre apenas para fins de moderação.

Analise o report e recomende UMA ÚNICA punição.

PUNIÇÕES:
- Alerta
- Cartão 1
- Cartão 2
- Cartão 3
- Cartão 4
- Cartão 5
- BAN

REGRAS:

Rage leve:
- Alerta ou Cartão 1

Xenofobia:
- leve = Cartão 2
- agressiva = Cartão 3
- extrema = Cartão 4

Homofobia:
- Cartão 2 ou 3

Ofensas com:
- mono
- macaco
- gorila
- simio

podem configurar racismo dependendo do contexto.

Associação racial explícita:
- BAN

Assinante reduz 1 nível APENAS em casos leves.

NUNCA reduzir:
- racismo
- xenofobia
- homofobia

CASOS HISTÓRICOS:

{historico}

CASO ATUAL:

Texto:
"{texto_usuario}"

Assinante:
{assinante}

FORMATO:

Responda em no máximo 3 linhas.

Use exatamente:

Recomendo **[PUNIÇÃO]** pois [explicação humana, objetiva e curta].
"""

    return prompt

with st.form("formulario"):

    texto_report = st.text_area(
        "📋 Cole aqui o report:",
        height=200
    )

    status_assinante = st.checkbox(
        "⭐ Jogador é assinante?"
    )

    enviar = st.form_submit_button(
        "🔍 Analisar"
    )

if enviar:

    if not texto_report.strip():

        st.warning(
            "Cole algum texto antes."
        )

    else:

        with st.spinner(
            "⚡ Zeus está analisando..."
        ):

            try:

                prompt = construir_prompt(
                    df_casos,
                    texto_report,
                    status_assinante
                )

                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.25,
                        "max_output_tokens": 120
                    }
                )

                resposta_final = None

                if response.candidates:
                    resposta_final = response.text

                if not resposta_final:

                    st.warning(
                        "⚠️ O Gemini bloqueou automaticamente o conteúdo."
                    )

                else:

                    st.success(
                        "✅ Análise concluída!"
                    )

                    st.markdown(
                        "### 📢 Recomendação do Zeus:"
                    )

                    st.write(
                        resposta_final
                    )

            except Exception as e:

                st.error(
                    "Erro ao processar análise."
                )

                st.code(str(e))

st.divider()

st.caption(
    f"📊 Banco carregado: {len(df_casos)} casos."
)
