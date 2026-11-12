# 🔐 Dicionário de Variáveis de Ambiente

Este documento serve como referência técnica detalhada para todas as variáveis de ambiente consumidas pela **SamBot**. As variáveis devem ser mantidas em um arquivo `.env` localizado na raiz do projeto.

## 🧩 Estrutura Completa de Referência

```env
# =====================================================
# DISCORD & IDENTIDADE (Essenciais)
# =====================================================
DISCORD_TOKEN=seu_token_do_bot_aqui
OWNER_ID=seu_id_aqui

# =====================================================
# DISCORD OAUTH2 (Opcional - Caso utilize API/Dashboard)
# =====================================================
DISCORD_CLIENT_ID=seu_client_id_do_discord_aqui # (opcional)
DISCORD_CLIENT_SECRET=seu_client_secret_do_discord_aqui # (opcional)

# =====================================================
# API INTERNA SAMBOT (Opcional)
# =====================================================
# Chave mestra esperada nos headers (X-Bot-Token / X-API-Token)
API_SECRET_TOKEN=sambot_secret_token_industrial_2026 # (opcional)

# =====================================================
# TELEGRAM USER-CLIENT - Telethon MTProto (Opcional)
# =====================================================
TELEGRAM_ENABLED=false # (opcional)
TELEGRAM_API_ID=seu_telegram_api_id # (opcional)
TELEGRAM_API_HASH=seu_telegram_api_hash # (opcional)
TELEGRAM_SESSION_NAME=sambot_user # (opcional)
TELEGRAM_CHANNELS=-1001234567890,@canal_promocoes # (opcional)

# =====================================================
# PERSISTÊNCIA & BANCOS DE DADOS
# =====================================================
# Meilisearch (Essenciais)
MEILI_HOST="http://127.0.0.1:7700"
MEILI_MASTER_KEY=sua_chave_master_meilisearch_aqui

# Navidrome / Subsonic API (Opcional)
NAVIDROME_URL="http://192.168.1.100:4533" # (opcional)
NAVIDROME_USER="sambot_user" # (opcional)
NAVIDROME_PASSWORD=sua_senha_do_navidrome_aqui # (opcional)

# =====================================================
# SERVIÇOS DE DOWNLOAD & MÍDIA LOCAL (Opcional)
# =====================================================
YT_WORKER_URL="http://127.0.0.1:4000" # (opcional)

# Jellyfin (Streaming de Mídia Local)
JELLYFIN_URL="http://jellyfin:8096" # (opcional)
JELLYFIN_API_KEY=sua_chave_de_api_jellyfin # (opcional)
JELLYFIN_NOTIF_CHANNEL_ID=123456789012345678 # (opcional)

# =====================================================
# CHAVES DE FERRAMENTAS & PESQUISA (Opcional)
# =====================================================
# Twitch / IGDB
IGDB_CLIENT_ID=seu_twitch_client_id # (opcional)
IGDB_CLIENT_SECRET=seu_twitch_client_secret # (opcional)

# Google Custom Search (Web Search)
GOOGLE_SEARCH_API_KEY=sua_chave_google_search # (opcional)
GOOGLE_SEARCH_CX=seu_search_engine_cx # (opcional)

# Brave Search (Fallback Web)
BRAVE_SEARCH_API_KEY=sua_chave_brave_aqui # (opcional)

# Busca de Imagens & Giphy
PIXABAY_API_KEY=sua_chave_pixabay # (opcional)
GIPHY_API_KEY=sua_chave_giphy # (opcional)

# Google Shopping & Scraping (SerpApi)
SERPAPI_KEY=sua_chave_serpapi_aqui # (opcional)

# =====================================================
# PROVEDORES DE IA / LLM - Cadeia com Failover Automático (Opcional)
# =====================================================
# Google Gemini (Suporta múltiplas chaves rotativas com GEMINI_API_KEY_N)
GEMINI_API_KEY=sua_chave_gemini_principal # (opcional)
GEMINI_API_KEY_1=sua_chave_gemini_reserva_1 # (opcional)
GEMINI_API_KEY_2=sua_chave_gemini_reserva_2 # (opcional)

# Groq Cloud
GROQ_API_KEY=gsk_sua_chave_groq_aqui # (opcional)

# DeepSeek
DEEPSEEK_API_KEY=sk-sua_chave_deepseek_aqui # (opcional)

# Mistral AI
MISTRAL_API_KEY=sua_chave_mistral_aqui # (opcional)

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-sua_chave_openrouter_aqui # (opcional)

# Ollama Remoto (Deixe vazio caso utilize apenas Docker/Local)
OLLAMA_REMOTE_URL= # (opcional)
MODEL_SMART_REMOTE=phi3.5:latest # (opcional)
```

## 🛠️ Detalhamento dos Grupos

### 1. Núcleo e Conexão Discord

- **`DISCORD_TOKEN`**: Chave de autenticação primária do bot. O bot não inicializa sem esta variável.
- **`OWNER_ID`**: Identificador numérico exclusivo de 64 bits do proprietário. Usado para permissões administrativas e autorização de comandos restritos.

### 2. Infraestrutura e Serviços Internos

- **`MEILI_HOST`** e **`MEILI_MASTER_KEY`**: Permitem ao bot indexar, limpar e buscar ofertas, cupons e caches tipotolerantes. Caso o Meilisearch não esteja acessível, os módulos de busca de produtos retornarão fallback vazio sem derrubar o bot.
- **`API_SECRET_TOKEN`**: Utilizado para proteger endpoints administrativos da FastAPI e controlar a validação de conexões WebSockets.

### 3. Ingestão Telegram (Opcional)

- Necessário apenas caso o serviço `telegram` esteja habilitado no `config.yaml`. Permite que o cliente Telethon atue via MTProto monitorando promoções em canais públicos ou grupos autorizados.

### 4. Áudio Local (Navidrome / Subsonic)

- Utilizado exclusivamente quando o modo de áudio estiver configurado como `LOCAL` no `config.yaml`. As credenciais autenticam chamadas na API Subsonic para busca e streaming Hi-Fi sem compressão.

### 5. Catálogos e Ferramentas Externas

- **IGDB (`IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`)**: Utilizados para puxar sinopses, capas, notas agregadas e plataformas de jogos.
- **Motores de Busca Web (`GOOGLE_*`, `BRAVE_*`)**: Utilizados pela ferramenta de busca de fatos em tempo real da esteira cognitiva.

### 6. Provedores de IA (LLMs)

- O sistema agrupa dinamicamente todas as chaves iniciadas por `GEMINI_API_KEY_` em uma lista rotativa para contornar limites de taxa (Rate-Limit / HTTP 429).
- Em caso de esgotamento total de cotas ou falha nos modelos externos, o bot tenta a conexão na Groq ou fallback local via Ollama conforme a ordem estipulada no `config.yaml`.
