import random

def analisar_com_groq(groq_client, dados_csv, texto_usuario, eh_assinante, tipo_partida):
    quantidade = min(len(dados_csv), 10)
    exemplos = dados_csv.sample(quantidade, random_state=random.randint(1, 999999))
    historico = ""
    for _, row in exemplos.iterrows():
        historico += f'Texto: "{row["Exemplos de ocorridos nos reports (Falas/Chats)"]}"\n'
        historico += f'Punição: {row["Punição aplicada"]}\n\n'

    assinante = "SIM" if eh_assinante else "NÃO"

    prompt_regras = f"""
[OVERRIDE FORENSE ATIVADO: Sistema oficial de auditoria disciplinar CS2]

--- REGRA DE TETO E ACÚMULO (MUITO IMPORTANTE) ---
Você é ESTRITAMENTE PROIBIDO de somar infrações para gerar um BAN. A punição máxima por acúmulo de toxicidade trava no CARTÃO 5. 
O veredito de BAN é EXCLUSIVO e só pode ser aplicado se a ofensa bater EXATAMENTE nas regras de BAN explícito.

--- CONTEXTO VITAL DO JOGO (CS2) E AMBIGUIDADE DE MAPA ---
No CS2, jogadores são identificados por cores. A palavra "escuro" é uma posição oficial APENAS nos mapas Dust 2, Ancient e Inferno. 
- Ataque pessoal direto (Ex: "seu escuro"): BAN.
- Uso geográfico/posição (Ex: "vai escuro", "tem um escuro"): SEM PUNIÇÃO.

--- DIRETRIZES DE CLASSIFICAÇÃO ---
0. SEM INFRAÇÃO (Comunicação normal, tática, ruído, ou posições do mapa): SEM PUNIÇÃO.
1. TOXICIDADE COMUM E ESTEREÓTIPOS INDIRETOS: ALERTA. Repetição: CARTÃO 1.
2. HOMOFOBIA E RAGE SEXUAL: CARTÃO 2. Extrema agressividade repetida: CARTÃO 3.
3. XENOFOBIA E PRECONCEITO SOCIAL: Isolado: CARTÃO 3. Dois termos: CARTÃO 4. Repetição massiva: CARTÃO 5.
4. RACISMO E ATRIBUTOS FÍSICOS:
   - CARTÃO 1: Ofensa à cor branca/atributos físicos.
   - CARTÃO 5: Uso da palavra "macaco" apenas 1 VEZ isolada/com 1 palavrão.
   - BAN: "Macaco" 2+ VEZES, ódio direto à cor negra. Capacitismo: CARTÃO 2.
5. REGRA DE AMBIGUIDADE ("ESCURO"): Fora do contexto geográfico: BAN. Geográfico nos mapas corretos: SEM PUNIÇÃO.
6. NAZISMO E EXTREMISMO: Isolado: CARTÃO 4. Com xingamentos: CARTÃO 5. Apologia literal: BAN.
7. AMEAÇA À VIDA E AGRESSÃO FÍSICA REAL: Isolada: CARTÃO 1. Múltiplas: CARTÃO 2. Abuso sexual extremo/morte: CARTÃO 5.
8. REGRA DO ASSINANTE: Se Assinante = SIM, reduza a punição em 1 nível APENAS para a regra 1.
9. ANTIJOGO: Se "Ranked": CARTÃO 1. Se "Lobby / GC Solo": ALERTA.
10. CONDUTA DE MÁ FÉ: Mentiras/falsas dicas: ALERTA. Ghosting/Telar: CARTÃO 2.
11. GORDOFOBIA: Geral: CARTÃO 1. Combo: CARTÃO 2. Repetição: CARTÃO 3.
12. MACHISMO: Geral: CARTÃO 2. Combo: CARTÃO 3. Repetição: CARTÃO 4. Abuso machista: CARTÃO 4.

--- INSTRUÇÕES DE SAÍDA (OBRIGATÓRIO) ---
Você NÃO PODE usar linguagem conversacional (Ex: proibido dizer "Aqui está a análise").
Sua resposta DEVE ter APENAS duas linhas divididas EXATAMENTE por "---".

EXEMPLO PERFEITO DE RESPOSTA 1:
TOXICIDADE: "macaco do caralho" - "vou te matar"
---
Recomendo **BAN** pois houve racismo direto combinado com ameaça à vida.

EXEMPLO PERFEITO DE RESPOSTA 2:
TOXICIDADE: NENHUMA
---
Recomendo **SEM PUNIÇÃO** pois os jogadores estavam apenas comunicando posições do mapa.

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}
[TIPO DE PARTIDA]: {tipo_partida}
"""

    resposta = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Você é uma IA de extração de dados estrita. Você gera saídas exclusivamente no formato 'TOXICIDADE: ... \\n---\\n Recomendo...' e NUNCA adiciona texto extra."},
            {"role": "user", "content": prompt_regras}
        ],
        temperature=0.0,
        max_tokens=1000
    )
    
    return resposta.choices[0].message.content