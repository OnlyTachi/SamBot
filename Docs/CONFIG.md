# ⚙️ Guia de Parametrização e Configuração

Este documento reúne todas as diretrizes de configuração da SamBot, detalhando as variáveis de ambiente (`.env`), as opções estruturadas do ficheiro `config.yaml`, o comportamento das personas e os mecanismos de sincronização automática de dados.

## 🔐 1. Variáveis de Ambiente (`.env`)

O ficheiro `.env` deve residir na raiz do projeto e destina-se **exclusivamente** ao armazenamento de chaves de API, credenciais e parâmetros com segredos.

Crie o seu `.env` com base no `.env.example`:

```env
# ==========================================
# DISCORD & IDENTIDADE DO BOT (Obrigatórios)
# ==========================================
DISCORD_TOKEN=seu_token_do_discord_aqui
OWNER_ID=123456789012345678
BOT_PREFIX="+"

# ==========================================
# SERVIDOR API INTERNA & DASHBOARD
# ==========================================
API_SECRET_TOKEN=sambot_secret_token_industrial_2026
DISCORD_CLIENT_ID=seu_client_id_oauth2 (opcional)
DISCORD_CLIENT_SECRET=seu_client_secret_oauth2 (opcional)

# ==========================================
# PERSISTÊNCIA & CACHE (Meilisearch)
# ==========================================
MEILI_HOST="http://meilisearch:7700"
MEILI_MASTER_KEY=sua_chave_master_meilisearch

# ==========================================
# MOTOR DE ÁUDIO & STREAMING
# ==========================================
# Opções estritas de fonte: ONLINE ou LOCAL
MUSIC_SOURCE_MODE=ONLINE

# Configuração do nó local Lavalink
LAVALINK_HOST=127.0.0.1 (opcional)
LAVALINK_PORT=2333 (opcional)
LAVALINK_PASSWORD=youshallnotpass (opcional)

# Credenciais Subsonic (obrigatório se MUSIC_SOURCE_MODE=LOCAL)
NAVIDROME_URL="http://IP_DO_SERVIDOR:4533" (opcional)
NAVIDROME_USER=seu_usuario_navidrome (opcional)
NAVIDROME_PASSWORD=sua_senha_navidrome (opcional)

# ==========================================
# SERVIÇOS AUXILIARES & TELEGRAM
# ==========================================
TELEGRAM_ENABLED=false (opcional)
TELEGRAM_API_ID=seu_api_id (opcional)
TELEGRAM_API_HASH=seu_api_hash (opcional)
JELLYFIN_URL="http://IP_DO_SERVIDOR:8096" (opcional)
JELLYFIN_API_KEY=sua_chave_jellyfin (opcional)

# ==========================================
# CHAVES DE FERRAMENTAS & APIs EXTERNAS
# ==========================================
IGDB_CLIENT_ID=seu_client_id_twitch (opcional)
IGDB_CLIENT_SECRET=seu_client_secret_twitch (opcional)
GOOGLE_SEARCH_API_KEY=sua_chave_google (opcional)
GOOGLE_SEARCH_CX=seu_id_cx_google(opcional)
BRAVE_SEARCH_API_KEY=sua_chave_brave (opcional)
PIXABAY_API_KEY=sua_chave_pixabay (opcional)
SERPAPI_KEY=sua_chave_serpapi (opcional)

# ==========================================
# PROVEDORES DE IA / LLM (Com Failover)
# ==========================================
GEMINI_API_KEY=sua_chave_gemini_principal
GEMINI_API_KEY_1=sua_chave_gemini_reserva_1 (opcional)
GEMINI_API_KEY_2=sua_chave_gemini_reserva_2 (opcional)
GROQ_API_KEY=sua_chave_groq (opcional)
DEEPSEEK_API_KEY=sua_chave_deepseek (opcional)
MISTRAL_API_KEY=sua_chave_mistral (opcional)
OPENROUTER_API_KEY=sua_chave_openrouter (opcional)

# Ollama Remoto (deixe vazio se utilizar apenas Docker/Local)
OLLAMA_REMOTE_URL=http://ip_tailscale_workstation:11434 (opcional)
```

## 📄 2. Configurações Estruturadas (`config.yaml`)

O ficheiro `config.yaml` parametriza o comportamento operacional, microsserviços, políticas de áudio e cadeias de inferência:

