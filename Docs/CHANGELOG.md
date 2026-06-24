# Changelog

## [v2.2.4] - 23 de junho de 2026

### 🧠 Atualizações Críticas no Cérebro & Pipeline Cognitivo

O motor de inteligência e o pipeline de processamento central da SamBot receberam uma grande atualização focada em autonomia de intenções através do `nlp_data.json` e resiliência contra bloqueios de geração e filtros rígidos das APIs de LLM.

#### 🔄 Integração Dinâmica com o `nlp_data.json` (Fallback do Roteador)

- **Eliminação de Barreiras Estáticas:** Substituída a antiga lista engessada de `triggers` fixos dentro do `Pipeline.py` por uma leitura dinâmica e automatizada que unifica todos os gatilhos mapeados no `nlp_data.json` em tempo de execução.
- **Roteamento Inteligente de Ferramentas:** Consultas sobre sinopses, mangás e animes (como as requisições para a `AnimeTool` via Jikan/Trace.moe) agora passam livremente pela triagem de intenções sem a necessidade de intervenção ou manutenção dupla no código Python.

#### 🛡️ Blindagem contra o Erro de Recitação (Gemini `finish_reason: 8`)

- **Tratamento de Filtros no `LLMFactory.py`:** Implementada uma validação defensiva no método de geração assíncrona para interceptar candidatos a respostas que venham vazios devido aos filtros de plágio e direitos autorais do Google (gerados quando dados brutos de ferramentas como sinopses oficiais são idênticos à internet).
- **Proteção de Falha (Failover):** Caso o filtro de recitação seja disparado, o gerenciador de chaves limpa o estado, evita a quebra do robô (`response.text Quick Accessor Error`) e rotaciona o processamento para as chaves subsequentes ou para o contêiner de contingência local do Ollama.
- **Diretriz de Parafrasagem Ativa:** Injetada uma instrução de proteção sistêmica no prompt de contexto geral (`full_sys`) ordenando à IA que nunca copie dados linha por linha das ferramentas de busca, forçando resumos autorais, limpos e carismáticos.

#### 💸 Calibração de Ferramentas de Jogos (`GameTool` & `CheapShark`)

- **Correção de Moeda:** Ajustada a priorização semântica do prompt para garantir que a LLM consuma e exiba os valores convertidos em Reais (BRL) calculados matematicamente pelo `CheapSharkService` e `CurrencyService`, abandonando a exibição padrão estática em dólares comuns da internet.

---

### 🚀 Visão Geral do Sistema de Áudio (Centralização & Desacoplamento)

O ecossistema de áudio da SamBot passou por uma grande reestruturação arquitetural focada em desacoplamento e resiliência (arquitetura opcional). A pasta monolítica de comandos do player foi fragmentada em Cogs especializados por subdomínios, e a lógica de infraestrutura de múltiplos servidores e balanceamento híbrido foi completamente isolada no módulo `Lavalink`.

---

## ✨ Novidades e Nova Arquitetura de Pastas (Áudio)

O módulo `Audio/Player/*` agora opera de forma modular, dividido estritamente em comandos de entrada, controles de fluxo e utilitários de equalização avançada.

### 🧠 Motor de Busca & Roteamento Cirúrgico

- **Ajuste de Roteamento Local:** Correção crítica no fluxo do `SearchManager` para forçar o parâmetro `node=node` explicitando o identificador `"LOCAL"` nas pesquisas geradas na Intranet. Isso impede que o Wavelink envie streams locais (`http://127.0.0.1/...`) por balanceamento global para nós na nuvem (Lavalink Online), eliminando erros de conexão externa do tipo _Host Unreachable_.

### 🎵 Fragmentação de Comandos e Componentização (Cogs)

- **`playCommand.py`:** Concentra exclusivamente a lógica pesada de pesquisa inteligente e injeção inicial de faixas únicas ou playlists inteiras na fila, consumindo de forma isolada os dados do `SearchManager`.
- **`controlCommand.py`:** Centraliza o painel visual interativo (`PlayerControlView`) com botões efêmeros para gerenciamento de fluxo em canais de voz, além dos comandos `/skip`, `/pause`, `/resume` e `/stop`.
- **`extraCommand.py`:** Agrupa ferramentas de manipulação temporal, volume e exibição fina de status, incluindo o comando `/nowplaying` (com a barra de progressão em texto estilizado), `/seek`, `/remove` e `/skipto`.

### 🏥 Suíte de Inicialização Resiliente & Opcional

- **Boot Isolado no Módulo:** A rotina de carregamento e ativação física dos nós (`setup_nodes`) foi transferida de forma definitiva do núcleo global do bot para o listener assíncrono `on_ready` dentro de `controlCommand.py`.
- **Garantia de Tolerância a Falhas:** Caso o servidor Lavalink local esteja offline ou desconfigurado no arranque, os erros de rede e handshakes TCP falhos are tratados e isolados em um bloco _try/except_, impedindo o travamento da inicialização geral da aplicação.

---

## 🔄 Modificações e Refatorações na Infraestrutura (Docker)

