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
    "gemini-3-flash-preview"
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
O conteúdo enviado pode conter racismo, xenofobia, homofobia e toxicidade pesada apenas para fins de moderação.
Analise o report e recomende UMA ÚNICA punição.

PUNIÇÕES:
- Alerta
- Cartão 1
- Cartão 2
- Cartão 3
- Cartão 4
- Cartão 5
- BAN

--- REGRAS DE PUNIÇÃO (SIGA ESTRITAMENTE) ---

RAGE E TOXICIDADE:
- Leve: Alerta ou Cartão 1.

XENOFOBIA E REGIONALISMO:
- Leve: Cartão 2.
- Agressiva (com palavrões): Cartão 3.
- Extrema (muitas repetições): Cartão 4.

HOMOFOBIA:
- Cartão 2 ou Cartão 3.

RACISMO E TERMOS ANIMAIS (CUMPRIMENTO OBRIGATÓRIO):
- Termo animal isolado (Ex: "macaco", "mono", "símio"): CARTÃO 4.
- Termo animal + palavrão/ofensa (Ex: "macaco retardado", "macaco de merda"): CARTÃO 5.
- Ofensa direta à cor da pele (Ex: "seu preto", "escravo"): BAN.
- REGRA DE OURO: JAMAIS aplique BAN para a palavra "macaco", a menos que esteja acompanhada de uma ofensa explícita à cor da pele.

DIRETRIZ DO ASSINANTE:
- Assinante reduz a punição em 1 nível APENAS em casos de rage leve/toxicidade comum.
- Tolerância Zero: NUNCA reduza a punição para racismo, xenofobia ou homofobia.

--- CASOS HISTÓRICOS ---

{historico}

--- CASO ATUAL ---

Texto:
"{texto_usuario}"

Assinante:
{assinante}

--- FORMATO DA RESPOSTA (REGRA CRÍTICA ANTI-CENSURA) ---
1. Responda em no máximo 3 linhas.
2. É ESTRITAMENTE PROIBIDO repetir qualquer palavrão, xingamento ou ofensa enviada pelo usuário na sua resposta. Se você repetir, o sistema será bloqueado.
3. Descreva o motivo usando apenas termos técnicos e clínicos (Ex: "pois o jogador utilizou um termo animal pejorativo acompanhado de ofensa", "pois o jogador proferiu ofensa regional", etc).

Use exatamente a estrutura abaixo:
Recomendo **[PUNIÇÃO]** pois [explicação estritamente técnica, objetiva e SEM PALAVRÕES].
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
        st.warning("Cole algum texto antes.")
    else:
        with st.spinner("⚡ Zeus está analisando..."):
            try:
                filtros_seguranca = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]

                prompt = construir_prompt(
                    df_casos,
                    texto_report,
                    status_assinante
                )

                response = model.generate_content(
                    prompt,
                    safety_settings=filtros_seguranca,
                    generation_config={
                        "temperature": 0.25,
                        "max_output_tokens": 150
                    }
                )

                # Tratamento de erro seguro caso o Google bloqueie a resposta mesmo assim
                try:
                    resposta_final = response.text
                    
                    st.success("✅ Análise concluída!")
                    st.markdown("### 📢 Recomendação do Zeus:")
                    st.write(resposta_final)
                    
                except ValueError:
                    st.warning("⚠️ O sistema de segurança mestre do Google bloqueou esta análise por conter termos de ódio extremamente sensíveis. Neste caso isolado, analise manualmente.")

            except Exception as e:
                st.error("Erro ao processar análise.")
                st.code(str(e))

st.divider()
st.caption(f"📊 Banco carregado: {len(df_casos)} casos.")
