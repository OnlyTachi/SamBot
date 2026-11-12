# 🎵 Motor de Áudio: Guia do Lavalink & Modos de Reprodução

Este documento detalha a arquitetura, configuração e operação do **Lavalink** no ecossistema da **SamBot**, abrangendo os modos **LOCAL** e **ONLINE**, balanceamento de nós, arquivos de configuração de referência e a filosofia de uso da biblioteca privada via Navidrome.

## 💡 Filosofia do Autor: Por que priorizar o Navidrome?

> **Nota do Desenvolvedor:**
> Manter um servidor de Lavalink próprio tocando diretamente do YouTube tornou-se uma dor de cabeça contínua. Entre constantes atualizações de travas da plataforma, necessidade recorrente de exportar novos _cookies_ de navegador, dependência de plugins externos em Java que quebram com frequência, geração de _poTokens_ e bloqueios de IP (_Rate Limits_ / Erro 429), a estabilidade nunca durava muito tempo.

> Como eu já possuo um fluxo automatizado que faz o download organizado de todas as minhas músicas diretamente no servidor (**Navidrome**), decidi simplificar a arquitetura: o bot toca o catálogo local, de forma instantânea e simples.

> **A escolha é livre:** Se você preferir configurar o seu próprio Lavalink com plugins de bypass para o YouTube (`youtube-plugin`, rotação de IPv6 ou cookies), a estrutura suporta normalmente, mas a manutenção dessas chaves e tokens fica sob sua responsabilidade. A rota mais recomendada e sem estresse continua sendo a biblioteca local (**Navidrome**) ou o uso de servidores públicos gerenciados no modo **`ONLINE`**.

## 🔀 Modos de Operação

A SamBot suporta dois modos estritos e mutuamente exclusivos, configurados no `.env` e no `config.yaml`:

| Modo         | Origem das Músicas                 | O que acontece por baixo dos panos?                                                                                                           | Cenário de Uso Recomendado                                                                 |
| ------------ | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **`LOCAL`**  | **Biblioteca Privada (Navidrome)** | O bot consulta o catálogo via API Subsonic. As faixas são transmitidas localmente pelo Lavalink.                                              | HomeLabs, redes locais/Tailscale, servidores com acervo próprio em FLAC/MP3.               |
| **`ONLINE`** | **Internet / Nuvem Pública**       | Ignora o acervo local e pesquisa diretamente em serviços web públicos através da lista de nós remotos configurados em `music.lavalink.nodes`. | Servidores públicos que priorizam tocar qualquer link de fora sem hospedar acervo próprio. |

> ⚠️ **Por que o Modo Híbrido foi Descontinuado?**
> Nas versões legadas, tentar misturar faixas do Navidrome e do YouTube na mesma fila gerava quebra de ciclo de vida no Wavelink (`Error 500 / Failed to decode track`), já que o socket de voz do Discord fica fisicamente atrelado ao nó Lavalink que iniciou a chamada. Além disso, alternar servidores durante a reprodução forçava reconexões que provocavam engasgos perceptíveis no áudio.

## 🛠️ 1. Configuração do Modo LOCAL (`application.local.yml`)

No modo local, o Lavalink opera enxuto: **todas as fontes de scraping da internet são desligadas** para economizar memória e evitar erros desnecessários, mantendo ativas apenas as fontes `http` (necessária para os streams da API Subsonic do Navidrome) e `local`.

```yaml
server:
  port: 2333
  address: 0.0.0.0
  http2:
    enabled: true # Melhora o throughput para múltiplos streams simultâneos

lavalink:
  server:
    password: "youshallnotpass" # Idêntica à LAVALINK_PASSWORD configurada no SamBot
    sources:
      # Desativa fontes da web que demandam scraping ou tokens externos
      youtube: false
      soundcloud: false
      bandcamp: false
      twitch: false
      vimeo: false
      nico: false
      # Fontes estritamente necessárias para a rede interna
      http: true # Obrigatório para receber os streams do Navidrome
      local: true # Permite reproduzir arquivos montados em volume

    # Filtros DSP suportados (+filtro nightcore, bassboost, volume, etc.)
    filters:
      volume: true
      equalizer: true
      timescale: true
      channelMix: true
      waveform: true

    bufferDurationMs: 400 # Buffer em RAM reduzido para reprodução local estável
    frameBufferDurationMs: 5000 # Pré-carregamento de 5s
    trackStuckThresholdMs: 10000
    useSeekGhosting: true
    playerUpdateInterval: 5

metrics:
  prometheus:
    enabled: false

logging:
  file:
    path: ./logs/lavalink.log
  level:
    root: INFO
    lavalink: INFO
```

