# 🔌 APIs, Provedores & Catálogo de Ferramentas

Este documento cataloga todos os serviços externos, motores de inferência, bibliotecas de vetorização e ferramentas auxiliares consumidas pela **SamBot**, organizados por subsistema funcional e modo de consumo pelo pipeline cognitivo.

## 📋 Visão Geral do Catálogo de Ferramentas

| Ferramenta                  | Identificador   | Dependência / API                         | Finalidade                                                                   |
| --------------------------- | --------------- | ----------------------------------------- | ---------------------------------------------------------------------------- |
| **Busca Web**               | `web_search`    | Google Custom Search / Brave / DuckDuckGo | Fatos em tempo real, notícias e resolução de dúvidas contextuais.            |
| **Clima & Tempo**           | `weather`       | Open-Meteo & Nominatim                    | Previsão climática, sensação térmica e chuva sem necessidade de API Key.     |
| **Identificação de Animes** | `anime_trace`   | Trace.moe                                 | Reconhecimento de cenas de anime a partir de prints ou anexos de imagem.     |
| **Catálogo de Animes**      | `anime_info`    | Jikan API v4 (MyAnimeList)                | Sinopses, notas, episódios, estúdios e lançamentos de animes.                |
| **Catálogo de Games**       | `game_search`   | IGDB (Twitch API v4)                      | Capas, gêneros, plataformas, notas da crítica e resumo de jogos.             |
| **Promoções de Jogos**      | `game_deals`    | CheapShark API & AwesomeAPI               | Comparador de preços de jogos de PC (Steam, Epic, GOG) convertido para BRL.  |
| **Mídia Local**             | `media_library` | Navidrome (Subsonic) / Jellyfin           | Busca de faixas, álbuns, filmes e séries no servidor multimídia residencial. |
| **Calculadora Segura**      | `calculator`    | SymPy & AST Python (`ast.parse`)          | Avaliação determinística e simbólica de expressões matemáticas e unidades.   |

## 🧠 1. Cérebro: Inteligência Artificial, Vetorização e Ferramentas

O núcleo cognitivo (`Brain/`) foi projetado para operar de forma modular e resiliente. Ele combina processamento local ultrarrápido, uma cadeia de modelos de linguagem com failover automático (`LLMChainOrchestrator`), roteamento semântico (`TLMRouter`) e ferramentas especializadas para consulta de dados em tempo real.

### 1.1. Cadeia de Provedores LLM (`Brain/Providers/`)

As requisições de texto e análise multimodal são orquestradas pela `LLMFactory` seguindo a ordem definida em `LLM_CHAIN_ORDER` (padrão: `gemini,groq,ollama`):

- **Google Gemini (`GeminiDriver` — SDK `google-genai`):** Motor principal de raciocínio, visão computacional e geração de respostas. Utiliza o modelo `gemini-2.5-flash` (configurável via `GEMINI_MODEL_NAME`) e suporta rotação dinâmica entre múltiplas chaves (`GEMINI_API_KEY`, `GEMINI_API_KEY_1`, `GEMINI_API_KEY_N`). Chaves que atingem limites de cota (_HTTP 429 / RESOURCE_EXHAUSTED_) entram automaticamente em quarentena temporária (_cooldown_ de 300 segundos).
- **Groq Cloud (`GroqDriver`):** Provedor secundário de inferência ultrarrápida (padrão: `llama-3.1-8b-instant`). Possui poda automática de histórico para evitar erros de limite de tokens por minuto (_HTTP 413 / TPM_) em planos gratuitos.
- **DeepSeek (`DeepSeekDriver`):** Driver compatível com o padrão OpenAI para os modelos `deepseek-chat`, atuando como camada adicional de contingência.
- **Mistral AI (`MistralDriver`):** Integração via API oficial para modelos `mistral-small-latest`.
- **OpenRouter (`OpenRouterDriver`):** Gateway unificado que permite rotear requisições para modelos abertos e gratuitos (padrão: `meta-llama/llama-3.3-70b-instruct:free`).
- **Ollama (`OllamaDriver`):** Infraestrutura local ou remota com fallback em dois estágios: tenta primeiramente um servidor remoto acelerado por GPU (`OLLAMA_REMOTE_URL` / `MODEL_SMART_REMOTE`) e, em caso de indisponibilidade, recua para a instância local (`OLLAMA_LOCAL_URL` / `qwen2.5:1.5b`).

