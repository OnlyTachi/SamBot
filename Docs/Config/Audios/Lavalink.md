## 🎵 Guia de Mídia e Balanceamento de Áudio (Lavalink)

Este documento explica como o bot processa, busca e toca músicas no Discord, cobrindo a arquitetura de redes, fontes de mídia e o sistema inteligente de balanceamento.

### 🧩 O que é o Lavalink?

O **Lavalink** é o "motor de som" do bot. Em vez do bot processar o áudio diretamente na sua aplicação principal (o que consumiria muita memória), ele delega essa função ao Lavalink, que baixa, decodifica e transmite a música para as chamadas de voz com alta qualidade e sem travamentos.

---

### 🌐 Conexão Interna vs. Externa

A SamBot utiliza uma estratégia **mista** para conectar seus servidores de som, combinando a segurança da rede interna com a capacidade da nuvem:

```
                  ┌──────────────────────────────┐
                  │      SamBot (Aplicação)      │
                  └──────────────┬───────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
                 ▼                               ▼
    ┌─────────────────────────┐     ┌─────────────────────────┐
    │     Lavalink LOCAL      │     │    Lavalinks ONLINE     │
    │      (Rede Interna)     │     │        (Nuvem)          │
    ├─────────────────────────┤     ├─────────────────────────┤
    │  • Toca mídia própria   │     │  • Toca fontes da Web   │
    │  • Via subsonic         │     │  • Failover automático  │
    │  • Zero uso de internet │     │  • Múltiplos nós/hosts  │
    └─────────────────────────┘     └─────────────────────────┘

```

#### 1. Lavalink Local (Interno)

- **Como funciona:** Roda no mesmo servidor ou na mesma rede privada do bot (usando **Docker** ou IP direto da VPN/Tailscale).
- **Principal utilidade:** Tocar coleções de áudio próprias gravadas nas bibliotecas locais (**Navidrome** e **Jellyfin**).
- **Vantagem:** Economiza banda de internet, não depende de conexões externas e oferece respostas de baixíssima latência.

_Obs: Caso queira configurar lavalink local para tocar diretamente do youtube, fique por conta propria configurar ele, como eu baixo minhas playlistm nao fiz a configuracao dos cookies e afins. Abaixo esta a linha de comando que uso pra baixar musica ou playlist do youtube_

```bash
alias yt='yt-dlp --cookies "$HOME/cookies.txt" --js-runtimes node --remote-components ejs:github -x --audio-format mp3 --audio-quality 0 --embed-thumbnail --add-metadata --download-archive "$HOME/HomeLab/Navidrome/music/historico.txt" -o "$HOME/HomeLab/Navidrome/music/%(artist,uploader)s/[%(album,playlist)s]/%(title)s.%(ext)s"'
```

#### 2. Lavalink Online (Externo / Nuvem)

- **Como funciona:** Conecta-se a nós (nodes) do Lavalink hospedados na nuvem através da internet segura (HTTPS/WSS).
- **Principal utilidade:** Processar e transmitir conteúdos buscados em serviços públicos da internet.
- **Vantagem:** Isola a rede interna e permite adicionar múltiplos servidores de apoio. Se um servidor da nuvem cair, o bot continua funcionando com os outros.

---

### 🔀 Como funciona o Balanceamento e Modos de Mídia

O bot possui um sistema de decisão configurável pela variável `MUSIC_SOURCE_MODE` no arquivo `.env`. Esse parâmetro define como e onde o bot deve priorizar a busca e execução das músicas:

| Modo (`MUSIC_SOURCE_MODE`) | Onde ele busca primeiro?   | Como funciona o fluxo?                                                                                                                                      | Para quem/quando serve?                                                                                      |
| -------------------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **`HIBRIDO`** _(Padrão)_   | **Rede Local (Navidrome)** | Busca primeiro no acervo interno. Se a música não for encontrada no servidor local, ele aciona automaticamente os servidores **Online** para buscar na web. | **Uso Recomendado.** Maximiza a velocidade e a economia de dados, sem deixar de tocar o que o usuário pedir. |
| **`LOCAL`**                | **Rede Local Apenas**      | Toca exclusivamente os áudios hospedados nas bibliotecas do servidor (**Navidrome/Jellyfin**). Desativa conexões para a web.                                | Ideal para ambientes offline, redes corporativas restritas ou conservação estrita de banda.                  |
| **`ONLINE`**               | **Internet / Nuvem**       | Ignora as bibliotecas locais e faz buscas diretamente nos provedores públicos da web.                                                                       | Indicado quando a biblioteca interna está desativada ou o foco é estritamente conteúdo da internet.          |

---

### 🛡️ Tolerância a Falhas e Balanceamento de Nós (Nodes)

Nos servidores online, a SamBot permite registrar uma lista de hosts separados por vírgula no `.env`:

```env
LAVALINK_ONLINE_HOSTS=node1.servidor.com, node2.servidor.com
```

- **Distribuição de Carga:** Quando o bot entra em vários canais de voz ao mesmo tempo, ele distribui a reprodução entre os servidores cadastrados disponíveis.
- **Redundância (Failover):** Se um dos servidores de som na nuvem oscilar, cair ou for desligado para manutenção, o bot redireciona a conexão para o próximo nó ativo da lista sem derrubar a experiência do usuário.
