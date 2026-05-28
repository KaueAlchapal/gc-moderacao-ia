import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
import random

# =========================================

# CONFIG DA PÁGINA

# =========================================

st.set_page_config(
page_title="Zeus AI - Moderação",
page_icon="logo.png",
layout="centered"
)

# =========================================

# CABEÇALHO

# =========================================

col1, col2 = st.columns([1, 4])

with col1:
if os.path.exists("logo.png"):
st.image("logo.png", width=90)

with col2:
st.title("Zeus - IA Moderadora")
st.subheader("Assistente de Análise de Reports")

st.write(
"Ferramenta de apoio à tomada de decisão "
"baseada no histórico interno de moderação."
)

# =========================================

# CSV

# =========================================

CSV_FILE = "casos.csv"

@st.cache_data
def carregar_csv():

```
if os.path.exists(CSV_FILE):
    return pd.read_csv(CSV_FILE)

return pd.DataFrame(columns=[
    "Exemplos de ocorridos nos reports (Falas/Chats)",
    "Punição aplicada",
    "Assinante?"
])
```

df_casos = carregar_csv()

# =========================================

# GEMINI

# =========================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
st.error("⚠️ GEMINI_API_KEY não encontrada.")
st.stop()

genai.configure(api_key=api_key)

# MODELO RÁPIDO

model = genai.GenerativeModel(
"gemini-3.1-flash-lite"
)

# =========================================

# PROMPT

# =========================================

def construir_prompt(
dados_csv,
texto_usuario,
eh_assinante
):

```
# mistura diversidade
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
```

Você é Zeus, analista sênior de moderação da Gamers Club.

Analise o log/report e recomende UMA ÚNICA punição.

========================
PUNIÇÕES
========

* Alerta
* Cartão 1
* Cartão 2
* Cartão 3
* Cartão 4
* Cartão 5
* BAN

========================
REGRAS
======

Rage leve:

* Alerta ou Cartão 1

Xenofobia:

* leve = Cartão 2
* agressiva = Cartão 3
* extrema/repetitiva = Cartão 4

Homofobia:

* Cartão 2 ou 3

Ofensas envolvendo primatas/animais:

* Cartão 4 ou 5

Associação racial explícita:

* BAN

========================
CONTEXTO MULTILÍNGUE
====================

Considere:

* português
* espanhol
* portunhol
* gírias LATAM

Termos como:

* mono
* monos
* monito
* simio
* gorila
* macaco

PODEM representar ofensa racial dependendo do contexto.

Exemplos:

* "mono de mierda"
* "mono negro"
* "preto macaco"
* "negro imundo"

são graves.

========================
ASSINANTE
=========

Assinante reduz 1 nível SOMENTE em toxicidade leve.

NUNCA reduzir:

* racismo
* xenofobia
* homofobia

========================
CASOS HISTÓRICOS
================

{historico}

========================
CASO ATUAL
==========

Texto:
"{texto_usuario}"

Assinante:
{assinante}

========================
FORMATO
=======

Responda em até 3 linhas:

Recomendo **[PUNIÇÃO]**
Confiança: [0-100%]
Motivo: [curto]
"""

```
return prompt
```

# =========================================

# FORMULÁRIO

# =========================================

with st.form("formulario"):

```
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
```

# =========================================

# ANÁLISE

# =========================================

if enviar:

```
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
                    "temperature": 0.1,
                    "max_output_tokens": 120,
                }
            )

            # =====================================
            # TRATAMENTO DE BLOQUEIO
            # =====================================

            resposta_final = None

            try:
                resposta_final = response.text
            except:
                resposta_final = None

            # se Gemini bloquear
            if not resposta_final:

                st.warning(
                    "⚠️ O modelo bloqueou automaticamente "
                    "o conteúdo por segurança. "
                    "Reveja manualmente o caso."
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
```

# =========================================

# RODAPÉ

# =========================================

st.divider()

st.caption(
f"📊 Banco carregado: {len(df_casos)} casos."
)