### 1.2. Memória Vetorial & Processamento Local (NLP)

Para eliminar latência de rede e dependência de APIs externas na indexação de memórias e rotas semânticas, todo o processamento vetorial ocorre localmente no processo da aplicação:

- **FastEmbed & ONNX Runtime (`SmartEmbeddingFunction`):** Motor embarcado utilizando o modelo `sentence-transformers/all-MiniLM-L6-v2` (vetores densos de **384 dimensões**). No boot, realiza auto-diagnóstico de hardware e elege automaticamente o melhor acelerador disponível: **CUDA** (NVIDIA), **ROCm** (AMD), **DirectML** (Windows/iGPU), **OpenVINO** (Intel) ou **CPU**.
- **ChromaDB (`VectorStore`):** Banco de dados vetorial persistente (`Data/Persistence/VectorDB/`) que indexa por distância de cosseno três coleções distintas: fatos permanentes dos usuários (`fatos_usuario`), resumos consolidados pelo Ciclo Noturno (`resumos_diarios`) e gatilhos de ferramentas (`rotas_intencoes`).
- **spaCy & RapidFuzz (`LimpezaManager`):** Motor linguístico local (`pt_core_news_sm`) responsável por remover emojis, normalizar gírias, extrair lemas e interceptar intenções triviais na **Camada 0** sem gastar tokens de API.

### 1.3. Ferramentas Cognitivas & Auxiliares (`Brain/Tools/`)

Acionadas dinamicamente pelo `TLMRouter` com base na intenção semântica do usuário:

#### Pesquisa Web, Visão & Mídia Visual (`Research/`)

- **Busca Web (`BuscaTool` / `web_search`):** Acionada quando o `TLMRouter` identifica necessidade de dados recentes não presentes no conhecimento estático do bot. Consulta sequencialmente a **Google Custom Search API**, **Brave Search API** e **DuckDuckGo Instant Answer API** (fallback gratuito sem chave), compilando os 3 principais snippets e suas fontes para que a LLM sintetize a resposta sem alucinações.
- **Visão Computacional (`VisionTool`):** Extrai anexos de imagem do Discord (`.png`, `.jpg`, `.webp`, `.heic`) e os envia para análise multimodal nos drivers compatíveis.
- **Imagens & GIFs (`ImageSearchTool` & `GifService`):** Integração com **Pixabay API** para busca de imagens e **Giphy API** para GIFs contextuais de reação.

#### Cultura Pop & Anime (`Anime/`)

- **Identificação de Animes (`anime_trace` — Trace.moe API):** Reconhecimento visual de cenas de anime a partir de prints ou anexos enviados no Discord. Processa a imagem via buffer e retorna o título (Romaji e Inglês via AniList), episódio, minutagem exata e pré-visualização, aplicando um corte padrão de **85% de similaridade visual** para evitar falsos positivos.
- **Catálogo de Animes (`anime_info` — Jikan API v4):** Consulta assíncrona direta ao **MyAnimeList**, retornando título canônico, status de exibição, número de episódios, estúdio de animação, sinopse e score da comunidade.

#### Compras, Ofertas & Cupons (`Shopping/`)

- **Agregador de Produtos (`ProductSearchTool`):** Executa buscas simultâneas (`asyncio.gather`) via scraping estruturado (Astro Islands) no **Pelando**, **API Oficial do Mercado Livre** (`/sites/MLB/search`) e **Google Shopping** (via **SerpApi**).
- **Buscador de Cupons (`CupomFinder`):** Consulta a API nativa do **Promobit**, realiza raspagem HTML no **Pelando** e utiliza **SerpApi** como fallback.
- **Cache & Monitoramento (`ShoppingDataManager` & `PriceTracker`):** Indexa ofertas com expiração automática (TTL) no **Meilisearch** e monitora listas de desejos durante a madrugada.

#### Utilidades, Mídia Residencial & Cálculos (`Tools/`)

