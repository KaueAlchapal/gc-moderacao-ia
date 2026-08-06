 Zeus - IA Moderadora de CX

Olá!

Apresento o **Zeus**, o nosso Assistente de Inteligência Artificial criado para apoiar o time de CX (Community Experience).

O objetivo do Zeus não é substituir o julgamento humano (a palavra final é sempre sua!), mas sim atuar como um "colega analista" super rápido. Ele lê as denúncias, cruza com as nossas regras internas e sugere a punição mais justa em segundos, ajudando a padronizar as nossas decisões.

- Nesse projeto, a infraestrutura do Zeus foi desenhada com foco em baixa latência (velocidade) e consistência de respostas, garantindo que a operação escale sem gargalos.

- Ambiente Isolado: Temos uma API Key do Google Gemini dedicada exclusivamente para o Zeus. Isso significa que nossos limites de requisições por minuto (RPM) e processamento (TPM) são próprios, blindando a ferramenta contra instabilidades de outros sistemas.

- O Modelo usado (Gemini 3.1 Flash Lite): Escolhemos operar especificamente na versão Flash Lite. Diferente dos modelos mais pesados (como o Pro ou Ultra), o Flash Lite é construído especificamente para tarefas de alta frequência e processamento rápido de texto. Ele devolve a classificação em questão de segundos com um custo computacional baixíssimo.
  
- Configuramos o modelo no código com a "temperatura zero" (temperature: 0.0). Isso remove a "criatividade" da IA, forçando-a a agir como um classificador estrito. Ela não inventa regras!

# Como o Zeus pensa?
Ele foi treinado para seguir rigorosamente as nossas **Regras de Ouro**, incluindo:
* **Tolerância Zero contra Preconceito:** Punições severas para xenofobia e homofobia (Cartões 2 a 4) e BAN imediato para racismo explícito.
* **Diretriz de Assinantes:** O Zeus sabe que usuários assinantes da plataforma têm direito a redução de pena em casos leves de rage/toxicidade, mas ele corta esse benefício imediatamente se a infração envolver qualquer tipo de preconceito grave.
* **Consistência:** Ele sugere sempre uma punição única e direta, para você não ter que ficar em dúvida.

---

# Como o projeto funciona (Sem termos difíceis)

Este projeto usa uma interface simples e a inteligência do Google (Gemini) nos bastidores. Temos apenas dois arquivos que importam para nós:

* Arquivo `app.py`: É onde estão as regras lógicas e o código da IA. **Você não precisa mexer aqui.**
* Arquivo `casos.csv`: É o nosso **Livro de Regras**! É literalmente uma planilha com o nosso histórico orgânico de punições. É lendo esse arquivo que o Zeus aprende como a nossa equipe decide punições.

*Desenvolvido para acelerar as análises e proteger a nossa comunidade.* 
