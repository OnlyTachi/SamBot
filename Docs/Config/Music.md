# 🎵 Módulo de Áudio e Música

Este documento detalha o funcionamento do sistema de reprodução musical da **SamBot**, oferecendo um guia práticoe orientações para desenvolvedores.

## 💡 Para Usuários: Como Funciona no Dia a Dia?

O módulo de música da SamBot foi feito para ser simples e intuitivo. Você pode pedir qualquer música por nome ou enviar links de mídia!

### 🌟 Principais Recursos

- **Busca Inteligente:** Pesquise músicas por palavras-chave ou envie URLs diretas.
- **Bibliotecas Pessoais:** O bot se conecta à biblioteca do servidor para tocar arquivos de alta fidelidade e instantaneo
- **Fila Dinâmica:** Adicione, pule, pause e reordene músicas facilmente.
- **Filtros de Áudio:** Aplique efeitos sonoros nas chamadas de voz em tempo real.

---

### 📋 Comandos Mais Usados

| Comando              | O que faz?                                 | Exemplo                       |
| -------------------- | ------------------------------------------ | ----------------------------- |
| `+play <nome/link>`  | Toca uma música ou adiciona à fila.        | `+play Deftones Digital Bath` |
| `+skip`              | Pula para a próxima música da fila.        | `+skip`                       |
| `+stop`              | Para a música e desconecta o bot do canal. | `+stop`                       |
| `+queue`             | Exibe a lista das próximas músicas.        | `+queue`                      |
| `+pause` / `+resume` | Pausa ou retoma a reprodução.              | `+pause`                      |

## 🛠️ Para Desenvolvedores: Arquitetura Técnica

Para quem atua no código do sistema, o módulo de música utiliza uma **arquitetura orientada a eventos e microserviços de áudio**, separando a lógica dos comandos do Discord do processamento pesado de mídia.

```
                           ┌───────────────────────────┐
                           │      Comando do Usuário   │
                           └─────────────┬─────────────┘
                                         │
                                         ▼
                           ┌───────────────────────────┐
                           │   SamBot (Wavelink/Cog)   │
                           └─────────────┬─────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │ Checa `MUSIC_SOURCE_MODE` (.env)           │
                   └──────────┬─────────────────────┬──────────┘
                              │                     │
                              ▼                     ▼
               ┌────────────────────────┐  ┌────────────────────────┐
               │    Fonte Local (Hi-Fi) │  │   Fonte Web (Online)   │
               └──────────┬─────────────┘  └──────────┬─────────────┘
                          │                           │
                          ▼                           ▼
                 [Navidrome / Jellyfin]       [Lavalink Online]
                          │                           │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                           ┌───────────────────────────┐
                           │  Discord Voice Gateway    │
                           └───────────────────────────┘

```

### 1. Motor de Reprodução (`Wavelink`)

- O bot utiliza a biblioteca **Wavelink** (wrapper assíncrono para Python) para se comunicar com o servidor de áudio via WebSockets e REST API.
- Os canais de áudio e filas são gerenciados no estado global do player de cada servidor (`discord.Guild`).

### 2. Fluxo de Decisão de Busca (`MUSIC_SOURCE_MODE`)

Antes de realizar a pesquisa, a engine verifica o parâmetro configurado no ambiente:

1. **`HIBRIDO`:** Realiza uma chamada de busca primeiro no acervo interno. Se houver divergência ou não encontrar resultados, aciona os nós na nuvem.
2. **`LOCAL`:** Restringe as chamadas e consultas exclusivamente ao catálogo interno.
3. **`ONLINE`:** Ignora o acervo privado e delega as buscas diretamente aos nós externos.

## 🔗 Documentações Relacionadas

Para entender em detalhes como o motor de reprodução e a biblioteca local funcionam individualmente, consulte:

- 📡 **[Lavalink](./Audios/Lavalink.md)**: Entenda como funciona o motor de som, os nós internos/externos e a redundância/failover.
- 🎧 **[Navidrome](./Audios/Navidrome.md)**: Detalhes sobre a integração da biblioteca de áudio via API Subsonic.