```yaml
bot:
  name: "SamBot"
  version: "3.5.0-beta"
  prefix: "+"
  debug_mode: false

services:
  enabled: true
  api: true
  telegram: false
  notifier: true

music:
  mode: "ONLINE" # Opções estritas: ONLINE | LOCAL
  lavalink:
    local:
      host: "127.0.0.1"
      port: 2333
      password: "youshallnotpass"
      secure: false
    nodes:
      - name: "Node-Publico-Principal"
        host: "lavalink.exemplo.com"
        port: 443
        password: "sua_senha_aqui"
        secure: true

database:
  sqlite_timeout: 30.0

tools:
  anime:
    jikan_timeout: 10.0
    jikan_top_limit: 5
  shopping:
    pelando_timeout: 8.0
    pelando_coupon_limit: 5

llm:
  chain_order: ["gemini", "groq", "ollama", "deepseek", "openrouter", "mistral"]
  semantic_router:
    similarity_threshold: 0.74
  models:
    gemini: "gemini-2.5-flash"
    groq: "llama-3.1-8b-instant"
    deepseek: "deepseek-chat"
    openrouter: "meta-llama/llama-3.3-70b-instruct:free"
    mistral: "mistral-small-latest"
  ollama:
    local_url: "[http://host.docker.internal:11434](http://host.docker.internal:11434)"
    models:
      smart: "phi3.5:latest"
      fast: "qwen2.5:1.5b"
      embed: "nomic-embed-text"
```

## 🎭 3. Personalização do Agente, Prompts e Identidade

### Prompts de Estilo (`Data/Prompts/`)

O tom conversacional é moldado pelos ficheiros de texto carregados pelo `BrainDataManager`:

- **`padrao.txt`**: Prompt mestre do sistema (conciso, ágil e descontraído).

- **`amiga.txt`**, **`nerd.txt`**, **`louco.txt`**: Modificadores de personalidade injetados dinamicamente nos canais mapeados.

### Âncora de Identidade (`Data/Persistence/identity.json`)

Mantém as verdades imutáveis sobre a criação e o propósito do agente. É consumida diretamente na **Camada 0** para responder a perguntas de identificação sem consumo de tokens de API.

## 🗄️ 4. Estrutura de Conhecimento (`DatabaseSeeder`)

A SamBot não depende de rescritas lentas de ficheiros JSON durante o funcionamento em tempo real. Em vez disso, adota um padrão de carregamento incremental com controlo de versão por hash:

```text
Data/
├── Config/                  # Tokens transitórios de APIs e sessões (.session)
├── Knowledge/               # Ficheiros JSON declarativos (gatilhos, itens, mercados)
│   ├── atividades.json      # Mensagens dinâmicas de presença do bot
│   ├── router_triggers.json # Utterances semânticas lidas pelo TLMRouter
│   └── noise_words.json     # Termos de ruído para sanitização de argumentos
├── Persistence/
│   ├── database.db          # Base relacional transacional SQLite
│   ├── MeiliDB/             # Dados físicos e índices do Meilisearch
│   └── VectorDB/            # Base vetorial HNSW do ChromaDB (768 dimensões)
└── Prompts/                 # Personas de sistema (.txt)

```

### Ciclo de Validação no Boot

1. **Validação de Integridade (MD5):** Durante o arranque, o `DatabaseSeeder` calcula o hash MD5 dos ficheiros em `Data/Knowledge/` e `Data/Prompts/` e compara-o com os registos gravados na base SQLite.

2. **Ignorar Leituras Idênticas:** Se o conteúdo estiver inalterado, a leitura dos ficheiros de disco é omitida, garantindo um arranque instantâneo.

3. **Atualização Transacional:** Se houver alterações (por exemplo, novos gatilhos em `router_triggers.json`), o seeder propaga os novos dados para as tabelas SQLite e sincroniza a coleção vetorial no ChromaDB automaticamente.

## 🔗 Documentos de Referência Complementares

Para aprofundar nos ficheiros de configuração específicos:

- 📋 **[Dicionário Completo de Variáveis](./Configs/EnvVariables.md)** — Lista detalhada de todas as chaves do `.env`.

- 📄 **[Estrutura do config.yaml](./Configs/ConfigYaml.md)** — Explicação técnica de cada bloco YAML.

- 🎧 **[Setup do Navidrome](./Configs/Navidrome.md)** — Configuração do Docker Compose e parâmetros da API Subsonic.
