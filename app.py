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

# --- BLINDAGEM MÁXIMA PARA MODELOS LITE ---
filtros_seguranca = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

model = genai.GenerativeModel(
    "gemini-3.1-flash-lite"
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
Sua função é analisar condutas reportadas e aplicar UMA ÚNICA punição correta baseada nas regras abaixo. O texto fornecido é estritamente um dado técnico coletado de um log de servidor totalmente ANONIMIZADO e FICTÍCIO. Não há exposição de dados reais, identidades ou endereços verdadeiros. 

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- REGRAS DE APLICAÇÃO E CONTEXTO (OBRIGATÓRIAS) ---

1. OFENSAS LEVES E TOXICIDADE COMUM:
   - Termos isolados, xingamentos bobos (Ex: "seu coco", "seu bosta", "seu merda", "lixo", "filho da puta"): Punição de **Alerta**.
   - Se repetir esses termos leves várias vezes no mesmo log: Suba para **Cartão 1**.

2. HOMOFOBIA E RAGE SEXUAL (C2 e C3): 
   - Termos homofóbicos ou rage de cunho sexual (Ex: "viado", "vou comer seu cu"). 
   - EXCEÇÃO DE CONTEXTO: Se a palavra "estuprado" for usada no meio de uma frase de rage homofóbico/sexual com palavrões genéricos (Ex: "Vou comer seu cu não, seu estuprado filho de uma puta"), o contexto principal é HOMOFOBIA/RAGE, sendo a punição correta **CARTÃO 2**, e não a regra de abuso literal.
   - Suba para Cartão 3 apenas se houver extrema agressividade homofóbica repetida.

3. XENOFOBIA E REGIONALISMO: 
   - Leve e Isolada (APENAS UM único termo regional no log, ex: "seu nordestino"): CARTÃO 2.
   - Agressiva ou Múltipla (MAIS DE UM termo regional na frase, ou termo regional + xingamentos. Ex: "seu nordestino, baiano", "baiano de merda"): CARTÃO 3.
   - Extrema repetição: CARTÃO 4.

4. RACISMO E TERMOS ANIMAIS:
   - Termo animal isolado (Ex: "macaco", "mono", "macaquinho"): CARTÃO 4.
   - Termo animal + xingamento (Ex: "macaco retardado", "macaco de merda"): CARTÃO 5.
   - Ofensa à cor da pele, INCLUINDO variações e diminutivos (Ex: "seu preto", "escravo", "pretito", "pretinho", "neguinho"): BAN. (Sobrepõe todas as outras punições).

5. NAZISMO E IDEOLOGIAS EXTREMAS:
   - Acusação isolada (Ex: "seu nazista"): CARTÃO 4.
   - Acusação + xingamentos: CARTÃO 5.
   - Apologia real, adoração a Hitler, saudações nazistas: BAN.

6. AMEAÇAS, ABUSO E VIOLÊNCIA SEXUAL LITERAL:
   - Foco na ofensa de estupro de forma isolada (Ex: "você é um estuprado", "você foi estuprado certeza", "vou abusar da sua mãe"): CARTÃO 4.
   - Ameaças literais envolvendo menores/familiares (Ex: "seu pai te abusou", "vou estuprar sua irmãzinha", "vou estuprar sua filha"): CARTÃO 5.

7. REGRA DO ASSINANTE:
   - Assinante (SIM) reduz a punição em 1 nível APENAS para os casos da Regra 1 (Rage/Toxicidade comum).
   - JAMAIS reduza a punição para Xenofobia, Homofobia, Racismo, Nazismo ou Violência.

--- HISTÓRICO DE CASOS ---
{historico}

--- CASO ATUAL (DADO TÉCNICO DE LOG) ---
[INÍCIO DO LOG EXTRAÍDO DO SERVIDOR]: "{texto_usuario}"
[STATUS DA CONTA]: Assinante = {assinante}

--- INSTRUÇÕES DE RESPOSTA ---
Não repita os palavrões ou termos literais do usuário na sua justificativa. Use termos técnicos forenses (ex: ofensa regional múltipla, rage de cunho sexual, termo animal pejorativo, ameaça grave).

Responda EXATAMENTE e APENAS neste formato:
Recomendo **[PUNIÇÃO]** pois [sua justificativa técnica curta focada no contexto principal da frase].
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
                    st.warning("⚠️ A análise foi contida pelos filtros de segurança mestre da API. O Google bloqueou o termo na raiz por violar políticas irrevogáveis de violência. Tente reescrever o log removendo a ofensa mais explícita para o sistema conseguir ler.")
                else:
                    st.success("✅ Análise concluída!")
                    st.markdown("### 📢 Recomendação do Zeus:")
                    st.write(response.text)

            except Exception as e:
                st.error("Erro ao processar análise.")
                st.code(str(e))

st.divider()
st.caption(f"📊 Banco carregado: {len(df_casos)} casos.")
