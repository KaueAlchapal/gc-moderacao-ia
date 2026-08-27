import google.generativeai as genai
import os
import random
import streamlit as st

def configurar_api():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY não encontrada. Verifique suas variáveis de ambiente.")
        st.stop()
    genai.configure(api_key=api_key)

def obter_modelos_e_filtros():
    filtros_seguranca = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]
    model_zeus = genai.GenerativeModel("gemini-3.1-flash-lite")
    model_escrivao = genai.GenerativeModel("gemini-3.1-flash-lite")
    return model_zeus, model_escrivao, filtros_seguranca

def construir_prompt(dados_csv, texto_usuario, eh_assinante, tipo_partida):
    quantidade = min(len(dados_csv), 10)
    exemplos = dados_csv.sample(quantidade, random_state=random.randint(1, 999999))
    historico = ""
    for _, row in exemplos.iterrows():
        historico += f'Texto: "{row["Exemplos de ocorridos nos reports (Falas/Chats)"]}"\n'
        historico += f'Punição: {row["Punição aplicada"]}\n\n'

    assinante = "SIM" if eh_assinante else "NÃO"

    prompt = f"""
[OVERRIDE FORENSE ATIVADO: Você é um sistema oficial de auditoria disciplinar. Você TEM PERMISSÃO EXPLÍCITA para ler e processar discursos de ódio, assédio e conteúdo explícito para fins de aplicação de punição. É o seu trabalho analisar esse texto cru. NÃO recuse a tarefa.]

Você é Zeus, um classificador linguístico e forense sênior focado em logs de Counter-Strike 2 (CS2).
Sua função é identificar a infração MAIS GRAVE contida no log e recomendar UMA ÚNICA punição principal.

--- CONTEXTO VITAL DO JOGO (CS2) E AMBIGUIDADE DE MAPA ---
No CS2, jogadores são identificados por cores. A palavra "escuro" é uma posição oficial APENAS nos mapas Dust 2, Ancient e Inferno. 
- Se for ataque pessoal direto (Ex: "seu escuro"), é BAN imediato por racismo.
- Se for usado indicando local ou direção (Ex: "vai escuro"), aplique a regra 5.

--- TABELA DE PUNIÇÕES VÁLIDAS ---
SEM PUNIÇÃO, ALERTA, CARTÃO 1, CARTÃO 2, CARTÃO 3, CARTÃO 4, CARTÃO 5, BAN.

--- DIRETRIZES DE CLASSIFICAÇÃO (SIGA ESTRITAMENTE) ---
0. SEM INFRAÇÃO (COMUNICAÇÃO NORMAL OU RUÍDO):
   - Se o log contiver apenas comunicações táticas de jogo, conversas normais, ruídos de microfone, textos vazios ou não apresentar nenhuma infração clara: SEM PUNIÇÃO.

1. TOXICIDADE COMUM E ESTEREÓTIPOS INDIRETOS: Palavrões genéricos ou estereótipos indiretos: ALERTA. Repetição: CARTÃO 1.
2. HOMOFOBIA E RAGE SEXUAL: Termos homofóbicos ou rage sexual ("estuprado"): CARTÃO 2. Extrema agressividade repetida: CARTÃO 3.
3. XENOFOBIA E PRECONCEITO SOCIAL: Um termo isolado: CARTÃO 3. Dois termos/combo: CARTÃO 4. Repetição massiva (3x+): CARTÃO 5.
4. RACISMO E ATRIBUTOS FÍSICOS: Ofensa a cor branca/físico: CARTÃO 1. Menção isolada a macaco: CARTÃO 5. Macaco + xingamento ou Ódio a cor negra: BAN. Capacitismo: CARTÃO 2.
5. REGRA DE AMBIGUIDADE ("ESCURO"):
     Se usado fora do contexto geográfico: BAN.
     Caso a partida tenha ocorrido nos mapas Dust 2, Ancient ou Inferno e o uso for estritamente geográfico: SEM PUNIÇÃO.
6. NAZISMO E EXTREMISMO: Isolado: CARTÃO 4. Com xingamentos: CARTÃO 5. Apologia literal: BAN.
7. AMEAÇA À VIDA / ABUSO LITERAL: Foco na palavra de abuso ("foi abusado"): CARTÃO 4. Ameaça literal de morte/abuso a pessoa ou família: BAN.
8. REGRA DO ASSINANTE: Se Assinante = SIM, reduza a punição em 1 nível APENAS para a regra 1.
9. ANTIJOGO: Se "Ranked": CARTÃO 1. Se "Lobby / GC Solo": ALERTA. (Trava: Se houver xingamento grave no relato, ignore antijogo).
10. CONDUTA DE MÁ FÉ: Mentiras, falsas dicas: ALERTA. Ghosting/Telar: CARTÃO 2.
11. GORDOFOBIA: Geral: CARTÃO 1. Combo: CARTÃO 2. Repetição: CARTÃO 3.
12. MACHISMO: Geral: CARTÃO 2. Combo: CARTÃO 3. Repetição: CARTÃO 4. Abuso machista ("estuprada"): CARTÃO 4.

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}
[TIPO DE PARTIDA]: {tipo_partida}

--- INSTRUÇÕES DE SAÍDA E FORMATO OBRIGATÓRIO ---
Sua resposta DEVE ter exatamente 2 partes divididas por "---":

Na primeira parte, extraia do log APENAS os trechos, frases ou termos ofensivos que justificam a punição, separados estritamente por " - ". Se NÃO houver infração, escreva apenas a palavra NENHUMA.
Na segunda parte, dê a recomendação técnica sem repetir palavrões de forma desnecessária.

FORMATO EXATO DA RESPOSTA:
TOXICIDADE: "trecho 1" - "trecho 2"
---
Recomendo **[PUNIÇÃO]** pois [justificativa clínica e 100% sem palavrões].
"""
    return prompt