- **Orquestração de Boot Sequencial (`docker-compose.yml`):** Implementada a propriedade `depends_on` condicionada ao status de saúde (`service_healthy`) para o contêiner `sambot`. O bot agora aguarda em segundo plano até que o contêiner vizinho `lavalink_local` finalize completamente a inicialização do Java e esteja pronto para receber conexões.
- **Teste de Saúde sem Autenticação (Healthcheck TCP):** Desenvolvido um validador de saúde de baixo nível baseado em sockets nativos do Linux (`/dev/tcp/127.0.0.1/2333`). Isso elimina testes baseados em requisições HTTP (`wget` / `curl`), contornando de forma elegante os bloqueios e logs de erros de credenciais ausentes (`Authorization missing`) causados pelo filtro de segurança nativo do Lavalink v4.
- **Isolamento de Redes Internas:** Substituição de endereços de loopback estáticos (`127.0.0.1`) no arquivo `.env` pelo mapeamento DNS interno do Docker Compose (`LAVALINK_LOCAL_HOST=lavalink`), permitindo comunicações de rede perfeitas entre contêineres na mesma ponte (_bridge_).

---

## 🐛 Correções de Erros (Bug Fixes)

#### Sincronização do Diagnóstico Subsonic (AttributeError):

- **Correção:** Resolvida a falha que disparava uma exceção de atributo ao invocar a rotina de teste automático da biblioteca do Navidrome.
- **Solução:** Reincorporado o método assíncrono `test_navidrome_connection()` diretamente dentro da nova estrutura orientada a objetos da classe `SearchManager` em `Lavalink/_search_manager.py`, reativando pings em tempo de boot via protocolo JSON.

#### Tratamento de Strings de Falha Híbrida (`NOT_FOUND_LOCAL`):

- **Correção:** Sincronizados os retornos literais de erro entre a busca e a interface. O comando `/play` agora checa adequadamente pela string de retorno atualizada `"NOT_FOUND_LOCAL"`, garantindo o envio correto do embed explicativo instruindo o usuário a ajustar o arquivo `.env` para o modo híbrido ou online.

---

## 🗑️ Remoções

- **Arquivo Monolítico Extinto:** Remoção definitiva do arquivo legado `Audio/Player/commands.py`, eliminando duplicidades de código, heranças circulares e unificando as chamadas nas extensões fragmentadas.
- **Parâmetros Obsoletos no `_search_manager.py`:** Retiradas as variáveis redundantes `api_version` e `client_name` do inicializador da busca, deixando-as fixas em suas respectivas rotinas de autenticação Subsonic.

---

## 📁 Estrutura de Arquivos Afetados

```text
├── docker-compose.yml             # Orquestração do healthcheck TCP e dependência de boot
├── application.yml                # Configuração do Lavalink (Fontes locais ativas, HTTP true)
├── Brain/
│   ├── Core/
│   │   └── Pipeline.py            # Roteamento dinâmico via nlp_data.json e diretriz de parafrasagem
│   └── Providers/
│       └── LLMFactory.py          # Interceptador defensivo de falhas de recitação (Erro Part/Finish Reason 8)
├── Audio/
│   ├── Lavalink/
│   │   ├── _node_manager.py       # Inicializador dinâmico de nós locais e remotos
│   │   └── _search_manager.py     # Injeção de ping.view e roteamento local corrigido para Navidrome
│   └── Player/
│       ├── playCommand.py         # Novo Cog isolado focado no comando play e carregamento de listas
│       ├── controlCommand.py      # Novo Cog focado na PlayerControlView, listeners e controles diretos
│       └── extraCommand.py        # Novo Cog focado em filtros, volume, barra de progresso e manipulação

```

## [v2.2.3] - 17 de junho de 2026

### 🚀 Visão Geral do Sistema de Áudio (Reestruturação Híbrida)

O sistema de áudio da SamBot foi estabilizado e atualizado para uma arquitetura orientada a subdomínios, unificando a velocidade do **Lavalink v4** (com a biblioteca **Wavelink**) à robustez do seu servidor de mídia pessoal **Navidrome**.

O experimento com extração de áudio local nativa (`yt-dlp` e `FFmpeg`) foi descontinuado devido à alta latência e instabilidade, retornando ao ecossistema assíncrono de alto desempenho do Lavalink sob um fluxo inteligente de tomada de decisão.

## ✨ Novidades e Nova Arquitetura de Busca

### 🧠 Motor de Busca Inteligente (`_search_manager.py`)

- **Introdução do SearchManager:** Criado um núcleo orquestrador assíncrono (`SearchManager`) que analisa dinamicamente a propriedade `MUSIC_SOURCE_MODE` do `.env`.
- **Integração com API Subsonic (Navidrome):** Implementado o consumo seguro e criptografado da API do Navidrome através de tokens e salts dinâmicos em `MD5` (`_generate_auth_params`). A senha nunca transita limpa pela rede.
- **Roteamento de Três Modos de Reprodução:**
  - `ONLINE`: Ignora o armazenamento local e pesquisa faixas via YouTube/Lavalink.
  - `LOCAL`: Realiza pesquisas exclusivas no Navidrome. Se a faixa não for encontrada, emite um aviso no chat sem gastar recursos da internet.
  - `HIBRIDO` (Padrão): Tenta pescar o arquivo `.mp3`/`.flac` local na API do Navidrome. Se falhar, realiza um _fallback_ transparente e silencioso para a internet através do Wavelink.

### 🎵 Comandos Híbridos Completos (`Player/commands.py`)

- **Unificação dos Controles de Voz:** O comando `play` foi totalmente remodelado para suportar o retorno duplo (`Resultado_Do_Wavelink, Origem_Do_Audio`) do `SearchManager`.
- **Identificação de Origens no Chat:** O bot agora adiciona rodapés e avisos informativos (`🗄️ Biblioteca Local (Navidrome)` ou `🌐 Internet (Fallback)`) para dar feedback visual aos usuários sobre a economia de banda de internet realizada no servidor.
- **Comandos Completados:** Integrados nativamente como híbridos os comandos `/skip`, `/pause`, `/resume`, `/stop` e o painel gráfico de progressão temporal com barras de texto estilizadas no `/nowplaying`.

