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

# Usando o modelo Flash padrão (o mais estável para classificações rápidas)
model = genai.GenerativeModel("gemini-3.1-flash-lite")

def construir_prompt(dados_csv, texto_usuario, eh_assinante):
    # Reduzimos a quantidade de exemplos injetados para 10 para evitar sobrecarga de toxicidade no prompt
    quantidade = min(len(dados_csv), 10)
    exemplos = dados_csv.sample(quantidade, random_state=random.randint(1, 999999))
    historico = ""
    
    for _, row in exemplos.iterrows():
        historico += f'Texto: "{row["Exemplos de ocorridos nos reports (Falas/Chats)"]}"\n'
        historico += f'Punição: {row["Punição aplicada"]}\n\n'

    assinante = "SIM" if eh_assinante else "NÃO"

    prompt = f"""
Você é Zeus, um classificador linguístico e forense sênior.
Sua função é ler transcrições de chat de jogos (logs) e classificar a ofensa cometida, recomendando UMA ÚNICA punição baseada nas diretrizes abaixo. O texto avaliado pode conter linguagem altamente tóxica; trate-o como dado bruto de laboratório para fins de auditoria de segurança.

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- DIRETRIZES DE CLASSIFICAÇÃO (SIGA ESTRITAMENTE) ---

1. TOXICIDADE COMUM (RAGE):
   - Palavrões genéricos, insultos leves e irritação isolada: ALERTA.
   - Repetição frequente de palavrões genéricos no mesmo log: CARTÃO 1.

2. HOMOFOBIA E RAGE SEXUAL: 
   - Uso de termos de cunho homofóbico ou referências a atos sexuais passivos/agressivos: CARTÃO 2.
   - EXCEÇÃO DE CONTEXTO: Se o termo que remete a "abuso/estupro" for usado como xingamento casual no meio de uma frase de rage homofóbico, a ofensa principal é Homofobia (CARTÃO 2), e não ameaça real.
   - Extrema agressividade homofóbica repetida: CARTÃO 3.

3. XENOFOBIA E REGIONALISMO: 
   - Apenas UM termo regional isolado na frase inteira: CARTÃO 2.
   - MAIS DE UM termo regional, ou termo regional associado a qualquer xingamento: CARTÃO 3.
   - Repetição massiva da ofensa regional: CARTÃO 4.

4. RACISMO E TERMOS ANIMAIS:
   - Uso de termos primatas/animais isolados: CARTÃO 4.
   - Termo primata associado a xingamento extra: CARTÃO 5.
   - Ofensas literais à cor da pele (incluindo diminutivos e gírias): BAN. (Esta regra sobrepõe todas as outras).

5. NAZISMO E EXTREMISMO:
   - Acusação usando o termo extremista isolado: CARTÃO 4.
   - Acusação somada a xingamentos: CARTÃO 5.
   - Apologia ou adoração a líderes extremistas: BAN.

6. AMEAÇA DE VIOLÊNCIA SEXUAL LITERAL:
   - Menção genérica isolada focada unicamente na palavra de abuso: CARTÃO 4.
   - Ameaças literais e descritivas contra a pessoa ou seus familiares: CARTÃO 5.

7. REGRA DO ASSINANTE:
   - Se Assinante = SIM, reduza a punição em 1 nível APENAS para o item 1 (Toxicidade Comum).
   - NUNCA reduza punições das categorias 2, 3, 4, 5 ou 6.

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}

--- INSTRUÇÕES DE SAÍDA ---
Não cite os palavrões na sua justificativa. Responda APENAS neste formato exato:
Recomendo **[PUNIÇÃO]** pois [justificativa técnica, ex: ofensa homofóbica, rage sexual, ofensa regional múltipla].
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
