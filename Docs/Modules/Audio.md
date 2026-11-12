# 🎵 Módulo de Áudio e Entretenimento Musical

O módulo de áudio da SamBot foi construído sobre a arquitetura assíncrona **Wavelink/Lavalink**, integrando controles híbridos (comandos com prefixo `+` e comandos slash `/`), equalização e filtros em tempo real, persistência de playlists individuais e interface interativa com botões no Discord.

## 🎛️ 1. Comandos Disponíveis

### 1.1. Controles Básicos & Fila (Comandos Híbridos)

Estes comandos funcionam tanto utilizando o prefixo padrão configurado (ex.: `+play`) quanto através de slash commands (`/play`).

| Comando               | Tipo        | Descrição                                                         | Exemplo de Uso                |
| :-------------------- | :---------- | :---------------------------------------------------------------- | :---------------------------- |
| `+play <busca/link>`  | **Híbrido** | Busca e enfileira faixas individuais ou playlists completas.      | `+play Deftones Digital Bath` |
| `+skip` (ou `+pular`) | **Híbrido** | Pula a faixa atual e avança para a próxima da fila.               | `+skip`                       |
| `+pause` / `+resume`  | **Híbrido** | Alterna entre pausar e retomar a execução da faixa atual.         | `+pause`                      |
| `+stop` (ou `+leave`) | **Híbrido** | Interrompe o áudio, limpa toda a fila e desconecta o bot da call. | `+stop`                       |
| `+queue` (ou `+fila`) | **Híbrido** | Exibe as faixas enfileiradas com paginação automática.            | `+queue`                      |
| `+nowplaying` (`+np`) | **Híbrido** | Exibe detalhes da música em execução com barra de progresso.      | `+nowplaying`                 |
| `+shuffle`            | **Híbrido** | Embaralha aleatoriamente as músicas presentes na fila.            | `+shuffle`                    |
| `+volume [0-100]`     | **Híbrido** | Ajusta o ganho de volume do player em tempo real.                 | `+volume 80`                  |

### 1.2. Filtros e Manipulação Avançada (Slash Commands `/`)

Comandos especializados que operam sobre os processadores DSP do nó Lavalink:

| Comando Slash | Parâmetros | Descrição                                                                                                                 | Exemplo                    |
| :------------ | :--------- | :------------------------------------------------------------------------------------------------------------------------ | :------------------------- |
| `/filtro`     | `efeito`   | Aplica curvas de equalização e alteração de tom/velocidade: `Nightcore`, `Vaporwave`, `Bassboost` ou `Desativar Filtros`. | `/filtro efeito:Nightcore` |
| `/seek`       | `segundos` | Salta a reprodução para a marca temporal especificada.                                                                    | `/seek segundos:120`       |
| `/remove`     | `numero`   | Remove cirurgicamente uma faixa da fila pelo seu índice numérico.                                                         | `/remove numero:3`         |
| `/skipto`     | `posicao`  | Pula diretamente para a faixa selecionada, descartando as anteriores.                                                     | `/skipto posicao:5`        |

### 1.3. Sistema de Playlists Pessoais

Permite aos usuários manter coleções permanentes salvas na base de dados para execução instantânea:

- `/playlist salvar <nome>`: Captura a faixa atual ou todas as faixas da fila do servidor e as salva sob o nome informado.
- `/playlist carregar <nome>`: Injeta todas as músicas da playlist salva na fila atual da chamada.
- `/playlist listar`: Exibe um resumo de todas as playlists cadastradas pelo autor do comando.
- `/playlist apagar <nome>`: Exclui permanentemente a playlist correspondente.

## 🎚️ 2. Painel Interativo por Botões (`PlayerView`)

Sempre que uma nova faixa inicia sua execução, a SamBot despacha uma mensagem de incorporação com o painel interativo de controles (`discord.ui.View`):

```text
┌────────────────────────────────────────────────────────┐
│  Tocando Agora: Deftones - Digital Bath                │
│  Duração: [🔘────────────────────] 01:14 / 04:15       │
│  Pedido por: @Tachi                                    │
├────────────────────────────────────────────────────────┤
│[ ⏯️ Pause/Play ]  [ ⏭️ Skip ]  [ 🔁 Loop ] [ ⏹️ Stop ] │
└────────────────────────────────────────────────────────┘
```

- **⏯️ Pause/Play:** Alterna instantaneamente o estado do player de voz.
- **⏭️ Skip:** Pula a música sem a necessidade de digitar mensagens no canal.
- **🔁 Loop:** Alterna entre os modos de repetição: _Faixa Única_, _Fila Completa_ ou _Desativado_.
- **⏹️ Stop:** Encerra a reprodução e libera o canal de voz.

## 🛡️ 3. Modos Operacionais: `ONLINE` vs `LOCAL`

O direcionamento das requisições obedece estritamente ao parâmetro `music.mode` do `config.yaml`:

- **Modo `ONLINE`:** As buscas consultam provedores públicos na internet e nós Lavalink remotos configurados no pool resiliente. Caso um nó sofra timeout ou recusa de conexão, ele entra automaticamente em castigo (_cooldown_ de 1 hora) e as solicitações são redirecionadas para os nós saudáveis.
- **Modo `LOCAL`:** O bot desliga chamadas para a nuvem e conecta-se via API Subsonic à biblioteca do servidor local (**Navidrome**), entregando reprodução sem compressão de banda com stream direto para o Lavalink local.