### 🛠️ Correções de Erros (Bug Fixes)

#### Tipo de União em Type Hints (TypeError: unsupported operand type(s) for |):

- Corrigido o erro crítico que impedia o carregamento do Cog Modules.Audio.Player.commands.
- O interpretador Python avaliava o tipo wavelink.Search como string devido ao ciclo de importações internas do Wavelink, gerando uma falha ao tentar aplicar o operador de união binária | ("string" | None).
- Substituído pelo uso seguro e retrocompatível de typing.Optional e typing.Tuple.

### 🚀 Novas Funcionalidades (Features)

#### Diagnóstico de Conexão Subsonic/Navidrome (Ping Test):

- Adicionada a função de teste de conectividade física e autenticação com o servidor local Navidrome usando o endpoint nativo ping.view da API Subsonic.

- Exibição de relatórios amigáveis no terminal detalhando se a biblioteca local está sincronizada ou se há falhas de credenciais no .env.

#### 🧹 Refatoração & Unificação

**Consolidação do Launcher e Testes (\_core.py):**

- Unificados o inicializador do Lavalink (Wavelink Core) e as rotinas de teste e diagnóstico de conexões de áudio no arquivo \_core.py.

- Remoção completa de parâmetros depreciados e configurações obsoletas legadas.

- Centralização de logs e informações de status de inicialização para facilitar a auditoria de problemas de rede.

## [v2.2.2] - 30 de maio de 2026

### 🚀 Visão Geral do Sistema de Áudio

O sistema de áudio da SamBot foi totalmente reestruturado e refatorado para isolar responsabilidades. A dependência do servidor Java (**Lavalink**) e da biblioteca **Wavelink** foi completamente eliminada.

O bot agora utiliza **reprodução local nativa** via `yt-dlp` e `FFmpegPCMAudio`, reduzindo drasticamente o consumo de memória do servidor. O gerenciamento de estado (filas) e a lógica de negócios (extração e armazenamento) foram desvinculados das interfaces de comandos (Cogs) do Discord, tornando o código altamente testável, escalável e isolado.

---

## ✨ Novidades e Nova Arquitetura de Pastas

O módulo `Modules/Audio/*` agora está dividido estritamente nos domínios: `Player`, `Queue`, `Playlists` e `Utils`.

### 🎵 Novo Motor de Áudio & Autenticação Inteligente

- **Engine de Extração Local:** Processamento de áudio nativo rodando localmente através do `yt-dlp`.
- **Autenticação Interceptada via Discord:** Implementação da classe `YTDLLogger` no motor do player para evitar erros `403 Forbidden` e bloqueios do YouTube. O controle de ambiente é feito via variável `BOT_AUTH_MODE`.
- **Suporte a Cookies do Navegador:** Ideal para uso em ambiente local.
- **Autenticação OAuth2 por Dispositivo:** Ideal para VPS/servidores sem interface gráfica. O bot intercepta o fluxo Device OAuth do YouTube e envia automaticamente uma mensagem formatada por DM para o desenvolvedor (`OWNER_ID`) com o código de pareamento temporário e o link de ativação (`google.com/device`).
- **Mecanismo de Fallback:** Caso a DM do proprietário esteja fechada, o bot envia uma mensagem pública marcando o dono diretamente no chat onde o comando foi disparado.

### 🧠 Gerenciador de Estado Independente (`Queue/_manager.py`)

- Criada a classe `QueueManager` como um _singleton_ global. Qualquer arquivo do projeto pode acessar e modificar as filas de reprodução dos servidores sem depender do objeto `bot` ou de requisições diretas a Cogs.

### 📊 Painel de Status, Logs & Métricas Compartilhadas

- **Diagnósticos no Launcher (`launcher.py`):** Adicionado o Painel de Logs e Status (Opção 5) para monitorar arquivos locais (`txt`, `sambot_general.log` e `sambot_errors.log`) em tempo real, além de integração para fluxo contínuo (_stream_) de logs do Docker (`docker compose logs -f --tail=50`) e limpeza segura de cache.
- **Mapeamento de Métricas Dinâmicas (`Core/Bot.py`):** Monitoramento passivo de mensagens lidas (`on_message`), comandos executados com sucesso e tempo total ativo em chamadas de voz (`voice_time_minutes`). Um loop assíncrono sincroniza e grava esses dados a cada 1 minuto no arquivo `logs/bot_stats.json`.

### ⚙️ Assistente de Instalação Aperfeiçoado

- **Instruções com Chave de Ajuda (`help_`):** Mapeamento detalhado para todas as variáveis do `.env.example`. Digitar `?` em qualquer pergunta do instalador exibe uma dica completa sobre a chave API. Correção de dependência circular/temporal com a inicialização prévia do dicionário `advanced_keys`.

---

## 🔄 Modificações e Refatorações

