# Changelog

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
