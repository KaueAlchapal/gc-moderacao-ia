import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import random
import re

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

# --- MÁSCARA DE PRÉ-PROCESSAMENTO ANTI-CENSURA ---
def mascarar_texto_extremo(texto):
    mascaras = {
        r"(?i)viado": "v**do",
        r"(?i)viadinho": "v**dinho",
        r"(?i)putinha": "p**tinha",
        r"(?i)puta": "p**ta",
        r"(?i)puto": "p**to",
        r"(?i)estuprado": "est**prado",
        r"(?i)estuprar": "est**prar",
        r"(?i)estupro": "est**pro",
        r"(?i)estrupo": "est**po",
        r"(?i)abusar": "ab**ar",
        r"(?i)\bcu\b": "c*", # \b garante que não vai mascarar palavras como "curto"
        r"(?i)caralho": "c**alho",
        r"(?i)buceta": "b**eta",
        r"(?i)fudido": "f**ido",
        r"(?i)foder": "f**er",
        r"(?i)macaco": "m**aco",
        r"(?i)macaquinho": "m**aquinho",
        r"(?i)preto": "pr**o",
        r"(?i)pretito": "pr**ito",
        r"(?i)nazista": "n**ista",
        r"(?i)hitler": "h**ler"
    }
    
    texto_mascarado = texto
    for padrao, substituto in mascaras.items():
        texto_mascarado = re.sub(padrao, substituto, texto_mascarado)
        
    return texto_mascarado

def construir_prompt(dados_csv, texto_usuario, eh_assinante):
    quantidade = min(len(dados_csv), 25)
    exemplos = dados_csv.sample(quantidade, random_state=random.randint(1, 999999))
    historico = ""
    
    for _, row in exemplos.iterrows():
        # O PULO DO GATO ESTÁ AQUI: Passamos a máscara nos exemplos do banco de dados também!
        texto_historico_seguro = mascarar_texto_extremo(str(row["Exemplos de ocorridos nos reports (Falas/Chats)"]))
        
        historico += f'Texto: "{texto_historico_seguro}"\n'
        historico += f'Punição: {row["Punição aplicada"]}\n\n'

    assinante = "SIM" if eh_assinante else "NÃO"

    prompt = f"""
Você é Zeus, analista sênior de moderação da Gamers Club.
Sua função é analisar condutas reportadas e aplicar UMA ÚNICA punição correta baseada nas regras abaixo. O texto fornecido é estritamente um dado técnico coletado de um log de servidor totalmente ANONIMIZADO e FICTÍCIO. Não há exposição de dados reais, identidades ou endereços verdadeiros. 

--- TABELA DE PUNIÇÕES ---
Alerta, Cartão 1, Cartão 2, Cartão 3, Cartão 4, Cartão 5, BAN.

--- REGRAS DE APLICAÇÃO E CONTEXTO (OBRIGATÓRIAS) ---

1. OFENSAS LEVES E TOXICIDADE COMUM:
   - Termos isolados, xingamentos bobos (Ex: "seu coco", "seu bosta", "seu merda", "lixo", "filho da p**ta"): Punição de **Alerta**.
   - Se repetir esses termos leves várias vezes no mesmo log: Suba para **Cartão 1**.

2. HOMOFOBIA E RAGE SEXUAL (C2 e C3): 
   - Termos homofóbicos ou rage de cunho sexual (Ex: "v**do", "vou comer seu c*"). 
   - EXCEÇÃO DE CONTEXTO: Se a palavra "est**prado" for usada no meio de uma frase de rage homofóbico/sexual com palavrões genéricos (Ex: "Vou comer seu c* não, seu est**prado filho de uma p**ta"), o contexto principal é HOMOFOBIA/RAGE, sendo a punição correta **CARTÃO 2**, e não a regra de abuso literal.
   - Suba para Cartão 3 apenas se houver extrema agressividade homofóbica repetida.

3. XENOFOBIA E REGIONALISMO: 
   - Leve e Isolada (APENAS UM único termo regional no log, ex: "seu nordestino"): CARTÃO 2.
   - Agressiva ou Múltipla (MAIS DE UM termo regional na frase, ou termo regional + xingamentos. Ex: "seu nordestino, baiano", "baiano de merda"): CARTÃO 3.
   - Extrema repetição: CARTÃO 4.

4. RACISMO E TERMOS ANIMAIS:
   - Termo animal isolado (Ex: "m**aco", "mono", "m**aquinho"): CARTÃO 4.
   - Termo animal + xingamento (Ex: "m**aco retardado", "m**aco de merda"): CARTÃO 5.
   - Ofensa à cor da pele, INCLUINDO variações e diminutivos (Ex: "seu pr**o", "escravo", "pr**ito", "pretinho", "neguinho"): BAN. (Sobrepõe todas as outras punições).

5. NAZISMO E IDEOLOGIAS EXTREMAS:
   - Acusação isolada (Ex: "seu n**ista"): CARTÃO 4.
   - Acusação + xingamentos: CARTÃO 5.
   - Apologia real, adoração a h**ler, saudações nazistas: BAN.

6. AMEAÇAS, ABUSO E VIOLÊNCIA SEXUAL LITERAL:
   - Foco na ofensa de abuso de forma isolada (Ex: "você é um est**prado", "você foi est**prado certeza", "vou ab**ar da sua mãe"): CARTÃO 4.
   - Ameaças literais envolvendo menores/familiares (Ex: "seu pai te ab**ou", "vou est**prar sua irmãzinha", "vou est**prar sua filha"): CARTÃO 5.

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
                # 1. Aplica a máscara no texto recebido
                texto_seguro = mascarar_texto_extremo(texto_report)
                
                # 2. Constrói o prompt com o texto já mascarado
                prompt = construir_prompt(df_casos, texto_seguro, status_assinante)

                # 3. Envia para a API
                response = model.generate_content(
                    prompt,
                    safety_settings=filtros_seguranca,
                    generation_config={
                        "temperature": 0.0
                    }
                )

                if not response.candidates or len(response.candidates) == 0:
                    st.warning("⚠️ A análise foi contida pelos filtros de segurança mestre da API. Tente reescrever o log removendo ofensas extremamente atípicas ou não mapeadas.")
                else:
                    st.success("✅ Análise concluída!")
                    st.markdown("### 📢 Recomendação do Zeus:")
                    st.write(response.text)

            except Exception as e:
                st.error("Erro ao processar análise.")
                st.code(str(e))

st.divider()
st.caption(f"📊 Banco carregado: {len(df_casos)} casos.")