- **Motor de Extração de Áudio (`Player/_core.py`):** O antigo `Core.py` foi enxugado. Ele agora contém exclusivamente a configuração do `yt-dlp` e a classe `YTDLSource`, atuando puramente nos bastidores.
- **Comandos de Reprodução e Controle (`Player/commands.py`):** Os antigos `Reproducao.py` e `Controles.py` foram unificados. O comando `play` foi adaptado para usar o `discord.VoiceClient` nativo e o `FFmpeg`, detectando automaticamente URLs ou busca por texto puro (`ytsearch:`). A função recursiva `play_next` foi realocada para dentro desta classe Cog e adaptada para repassar o contexto (`ctx`).
- **Controles de Áudio:** Comandos como `skip`, `stop`, `pause`, `volume` e `shuffle` foram totalmente reescritos para manipular a nova fila interna do `QueueManager` e os eventos nativos do Discord.
- **Comandos de Informação (`Queue/info_commands.py`):** O antigo `Info.py` foi movido para o domínio da fila. Os comandos `nowplaying` e `queue` agora consomem os dados diretamente do `queue_manager` e exibem embeds atualizados para a nova estrutura do `yt-dlp`.
- **Módulo de Playlists (`Playlists/commands.py` e `Playlists/manager.py`):** Os comandos do antigo `PlaylistUser.py` e a lógica de salvamento em JSON foram agrupados no mesmo domínio. A extração de metadados agora roda de forma assíncrona com `stream=False`. A transição de músicas da playlist para o bot consome o novo gerenciador de fila e repassa o contexto (`ctx`).
- **Injeção de Dependências:** O carregamento recursivo no inicializador central `Bot.py` lê arquivos de extensão `commands.py` e `info_commands.py`, ignorando as lógicas isoladas que começam com `_` (como `_manager.py` e `_core.py`).

---

## 🗑️ Remoções

- **Lavalink & Wavelink Extintos:** O servidor Java (`Lavalink.jar`), seus plugins e a biblioteca `wavelink` foram 100% removidos do projeto e das dependências.
- **Acoplamento do Cog Principal:** Removida a necessidade de utilizar `self.bot.get_cog("AudioCore")` para gerenciar a fila ou processar músicas.
- **Armazenamento de Filas no Cog:** O dicionário global de instâncias `self.queues` foi eliminado, deixando de forçar o `AudioCore` a ser o dono absoluto do estado de reprodução.
- **Comando Loop (Temporário):** Desativado temporariamente. A função de repetição precisa ser reimplementada futuramente utilizando a nova lógica da fila interna do `QueueManager`.

---

## 📁 Estrutura de Arquivos Afetados

```text
├── launcher.py                    # Assistente, menu, logs e leitor de bot_stats.json
├── Core/
│   └── Bot.py                     # Captura de mensagens, comandos, call time e loop de escrita JSON
├── Audio/
│   ├── Player/
│   │   ├── _core.py               # Configurações do yt-dlp, YTDLSource e o interceptador YTDLLogger
│   │   └── commands.py            # Comandos de reprodução e controles nativos unificados (repassando ctx)
│   ├── Queue/
│   │   ├── _manager.py            # Gerenciador de estado global independente (Singleton)
│   │   └── info_commands.py       # Comandos de exibição da fila e música atual (nowplaying/queue)
│   └── Playlists/
│       ├── manager.py             # Lógica de persistência em JSON de listas de reprodução
│       └── commands.py            # Comandos de playlists adaptados para o QueueManager (repassando ctx)
└── logs/
    └── bot_stats.json             # Estado persistido de métricas compartilhadas (Gerado dinamicamente)

```

> ⚙️ **Impacto Técnico:** O código agora opera de forma desacoplada e modular. Caso seja necessário adicionar um banco de dados no futuro ou implementar testes unitários de lógica de filas, será possível interagir diretamente com o `QueueManager` e o `PlaylistManager` sem a necessidade de simular ou invocar interações da API do Discord.

## [v2.2.1] - 30 de maio de 2026

**✨ Melhorias e Novidades**

- **Novos Atalhos:** Adicionado o atalho `aleatorio` ao comando de embaralhar (`shuffle`), facilitando o uso para quem prefere comandos em português.

- **Interface mais Clara:** O rodapé do comando `/fila` agora exibe com exatidão o status atual do loop, informando se está a repetir uma única música, a fila inteira ou se está desativado.

**🐛 Correções de Bugs**

- **Sistema de Repetição (Loop):** O comando `/loop` foi atualizado para utilizar os parâmetros corretos das versões recentes do Wavelink (`QueueMode.loop` e `QueueMode.loop_all`), eliminando erros de código.

- **Baralhamento da Fila (Shuffle):** O comando `/aleatorio` agora utiliza o método nativo de embaralhar do player (`vc.queue.shuffle()`), substituindo a antiga tentativa de baralhar a fila como uma lista comum do Python que causava erros.

- **Limpeza de Conflitos:** Removida a duplicata do comando `loop` no ficheiro `Controles.py` que estava a criar conflitos e a anular as correções.

- **Adição à Fila (Compatibilidade):** Ajuste sugerido nos métodos de reprodução (`/play` e carregar playlists) para substituir o obsoleto `put_wait()` pelo atualizado `put()`, prevenindo que o bot congele ao adicionar novas faixas.

## [v2.2.0] - 24 de maio de 2026

### 🚀 Instalação e Infraestrutura

- **Novo Assistente de Inicialização (`launcher.py`):** O processo de boot foi completamente reescrito em Python, criando um painel de controle interativo no terminal.
  - **Setup Wizard Interativo:** A SamBot agora guia usuários novatos passo a passo na criação do arquivo `.env`, com dicas de ajuda didáticas (acionadas ao digitar `?`) para explicar o que é o Token ou o Owner ID.
  - **Divulgação Progressiva:** Implementado um Menu Avançado opcional para configuração de chaves secundárias (Steam, IGDB, Gemini, Google Search), permitindo pular serviços que o usuário ainda não possui sem causar falhas no código.
  - **Menu de Boot Seguro:** O painel impede inicializações sem o `.env` configurado e oferece opções claras para rodar via Docker ou Nativamente, incluindo detecção inteligente de portas (ping no Lavalink 2333) e uma trava de segurança contra a exclusão acidental de chaves.
