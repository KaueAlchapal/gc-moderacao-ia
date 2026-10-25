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
- Gírias como "porra", "caralho", "fdp", "merda" e "viado" (como vocativo, ex: "porra, viado") são Toxicidade Comum/Rage.
- Homofobia real exige ataque de ódio direcionado à sexualidade.

--- DIRETRIZES DE CLASSIFICAÇÃO (CALIBRADAS) ---
0. SEM INFRAÇÃO (Comunicação normal, tática, posições do mapa): SEM PUNIÇÃO.
1. TOXICIDADE COMUM E ESTEREÓTIPOS INDIRETOS: Palavrões genéricos ("fdp", "vtnc", "merda"), estereótipos indiretos, rage e vocativos ("viado" sem ofensa). Punição: ALERTA. Repetição: CARTÃO 1.
2. HOMOFOBIA E RAGE SEXUAL: Termos homofóbicos ou rage sexual (Ex: "fui estuprado [no jogo]"): CARTÃO 2. Extrema agressividade repetida: CARTÃO 3.
3. XENOFOBIA E PRECONCEITO SOCIAL: Um termo isolado (ex: "favelado"): CARTÃO 3. Dois termos/combo: CARTÃO 4. Repetição massiva (4x+): CARTÃO 5.
4. RACISMO E ATRIBUTOS FÍSICOS (ATENÇÃO ÀS DIFERENÇAS):
   - CARTÃO 1: Ofensa à cor branca ou atributos físicos comuns. Capacitismo: CARTÃO 2.
   - CARTÃO 4: Uso isolado ou simples das palavras "mono" (espanhol), "seu chimpanzé", "chimpanzé retardado".
   - CARTÃO 5: Uso da palavra "macaco" apenas 1 VEZ isolada OU acompanhada de apenas 1 palavrão genérico (Ex: "macaco do caralho", "macaco lixo", "macaco fdp").
   - BAN: A palavra "macaco" dita 2 VEZES OU MAIS (repetição), acompanhada de múltiplos xingamentos combinados, ou qualquer ofensa/ódio direto direcionado à cor negra (Ex: "preto de merda", "odeio negros", "pretinho", "seu preto do caralho").
5. REGRA DE AUDITORIA DA PALAVRA "ESCURO" (GATILHO OBRIGATÓRIO):
   Sempre que a palavra "escuro" aparecer no relato/transcrição:
   - CALCULE A PUNIÇÃO PRINCIPAL IGNORANDO A PALAVRA "ESCURO" (baseie-se apenas nos outros xingamentos existentes no texto (caso tenha), como "filho da puta", "merda", etc.).
   - ADICIONE OBRIGATORIAMENTE O AVISO DA PALAVRA "escuro" PARA O ANALISTA NO FINAL DA RECOMENDAÇÃO.
   - EXCEÇÃO DE BAN DIRETO: Só recomende BAN direto se o termo for um ataque racista pessoal explícito e fora de contexto de jogo (Ex: "seu escuro nojento", "seu escurinho").
6. NAZISMO E EXTREMISMO: Isolado: CARTÃO 4. Com xingamentos: CARTÃO 5. Apologia literal: BAN.
7. AMEAÇA À VIDA E AGRESSÃO FÍSICA REAL (GRAVÍSSIMO):
   - Ameaça de agressão física na vida real de forma isolada (Ex: "se eu te ver na rua te bato"): CARTÃO 1. 
   - Repetições e ameaças de morte (Ex: "se eu te ver na rua eu te mato e te bato, vou atirar em você"): CARTÃO 2.
   - Ameaça literal de abuso sexual extremo à pessoa/família (Ex: "Vou estuprar sua irmãzinha"): CARTÃO 5. ATENÇÃO: Considere variações ortográficas ("estrupo", "estruparam") como ofensa real grave.
8. REGRA DO ASSINANTE: Se Assinante = SIM, reduza a punição em 1 nível APENAS para a regra 1.
9. ANTIJOGO: Se "Ranked": CARTÃO 1. Se "Lobby / GC Solo": ALERTA. (Trava: Se houver xingamento grave no relato, ignore antijogo).
10. CONDUTA DE MÁ FÉ: Mentiras, falsas dicas: ALERTA. Ghosting/Telar: CARTÃO 2.
11. GORDOFOBIA: Geral: CARTÃO 1. Combo: CARTÃO 2. Repetição: CARTÃO 3.
12. MACHISMO: Geral: CARTÃO 2. Combo: CARTÃO 3. Repetição: CARTÃO 4. Abuso machista ("estuprada", "piranha"): CARTÃO 4.

--- INSTRUÇÕES DE SAÍDA E EXTRAÇÃO (OBRIGATÓRIO) ---
Sua resposta DEVE ter APENAS duas partes divididas EXATAMENTE por "---". NÃO use linguagem conversacional.
REGRA DE EXTRAÇÃO: Na linha "TOXICIDADE:", NUNCA extraia apenas a palavra ofensiva isolada. Extraia a FRASE COMPLETA que dá contexto à ofensa (Ex: em vez de extrair apenas "macaco" e "macacos", extraia a frase completa da toxicidade: "Você é um macaco cara, que isso, lá na selva dos macacos"). Se houver várias frases distintas, separe-as por " - ".

EXEMPLO PERFEITO 1 (PALAVRÕES COMUNS + PRESENÇA DA PALAVRA ESCURO):
TOXICIDADE: "cala a boca seu filho da puta" - "acho que tem escuro pessoal"
---
Recomendo **ALERTA** pelo uso de palavrões genéricos. **⚠️ AVISO AO ANALISTA:** A palavra "escuro" foi identificada na transcrição. Verifique se a partida ocorreu em um mapa com essa posição (Dust 2, Ancient ou Inferno) e se foi usada apenas como call-out de mapa. Caso tenha sido usada como ofensa racista, altere o veredito para **BAN**.

EXEMPLO PERFEITO 2 (BAN POR RACISMO EXPLÍCITO):
TOXICIDADE: "só macaco na live, vamos dar ban na Twitch, só macaco lá na selva" - "seu preto do caralho"
---
Recomendo **BAN** pois há racismo explícito com uso de termos pejorativos direcionados à cor da pele combinados com rage.

EXEMPLO PERFEITO 3 (CARTÃO 4 POR TOXICIDADE):

TOXICIDADE: "Você é idiota, seu chimpanzé do caralho" 
--- Recomendo CARTÃO 4 pelo uso de termo que pode ser considerado racista "chimpanzé" associado a palavrão genérico.


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