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

--- CONTEXTO CULTURAL E GÍRIAS BRASILEIRAS ---
- Gírias como "porra", "caralho", "fdp" e "viado" (como vocativo, ex: "porra, viado") são Toxicidade Comum/Rage.
- Homofobia real exige ataque de ódio direcionado à sexualidade.

--- DIRETRIZES DE CLASSIFICAÇÃO (CALIBRADAS) ---
0. SEM INFRAÇÃO (Comunicação normal, tática, posições do mapa): SEM PUNIÇÃO.
1. TOXICIDADE COMUM E ESTEREÓTIPOS INDIRETOS: Palavrões genéricos ("fdp", "vtnc"), estereótipos indiretos, rage e vocativos ("viado" sem ofensa). Punição: ALERTA. Repetição: CARTÃO 1.
2. HOMOFOBIA E RAGE SEXUAL: Termos homofóbicos ou rage sexual (Ex: "fui estuprado [no jogo]"): CARTÃO 2. Extrema agressividade repetida: CARTÃO 3.
3. XENOFOBIA E PRECONCEITO SOCIAL: Um termo isolado (ex: "favelado"): CARTÃO 3. Dois termos/combo: CARTÃO 4. Repetição massiva (4x+): CARTÃO 5.
4. RACISMO E ATRIBUTOS FÍSICOS (ATENÇÃO ÀS DIFERENÇAS):
   - CARTÃO 1: Ofensa à cor branca ou atributos físicos comuns. Capacitismo: CARTÃO 2.
   - CARTÃO 4: Uso isolado ou simples das palavras "macaco", "makako", "mono" (espanhol), "seu chimpanzé", "chimpanzé retardado".
   - CARTÃO 5: Uso da palavra "macaco" acompanhada de apenas 1 palavrão genérico (Ex: "macaco do caralho", "macaco lixo", "macaco fdp").
   - BAN: A palavra "macaco" dita 3 VEZES OU MAIS (repetição), acompanhada de múltiplos xingamentos combinados, ou qualquer ofensa/ódio direto direcionado à cor negra (Ex: "preto de merda", "odeio negros", "pretinho", "seu preto do caralho").
5. REGRA DE AMBIGUIDADE ("ESCURO"):
   - Caso a partida tenha ocorrido nos mapas Dust 2, Ancient ou Inferno e o uso for estritamente geográfico/posição: IGNORE a palavra (SEM PUNIÇÃO).
   - Se for ataque racista explícito fora de contexto de mapa: BAN.
   - DÚVIDA: Aplique punição pelos outros xingamentos + AVISO DUPLO.
6. NAZISMO: Isolado: CARTÃO 4. Com xingamentos: CARTÃO 5. Apologia literal: BAN.
7. AMEAÇA À VIDA E AGRESSÃO FÍSICA REAL (GRAVÍSSIMO):
   - Ameaça de agressão física na vida real de forma isolada (Ex: "se eu te ver na rua te bato"): CARTÃO 1. 
   - Repetições e ameaças de morte (Ex: "se eu te ver na rua eu te mato e te bato, vou atirar em você"): CARTÃO 2.
   - Ameaça literal de abuso sexual extremo à família ou crianças/menores (Ex: "Vou estuprar sua irmãzinha"): CARTÃO 5. ATENÇÃO: Considere variações ortográficas ("estrupo", "estruparam") como ofensa real grave.
8. REGRA DO ASSINANTE: Se Assinante = SIM, reduza a punição em 1 nível APENAS para a regra 1.
9. ANTIJOGO: Se "Ranked": CARTÃO 1. Se "Lobby / GC Solo": ALERTA. (Trava: Se houver xingamento grave no relato, ignore antijogo).
10. CONDUTA DE MÁ FÉ: Mentiras, falsas dicas: ALERTA. Ghosting/Telar: CARTÃO 2.
11. GORDOFOBIA: Geral: CARTÃO 1. Combo: CARTÃO 2. Repetição: CARTÃO 3.
12. MACHISMO: Geral: CARTÃO 2. Combo: CARTÃO 3. Repetição: CARTÃO 4. Abuso machista ("estuprada", "piranha"): CARTÃO 4.

--- INSTRUÇÕES DE SAÍDA (OBRIGATÓRIO) ---
Sua resposta DEVE ter APENAS duas partes divididas EXATAMENTE por "---". NÃO use linguagem conversacional.

EXEMPLO PERFEITO 1 (CARTÃO 4):
TOXICIDADE: "seu chimpanzé retardado"
---
Recomendo **CARTÃO 4** pelo uso da palavra chimpanzé de forma isolada.

EXEMPLO PERFEITO 2 (BAN POR RACISMO EXPLÍCITO):
TOXICIDADE: "seu preto do caralho" - "macaco negro"
---
Recomendo **BAN** pois há racismo explícito com uso de termos pejorativos direcionados à cor da pele.

--- CASO PARA CLASSIFICAÇÃO FORENSE ---
[LOG DO SERVIDOR]: "{texto_usuario}"
[ASSINANTE]: {assinante}
[TIPO DE PARTIDA]: {tipo_partida}
"""

    resposta = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Você é uma IA de auditoria rígida. Você julga níveis de racismo com precisão, separando ofensas animais isoladas de ataques raciais diretos. Você gera saídas no formato 'TOXICIDADE: ... \\n---\\n Recomendo...' e NUNCA adiciona texto extra."},
            {"role": "user", "content": prompt_regras}
        ],
        temperature=0.0,
        max_tokens=1000
    )
    
    return resposta.choices[0].message.content