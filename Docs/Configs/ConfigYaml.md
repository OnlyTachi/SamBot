# 📄 Estrutura de Configuração (`config.yaml`)

O arquivo `config.yaml` gerencia o comportamento operacional da **SamBot**, parâmetros de rede, prioridades na esteira de IA e limites de ferramentas.

## 🧩 Estrutura Completa de Referência

```yaml
# ==========================================
# 1. PARÂMETROS GERAIS DO BOT
# ==========================================
bot:
  prefix: "+"
  debug_mode: false
  owner_id: 123456789012345678

# ==========================================
# 2. SERVIÇOS E MICROSSERVIÇOS (ServiceManager)
# ==========================================
services:
  api:
    enabled: false
    host: "0.0.0.0"
    port: 8080
    cors_origins:
      - "*"
  telegram:
    enabled: false
    channels:
      - "promocoes_hardware"
      - "achados_gamer"
      - -1001234567890
  notifications:
    enabled: false
    rate_limit_pause_seconds: 5.0
  price_tracker:
    enabled: false
    check_interval_hours: 6

# ==========================================
# 3. BANCO DE DADOS E PERSISTÊNCIA
# ==========================================
database:
  sqlite_path: "data/database.db"
  sqlite_timeout: 30.0

# ==========================================
# 4. MOTOR DE ÁUDIO E MÍDIA
# ==========================================
music:
  mode: "ONLINE" # Opções estritas: ONLINE | LOCAL
  volume_default: 80
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
      - name: "Node-Backup-Nuvem"
        host: "lavalink2.exemplo.com"
        port: 443
        password: "sua_senha_aqui"
        secure: true

# ==========================================
# 5. ESTEIRA COGNITIVA & MODELOS DE LINGUAGEM
# ==========================================
llm:
  chain_order:
    - "gemini"
    - "groq"
    - "ollama"
  semantic_router:
    enabled: true
    similarity_threshold: 0.74
    hash_validation: true
  models:
    gemini: "gemini-2.0-flash"
    groq: "llama-3.1-8b-instant"
    openrouter: "meta-llama/llama-3.3-70b-instruct:free"
    deepseek: "deepseek-chat"
    mistral: "mistral-small-latest"
  ollama:
    remote_url: "http://100.100.100:11434"
    local_url: "http://host.docker.internal:11434"
    models:
      smart: "phi3.5:latest"
      fast: "qwen2.5:1.5b"
      embed: "nomic-embed-text"

# ==========================================
# 6. FERRAMENTAS E INTEGRAÇÕES EXTERNAS
# ==========================================
tools:
  anime:
    jikan:
      timeout: 10.0
      top_limit: 5
    tracemoe:
      similarity_cutoff: 0.85
  shopping:
    pelando:
      timeout: 8.0
      coupon_limit: 5
    mercadolivre:
      timeout: 8.0
      search_limit: 5
  weather:
    open_meteo:
      timeout: 6.0
      temperature_unit: "celsius"
```

## 🔍 Módulos de Configuração

### `bot`

Define as preferências visuais e operacionais fundamentais da sessão Discord, incluindo o prefixo textual de fallback para comandos legados e mensagem de presença.

### `services`

Controla os ciclos de vida gerenciados pelo `ServiceManager`. Cada bloco pode ser desativado individualmente definindo `enabled: false`, permitindo que instâncias de teste subam sem dependências complexas (como cliente Telegram ou rastreadores periódicos).

### `music`

Controla o direcionamento do motor de áudio. A chave `mode` opera sob valores mutuamente exclusivos (`ONLINE` ou `LOCAL`). No modo `ONLINE`, a lista `nodes` fornece redundância automática com isolamento em caso de falha.

### `llm`

Define a esteira de execução dos modelos de linguagem:

- `chain_order`: Sequência prioritária da cascata de failover.
- `semantic_router.similarity_threshold`: Limiar semântico para ativação de rotas e ferramentas (calibrado em **0.74**).
- `ollama`: Conexões com instâncias locais ou remotas
