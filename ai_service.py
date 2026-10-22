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

--- CONTEXTO CULTURAL E GÍRIAS BRASILEIRAS (MUITO IMPORTANTE) ---
No cenário de jogos no Brasil, palavrões como "porra", "caralho", "filha da puta", "vai tomar no cu" e a palavra "viado" são frequentemente usados como vícios de linguagem, frustração ou vocativos casuais (Ex: "porra, viado", "pega a arma aí, viado", "caralho, morri"). 
- O uso de "viado" como gíria ou vocativo NÃO É HOMOFOBIA. Deve ser tratado como Rage/Toxicidade Comum.
- Homofobia real exige um ataque de ódio DIRECIONADO e pejorativo à sexualidade da pessoa.

--- REGRA DE TETO E ACÚMULO ---
Você é ESTRITAMENTE PROIBIDO de somar infrações leves para gerar um BAN. A punição máxima por acúmulo de toxicidade trava no CARTÃO 5. 

--- DIRETRIZES DE CLASSIFICAÇÃO (CALIBRADAS) ---
0. SEM INFRAÇÃO (Comunicação normal, tática, posições do mapa): SEM PUNIÇÃO.
1. TOXICIDADE COMUM E RAGE (GÍRIAS): Xingamentos genéricos sem alvo de ódio ("fdp", "vtnc", "porra"), rage com o jogo, e vocativos casuais ("viado" sem ofensa direta). Punição: ALERTA. Se for repetição constante direcionada a um jogador: CARTÃO 1.
2. HOMOFOBIA REAL E RAGE SEXUAL: Ataque claro e direto à orientação sexual. CARTÃO 2.
3. XENOFOBIA E PRECONCEITO SOCIAL: Isolado: CARTÃO 3. Dois termos: CARTÃO 4. Repetição massiva: CARTÃO 5.
4. RACISMO E ATRIBUTOS FÍSICOS:
   - CARTÃO 1: Ofensa à cor branca/atributos físicos.
   - CARTÃO 5: Uso da palavra "macaco" apenas 1 VEZ isolada.
   - BAN: "Macaco" 2+ VEZES, ódio direto à cor negra.
5. REGRA DO MAPA ("ESCURO"):
   No CS2, "escuro" é lugar (Ex: "escuro baixo", "tá no escuro").
   - Se a fala for sobre lugar/posição: IGNORE a palavra, não é toxicidade.
   - Se for ataque racista direto (Ex: "seu escuro nojento"): BAN.
   - SE houver DÚVIDA se foi ofensa, aplique a punição baseada nos outros xingamentos e adicione o AVISO DUPLO (veja Exemplo 3).
6. NAZISMO E EXTREMISMO: Isolado: CARTÃO 4. Apologia literal: BAN.
7. AMEAÇA À VIDA E AGRESSÃO: Isolada: CARTÃO 1. Múltiplas: CARTÃO 2. Abuso sexual/morte: CARTÃO 5.
8. REGRA DO ASSINANTE: Se Assinante = SIM, reduza a punição em 1 nível APENAS para a regra 1.
9. ANTIJOGO: Se "Ranked": CARTÃO 1. Se "Lobby / GC Solo": ALERTA.

--- INSTRUÇÕES DE SAÍDA (OBRIGATÓRIO) ---
Você NÃO PODE usar linguagem conversacional (Ex: proibido dizer "Aqui está a análise").
Sua resposta DEVE ter APENAS duas partes divididas EXATAMENTE por "---".

EXEMPLO PERFEITO 1 (RAGE COMUM / GÍRIA):
TOXICIDADE: "porra, viado" - "vai tomar no cu" - "caralho"
---
Recomendo **ALERTA** (ou Cartão 1 no máximo) pois trata-se de rage comum e vícios de linguagem/gírias, sem ataque de ódio direto.

EXEMPLO PERFEITO 2 (POSIÇÃO DE MAPA):
TOXICIDADE: NENHUMA
---
Recomendo **SEM PUNIÇÃO** pois os jogadores estavam apenas comunicando posições do mapa como "escuro baixo".

EXEMPLO PERFEITO 3 (DÚVIDA NO RACISMO):
TOXICIDADE: "filha da puta" - "escuro"
---
Recomendo **ALERTA**. **ATENÇÃO ANALISTA:** Caso o termo "escuro" tenha sido utilizado com intenção racista na voz do jogador (e não posição do mapa), aplique **BAN**.

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}
[TIPO DE PARTIDA]: {tipo_partida}
"""

    resposta = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Você é uma IA de auditoria rígida. Você entende de gírias brasileiras e NUNCA confunde gírias com homofobia real. Você gera saídas exclusivamente no formato 'TOXICIDADE: ... \\n---\\n Recomendo...' e NUNCA adiciona texto extra."},
            {"role": "user", "content": prompt_regras}
        ],
        temperature=0.0,
        max_tokens=1000
    )
    
    return resposta.choices[0].message.content