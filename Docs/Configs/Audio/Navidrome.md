# 🎧 Serviço de Biblioteca de Áudio

Este documento detalha a arquitetura, configuração via Docker Compose, protocolos de segurança e fluxos de integração da biblioteca privada **Navidrome** com a **SamBot** através da **API Subsonic**.

## 💡 O que é e por que utilizamos o Navidrome?

O **Navidrome** é o servidor de streaming privado responsável por armazenar, organizar e servir os arquivos de áudio em altíssima qualidade (Hi-Fi / FLAC / MP3) para a SamBot.

Em vez de depender de APIs ou nós remotos externos sujeitos a instabilidades e bloqueios de IP, o bot conecta-se diretamente à **API Subsonic** nativa do Navidrome. Isso possibilita buscas instantâneas e streaming de baixa latência na rede local, sem consumo desnecessário de banda de internet externa.

## 🐳 1. Modelo de Infraestrutura (`docker-compose.yml`)

O ecossistema recomendado executa o Navidrome junto a ferramentas auxiliares de gerenciamento e automação de acervo musical (como Lidarr e Spindle, ambas opcionais):

```yaml
services:
  navidrome:
    image: deluan/navidrome:latest
    container_name: navidrome
    user: 1000:1000 # Ajuste para o UID:GID do seu usuário local
    restart: unless-stopped
    ports:
      - "4533:4533"
    environment:
      ND_SCANSCHEDULE: "1h"
      ND_LOGLEVEL: "info"
      ND_SESSIONTIMEOUT: "24h"
      ND_BASEURL: "https://seu-dominio-ou-ip.com:4533"
      ND_PLUGINS_ENABLED: "true"
      ND_PLUGINS_AUTORELOAD: "true"
      ND_LASTFM_ENABLED: "true"
      ND_LASTFM_SECRET: "SEU_LASTFM_SECRET_AQUI"
      ND_LASTFM_APIKEY: "SUA_LASTFM_API_KEY_AQUI"
    volumes:
      - "./data/navidrome:/data"
      - "/caminho/para/suas/musicas:/music:ro"

  # (Opcional) Ferramenta para gerenciar e sincronizar playlists/scripts
  spindle:
    image: heywoodlh/spindle:latest
    container_name: spindle
    restart: unless-stopped
    privileged: true
    ports:
      - "8282:8282"
    volumes:
      - "./spindle-data:/app/data"
    environment:
      - SPINDLE_SHARED_SECRET=sua_chave_secreta_aqui
      - TZ=America/Sao_Paulo

  # (Opcional) Gerenciador automático de álbuns e discografias
  lidarr:
    image: lscr.io/linuxserver/lidarr:latest
    container_name: lidarr
    restart: unless-stopped
    ports:
      - "8686:8686"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/Sao_Paulo
    volumes:
      - "./lidarr-config:/config"
      - "/caminho/para/suas/musicas:/music"
```

