# SamBot Internal API

Documentação completa da API interna da **SamBot Core (v3.3.1-beta)**.  
A API provê controle do player de áudio (Lavalink/Navidrome), telemetria em tempo real, fluxo de OAuth2 com Discord, fila assíncrona de download, inspeção de bases de dados (SQLite, ChromaDB, Meilisearch) e editor de configurações dinâmicas em disco.

## 1. Visão Geral & Arquitetura

- **Base URL:** `http://<host>:<port>` (padrão: `http://0.0.0.0:8001`)
- **Protocolos:** HTTP/1.1, HTTP/2 (via reverse-proxy), WebSocket bidirecional (`/ws/bot` e `/api/v1/logs/ws`).
- **Padrão de Resposta:** `application/json; charset=utf-8`.
- **CORS:** Origens permitidas configuráveis em `api.cors_origins` (padrão `http://localhost:3000`).

## 2. Autenticação & Segurança

A API adota dois mecanismos de controle de acesso:

1. **Token Interno do Bot (Header `X-Bot-Token`):**  
   Obrigatório na maioria dos endpoints administrativos e de controle. Validado contra `api.secret_token` ou chave de staff persistida no SQLite.
   ```http
   X-Bot-Token: <SAMBOT_INTERNAL_TOKEN>
   ```
2. **Bearer Token do Discord (Header `Authorization`):**  
   Utilizado nas rotas de sessão do usuário `/api/auth/discord/session` para validar o token OAuth2 oficial retornado pelo Discord.
   ```http
   Authorization: Bearer <DISCORD_ACCESS_TOKEN>
   ```

### Política "Anti-Ghost DJ"

Para executar qualquer comando de player (`PLAY`, `PAUSE`, `SKIP`, `SEEK`, `SET_VOLUME`, `SET_LOOP`, `SHUFFLE`), o usuário requisitante:

- **Não pode ser convidado** (`userId != "usr_guest"`).
- **Deve estar conectado** no mesmo canal de voz onde o bot se encontra ativo no servidor Discord.

## 3. Endpoints REST

### 3.1. Controle do Player & Telemetria (`/api/control`)

#### `GET /api/control/ping-matrix`

Retorna matriz de latência triangular entre SamBot, Navidrome e Internet externa.

- **Autenticação:** `X-Bot-Token`
- **Exemplo de Resposta (200 OK):**

```json
{
  "success": true,
  "sam_ws_discord": 133,
  "internet_external": 14,
  "navidrome": 4,
  "server_time": 1793041284.12
}
```

#### `GET /api/control/status`

Snapshot completo de integridade operacional, hardware e sessão de voz ativa.

- **Query Params:** `guildId` (opcional - filtra a sessão de voz da guilda).
- **Autenticação:** `X-Bot-Token`
- **Exemplo de Resposta (200 OK):**

```json
{
  "status": "ONLINE",
  "version": "3.3.1-beta",
  "bot_user": {
    "name": "Boneco",
    "id": "86957423489320",
    "avatar": "https://cdn.discordapp.com/avatars/..."
  },
  "activeVoiceSession": {
    "channelId": "123456789012345678",
    "channelName": "Geral - Voz",
    "guildId": "801575672232",
    "guildName": "Servidor Oficial",
    "pingMs": 18,
    "bitrateKbps": 384,
    "userCount": 4
  },
  "system": {
    "os": "Linux 6.6.0",
    "python": "3.11.9",
    "cpu_usage_percent": 3.4,
    "ram_used_gb": 1.25,
    "ram_total_gb": 15.6,
    "ram_percent": 8.0
  },
  "telemetry": { ... }
}
```

#### `POST /api/control/player`

Dispara ações diretas sobre o player de áudio via REST.

- **Autenticação:** `X-Bot-Token`
- **Corpo da Requisição:**

```json
{
  "action": "PLAY | ENQUEUE | PAUSE | RESUME | SKIP | SEEK | SET_VOLUME | SET_LOOP | SHUFFLE | CLEAR_QUEUE",
  "payload": {
    "trackId": "subsonic_track_id",
    "position": 120,
    "volume": 80,
    "mode": "OFF | TRACK | QUEUE | PLAYLIST",
    "bitRate": 320
  },
  "guildId": "80141553443532232",
  "userId": "845013123626498"
}
```

