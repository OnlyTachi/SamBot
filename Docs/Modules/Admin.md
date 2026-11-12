# 🛡️ Administração, Auditoria & Moderação Automática

O subsistema administrativo da SamBot (`sambot/Modules/Admin/`) fornece ferramentas para a gestão de segurança dos servidores Discord, incluindo trilha de auditoria em 6 níveis de severidade, moderação automática de mensagens (AutoMod) e comandos operacionais de punição.

## 📜 1. Trilha de Auditoria em 6 Níveis de Severidade

Os eventos ocorridos no servidor são capturados, categorizados e encaminhados para o canal de logs configurado na guilda. O sistema emprega 6 níveis estritos de severidade:

| Nível | Identificador | Cor do Embed             | Exemplos de Eventos Monitorados                                           |
| :---: | :------------ | :----------------------- | :------------------------------------------------------------------------ |
| **1** | `TRACE`       | Cinza Claro (`0x95A5A6`) | Alterações de apelidos comuns, movimentações simples de call.             |
| **2** | `DEBUG`       | Ciano (`0x1ABC9C`)       | Invocação de comandos de utilidade e consultas gerais.                    |
| **3** | `INFO`        | Azul (`0x3498DB`)        | Entrada/saída de membros, criação de canais de texto ou voz.              |
| **4** | `WARN`        | Amarelo (`0xF1C40F`)     | Violações de filtros leves de AutoMod, excesso de mensagens (flood).      |
| **5** | `ERROR`       | Laranja (`0xE67E22`)     | Mensagens deletadas contendo links suspeitos, tentativas de spam massivo. |
| **6** | `CRITICAL`    | Vermelho (`0xE74C3C`)    | Expulsões, banimentos manuais, deleção de canais e tentativas de raid.    |

## 🤖 2. Moderação Automática (AutoMod)

O motor de AutoMod inspeciona todas as mensagens recebidas em tempo real antes de qualquer processamento cognitivo ou despacho de comandos:

### 2.1. Filtro Anti-Spam e Anti-Flood

- **Detecção:** Monitora janelas de tempo deslizantes por usuário (ex.: 5 mensagens em menos de 3 segundos).
- **Ação:** Apaga as mensagens em excesso, emite aviso público efêmero e aplica mute temporário preventivo de 5 minutos em caso de reincidência.

### 2.2. Filtro Anti-Links e Domínios Maliciosos

- **Detecção:** Identifica URLs em texto comum ou mascaradas via Markdown.
- **Ação:** Verifica contra a lista branca de domínios seguros cadastrados pelo servidor. URLs desconhecidas ou marcadas como phishing são apagadas imediatamente com log de nível `ERROR`.

### 2.3. Bloqueio de Convites do Discord (Anti-Invite)

- **Detecção:** Regex dedicada a identificar códigos de convites de outros servidores (`discord.gg/*`, `discord.com/invite/*`).
- **Ação:** Remove o convite instantaneamente, a menos que o autor possua permissão de `Gerenciar Servidor` ou cargo na lista de bypass configurada.

## 🔨 3. Comandos de Punição e Moderação

Comandos de intervenção rápida disponíveis para administradores e moderadores autorizados:

| Comando     | Sintaxe                                 | Descrição                                                                      |
| :---------- | :-------------------------------------- | :----------------------------------------------------------------------------- |
| `+kick`     | `+kick <@membro> [motivo]`              | Expulsa o membro do servidor com notificação do motivo via DM.                 |
| `+ban`      | `+ban <@membro> [dias_delete] [motivo]` | Bane permanentemente o usuário e opcionalmente limpa o histórico de mensagens. |
| `+unban`    | `+unban <user_id> [motivo]`             | Remove o banimento do identificador numérico informado.                        |
| `+mute`     | `+mute <@membro> <tempo> [motivo]`      | Aplica timeout temporário via API nativa do Discord (ex.: `10m`, `2h`, `1d`).  |
| `+unmute`   | `+unmute <@membro>`                     | Remove o timeout do membro imediatamente.                                      |
| `+clear`    | `+clear <quantidade>`                   | Purga em lote até 100 mensagens recentes do canal de texto.                    |
| `+slowmode` | `+slowmode <segundos>`                  | Define o intervalo de espera obrigatório para envio de mensagens no canal.     |
