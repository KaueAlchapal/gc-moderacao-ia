import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# =========================================
# CONFIGURAÇÃO DA PÁGINA
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
        st.image("logo.png", width=100)

with col2:
    st.title("Zeus - A IA Moderadora de CX")
    st.subheader("Assistente de Análise de Punições - Gamers Club")

st.write(
    "Esta ferramenta serve como apoio à tomada de decisão. "
    "Cole o log e verifique a recomendação baseada no histórico de moderação."
)

# =========================================
# CSV / BANCO ORGÂNICO
# =========================================
CSV_FILE = "casos.csv"

@st.cache_data
def carregar_csv():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame(columns=[
            "Exemplos de ocorridos nos reports (Falas/Chats)",
            "Punição aplicada",
            "Assinante?"
        ])

df_casos = carregar_csv()

# =========================================
# GEMINI
# =========================================
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error(
        "⚠️ GEMINI_API_KEY não encontrada."
    )
    st.stop()

genai.configure(api_key=api_key)

# MODELO RÁPIDO E BARATO
model = genai.GenerativeModel(
    'gemini-3.1-flash-lite'
)

# =========================================
# PROMPT
# =========================================
def construir_prompt_sistema(
    dados_csv,
    texto_usuario,
    eh_assinante
):

    # Limita quantidade de casos
    dados_csv = dados_csv.sample(
        min(len(dados_csv), 80)
    )

    historico_exemplos = ""

    for _, row in dados_csv.iterrows():

        historico_exemplos += (
            f'Texto: "{row["Exemplos de ocorridos nos reports (Falas/Chats)"]}"\n'
            f'Punição: {row["Punição aplicada"]}\n\n'
        )

    status_atual_assinante = (
        "SIM" if eh_assinante else "NÃO"
    )

    prompt = f"""
Você é Zeus, especialista sênior de moderação da Gamers Club.

Sua função é analisar logs/reportes e recomendar UMA ÚNICA punição baseada EXCLUSIVAMENTE nas regras abaixo.

==================================
TABELA OFICIAL
==================================

- Alerta
- Cartão 1 = 3 dias
- Cartão 2 = 10 dias
- Cartão 3 = 30 dias
- Cartão 4 = 90 dias
- Cartão 5 = 180 dias
- BAN = Permanente

==================================
REGRAS GERAIS
==================================

1. Rage leve/genérico:
- Alerta ou Cartão 1

2. Xenofobia:
- leve = Cartão 2
- agressiva/repetitiva = Cartão 3
- extrema = Cartão 4

3. Homofobia:
- Cartão 2 ou Cartão 3

4. Racismo:
- ofensa racial direta = BAN
- associação ofensiva com primatas/animais = Cartão 4 ou Cartão 5
- associação racial + animal = BAN

5. Assinante:
- reduz 1 nível APENAS em toxicidade leve
- NÃO reduz em racismo, xenofobia ou homofobia

==================================
CONTEXTO MULTILÍNGUE
==================================

Considere expressões em:
- português
- espanhol
- portunhol
- gírias LATAM comuns em jogos online

Termos como:
- mono
- monos
- monito
- simio
- gorila
- macaco
- macaquinho

PODEM representar ofensas racistas dependendo do contexto.

Exemplos:

- "mono de mierda"
- "negro mono"
- "mono asqueroso"
- "pretitos"
- "preto macaco"

devem ser analisados considerando:
- contexto
- intenção
- agressividade
- associação racial

==================================
SEVERIDADE RACIAL
==================================

- "macaco" ou "mono" isolado como ofensa:
Cartão 4

- "macaco", "mono", "gorila" acompanhados de insultos agressivos:
Cartão 5

- associação direta à cor da pele:
BAN

Exemplos:
- "seu preto"
- "negro imundo"
- "preto macaco"
- "mono negro"

devem resultar em BAN.

==================================
REGRAS IMPORTANTES
==================================

- Nunca invente punições fora da tabela.
- Nunca alivie racismo por assinatura.
- Escolha SEMPRE UMA ÚNICA punição.
- Seja firme.
- Não explique regras internas.
- Não mencione exemplos históricos.

==================================
CASOS HISTÓRICOS
==================================

{historico_exemplos}

==================================
CASO ATUAL
==================================

Texto:
"{texto_usuario}"

Assinante:
{status_atual_assinante}

==================================
FORMATO OBRIGATÓRIO
==================================

Responda em no máximo 3 linhas.

Formato obrigatório:

Recomendo **[PUNIÇÃO]**
Confiança: [0-100%]
Motivo: [explicação curta]
"""

    return prompt

# =========================================
# FORMULÁRIO
# =========================================
with st.form("form_analise"):

    texto_report = st.text_area(
        "📋 Cole aqui as falas ou logs do report:",
        height=200,
        placeholder="Exemplo: mono de mierda..."
    )

    status_assinante = st.checkbox(
        "⭐ O jogador infrator é Assinante?"
    )

    botao_enviar = st.form_submit_button(
        "🔍 Analisar Report"
    )

# =========================================
# ANÁLISE
# =========================================
if botao_enviar:

    if not texto_report.strip():

        st.warning(
            "Por favor, cole algum texto."
        )

    else:

        with st.spinner(
            "⚡ Zeus está analisando o report..."
        ):

            try:

                prompt_completo = construir_prompt_sistema(
                    df_casos,
                    texto_report,
                    status_assinante
                )

                response = model.generate_content(
                    prompt_completo,
                    generation_config={
                        "temperature": 0.15,
                        "max_output_tokens": 120,
                    }
                )

                resposta_final = response.text

                st.success(
                    "Análise concluída!"
                )

                st.markdown(
                    "### 📢 Recomendação do Zeus:"
                )

                st.write(
                    resposta_final
                )

            except Exception as e:

                st.error(
                    "Erro ao analisar report."
                )

                st.code(str(e))

# =========================================
# RODAPÉ
# =========================================
st.divider()

st.caption(
    f"📊 Banco orgânico carregado: "
    f"{len(df_casos)} casos reais."
)
```