---

### 3.2. Autenticação Discord OAuth2 (`/api/auth/discord`)

#### `POST /api/auth/discord/exchange`

Troca o authorization code pelo token oficial do Discord e cruza com a presença do usuário nos canais de voz do bot.

- **Corpo da Requisição:**

```json
{
  "code": "discord_oauth2_authorization_code",
  "redirect_uri": "http://localhost:3000/"
}
```

- **Resposta (200 OK):**

```json
{
  "success": true,
  "token": "access_token_discord",
  "user": {
    "id": "845015655676498",
    "username": "tachi",
    "avatar": "https://cdn.discordapp.com/avatars/...",
    "currentVoiceChannel": {
      "connected": true,
      "id": "123456789012345678",
      "name": "Estúdio A",
      "guildId": "333532432443",
      "guildName": "Servidor de Teste",
      "bitrateKbps": 384,
      "pingMs": 18
    }
  }
}
```

#### `GET /api/auth/discord/session`

Valida o token Bearer persistido no navegador e revalida a presença na chamada de voz.

- **Headers:** `Authorization: Bearer <access_token>`

---

### 3.3. Pipeline de Download & Ingestão (`/api/download`)

#### `POST /api/download/tasks`

Enfileira uma URL externa (YouTube, SoundCloud, Bandcamp) para ser extraída via `yt-dlp`, tagueada com `beets` e escaneada no Navidrome.