## 🌐 2. Configuração do Modo ONLINE com Plugin (`application.online.yml`)

Para quem deseja hospedar um Lavalink próprio tocando do YouTube, o Lavalink v4 exige o uso do plugin modular oficial `youtube-plugin`.

```yaml
server:
  port: 2333
  address: 0.0.0.0

lavalink:
  plugins:
    # Plugin oficial do YouTube para Lavalink v4
    - dependency: "dev.arbjerg.lavalink.libraries.v4:youtube-plugin:1.11.4"
      repository: "https://maven.lavalink.dev/releases"

  server:
    password: "youshallnotpass"
    sources:
      youtube: false # Desativado aqui pois o plugin assume o controle
      soundcloud: true
      bandcamp: true
      twitch: true
      vimeo: true
      nico: false
      http: true
      local: false

    filters:
      volume: true
      equalizer: true
      timescale: true
      channelMix: true
      waveform: true

    bufferDurationMs: 1000 # Buffer ampliado para absorver oscilações externas
    frameBufferDurationMs: 10000 # 10s de pré-carregamento em cache
    trackStuckThresholdMs: 12000

# Parâmetros de autenticação e clientes do YouTube
plugins:
  youtube:
    enabled: true
    allowSearch: true
    allowDirectVideoIds: true
    allowDirectPlaylistIds: true
    clients:
      - MUSIC
      - ANDROID_VR
      - WEB
      - TVHTML5EMBEDDED

    # OPÇÃO 1: Autenticação via Cookies (Recomendado para VPS)
    # Exporte os cookies do YouTube em formato Netscape e monte o arquivo no container
    # cookie: "cookies.txt"

    # OPÇÃO 2: Rotação de IPv6 (Para servidores com bloco /64 dedicado)
    # ratelimit:
    #   ipBlocks: ["2a01:4f8:xxxx:xxxx::/64"]
    #   strategy: "RotateOnBan" # RotateOnBan | LoadBalance | NanoSwitch
    #   searchTriggersFail: true
    #   retryLimit: 3

metrics:
  prometheus:
    enabled: false

logging:
  level:
    root: INFO
    lavalink: INFO
```

## 🛡️ 3. Redundância e Failover no `config.yaml`

No modo `ONLINE`, a SamBot suporta cadastro em pool de múltiplos nós de áudio. Se um servidor remoto cair, ele entra em quarentena (_cooldown_ de 1 hora) e a fila de chamadas comuta automaticamente para o próximo nó saudável:

```yaml
music:
  mode: "ONLINE" # Opções estritas: ONLINE | LOCAL

  lavalink:
    # Nó local (usado caso mode seja LOCAL)
    local:
      host: "127.0.0.1"
      port: 2333
      password: "youshallnotpass"
      secure: false

    # Pool de nós remotos com failover automático (usado se mode for ONLINE)
    nodes:
      - name: "Node-Publico-Principal"
        host: "lavalink.exemplo.com"
        port: 443
        password: "sua_senha_aqui"
        secure: true

      - name: "Node-Reserva-Secundario"
        host: "lavalink-backup.exemplo.com"
        port: 443
        password: "sua_senha_aqui"
        secure: true
```

## 🔗 Próximos Passos & Integrações

- 🎧 **[Navidrome & API Subsonic](./Navidrome.md)**: Guia completo de configuração do servidor local de áudio e rotação de senhas com salt MD5.

- ⚙️ **[Guia Geral de Configuração](/Docs/CONFIG.md)**: Parâmetros do `.env` e variáveis do bot.
