# 🔌 APIs & Integrações Externas

Esta secção detalha todos os serviços externos, APIs e motores de processamento que alimentam as funcionalidades da **SamBot**.

## 🧠 Inteligência Artificial & Processamento de Linguagem

O "cérebro" do bot utiliza uma arquitetura híbrida para garantir alta disponibilidade e processamento semântico.

- **Google Gemini API:** Utilizada como o motor principal de raciocínio e geração de respostas através do `LLMFactory`.
- **Nomic AI:** Fornece os modelos de _Embeddings_ para converter texto em vetores numéricos, permitindo a busca semântica na memória do bot.
- **ChromaDB:** Banco de dados vetorial local utilizado para armazenar e recuperar memórias de longo prazo e factos sobre os utilizadores.
- **Ollama (Local):** Utilizado para rodar modelos como `Phi-3.5` ou `Qwen` localmente durante o Ciclo Noturno (`NightCycle`) para manutenção de dados.

## 🎵 Áudio & Streaming

A SamBot utiliza uma infraestrutura de áudio profissional isolada para evitar latência e bloqueios de IP.

- **Lavalink (v4):** Servidor de processamento de áudio que gere as streams em tempo real.
- **YouTube (via Plugin):** Integração através do `youtube-plugin` para Lavalink, permitindo a pesquisa e reprodução de vídeos e playlists.
- **SoundCloud / Twitch / Bandcamp:** Suportados nativamente através das fontes do servidor Lavalink.
- **Wavelink:** Biblioteca Python que faz a ponte entre o Discord e o servidor Lavalink.

## 🎮 Jogos & Lojas

Módulos dedicados a fornecer informações em tempo real sobre o mundo dos videojogos.

- **Steam Web API:** Utilizada para procurar preços, descrições e avaliações de jogos diretamente na loja da Valve.
- **IGDB (Twitch API):** Fornece uma base de dados exaustiva sobre jogos, incluindo capas, datas de lançamento e plataformas.
- **CheapShark API:** Utilizada pelas ferramentas de IA para comparar preços de jogos em múltiplas lojas digitais e encontrar promoções.

## 🫂 Interações Sociais & Diversão

- **Nekos.best (v2):** API REST que fornece GIFs de anime de alta qualidade para os comandos de interação social (`hug`, `slap`, `pat`, etc.).

## 🛠️ Outras Utilidades

- **OpenWeatherMap:** (Via `WeatherTool`) Utilizada para fornecer informações meteorológicas em tempo real.
- **Google Search / DuckDuckGo:** (Via `BuscaTools`) Permite que o agente de IA realize pesquisas na web para responder a perguntas sobre eventos atuais.

---

### 🔑 Configuração de Credenciais

Todas as chaves de API mencionadas acima devem ser configuradas no ficheiro `.env` na raiz do projeto para que os módulos carreguem corretamente. Para chaves específicas de tokens (como IGDB), os ficheiros JSON em `Data/Config/` são atualizados automaticamente pelo sistema de autenticação do bot.