- **Autenticação:** `X-Bot-Token`
- **Corpo da Requisição:**

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "requester": {
    "id": "8433322326498",
    "name": "tachi"
  }
}
```

- **Resposta (200 OK):**

```json
{
  "success": true,
  "taskId": "dl_1793041284_a1b2c",
  "url": "https://www.youtube.com/watch?v=...",
  "status": "QUEUED",
  "progress": 5,
  "title": "Aguardando extração...",
  "artist": "Pipeline yt-dlp",
  "logOutput": [
    "[19:01:24] Tarefa dl_1793041284_a1b2c registada na Sam.",
    "[19:01:24] Handshake com worker concluído."
  ],
  "track": null
}
```

#### `GET /api/download/tasks/{task_id}`

Consulta o progresso e logs do worker Node.js para uma tarefa.

- **Autenticação:** `X-Bot-Token`
- **Status Possíveis:** `QUEUED`, `EXTRACTING`, `TAGGING`, `RESCANNING`, `COMPLETED`, `FAILED`.

---

### 3.4. Notificações & Webhooks (`/api/v1`)

#### `POST /api/v1/notifications/promo`

Enfileira um card rico de oferta para envio em canal de servidor ou DM de membro.

- **Autenticação:** `X-Bot-Token`
- **Corpo da Requisição:**

```json
{
  "target_type": "server | dm | all",
  "target_id": "123456789012345678",
  "titulo": "Placa de Vídeo RTX 4070 Super",
  "preco": 3899.9,
  "loja": "Kabum",
  "link": "https://...",
  "imagem_url": "https://..."
}
```

#### `GET /api/v1/webhooks` | `POST /api/v1/webhooks` | `DELETE /api/v1/webhooks/{webhook_id}`

Gerencia webhooks HTTP externos inscritos nos eventos do bot (`promo_alert`, `price_drop`).

#### `POST /api/v1/webhooks/{webhook_id}/test`

Dispara payload de teste (`event: ping`) para o webhook cadastrado.

---

### 3.5. Bases de Dados & RAG (`/api/v1/db`)

- **`GET /api/v1/db/sqlite/tables`**: Lista tabelas do SQLite (`users`, `knowledge`, `config`, `prompts`) com contagem total de registros.
- **`GET /api/v1/db/sqlite/table/{table_name}?page=1&limit=25&search=termo`**: Retorna dados paginados com decodificação automática de JSONs persistidos.
- **`GET /api/v1/db/meili/stats`**: Status e volumetria do índice `ofertas` no Meilisearch.
- **`GET /api/v1/db/meili/ofertas?query=termo&limit=20`**: Consulta direta com ordenação por menor preço.
- **`GET /api/v1/db/chroma/collections`**: Lista coleções vetoriais ativas (`fatos_usuario`, `resumos_diarios`, `rotas_intencoes`) e modo de execução.
- **`GET /api/v1/db/chroma/collection/{collection_name}`**: Documentos, metadados e IDs persistidos na coleção.
- **`POST /api/v1/db/chroma/query-test`**: Teste de busca semântica em tempo real para auditoria de distância e threshold de similaridade.

---

### 3.6. Arquivos & Configuração Dinâmica (`/api/v1/files`)

- **`GET /api/v1/files/tree`**: Árvore restrita de arquivos editáveis (`configs`, `prompts`, `knowledge`, `persistence`).
- **`GET /api/v1/files/read?path=Data/Prompts/padrao.txt`**: Leitura de texto com proteção contra _path traversal_.
- **`POST /api/v1/files/save`**: Gravação com validação de sintaxe (JSON/YAML) e gatilho de sincronização a quente (`hot_reload` ou `reindex_routes` no ChromaDB).

---

### 3.7. Logs & Métricas (`/api/v1/logs`)

- **`GET /api/v1/logs/tail?log_type=general|errors&lines=100`**: Últimas linhas do arquivo de log em disco.
- **`GET /api/v1/logs/stats?userId=<id>`**: Métricas agregadas de rede (ping do bot, estabilidade) e contribuições (músicas adicionadas, plays comunitários, minutos ouvidos).

## 4. WebSockets em Tempo Real

### 4.1. WebSocket Principal do Bot (`/ws/bot`)

Canal bidirecional utilizado pelo Dashboard para controle, handshake e recebimento de atualizações de estado do player.

#### Handshake Inicial (Cliente -> Servidor)

```json
{
  "op": "HANDSHAKE",
  "client": "SamBotMusicboard_WebUI",
  "guildId": "804464545457112232",
  "token": "sb_tok_live_..."
}
```

**Resposta do Servidor (`ACK`):**

```json
{
  "op": "ACK",
  "status": "AUTHENTICATED",
  "guildId": "80155555112232",
  "version": "3.3.1-beta"
}
```

#### Envio de Comandos (Cliente -> Servidor)

```json
{
  "op": "COMMAND",
  "data": {
    "action": "PLAY | PAUSE | RESUME | SKIP | SEEK | SET_VOLUME | SET_LOOP | SHUFFLE | CLEAR_QUEUE | REMOVE_QUEUE | REORDER_QUEUE",
    "payload": {
      "trackId": "navidrome_song_id",
      "position": 45,
      "volume": 75,
      "mode": "TRACK | QUEUE | OFF",
      "from": 2,
      "to": 0
    },
    "userId": "84533545626498",
    "guildId": "801411111167112232"
  },
  "traceId": "CMD_1793041299"
}
```

#### Eventos Broadcast do Player (Servidor -> Cliente)

Disparado pelo Maestro sempre que uma música inicia, pausa, a fila é alterada ou o player avança:

```json
{
  "op": "EVENT",
  "event": "PLAYER_STATE_UPDATE",
  "guildId": "8014155878882232",
  "data": {
    "isPlaying": true,
    "isPaused": false,
    "volume": 80,
    "position": 34,
    "repeatMode": "OFF",
    "currentTrack": {
      "id": "184920",
      "title": "contando os segundos pra te ver",
      "artist": "Artista",
      "album": "Album",
      "duration": 195,
      "source": "NAVIDROME",
      "bitRate": 320,
      "artwork": "/api/navidrome/cover?id=184920"
    },
    "queue": [ ... ],
    "voiceSession": {
      "id": "123456789",
      "name": "Geral",
      "userCount": 3,
      "bitrateKbps": 384,
      "pingMs": 18,
      "connected": true
    }
  }
}
```

---

### 4.2. WebSocket de Streaming de Logs (`/api/v1/logs/ws`)

Transmite linhas de log ao vivo à medida que são gravadas no disco pelo backend.

- **Query Params:** `?log_type=general|errors&token=<SAMBOT_INTERNAL_TOKEN>`
- **Mensagens:**
  - Histórico inicial: `{"type": "history", "message": "[2026-10-26 19:01:24] ..."}`
  - Novas linhas (streaming): `{"type": "log", "log_type": "general", "message": "..."}`