- **Suporte Multiplataforma Simplificado:** Os arquivos `start.sh` (Linux) e `start.bat` (Windows) foram reduzidos a gatilhos limpos que validam a existência do Python e invocam o painel gráfico de forma nativa e padronizada em qualquer sistema operacional.

### 📚 Documentação e Manuais

- **`README.md` Totalmente Revisado:** O guia principal foi reescrito para refletir a nova Arquitetura Híbrida Orientada a Domínios (DDD), o novo Fast Track de Embeddings e a nova forma de Instalação Rápida e Interativa via Launcher.
- **`ARCHITECTURE.md` Expandido:** Documento atualizado com uma visão profunda e técnica do ecossistema cognitivo. Agora ele detalha o motor descentralizado (`Pipeline.py`), a divisão estrita de responsabilidades de memória (ShortTerm, LongTerm, DataManager, SelfKnowledge) e os diagramas de fluxo de dados assíncronos e contingências (Failover).

### 🏗️ Arquitetura Cognitiva (Domain-Driven Design)

- **Reestruturação Completa da Memória:** A antiga pasta monolítica `Brain/Memory` foi dividida em subdomínios especializados para garantir alta escalabilidade e isolamento de responsabilidades:
  - **`DataManager/`:** O núcleo de persistência foi dividido em I/O protegido por threads (`_json_provider.py`), RAM estática (`_cache.py`) e um orquestrador unificado (`Manager.py`), permitindo leituras de dados sem travamentos.
  - **`ShortTerm/`:** Focado no contexto imediato, isolando o histórico de conversas locais (`Context.py`) e a injeção de reações de humor (`_expressions.py`).
  - **`LongTerm/`:** O banco de dados vetorial foi isolado (`VectorStore.py`). O sistema de extração ativa de fatos foi desacoplado do arquivo principal para um módulo dedicado (`_learning.py`).
  - **`SelfKnowledge/`:** Todo o conhecimento descritivo sobre o que o bot é e como ele opera (incluindo modificadores de personalidade) agora reside de forma nativa nesta pasta (`Identity.py` e `Curiosidades.py`).

### ⚙️ Núcleo e Pipeline de Processamento (Core)

- **Transplante de Cérebro (`Pipeline.py`):** Toda a lógica pesada de pensamento, roteamento de ferramentas e formatação de chunks de mensagens foi extraída do Discord Bot e migrada para um motor puro (`Brain/Core/Pipeline.py`).
- **Limpeza da Interface (`Agent.py`):** O módulo `Agent.py` foi limpo e reduzido a um simples receptor (Cog) do Discord. Sua única função agora é captar as menções, ignorar comandos, e encaminhar o sinal para o `Pipeline`.
- **Rotinas de Fundo Movidas:** O sistema de consolidação noturna e mercado financeiro (`NightCycle.py`) e o motor de normalização linguística (`Limpeza.py`) foram promovidos e migrados adequadamente para a pasta `Brain/Core/`.

### ⚡ Otimização de Performance e Latência da IA

- **Via Verde de Embeddings (Fast Track):** Refatoração crítica na função híbrida de geração de vetores (`_embeddings.py`).
  - **Problema resolvido:** O bot não perde mais 10 a 14 segundos testando modelos inativos ou chaves corrompidas (Erros 404) do Google Gemini a cada mensagem recebida.
  - **Solução:** O sistema agora salva localmente a última combinação de "Provedor + Modelo + Chave" que funcionou perfeitamente. Nas consultas subsequentes, ele utiliza essa "via verde" com latência quase zero. Este estado otimizado é validado e atualizado a cada 7 dias para garantir disponibilidade contínua sem prejudicar a performance do chat.

## [v2.1.5] - 23 de maio de 2026

### 🛠️ Novas Funcionalidades & Comandos

- **`+afk`:** Gerencia o status de ausência do usuário, notificando menções de forma autônoma.
- **`+anagrama`:** Gera anagramas aleatórios a partir de uma palavra informada e calcula o número total de permutações únicas.
- **`+calc`:** Calculadora integrada capaz de avaliar expressões matemáticas complexas com tratamento de erros robusto.
- **`+choose`:** Efetua a escolha aleatória e imparcial de uma opção contida em uma lista fornecida pelo usuário.
- **`+corinfo`:** Exibe detalhes técnicos completos de cores e paletas visuais a partir de entradas em formato Hexadecimal ou RGB.
- **`+dicio`:** Consulta e retorna definições gramaticais, sinônimos e frases de exemplo para termos e palavras.
- **`+moeda`:** Realiza a conversão de valores entre diferentes moedas em tempo real utilizando integração com API externa.
- **`+morse`:** Codifica textos legíveis em código Morse ou decodifica sequências de Morse para texto padrão.
- **`+qrcode`:** Gera instantaneamente códigos QR dinâmicos e exportáveis com base em links ou textos inseridos.
- **`+reminder`:** Cria e gerencia lembretes personalizados com suporte integrado à função de soneca (_snooze_).
- **`+tempo`:** Busca e exibe as condições climáticas e meteorológicas atuais para uma cidade especificada pelo usuário.
  Aqui está o novo bloco de comandos formatado exatamente no mesmo padrão de Markdown do anterior:

