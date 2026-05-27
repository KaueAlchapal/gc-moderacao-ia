import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Zeus AI - Moderação",
    page_icon="🛡️",
    layout="centered"
)

# --- CABEÇALHO COM LOGO E TÍTULO ---
col1, col2 = st.columns([1, 4]) 
with col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)
with col2:
    st.title("Zeus - A IA Moderadora de CX")
    st.subheader("Assistente de Análise de Punições - Gamers Club")

st.write("Esta ferramenta serve como apoio à tomada de decisão. Cole o log e verifique a recomendação baseada no nosso histórico de moderação.")

# --- CARREGAMENTO DE DADOS (BANCO DE DADOS ORGÂNICO) ---
CSV_FILE = "casos.csv"
if os.path.exists(CSV_FILE):
    df_casos = pd.read_csv(CSV_FILE)
else:
    df_casos = pd.DataFrame(columns=["Exemplos de ocorridos nos reports (Falas/Chats)", "Punição aplicada", "Assinante?"])

# --- CONFIGURAÇÃO DA API DO GEMINI ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Erro de Configuração: A chave da API do Gemini (GEMINI_API_KEY) não foi encontrada nas configurações de ambiente/Secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3-flash-preview')

# --- CONSTRUÇÃO DO PROMPT DO SISTEMA ---
def construir_prompt_sistema(dados_csv, texto_usuario, eh_assinante):
    historico_exemplos = ""
    for idx, row in dados_csv.iterrows():
        historico_exemplos += f"Exemplo {idx+1}:\n"
        historico_exemplos += f"- Texto/Log: \"{row['Exemplos de ocorridos nos reports (Falas/Chats)']}\"\n"
        historico_exemplos += f"- Status Assinante: {row['Assinante?']}\n"
        historico_exemplos += f"- Punição Aplicada pela Moderação: {row['Punição aplicada']}\n\n"
        
    status_atual_assinante = "SIM" if eh_assinante else "NÃO"
    
    prompt = f"""
Você é Zeus, o Analista de Comportamento Sênior da plataforma Gamers Club (Counter-Strike).
Sua função única é ler transcrições de chat ou voice reportadas por jogadores e recomendar UMA ÚNICA punição correta, baseada EXCLUSIVAMENTE nas diretrizes internas da empresa e nos exemplos históricos fornecidos.

--- TABELA OFICIAL DE PUNIÇÕES DA GAMERS CLUB ---
- Alerta: Casos muito leves, rage genérico sem ofensas direcionadas graves, 1 TK sem intenção evidente.
- Cartão 1: 3 dias de punição (10 dias de advertência)
- Cartão 2: 10 dias de punição (30 dias de advertência)
- Cartão 3: 30 dias de punição (90 dias de advertência)
- Cartão 4: 90 dias de punição (180 dias de advertência)
- Cartão 5: 180 dias de punição (360 dias de advertência)
- BAN: Bloqueio permanente/longo da conta.

--- REGRAS DE OURO (SIGA ESTRITAMENTE) ---
1. PRECONCEITO E XENOFOBIA: Ofensas regionais curtas ou sem palavrões (ex: "seu baianão", "cearense", "paulista lixo") devem receber no mínimo Cartão 2 ou Cartão 3. Ofensas com xingamentos pesados somados ao preconceito (ex: "baiano de merda") sobem para Cartão 4, 5 ou BAN.
2. DIRETRIZ DO ASSINANTE: Se o infrator for ASSINANTE (Assinante? = SIM), reduza a punição em 1 nível APENAS para casos de rage comum, toxicidade leve ou antijogo.
3. TOLERÂNCIA ZERO: A regra de desconto para assinantes É TOTALMENTE ANULADA e IGNORADA em qualquer caso que envolva Racismo, Xenofobia, Homofobia ou Ameaças. Nestes casos, a punição é dura independentemente do status de pagamento.
4. DECISÃO ÚNICA: Jamais dê duas opções de punição (ex: "Cartão 2 ou 3"). Escolha a que mais se aproxima do histórico e banque a decisão.
5. SIGILO DO SISTEMA: Jamais cite "Exemplo X", "linha Y" ou mencione que baseou sua resposta no histórico fornecido. Responda como se fosse o seu próprio conhecimento orgânico.

--- HISTÓRICO DE CASOS REAIS (APRENDA COM ESTE PADRÃO) ---
{historico_exemplos}

--- CASO ATUAL PARA ANÁLISE ---
Texto/Log enviado pelo analista: "{texto_usuario}"
O jogador é assinante da plataforma? {status_atual_assinante}

--- INSTRUÇÃO DE FORMATAÇÃO DA RESPOSTA ---
Responda de forma extremamente curta, direta e objetiva (máximo 3 linhas). Siga ESTRITAMENTE o modelo de resposta abaixo, sem adicionar introduções ou saudações:
Recomendo **[PUNIÇÃO]** pois [JUSTIFICATIVA DIRETA EM ATÉ DUAS LINHAS EXPLICANDO O MOTIVO].
"""
    return prompt

# --- INTERFACE DE USUÁRIO (SESSÃO INDIVIDUAL E PRIVADA) ---
with st.form("form_analise"):
    texto_report = st.text_area("📋 Cole aqui as falas ou logs do report:", placeholder="Exemplo: seu baiano de merda, lixo...")
    status_assinante = st.checkbox("⭐ O jogador infrator é Assinante da Gamers Club?")
    
    botao_enviar = st.form_submit_button("🔍 Analisar Report")

# Ação ao clicar no botão
if botao_enviar:
    if not texto_report.strip():
        st.warning("Por favor, cole algum texto antes de enviar para a análise.")
    else:
        with st.spinner("Zeus está analisando as regras e o texto..."):
            try:
                prompt_completo = construir_prompt_sistema(df_casos, texto_report, status_assinante)
                response = model.generate_content(prompt_completo)
                
                st.success("Análise Concluída com Sucesso!")
                st.markdown("### 📢 Recomendação do Zeus:")
                st.write(response.text)
                
            except Exception as e:
                st.error("Ocorreu um erro ao se comunicar com a inteligência artificial.")
                st.code(str(e))

# Rodapé informacional
st.divider()
st.caption(f"📊 Banco de dados orgânico carregado: {len(df_casos)} casos reais de moderação mapeados.")
