# Zeus AI | Moderação e Auditoria Forense para CX
Acelerando decisões e protegendo a nossa comunidade.

Apresento o Zeus, um Assistente de Inteligência Artificial desenhado especificamente para apoiar o time de CX (Community Experience) na moderação de eSports.

O objetivo do Zeus não é substituir o julgamento humano — a palavra final e o contexto sempre pertencerão ao analista. Ele atua como um "copiloto" de altíssima velocidade: transcreve áudios complexos em segundos, analisa logs de denúncias, cruza os dados com o nosso livro de regras interno e sugere a punição mais justa e padronizada. O resultado? Fim do gargalo de moderação, consistência nas aplicações de regras e uma comunidade mais segura.

# Arquitetura e Engenharia (Under the Hood)
A infraestrutura do Zeus foi projetada com foco absoluto em baixa latência, resiliência contra falhas e superação de barreiras físicas de APIs.

- Motor de Inferência (Gemini 3.1 Flash Lite): O "Cérebro". Escolhemos a versão Flash Lite do Google por ser construída para tarefas de alta frequência e processamento rápido. Com a temperatura zerada (Temperature 0.0), removemos a "criatividade" da IA, forçando-a a agir como um classificador estrito, clínico e baseado apenas nas regras.

- Motor de Transcrição Ultra-Rápida (Groq + Whisper Large V3): O "Ouvido". O processamento de áudio é feito pela API da Groq rodando o modelo Whisper Large V3. Isso nos permite converter minutos de denúncia de áudio em texto em poucos segundos, superando massivamente a velocidade do processamento convencional.

- Bypass de Limite de Arquivos (Fatiador Automático): APIs de áudio possuem limites rígidos (25 MB). Para lidar com denúncias longas (áudios de 10 min+ em .wav que chegam a 80MB), o Zeus utiliza a biblioteca pydub e o motor FFmpeg para realizar o "chunking". Ele corta o arquivo automaticamente em pedaços de 2 minutos, processa todos simultaneamente e costura a transcrição no final de forma imperceptível para o usuário.

- Sistema Anti-Queda (Resiliência): Integrado a um loop de repetição dinâmico, o sistema detecta gargalos de rede ou erros de Bad Gateway (502) no Cloudflare da Groq e realiza retentativas automáticas sem quebrar a aplicação para o analista.

- Segurança e Isolamento (Streamlit Secrets): Nenhuma chave de API é exposta no código (app.py). Utilizamos cofres encriptados de variáveis de ambiente para invocar a Groq e o Gemini. O aplicativo também possui roteamento dinâmico, separando o acesso administrativo do Modo Convidado (com trava de limite de usos).

# Como o Zeus pensa? (Regras de Negócio)
O modelo foi treinado via Few-Shot Prompting para seguir rigorosamente as nossas Regras de Ouro:

- Tolerância Zero contra Preconceito: Punições severas e progressivas para xenofobia e homofobia, e punições absolutas para racismo explícito, com lógicas matemáticas rigorosas (ex: Cartão 5 para uso único de "macaco", e BAN direto para repetições no mesmo log).

- Análise de Contexto Geográfico do CS2: O Zeus joga Counter-Strike. Ele sabe diferenciar quando a palavra "escuro" é usada como um termo racista camuflado ou quando é apenas uma comunicação tática (como posições nos mapas Dust 2, Inferno e Ancient).

- Extração Forense Visível: Ao invés de usar filtros cegos (Regex), o próprio Gemini audita o texto, extrai e exibe em um painel destacado apenas os recortes exatos das falas que motivaram a punição. Se a infração não existir, o painel se oculta sozinho.

- Veredito Clínico: O Zeus é proibido de repetir palavras de baixo calão em seus laudos finais, gerando justificativas limpas, objetivas e prontas para auditoria.

# Estrutura do Projeto
Para garantir a manutenibilidade e seguir padrões de Clean Code, o projeto é modularizado da seguinte forma:

   - app.py: A interface gráfica principal (Streamlit). Gerencia a UI, o upload, o fatiador de áudio (pydub) e a exibição das lógicas visuais.

   - ai_service.py: O núcleo da inteligência. Contém os prompts detalhados, o dicionário de regras e as instâncias da API do Google Gemini.

   - auth.py: Roteador de acessos que gerencia os perfis da equipe e bloqueia abusos de visitantes externos.

   - data_manager.py: O "Arquivista". Responsável por carregar o banco de dados e salvar feedbacks de re-treinamento da IA a partir dos administradores.

   - casos.csv: O nosso "Livro de Regras Vivo". Um banco de dados de casos reais anteriores que ensina a IA como o time humano aplica as punições na prática.

   - requirements.txt & packages.txt: Mapeamento vital de dependências do Python e dependências do servidor Linux (ffmpeg) necessárias para o processamento de áudio em nuvem.