* **`+info [subcomandos]`:** Módulo expandido com subcomandos estruturados para extração de metadados:
  - **`emojis`:** Estatísticas, IDs e detalhes dos emojis customizados do servidor.
  - **`invite`:** Rastreamento e informações sobre links de convites ativos.
  - **`server`:** Diagnóstico completo, contagem de membros e dados de criação da guilda.
* **`+manage emojis`:** Painel/ferramentas para adicionar, remover e gerenciar os emojis customizados do servidor diretamente pelo Discord.
* **`+manage webhook`:** Interface para criação, edição de propriedades e auditoria de webhooks ativos nos canais de texto.
* **`+sistema bemvindo`:** Módulo automatizado de boas-vindas para novos membros, integrando saudações customizadas e atribuição inicial.

### Módulos de Usuário & Economia (REFATORADO):

- **Informações e Utilidades do Usuário:** A unificação das propriedades de perfil otimizou o carregamento de dados e unificou os comandos de consulta de perfis.
- **Comando Dice (Dados):** Aprimoramento da lógica matemática interna e melhoria na exibição visual dos resultados de rolagem de dados no chat.
- **Sistema de Experiência (XP) & Ranking:** Refatoração completa do algoritmo de cálculo de
  progressão, garantindo consistência no armazenamento e carregamento de posições de rank globais e
  locais.

### **Atualizações em `Core/Bot.py`:**

- **Leitura Dinâmica de Configurações:** Realiza o parse e a leitura do arquivo `config.json` em tempo de execução para extrair nome e versão dinamicamente, com fallback seguro.
- **Tratamento Resiliente do Prefix:** Suporte robusto à extração via `os.getenv("BOT_PREFIX", "-")`, garantindo o prefixo padrão caso ocorram falhas ou ausência no arquivo `.env`.
- **Correção no Fluxo de Sincronização:** A rotina `run_diagnostics()` foi movida do `setup_hook` para o evento nativo `on_ready`, solucionando bugs de latência nula e adicionando persistência para a visualização `AppealStartView`.
- **Gerenciador de Erros Visual Avançado:** O listener global `on_command_error` agora gera embeds detalhados e intuitivos para exceções do tipo `MissingRequiredArgument`, eliminando mensagens em texto simples.
- **Padronização de Fuso Horário:** Correção na captura do `start_time` do sistema, migrando para o método recomendado `discord.utils.utcnow()`.

- **Subsistema de Logging & Diagnósticos (LOGS):**
- **Controle e Limitação de Arquivos:** Substituição do `FileHandler` genérico pela classe `RotatingFileHandler`, fixando o tamanho máximo por arquivo (ex: 5 MB) e o histórico em no máximo 3 arquivos simultâneos (deleção assíncrona do mais antigo).
- **Segregação Arquitetural de Arquivos de Log:** Separação analítica do fluxo de logs na pasta `logs/` para otimizar auditorias e debug:
- **`sambot_general.log`:** Captura o fluxo completo e cronológico do sistema, englobando os níveis `INFO`, `WARNING`, `ERROR` e `CRITICAL`.
- **`sambot_errors.log`:** Arquivo exclusivo de telemetria de falhas, retendo estritamente os níveis `ERROR` e `CRITICAL` através de filtros personalizados.

## [v2.1.2-beta] - 19 de abril de 2026

### 💰 Economia & RPG (Refatoração Completa)

- **Sistema Visual:** Implementação da biblioteca `easy-pil` para geração de cards dinâmicos.
  - **Perfil:** Agora exibe avatar redondo, barra de progresso de XP e planos de fundo customizáveis.
  - **Ranking:** Top 5 visual com barras de XP e download assíncrono de avatares para evitar travamentos.
- **Minigames Interativos:** Adição de desafios visuais para o comando `+work`:
  - **Lixeiro:** Minigame de separação de resíduos usando botões (`discord.ui.View`).
  - **Hacker:** Desafio de quebra de hash com geração de imagem dinâmica e ruído anti-bot.
- **Mercado de Capitais:** Criação da Bolsa de Valores Sam:
  - **Ativos:** Suporte para Ações e Fundos Imobiliários (FIIs) via `mercado.json`.
  - **Lógica Financeira:** Implementação de cálculo de Preço Médio (PM) e lucro/prejuízo em tempo real.
  - **Ciclo Noturno:** Automação via `NightCycle.py` para flutuação de preços e pagamento de dividendos durante a madrugada.
- **Cosméticos:** Loja de fundos de perfil com sistema de **Preview Efêmero** (imagem temporária antes da compra).

### 🛡️ Administração & Segurança (Suíte Admin)

- **Modularização:** O antigo arquivo `Admin.py` foi substituído por uma pasta dedicada com lógica isolada.
- **Auditoria Avançada:** Sistema de logs com **6 níveis de intensidade** (Básico até Geral) e suporte para filtros personalizados via menu dropdown.
- **AutoMod Configurável:** Proteção ativa contra links, spam (janela de tempo de 5s) e palavras bloqueadas com painel de controle interativo (`+configautomod`).
- **Avisos Públicos:** Novo módulo `Avisos.py` que centraliza e anuncia punições de forma elegante em canais configurados.
- **Moderação Nativa:** Comandos de `ban`, `kick` e `mute` (Timeout nativo do Discord) com verificação de hierarquia de cargos.

### 📈 Progressão & Chat

- **XP Passivo:** Sistema de ganho de XP por mensagens no chat com cooldown de 60 segundos.
- **Auto-Roles:** Configuração de cargos de recompensa automáticos ao atingir níveis específicos via `+configxp`.

