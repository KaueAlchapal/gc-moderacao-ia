import streamlit as st
import pandas as pd
import os
import google.generativeai as genai

# Configuração da página do Streamlit
st.set_page_config(
    page_title="GC Moderator AI - Assistente de Punições",
    page_icon="🎮",
    layout="centered"
)

# Título do Sistema
st.title("🛡️ GC Moderator AI")
st.subheader("Assistente de Análise de Punições - Gamers Club")
st.write("Esta ferramenta serve como apoio à tomada de decisão. Cole o log e verifique a recomendação baseada no nosso histórico de moderação.")

# --- CARREGAMENTO DE DADOS (BANCO DE DADOS ORGÂNICO) ---
# Se o arquivo casos.csv existir, ele lê. Se não, cria um vazio.
CSV_FILE = "casos.csv"
if os.path.exists(CSV_FILE):
    df_casos = pd.read_csv(CSV_FILE)
else:
    df_casos = pd.DataFrame(columns=["Exemplos de ocorridos nos reports (Falas/Chats)", "Punição aplicada", "Assinante?"])

# --- CONFIGURAÇÃO DA API DO GEMINI ---
# Resgata a API KEY guardada no cofre (Secrets) do Streamlit / Hugging Face
# Para testar localmente no seu PC, você pode descomentar a linha abaixo e colar sua chave:
# os.environ["GEMINI_API_KEY"] = "SUA_API_KEY_AQUI"

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Erro de Configuração: A chave da API do Gemini (GEMINI_API_KEY) não foi encontrada nas configurações de ambiente/Secrets.")
    st.info("💡 Se você estiver rodando localmente, configure a variável de ambiente ou descomente a linha de código correspondente no app.py.")
    st.stop()

genai.configure(api_key=api_key)
# Usando o Gemini 1.5 Flash (Gratuito, rápido e ideal para texto longo)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- CONSTRUÇÃO DO PROMPT (MENSAGEM DO SISTEMA) ---
def construir_prompt_sistema(dados_csv, texto_usuario, eh_assinante):
    # Transforma as linhas do CSV em formato de texto estruturado para a IA estudar
    historico_exemplos = ""
    for idx, row in dados_csv.iterrows():
        historico_exemplos += f"Exemplo {idx+1}:\n"
        historico_exemplos += f"- Texto/Log: \"{row['Exemplos de ocorridos nos reports (Falas/Chats)']}\"\n"
        historico_exemplos += f"- Status Assinante: {row['Assinante?']}\n"
        historico_exemplos += f"- Punição Aplicada pela Moderação: {row['Punição aplicada']}\n\n"
        
    status_atual_assinante = "SIM" if eh_assinante else "NÃO"
    
    prompt = f"""
Você é um Analista de Comportamento Sênior da plataforma Gamers Club (Counter-Strike).
Sua função única é ler transcrições de chat ou voice reportadas por jogadores e recomendar a punição correta baseada EXCLUSIVAMENTE nas diretrizes internas da empresa e nos exemplos históricos fornecidos abaixo.

--- TABELA OFICIAL DE PUNIÇÕES DA GAMERS CLUB ---
- Alerta: Casos muito leves, rage genérico sem ofensas direcionadas graves, 1 TK sem intenção evidente.
- Cartão 1: 3 dias de punição (10 dias de advertência)
- Cartão 2: 10 dias de punição (30 dias de advertência)
- Cartão 3: 30 dias de punição (90 dias de advertência)
- Cartão 4: 90 dias de punição (180 dias de advertência)
- Cartão 5: 180 dias de punição (360 dias de advertência)
- BAN: Bloqueio permanente/longo da conta (Casos de Racismo Explícito, Homofobia ou Discriminação severa, ameaças graves de morte/estupro).

--- DIRETRIZ / REGRA DO ASSINANTE ---
Se o infrator for ASSINANTE (Assinante? = SIM), a moderação aplica uma leve tolerância em punições médias ou leves. Nesses casos, reduza a punição recomendada em 1 nível (ex: de Cartão 3 cai para Cartão 2, de Cartão 2 cai para Cartão 1). 
CRÍTICO: Casos de RACISMO EXPLÍCITO, HOMOFOBIA OU XENOFOBIA SEVERA devem ser punidos com BAN ou Cartão 5 de forma estrita, IGNORANDO completamente o status de assinante. Não há desconto para crimes ou preconceitos graves.

--- HISTÓRICO DE CASOS REAIS (APRENDA COM ESTE PADRÃO) ---
{historico_examples}

--- CASO ATUAL PARA ANÁLISE ---
Texto/Log enviado pelo analista: "{texto_usuario}"
O jogador é assinante da plataforma? {status_current_assinante}

--- INSTRUÇÃO DE FORMATAÇÃO DA RESPOSTA ---
Responda de forma extremamente curta, direta e objetiva (máximo 3 linhas). Siga estritamente o modelo de resposta abaixo:
Recomendo **[PUNIÇÃO]** pois [JUSTIFICATIVA DIRETA EM ATÉ DUAS LINHAS EXPLICANDO O MOTIVO].
"""
    return prompt

# --- INTERFACE DE USUÁRIO (SESSÃO INDIVIDUAL E PRIVADA) ---
with st.form("form_analise"):
    texto_report = st.text_area("📋 Cole aqui as falas ou logs do report:", placeholder="Exemplo: seu baiano de merda, lixo...")
    status_assinante = st.checkbox("⭐ O jogador infrator é Assinante da Gamers Club?")
    
    # Botão de envio
    botao_enviar = st.form_submit_button("🔍 Analisar Report")

# Ação ao clicar no botão
if botao_enviar:
    if not texto_report.strip():
        st.warning("Por favor, cole algum texto antes de enviar para a análise.")
    else:
        with st.spinner("O Gemini está analisando o histórico da GC e processando..."):
            try:
                # Monta o prompt completo com a base de dados
                prompt_completo = construir_prompt_sistema(df_casos, texto_report, status_assinante)
                
                # Envia para a API do Gemini
                response = model.generate_content(prompt_completo)
                
                # Exibe o resultado de forma bonita
                st.success("Análise Concluída com Sucesso!")
                st.markdown("### 📢 Recomendação da IA:")
                st.write(response.text)
                
            except Exception as e:
                st.error("Ocorreu um erro ao se comunicar com a inteligência artificial.")
                st.code(str(e))

# Rodapé ou Informação sobre a base de dados atual
st.divider()
st.caption(f"📊 Banco de dados orgânico carregado: {len(df_casos)} casos reais de moderação mapeados.")
