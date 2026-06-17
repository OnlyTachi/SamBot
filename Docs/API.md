# 🔌 APIs & Integrações Externas

Esta secção detalha todos os serviços externos, APIs e motores de processamento que alimentam as funcionalidades da **SamBot**.

## 🧠 Inteligência Artificial & Processamento de Linguagem

O "cérebro" do bot utiliza uma arquitetura híbrida para garantir alta disponibilidade e processamento semântico.

- **Google Gemini API:** Utilizada como o motor principal de raciocínio e geração de respostas através do `LLMFactory`.
- **Nomic AI:** Fornece os modelos de _Embeddings_ para converter texto em vetores numéricos, permitindo a busca semântica na memória do bot.
- **ChromaDB:** Banco de dados vetorial local utilizado para armazenar e recuperar memórias de longo prazo e factos sobre os utilizadores.
- **Ollama (Local):** Utilizado para rodar modelos como `Phi-3.5` ou `Qwen` localmente durante o Ciclo Noturno (`NightCycle`) para manutenção de dados.

## 🎵 Áudio, Streaming & Servidores de Mídia

A SamBot utiliza uma infraestrutura híbrida de áudio de baixa latência capaz de mesclar arquivos pessoal com streaming da internet.

- **Lavalink (v4):** Servidor de processamento de áudio externo (rodando em porta segura SSL/TLS 443) que gerencia os fluxos de transmissão e decodificação em tempo real.
- **Wavelink (v3/v4 Wrapper):** Biblioteca Python assíncrona utilizada para fazer a ponte de comunicação nativa entre o ecossistema do Discord.py e o nó do Lavalink.
- **[Navidrome (Subsonic API):](Config/Navidrome.md)** Servidor de streaming local integrado diretamente ao bot. Permite que o `SearchManager` faça varreduras por chamadas HTTP assíncronas (`aiohttp`) na sua biblioteca de arquivos local de alta fidelidade antes de buscar dados na internet.
- **YouTube / SoundCloud:** Suportados de forma integrada via Lavalink como provedores de fallback online caso a música não seja encontrada na biblioteca do Navidrome.

## 🎮 Jogos & Lojas

Módulos dedicados a fornecer informações em tempo real sobre o mundo dos videojogos.

- **Steam Web API:** Utilizada para procurar preços, descrições e avaliações de jogos diretamente na loja da Valve.
- **IGDB (Twitch API):** Fornece uma base de dados exaustiva sobre jogos, incluindo capas, datas de lançamento e plataformas.
- **CheapShark API:** Utilizada pelas ferramentas de IA para comparar preços de jogos em múltiplas lojas digitais e encontrar promoções.
- **Easy-PIL:** Biblioteca principal para a criação de imagens dinâmicas. É utilizada para renderizar os cards de +perfil (com avatares redondos e barras de progresso) e o leaderboard do +rank.

## 🫂 Interações Sociais & Diversão

- **Nekos.best (v2):** API REST que fornece GIFs de anime de alta qualidade para os comandos de interação social (`hug`, `slap`, `pat`, etc.).

## 🛠️ Outras Utilidades

- **OpenWeatherMap:** (Via `WeatherTool`) Utilizada para fornecer informações meteorológicas em tempo real.
- **Google Search / DuckDuckGo:** (Via `BuscaTools`) Permite que o agente de IA realize pesquisas na web para responder a perguntas sobre eventos atuais.

---

### 🔑 Configuração de Credenciais

Todas as chaves de API mencionadas acima devem ser configuradas no ficheiro `.env` na raiz do projeto para que os módulos carreguem corretamente. Para chaves específicas de tokens (como IGDB), os ficheiros JSON em `Data/Config/` são atualizados automaticamente pelo sistema de autenticação do bot.
