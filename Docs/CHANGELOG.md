
# Changelog 

## [Music.py] - 2026-02-04

### 🛠️ Melhorias e Correções de Estabilidade

#### 1. Sistema de Retentativas (Retry Logic)

* **Implementação:** Adicionado loop de tentativa controlada (`for attempt in range(1, 3)`) durante o processo de adição de faixas.
* **Objetivo:** Mitigar falhas de handshake com o Lavalink, comuns em ambientes Docker ou devido a variações de IP do YouTube. O sistema agora aguarda 1 segundo entre tentativas antes de reportar erro.

#### 2. Robustez na Fila (Dead Tracks Handling)

* **Correção:** Implementado bloco `try/except` para evitar que músicas deletadas ou privadas interrompam o carregamento de playlists inteiras.
* **Comportamento:** Músicas problemáticas são capturadas e armazenadas em uma lista temporária (`error_tracks`), permitindo que o bot processe o restante da fila sem travamentos.

#### 3. Feedback de Erros (Error Reporting)

* **Interface:** Adicionada notificação via **Embed** (cor vermelha) ao finalizar o carregamento de playlists com falhas.
* **Detalhes:** O bot agora lista explicitamente quais faixas falharam, oferecendo transparência ao usuário sobre a diferença na contagem final de músicas.

#### 4. Correção do Estado de Pausa (Playback Fix)

* **Problema:** O player carregava a faixa, mas permanecia em estado "Idle" ou pausado indefinidamente.
* **Solução:** Injeção de `await vc.set_pause(False)` em três pontos críticos:
1. No início do carregamento de uma nova música.
2. No disparador do evento `on_wavelink_track_end`.
3. Na inicialização do comando `play`.

## [Core/Bot.py] - 2026-02-03

### 🛠️ Correções e Melhorias no Sistema de Status

#### 1. Correção de Parâmetros de Presença

* **Correção:** Removido o argumento `status` de dentro da instância `discord.Activity`.
* **Motivo:** O objeto `Activity` aceita apenas atributos de conteúdo (tipo, nome, etc); o status visual (online, dnd, etc) deve ser definido exclusivamente via `change_presence`.

#### 2. Implementação de Telemetria (Logs)

* **Monitoramento:** Adicionado `self.log.info` para confirmar atualizações de status bem-sucedidas diretamente no terminal.
* **Depuração:** Adicionado `self.log.error` com captura de exceção para detalhar falhas críticas durante a execução do loop de status.

#### 3. Otimização da Lógica de Fallback

* **Melhoria:** Refinada a validação da variável `opcoes` para garantir o uso da lista `padrao` caso o `DataManager` retorne dados vazios ou o arquivo `atividades.json` não seja encontrado.
* **Estabilidade:** Evita que o bot sofra erros de tipo (`AttributeError` ou `IndexError`) ao tentar escolher frases de uma fonte inexistente.

#### 4. Sincronização de Inicialização

* **Ajuste:** Reforçado o uso de `await self.wait_until_ready()` no `before_loop`.
* **Objetivo:** Garante que o bot estabeleça conexão total com o Gateway do Discord antes de tentar qualquer alteração de presença, prevenindo avisos de "shards" não prontos no terminal.

---
