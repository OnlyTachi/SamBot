# 🎧 Serviço de Biblioteca de Áudio

Este documento cobre a arquitetura, configuração e fluxos de integração da nossa biblioteca de áudio local com a **SamBot** através da **API Subsonic**.

## 💡 O que é e por que usamos o Navidrome?

O **Navidrome** é o servidor de streaming privado responsável por armazenar, organizar e servir os arquivos de áudio em altíssima qualidade (Hi-Fi) para a SamBot.

Em vez de depender de APIs externas de streaming para tocar arquivos da rede local, o bot utiliza a **API Subsonic** do Navidrome para fazer buscas instantâneas e tocar conteúdos de forma eficiente e sem consumo desnecessário de internet.

### 1. Modelo de Infraestrutura (`docker-compose.yml`)

O ecossistema recomendado utiliza o Navidrome junto a ferramentas auxiliares de gerenciamento de acervo (como Lidarr e Spindle, que sao totalmente opcionais).

```yaml
services:
  navidrome:
    image: deluan/navidrome:latest
    user: 1000:1000
    ports:
      - "4533:4533"
    restart: unless-stopped
    environment:
      ND_PLUGINS_ENABLED: "true"
      ND_PLUGINS_AUTORELOAD: "true"
      ND_LASTFM_ENABLED: "true"
      ND_LASTFM_SECRET: "SEU_LASTFM_SECRET_AQUI"
      ND_LASTFM_APIKEY: "SUA_LASTFM_API_KEY_AQUI"
      ND_BASEURL: "https://seu-dominio-ou-ip.com:4533"
    volumes:
      - "./data:/data"
      - "./music:/music:ro"

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

  lidarr:
    image: lscr.io/linuxserver/lidarr:latest
    container_name: lidarr
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/Sao_Paulo
    ports:
      - "8686:8686"
    volumes:
      - "./lidarr-config:/config"
      - "./music:/music"
```

> 📖 **Documentação Oficial:** Para obter detalhes sobre parâmetros avançados, acesse a [Documentação do Navidrome](https://www.navidrome.org/docs/).

---

### 📥 2. Baixando Playlists e Músicas Localmente

Para alimentar a pasta de músicas (`/music`) organizadamente para o Navidrome, você pode usar a seguinte linha de comando (utilizando `yt-dlp`):

```bash
alias yt='yt-dlp --cookies "$HOME/cookies.txt" --js-runtimes node --remote-components ejs:github -x --audio-format mp3 --audio-quality 0 --embed-thumbnail --add-metadata --download-archive "$HOME/caminho/para/Navidrome/music/historico.txt" -o "$HOME/caminho/para/Navidrome/music/%(artist,uploader)s/[%(album,playlist)s]/%(title)s.%(ext)s"'

```

> ℹ️ **Nota:** A configuração de cookies, pastas e autenticação do motor do Lavalink Online/YouTube para reproduções diretas da internet é de responsabilidade individual do mantenedor. O uso do download direto mantém a biblioteca local organizada e rápida.

## Configuração da API Subsonic

O Navidrome expõe nativamente a API compatível com o Subsonic na sua rota raiz, dispensando URLs escondidas.

### 1. Estrutura da URL

O endpoint base utilizado pelo bot é o **IP/Domínio e porta** da interface do Navidrome:

```text
http://IP_DO_SEU_SERVIDOR:4533

```

_(Caso utilize domínio ou proxy reverso com SSL, use `[https://seu-dominio.com](https://seu-dominio.com)`)_.

---

### 2. Validação Rápida de Conectividade

Antes de configurar o bot, é possível testar se a API do Navidrome está respondendo via navegador:

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

---

### 3. Variáveis de Ambiente (`.env`)

Copie a **URL base** (sem o sufixo `/rest/...`) para as variáveis de ambiente da SamBot, pois o manipulador interno de buscas completa as rotas automaticamente:

```env
# Define a busca no acervo local como prioridade
MUSIC_SOURCE_MODE=HIBRIDO

# Credenciais do Navidrome (Subsonic API)
NAVIDROME_URL=http://192.168.1.100:4533
NAVIDROME_USER=seu_usuario_aqui
NAVIDROME_PASSWORD=sua_senha_aqui

```

> ⚠️ **Atenção:** O usuário configurado no `.env` precisa ter a opção **"Allow Subsonic access"** habilitada nas suas permissões dentro do painel administrativo do Navidrome.
