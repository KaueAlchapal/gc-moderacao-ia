# Zeus AI | Moderação e Auditoria Forense para CX

> **Acelerando decisões e protegendo a nossa comunidade.**

Apresento o **Zeus**, um Assistente de Inteligência Artificial desenhado especificamente para apoiar o time de **CX (Community Experience)** na moderação de eSports. 

O objetivo do Zeus **não é substituir o julgamento humano** — a palavra final e o contexto sempre pertencerão ao analista. Ele atua como um "copiloto" de altíssima velocidade: lê denúncias e transcrições de áudio, cruza os dados com o nosso livro de regras interno e sugere a punição mais justa em segundos. O resultado? Decisões padronizadas, fim do gargalo de moderação e uma comunidade mais segura.

---

## ⚙️ Arquitetura e Engenharia (Under the Hood)

A infraestrutura do Zeus foi projetada com foco absoluto em **baixa latência** e **consistência de respostas**, garantindo que a operação escale sem lentidão.

* **Motor de Inferência (Gemini 3.1 Flash Lite):** Escolhemos operar especificamente na versão *Flash Lite*. Diferente de modelos pesados e lentos, este modelo foi construído para tarefas de alta frequência e processamento rápido de texto. Ele devolve a classificação forense com um custo computacional baixíssimo.
* **Determinismo (Temperature 0.0):** Configuramos o modelo no código com a temperatura zerada. Isso remove a "criatividade" da IA, forçando-a a agir como um classificador estrito, clínico e baseado em fatos. O Zeus não inventa regras, ele as aplica.
* **Ambiente Isolado:** Operamos com uma API Key dedicada exclusivamente para este sistema. Nossos limites de requisições (RPM) e processamento (TPM) são próprios, blindando a ferramenta contra instabilidades de outros produtos.
* **Controle de Acesso (Roteamento Dinâmico):** O aplicativo possui uma porta de segurança embutida, separando o acesso de administradores (via Link Mágico sem atrito) do acesso de visitantes (Modo Convidado com limite de cotas).

---

## 🧠 Como o Zeus pensa? (Regras de Negócio)

O modelo foi treinado para seguir rigorosamente as nossas **Regras de Ouro** de moderação:

* **Tolerância Zero contra Preconceito:** Punições severas e progressivas para xenofobia e homofobia (Cartões 2 a 4) e BAN sumário e imediato para racismo explícito.
* **Análise de Contexto Geográfico:** O Zeus entende de Counter-Strike. Ele sabe diferenciar quando a palavra "escuro" é usada como um termo racista camuflado ou quando é apenas uma comunicação tática geográfica (como nos mapas *Dust 2*, *Inferno* e *Ancient*).
* **Diretriz de Assinantes:** O sistema reconhece usuários assinantes e aplica o benefício de redução de pena em casos leves de *rage* ou toxicidade comum. Contudo, o Zeus é programado para **revogar** esse benefício imediatamente se a infração envolver qualquer tipo de preconceito.
* **Veredito Clínico:** O Zeus é proibido de repetir palavras de baixo calão em seus laudos, gerando justificativas limpas, clínicas e prontas para auditoria.

---

## 📁 Estrutura do Projeto

Para garantir manutenibilidade e seguir o padrão de *Clean Code*, o projeto é modularizado da seguinte forma:

* `app.py`: O "Maestro". A interface gráfica principal (construída em Streamlit) que conecta o analista ao motor da IA.
* `ai_service.py`: O "Cérebro". Contém as chaves de segurança, configurações de filtros e as engenharias de prompt (as leis do Zeus).
* `auth.py`: O "Segurança". Roteador de acessos que gerencia logins da equipe e bloqueia abusos de visitantes externos.
* `data_manager.py`: O "Arquivista". 
* `casos.csv`: O nosso **Livro de Regras Vivo**. Um histórico de dados orgânicos que ensina o Zeus (via *Few-Shot Prompting*) como a equipe toma decisões.

---
*Construído com Python, Streamlit e Google Generative AI.*
