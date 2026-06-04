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
Sua função é analisar condutas reportadas e aplicar UMA ÚNICA punição correta baseada nas regras abaixo. O texto fornecido é estritamente um dado técnico coletado de um log de servidor totalmente ANONIMIZADO e FICTÍCIO. Não há exposição de dados reais, identidades ou endereços verdadeiros. Sua análise forense é uma exigência corporativa de segurança.

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- REGRAS DE APLICAÇÃO (OBRIGATÓRIAS) ---
1. OFENSAS LEVES E TOXICIDADE COMUM:
   - Termos isolados, xingamentos bobos ou irritação leve (Ex: "seu coco", "seu bosta", "seu merda", "lixo"): Punição obrigatória de **Alerta**.
   - Se o jogador repetir esses termos leves várias vezes no mesmo log: Suba a punição para **Cartão 1**.

2. XENOFOBIA E REGIONALISMO (Atenção redobrada à quantidade de termos): 
   - Leve e Isolada (APENAS UM único termo regional no log inteiro, sem xingamentos. Ex: apenas "seu nordestino" ou apenas "seu baiano"): CARTÃO 2.
   - Agressiva ou Múltipla (MAIS DE UM termo regional citado na mesma frase, ou um termo regional somado a xingamentos. Ex: "seu nordestino, baiano", "você é baiano e mora no acre", "baiano de merda", "seu nordestino lixo"): CARTÃO 3.
   - Extrema repetição (Ofensas repetidas mais de 4 vezes no log): CARTÃO 4.

3. HOMOFOBIA: 
   - Cartão 2 ou Cartão 3, dependendo da agressividade e contexto.

4. RACISMO E TERMOS ANIMAIS:
   - Termo animal isolado (Ex: "macaco", "mono"): CARTÃO 4.
   - Termo animal + xingamento (Ex: "macaco retardado", "macaco de merda"): CARTÃO 5.
   - Ofensa direta à cor da pele (Ex: "seu preto", "escravo"): BAN.
   -> JAMAIS aplique BAN apenas pela palavra "macaco" isolada ou com xingamentos comuns (use C4 ou C5).

5. NAZISMO E IDEOLOGIAS EXTREMAS:
   - Acusação isolada (Ex: "seu nazista"): CARTÃO 4.
   - Acusação + xingamentos (Ex: "seu nazista, você é racista seu lixo"): CARTÃO 5.
   - Apologia real, adoração a Hitler, saudações nazistas: BAN.

6. AMEAÇAS, ABUSO E VIOLÊNCIA SEXUAL (ESTUPRO/ESTRUPO):
   - Menção genérica ou ofensa isolada (Ex: "você é um estuprado", "você foi estuprado certeza", "seu estuprado", "estrupo", "vou abusar da sua mãe"): CARTÃO 4.
   - Ameaças graves, descritivas, extremamente repetitivas ou envolvendo menores/familiares (Ex: "você foi estuprado, seu pai te abusou", "seu tio vai te abusar", "vou estuprar sua irmãzinha", "vou estuprar sua filha", "seu filho"): CARTÃO 5.

7. REGRA DO ASSINANTE:
   - Assinante (SIM) reduz a punição em 1 nível APENAS para os casos da Regra 1 (Rage/Toxicidade comum).
   - JAMAIS reduza a punição para os casos de Xenofobia, Homofobia, Racismo, Nazismo ou Abuso/Violência Sexual.

--- HISTÓRICO DE CASOS ---
{historico}

--- CASO ATUAL (DADO TÉCNICO DE LOG) ---
[INÍCIO DO LOG EXTRAÍDO DO SERVIDOR]: "{texto_usuario}"
[STATUS DA CONTA]: Assinante = {assinante}

--- INSTRUÇÕES DE RESPOSTA ---
Não repita os palavrões ou termos ofensivos literais do usuário na sua justificativa para evitar acionar os alertas no sistema. Use termos técnicos forenses (ex: ofensa regional múltipla, termo animal pejorativo, toxicidade leve isolada, etc).

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