> ⚠️ **Atenção:** O diretório montado em `/music` deve possuir permissões de leitura adequadas para o UID do container.
> 📖 **Documentação Oficial:** Para obter detalhes sobre parâmetros avançados de ambiente, acesse a [Documentação do Navidrome](https://www.navidrome.org/docs/).

## 🔒 2. Protocolo de Autenticação e Integração Subsonic

O Navidrome expõe nativamente a API compatível com Subsonic em sua raiz na porta `4533`, dispensando rotas ocultas.

### A. Autenticação Segura (Subsonic v1.16.1+)

Para cumprir as diretrizes de segurança, **a senha nunca deve transitar limpa pela rede**. O serviço interno do bot gera um _salt_ aleatório e calcula o hash MD5 da senha concatenada para cada chamada assíncrona:

```python
import hashlib
import secrets

def build_subsonic_params(username: str, password: str) -> dict:
    salt = secrets.token_hex(6)
    token = hashlib.md5((password + salt).encode("utf-8")).hexdigest()
    return {
        "u": username,
        "t": token,
        "s": salt,
        "v": "1.16.1",
        "c": "SamBot",
        "f": "json"
    }

```

### B. Endpoints Principais Consumidos pelo Bot

- **Validação de Conectividade (`ping.view`):**
  - **Rota:** `GET /rest/ping.view`
  - Executa a checagem física de autenticação e integridade do servidor durante o boot do bot ou no painel do launcher.
- **Busca de Conteúdo (`search3.view`):**
  - **Rota:** `GET /rest/search3.view?query={termo}`
  - Realiza varreduras textuais na biblioteca retornando correspondências de faixas, artistas e coleções.
- **Stream de Áudio Direto (`stream.view`):**
  - **Rota:** `GET /rest/stream.view?id={song_id}`
  - Gera a URL de fluxo direto autenticada que o nó Lavalink local (`http: true`) consome para decodificar e transmitir ao Discord.

### C. Validação Rápida via Navegador

Antes de configurar o bot, teste se a API está respondendo diretamente pelo navegador:

```text
http://IP_DO_SEU_SERVIDOR:4533/rest/ping.view?u=SEU_USUARIO&p=SUA_SENHA&v=1.16.1&c=teste&f=json
```

**Resposta esperada (`JSON`):**

```json
{
  "subsonic-response": {
    "status": "ok",
    "version": "1.16.1"
  }
}
```

## ⚙️ 3. Configuração no `.env` do Bot

Copie a URL base (sem o sufixo `/rest/...`) para as variáveis de ambiente da SamBot:

```env
# Define a busca e reprodução (LOCAL ou HIBRIDO)
MUSIC_SOURCE_MODE=LOCAL

# Credenciais do Navidrome (Subsonic API)
NAVIDROME_URL="http://192.168.1.100:4533"
NAVIDROME_USER="sambot_player"
NAVIDROME_PASSWORD="sua_senha_segura"
```

> ⚠️ **Atenção:** O usuário configurado precisa ter a opção **"Allow Subsonic access"** explicitamente habilitada no painel administrativo web do Navidrome.

## 📥 4. Alimentação e Download do Acervo

O ecossistema dispõe de dois métodos para popular e organizar o diretório de faixas (`/music`):

### A. Linha de Comando Manual (`yt-dlp`)

Ideal para importar playlists e discografias mantendo a estrutura de tags e pastas padronizada (`Artista/[Álbum]/Música`):

```bash
alias yt='yt-dlp --cookies "$HOME/cookies.txt" --js-runtimes node --remote-components ejs:github -x --audio-format mp3 --audio-quality 0 --embed-thumbnail --add-metadata --download-archive "$HOME/caminho/para/Navidrome/music/historico.txt" -o "$HOME/caminho/para/Navidrome/music/%(artist,uploader)s/[%(album,playlist)s]/%(title)s.%(ext)s"'

```

> ℹ️ **Nota:** A manutenção de cookies, diretórios locais e chaves para extração direta via YouTube é de responsabilidade individual do mantenedor.

### B. Pipeline Assíncrono via API SamBot (`/api/download/tasks`)

Na versão `v3.5.0-beta`, requisições enviadas ao endpoint de download são delegadas para um worker em segundo plano (`YT_WORKER_URL`, porta `4000`). O worker processa o áudio, aplica os metadados ID3 e aciona o scan automático da biblioteca no Navidrome para disponibilização imediata.

## 🔗 Documentação Relacionada

- 📡 **[Motor Lavalink & Modos de Áudio](/Docs/Configs/Audio/Lavalink.md):** Configuração do nó local e nós remotos com failover.
- 🎛️ **[Comandos de Áudio do Discord](/Docs/Modules/Audio.md):** Utilização do `/play`, gestão de filas e equalização.
- 🌐 **[API Interna & WebSockets](/Docs/Services/API.md):** Endpoints de controle remoto do player e métricas de latência (`ping-matrix`).
