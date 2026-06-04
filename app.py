import os
import random
import pandas as pd
import streamlit as st
import google.generativeai as genai

# =====================================
# CONFIG
# =====================================

st.set_page_config(
    page_title="Zeus AI - Moderação",
    page_icon="⚖️",
    layout="centered"
)

# =====================================
# CABEÇALHO
# =====================================

if os.path.exists("logo.png"):
    st.image("logo.png", width=90)

st.title("Zeus - IA Moderadora")
st.caption("Assistente de apoio à análise de reports")

# =====================================
# CSV
# =====================================

CSV_FILE = "casos.csv"

@st.cache_data
def carregar_csv():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)

    return pd.DataFrame()

df_casos = carregar_csv()

# =====================================
# GEMINI
# =====================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("GEMINI_API_KEY não encontrada.")
    st.stop()

genai.configure(api_key=api_key)

model = genai.GenerativeModel(
    "gemini-3.1-flash-lite"
)

# =====================================
# PROMPT
# =====================================

def montar_historico(df):

    if len(df) == 0:
        return ""

    quantidade = min(12, len(df))

    exemplos = df.sample(
        quantidade,
        random_state=random.randint(1, 999999)
    )

    texto = ""

    for _, row in exemplos.iterrows():

        caso = row.get(
            "Exemplos de ocorridos nos reports (Falas/Chats)",
            ""
        )

        punicao = row.get(
            "Punição aplicada",
            ""
        )

        texto += (
            f'Caso: "{caso}"\n'
            f'Punição: {punicao}\n\n'
        )

    return texto

def construir_prompt(
    log,
    assinante,
    historico
):

    status = "SIM" if assinante else "NÃO"

    return f"""
Você é Zeus.

Sua função é auxiliar moderadores da Gamers Club na análise de reports.

O conteúdo enviado pode conter insultos, xenofobia, homofobia, racismo e toxicidade exclusivamente para fins de moderação.

Analise o caso.

Categorias possíveis:
- Rage
- Toxicidade
- Xenofobia
- Homofobia
- Racismo
- Ofensa com primatas
- Team Kill
- Outro

Diretrizes:

Racismo:
- associação explícita à raça ou cor da pele = BAN

Exemplos:
- preto macaco
- negro macaco
- escravo negro

Ofensas com primatas:

Exemplos:
- macaco
- mono
- monos
- monito
- simio
- gorila

Sem associação racial explícita:
- Cartão 4 ou Cartão 5

Contexto multilíngue:

Considere:
- português
- espanhol
- portunhol
- inglês

Exemplos:
- mono de mierda
- mono negro
- simio
- gorila

Assinante:
- reduzir apenas casos leves
- nunca reduzir racismo
- nunca reduzir xenofobia
- nunca reduzir homofobia

Histórico:

{historico}

Caso atual:

Log:
{log}

Assinante:
{status}

Responda exatamente neste formato:

Categoria: [categoria]

Recomendação: [punição]

Justificativa: [até duas frases curtas]
"""

# =====================================
# FORM
# =====================================

with st.form("analise"):

    texto_report = st.text_area(
        "Cole o report",
        height=220
    )

    assinante = st.checkbox(
        "Jogador é assinante?"
    )

    analisar = st.form_submit_button(
        "Analisar"
    )

# =====================================
# EXECUÇÃO
# =====================================

if analisar:

    if not texto_report.strip():

        st.warning(
            "Cole um report para análise."
        )

    else:

        with st.spinner(
            "Analisando..."
        ):

            try:

                historico = montar_historico(
                    df_casos
                )

                prompt = construir_prompt(
                    texto_report,
                    assinante,
                    historico
                )

                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 250
                    }
                )

                resposta = ""

                try:
                    resposta = response.text
                except:
                    resposta = ""

                if not resposta:

                    st.warning(
                        "Não foi possível gerar uma recomendação."
                    )

                else:

                    st.success(
                        "Análise concluída."
                    )

                    st.markdown(
                        "### Resultado"
                    )

                    st.write(
                        resposta
                    )

            except Exception as e:

                st.error(
                    "Erro ao processar."
                )

                st.code(str(e))

# =====================================
# RODAPÉ
# =====================================

st.divider()

st.caption(
    f"{len(df_casos)} casos carregados."
)