### 🛠️ Utilitários & Interface

- **Otimização de Código:** Fusão dos módulos `General.py` e `Identify.py` no novo `Informacoes.py` para reduzir o consumo de memória.
- **Sistema de Ajuda Dinâmico:** Novo `+help` utilizando menus suspensos (`Select`) que agrupa comandos automaticamente por pasta pai, suportando expansão infinita.

### 🧠 Core & Infraestrutura

- **DataManager:** Centralização total de leitura/escrita de JSONs para garantir integridade dos dados entre os módulos.
- **Docker:** Estrutura otimizada para rodar no HomeLab com persistência de dados em volumes mapeados.

## [v2.1.1-beta] - 16 de abril de 2026

### 🚀 Adicionado

- **Playlists Pessoais (`PlaylistUser.py`):** Novo sistema que permite aos utilizadores criar, guardar, carregar, renomear e apagar as suas próprias playlists locais através de ficheiros JSON, sem depender de contas da cloud.
- **Estrutura Modular de Áudio:** O sistema de música foi dividido em componentes independentes para melhor manutenção (`Core.py`, `Controles.py`, `Info.py`, `Reproducao.py` e `_utils.py`).
- **Nova Documentação:** Aba de [API](API.md) para detalhar o que foi usada na bot

### 🔄 Alterado

- **Pesquisa Wavelink Nativa:** O comando `play` agora utiliza a pesquisa embutida do Lavalink/Wavelink para procurar músicas e links, aumentando a rapidez e a estabilidade.
- **Prefixo Dinâmico:** O rodapé do menu de ajuda (`HelpSystem.py`) agora adapta-se automaticamente a qualquer alteração de prefixo do bot.
- **Refatoração do Áudio:** Remoção da dependência da API nativa do YouTube (Google OAuth) para prevenir bloqueios e crashes (headless) ao rodar o bot via Docker.

### 🗑️ Removido

- Ficheiro monolítico `Music.py`.
- Ficheiro de autenticação `_YoutubeHelper.py` e comandos associados de gestão de tokens do Google.

### 🐛 Corrigido

- **Crashes em DMs:** Os comandos de servidor (`userinfo`, `serverinfo`, `servericon`, `clear`, `kick`, `ban`) receberam blindagem (`@commands.guild_only()`) para impedir falhas graves quando executados em Mensagens Diretas.
- **Steam Store KeyError:** Corrigida a falha silenciosa no módulo `SteamStore.py` que crashava o bot quando um jogo pesquisado era bloqueado por região ou não tinha detalhes públicos.
- **Limite do Discord Dropdown:** Foi imposto um limite de 25 opções no `SelectMenu` do `HelpSystem.py`, evitando erros catastróficos da API do Discord caso o número de módulos (Cogs) cresça no futuro.

## [v2.1.0-beta] - 10 de fevereiro de 2026

- Introduzidas funcionalidades nativas de visão computacional para o sistema do bot: O módulo `VisionTool` foi criado para processar e formatar imagens baixadas do Discord automaticamente.

VisionTool --process-images

- Modelo de Linguagem Multimodal (LLM) aprimorado: O bot agora é capaz de lidar com solicitações textuais juntamente com blobs de imagem para interações com a API, suportando especificamente entradas de conteúdo misto para o Google Gemini.

- Correção do bug "Loop da Morte": Um problema crítico em que chaves de modelo incorretas eram trocadas ao incorporar erros 404 foi resolvido com a implementação de uma lista de modelos alternativos e detecção inteligente de erros com base nos status dos modelos.

- Corrigido o problema de travamento do RAG relacionado à falta de argumento de consulta na recuperação de memória: O bot agora identifica corretamente se está executando operações de `search_memory` ou `query_relevant`, garantindo que os argumentos necessários sejam passados ​​para uma interação perfeita com o ChromaDB.

- Correções de espera assíncrona: Avisos sobre chamadas de corrotina não aguardadas em processos de recuperação de memória foram corrigidos para garantir um comportamento assíncrono confiável em dependências de agentes e ferramentas.

## [v2.0.5] - 9 de fevereiro de 2026

- **Sistema de Memória Vetorial (ChromaDB)**: A estrutura inicial do ChromaDB foi estabelecida com integração básica à funcionalidade de serviços de música Lavalink.

- Problemas intermitentes identificados durante a geração de embeddings usando chaves de modelo livres: A instabilidade identificada com os embeddings para o pipeline de texto-imagem está sendo tratada. Investigações e soluções adicionais estão em andamento para garantir um desempenho consistente em vários modelos, sem incorrer em custos adicionais ou configurações complexas.

## [Brain/Agent.py e Brain/Memory] - 2026-02-05

### 🧠 Otimização de Contexto e Memória Episódica

#### 1. Summarização de Histórico (Historico.py)

- **Compressão Inteligente:** Implementada lógica para condensar históricos que excedam 10 mensagens.
- **Economia de Tokens:** O sistema agora utiliza a LLM para gerar um parágrafo de resumo narrativo das mensagens antigas, mantendo apenas as interações mais recentes na íntegra. Isso permite sessões mais longas sem estourar a janela de contexto da IA.

#### 2. Validação Semântica de Fatos (Agent.py)

- **Filtro Cognitivo:** O método `_aprender_fatos` foi reescrito para não depender exclusivamente de _keywords_.
- **Análise via LLM:** Agora, ao detectar um possível fato pessoal, o agente consulta a LLM para validar a relevância e a veracidade da informação (ex: distingue "Eu sou programador" de "Eu sou o Batman"), evitando a poluição da memória de longo prazo com dados irrelevantes ou sarcasmo.