- **Meteorologia (`WeatherTool` / `weather`):** Realiza geocodificação de cidades para coordenadas (`lat`, `lon`) via **OpenStreetMap Nominatim** combinada com previsão climática da **Open-Meteo API** (temperatura atual, máxima/mínima, probabilidade de precipitação e velocidade do vento). Não requer chave de API.
- **Mídia Local (`JellyfinTool` / `media_library`):** Sincroniza o catálogo de filmes e séries de um servidor **Jellyfin**, indexa sinopses no ChromaDB para busca semântica e processa webhooks de novos conteúdos adicionados (complementando a consulta de faixas e álbuns do Navidrome).
- **Calculadora Segura (`CalculatorTool` / `calculator`):** Combina avaliação determinística baseada em **AST Python (`ast.parse`)** — que valida exclusivamente nós matemáticos permitidos (`Add`, `Sub`, `Mult`, `Div`, `Pow`, `USub`) para bloquear injeções de código sem usar `eval()` — com o motor simbólico **SymPy** para equações algébricas e conversões dinâmicas de unidades.
- **PokAPI (`PokemonTool`):** Consulta status base, tipos, medidas e itens da franquia Pokémon.

## 🎵 2. Áudio, Streaming & Biblioteca Privada

A SamBot opera sobre o ecossistema **Wavelink / Lavalink v4** em **dois modos estritos e mutuamente exclusivos** (`ONLINE` ou `LOCAL`), configurados via `config.yaml`:

- **Wavelink & Lavalink (v4):** Gerencia a conexão com o _Discord Voice Gateway_, decodificação de streams, filtros DSP e balanceamento entre múltiplos nós com quarentena automática (_cooldown_ de 1 hora) em caso de falha.
- **[Navidrome (Subsonic API v1.16.1+):](/Docs/Config/Audios/Navidrome.md)** Servidor de streaming privado utilizado no modo `LOCAL` (e integrado à ferramenta `media_library`). Realiza buscas (`/rest/search3.view`) e gera fluxos diretos autenticados via _salt + hash MD5_ (`/rest/stream.view`) para reproduzir acervos Hi-Fi (FLAC/MP3) na rede interna sem consumo de banda externa.
- **Provedores Públicos (`YouTube / SoundCloud`):** Utilizados exclusivamente quando o sistema opera em modo `ONLINE` através do pool de nós remotos.

## 🎮 3. Jogos, Cotações & Renderização Gráfica

Módulos dedicados ao ecossistema gamer e geração de mídia dinâmica:

- **Catálogo de Games (`IGDBService` / `game_search` — Twitch API v4):** Requer `IGDB_CLIENT_ID` e `IGDB_CLIENT_SECRET`. Consulta capas em alta resolução, fichas técnicas, avaliações da crítica, plataformas, datas de lançamento e enredos, gerenciando e renovando automaticamente o token OAuth2 da Twitch no SQLite.
- **Promoções & Câmbio (`CheapSharkService` / `game_deals` & `CurrencyService`):** Compara preços atuais, mínimos históricos e percentuais de desconto de jogos em lojas digitais de PC (Steam, GOG, Epic Games, Humble Store, Blizzard, EA) com link direto da oferta, convertendo os valores de USD para BRL utilizando a cotação em tempo real da **AwesomeAPI** (com cache de 2 horas).
- **Steam Web API (`SteamTool`):** Consulta promoções em destaque na loja brasileira (`cc=BR`) e requisitos de sistema.
- **Easy-PIL:** Biblioteca de manipulação de imagens utilizada para renderizar cards dinâmicos de perfil (`+perfil`) e rankings (`+rank`).

## 🫂 4. Interações Sociais & Mensageria

- **Nekos.best (v2):** API REST utilizada para obter GIFs de anime para comandos de interação social (`hug`, `slap`, `pat`, etc.).
- **Telegram User-Client (Telethon MTProto):** Integração opcional para monitorar canais de promoções em tempo real e alimentar o índice de ofertas do Meilisearch.

## 🔑 5. Gestão de Credenciais e Persistência

- **Essenciais:** Apenas `DISCORD_TOKEN`, `OWNER_ID`, `BOT_PREFIX` e as credenciais do **Meilisearch** (`MEILI_HOST`, `MEILI_MASTER_KEY`) são obrigatórios para a inicialização básica.
- **Opcionais:** Todas as demais chaves de API devem ser declaradas no arquivo `.env` na raiz do projeto apenas se você desejar ativar os respectivos drivers ou ferramentas (serviços como _Open-Meteo_, _Nominatim_, _Trace.moe_, _Jikan_ e _CheapShark_ funcionam sem autenticação).
- **Renovação Automática:** Tokens temporários de autenticação (como o _Access Token_ OAuth2 da Twitch/IGDB) são renovados e persistidos automaticamente no banco SQLite (`database.db`) através do `DataManagerFacade`.
