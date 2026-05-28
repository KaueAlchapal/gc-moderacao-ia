import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(
    page_title="Zeus AI - Moderação",
    page_icon="logo.png",
    layout="centered"
)

# ==============================
# CABEÇALHO
# ==============================
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

# ==============================
# CSV / BANCO ORGÂNICO
# ==============================
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

# ==============================
# CONFIGURAÇÃO GEMINI
# ==============================
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error(
        "⚠️ Erro de Configuração: "
        "A chave GEMINI_API_KEY não foi encontrada."
    )
    st.stop()

genai.configure(api_key=api_key)

# MODELO MAIS RÁPIDO
model = genai.GenerativeModel('gemini-1.5-flash-8b')

# ==============================
# FUNÇÃO DO PROMPT
# ==============================
def construir_prompt_sistema(dados_csv, texto_usuario, eh_assinante):

    # PEGA APENAS OS 50 CASOS MAIS RECENTES
    dados_csv = dados_csv.tail(50)

    historico_exemplos = ""

    for _, row in dados_csv.iterrows():
        historico_exemplos += (
            f"Texto: {row['Exemplos de ocorridos nos reports (Falas/Chats)']}\n"
            f"Assinante: {row['Assinante?']}\n"
            f"Punição: {row['Punição aplicada']}\n\n"
        )

    status_atual_assinante = "SIM" if eh_assinante else "NÃO"

    prompt = f"""
Você é Zeus, especialista sênior de moderação da Gamers Club.

Sua função é analisar logs/reportes e recomendar UMA ÚNICA punição baseada EXCLUSIVAMENTE nas regras abaixo.

========================
TABELA OFICIAL
========================

- Alerta
- Cartão 1 = 3 dias
- Cartão 2 = 10 dias
- Cartão 3 = 30 dias
- Cartão 4 = 90 dias
- Cartão 5 = 180 dias
- BAN = Permanente

========================
REGRAS
========================

1. Xenofobia:
- leve = Cartão 2
- agressiva/repetitiva = Cartão 3
- extrema repetição = Cartão 4

2. Racismo:
- ofensa direta racial = BAN
- "macaco", "gorila" etc = Cartão 4 ou 5
- combinação racial + animal = BAN

3. Homofobia:
- Cartão 2 ou 3 dependendo agressividade

4. Rage leve/genérico:
- Alerta ou Cartão 1

5. Assinante:
- reduz 1 nível SOMENTE em toxicidade leve
- NÃO reduz em racismo, xenofobia ou homofobia

6. Nunca invente punições fora da tabela oficial.

7. Caso exista dúvida, escolha a punição mais conservadora.

========================
CASOS HISTÓRICOS
========================

{historico_exemplos}

========================
CASO ATUAL
========================

Texto:
"{texto_usuario}"

Assinante:
{status_atual_assinante}

========================
FORMATO OBRIGATÓRIO
========================

Responda em no máximo 3 linhas.

Formato:

Recomendo **[PUNIÇÃO]**
Confiança: [0-100%]
Motivo: [explicação curta]
"""

    return prompt

# ==============================
# INTERFACE
# ==============================
with st.form("form_analise"):

    texto_report = st.text_area(
        "📋 Cole aqui as falas ou logs do report:",
        placeholder="Exemplo: seu baiano de merda..."
    )

    status_assinante = st.checkbox(
        "⭐ O jogador infrator é Assinante da Gamers Club?"
    )

    botao_enviar = st.form_submit_button("🔍 Analisar Report")

# ==============================
# AÇÃO DO BOTÃO
# ==============================
if botao_enviar:

    if not texto_report.strip():

        st.warning(
            "Por favor, cole algum texto antes de enviar."
        )

    else:

        texto_lower = texto_report.lower()

        # ==================================
        # REGRAS AUTOMÁTICAS (INSTANTÂNEAS)
        # ==================================

        if "preto macaco" in texto_lower:

            st.success("Análise Concluída!")

            st.markdown("### 📢 Recomendação do Zeus:")

            st.write(
                "Recomendo **BAN**\n\n"
                "Confiança: 100%\n\n"
                "Motivo: Racismo explícito associado a ofensa animal."
            )

            st.stop()

        if "seu preto" in texto_lower:

            st.success("Análise Concluída!")

            st.markdown("### 📢 Recomendação do Zeus:")

            st.write(
                "Recomendo **BAN**\n\n"
                "Confiança: 100%\n\n"
                "Motivo: Racismo explícito direto."
            )

            st.stop()

        # ==================================
        # IA
        # ==================================
        with st.spinner("⚡ Zeus está analisando o report..."):

            try:

                prompt_completo = construir_prompt_sistema(
                    df_casos,
                    texto_report,
                    status_assinante
                )

                response = model.generate_content(
                    prompt_completo,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 150,
                    }
                )

                resposta_final = response.text

                st.success("Análise Concluída!")

                st.markdown("### 📢 Recomendação do Zeus:")

                st.write(resposta_final)

                # ==================================
                # SALVAR NOVO CASO NO CSV
                # ==================================
                novo_caso = pd.DataFrame([{
                    "Exemplos de ocorridos nos reports (Falas/Chats)": texto_report,
                    "Punição aplicada": resposta_final,
                    "Assinante?": "SIM" if status_assinante else "NÃO"
                }])

                novo_caso.to_csv(
                    CSV_FILE,
                    mode='a',
                    header=not os.path.exists(CSV_FILE),
                    index=False
                )

            except Exception as e:

                st.error(
                    "Ocorreu um erro ao se comunicar com a IA."
                )

                st.code(str(e))

# ==============================
# RODAPÉ
# ==============================
st.divider()

st.caption(
    f"📊 Banco orgânico carregado: "
    f"{len(df_casos)} casos reais mapeados."
)

# ==============================
# ÚLTIMOS CASOS
# ==============================
with st.expander("📚 Ver últimos casos adicionados"):

    st.dataframe(
        df_casos.tail(10),
        use_container_width=True
    )