### 🛠️ Ferramentas e Roteamento (Agent.py)

#### 1. Multi-Tool Calling

- **Capacidade Paralela:** O roteador agora aceita e processa listas de ações JSON.
- **Cenário de Uso:** Permite responder perguntas complexas como "Qual a previsão do tempo para jogar X?" chamando `weather` e `game_search` na mesma iteração de pensamento.

### 🧠 Imersão e Interatividade (Agent.py)

#### 1. Feedback Cognitivo Imediato (Anti-Secura)

- **Melhoria:** O método `_aprender_fatos` agora retorna o dado extraído para o fluxo principal.
- **Comportamento:** O sistema injeta o fato recém-aprendido diretamente no prompt de sistema da resposta atual. Isso força a IA a confirmar explicitamente o aprendizado (ex: _"Prazer, Tachi! Já anotei que você curte hardware"_) em vez de dar respostas genéricas como _"Entendi"_.

#### 2. Reação Privada (Easter Egg)

- **Novo Recurso:** Implementado o listener `on_reaction_add` focado no emoji 🧠.
- **Experiência:** Quando o usuário clica na reação de "cérebro" deixada pela SamBot (indicando memória salva), ele recebe uma Mensagem Direta (DM) carinhosa confirmando o backup daquela informação (ex: _"Isso está guardadinho aqui! 💾💜"_).

#### 2. Robustez JSON (Retry Logic)

- **Auto-Correção:** Implementado loop de 3 tentativas para geração do JSON de ferramentas.
- **Feedback de Erro:** Se a LLM gerar um JSON inválido, o erro de sintaxe é reincorporado ao prompt na próxima tentativa, solicitando correção explícita. Isso mitiga alucinações de formato em modelos menores.

### 💬 Interface e Experiência (Agent.py)

#### 1. Smart Chunks (Formatação de Mensagens)

- **Refatoração:** O método `_enviar_resposta` foi reescrito para eliminar cortes abruptos em textos longos.
- **Lógica:** Em vez de cortar a mensagem exatamente no caractere 1900, o bot agora busca ativamente por quebras de linha (`\n`), finais de frase (`.`) ou espaços para dividir o texto de forma natural, melhorando significativamente a legibilidade de respostas extensas ou gerações criativas.

## [Music.py] - 2026-02-04

### 🛠️ Melhorias e Correções de Estabilidade

#### 1. Sistema de Retentativas (Retry Logic)

- **Implementação:** Adicionado loop de tentativa controlada (`for attempt in range(1, 3)`) durante o processo de adição de faixas.
- **Objetivo:** Mitigar falhas de handshake com o Lavalink, comuns em ambientes Docker ou devido a variações de IP do YouTube. O sistema agora aguarda 1 segundo entre tentativas antes de reportar erro.

#### 2. Robustez na Fila (Dead Tracks Handling)

- **Correção:** Implementado bloco `try/except` para evitar que músicas deletadas ou privadas interrompam o carregamento de playlists inteiras.
- **Comportamento:** Músicas problemáticas são capturadas e armazenadas em uma lista temporária (`error_tracks`), permitindo que o bot processe o restante da fila sem travamentos.

#### 3. Feedback de Erros (Error Reporting)

- **Interface:** Adicionada notificação via **Embed** (cor vermelha) ao finalizar o carregamento de playlists com falhas.
- **Detalhes:** O bot agora lista explicitamente quais faixas falharam, oferecendo transparência ao usuário sobre a diferença na contagem final de músicas.

#### 4. Correção do Estado de Pausa (Playback Fix)

- **Problema:** O player carregava a faixa, mas permanecia em estado "Idle" ou pausado indefinidamente.
- **Solução:** Injeção de `await vc.set_pause(False)` em três pontos críticos:

1. No início do carregamento de uma nova música.
2. No disparador do evento `on_wavelink_track_end`.
3. Na inicialização do comando `play`.

## [Core/Bot.py] - 2026-02-03

### 🛠️ Correções e Melhorias no Sistema de Status

#### 1. Correção de Parâmetros de Presença

- **Correção:** Removido o argumento `status` de dentro da instância `discord.Activity`.
- **Motivo:** O objeto `Activity` aceita apenas atributos de conteúdo (tipo, nome, etc); o status visual (online, dnd, etc) deve ser definido exclusivamente via `change_presence`.

#### 2. Implementação de Telemetria (Logs)

- **Monitoramento:** Adicionado `self.log.info` para confirmar atualizações de status bem-sucedidas diretamente no terminal.
- **Depuração:** Adicionado `self.log.error` com captura de exceção para detalhar falhas críticas durante a execução do loop de status.

#### 3. Otimização da Lógica de Fallback

- **Melhoria:** Refinada a validação da variável `opcoes` para garantir o uso da lista `padrao` caso o `DataManager` retorne dados vazios ou o arquivo `atividades.json` não seja encontrado.
- **Estabilidade:** Evita que o bot sofra erros de tipo (`AttributeError` ou `IndexError`) ao tentar escolher frases de uma fonte inexistente.

#### 4. Sincronização de Inicialização

- **Ajuste:** Reforçado o uso de `await self.wait_until_ready()` no `before_loop`.
- **Objetivo:** Garante que o bot estabeleça conexão total com o Gateway do Discord antes de tentar qualquer alteração de presença, prevenindo avisos de "shards" não prontos no terminal.

---
