# 🔧 Utilitários & Informações Gerais

O módulo de utilitários da SamBot (`sambot/Modules/Utility/`) reúne ferramentas de diagnóstico, consulta de telemetria, inspeção de perfis e o catálogo interativo de ajuda (`HelpSystem`).

## 📖 1. HelpSystem Dinâmico (`+ajuda` / `/help`)

O sistema de ajuda é renderizado dinamicamente a partir dos Cogs e comandos atualmente carregados na memória da aplicação, garantindo que novos módulos apareçam na listagem sem necessidade de documentação estática manual.

```text
┌────────────────────────────────────────────────────────┐
│  Central de Comandos — SamBot                          │
│  Selecione uma categoria no menu suspenso abaixo:      │
├────────────────────────────────────────────────────────┤
│  [ Menu de Seleção: 🎵 Música | 💰 Economia | ... ]    │
└────────────────────────────────────────────────────────┘
```

### Funcionalidades do HelpSystem:

- **Menu Suspenso Interativo (`discord.ui.Select`):** Divide os comandos por módulos (`Áudio`, `Economia`, `Administração`, `Utilidades`, `IA`).
- **Filtragem por Permissões:** Oculta comandos administrativos para membros que não possuem privilégios de execução no servidor.
- **Detalhamento de Comando:** Permite detalhar um comando específico (`+ajuda <comando>`), exibindo aliases, formato de argumentos e exemplos práticos.

## 📊 2. Informações de Servidor e Usuário

Comandos para inspeção detalhada de dados do Discord:

### 2.1. `+userinfo` (ou `/userinfo [@membro]`)

Gera um relatório do membro com os seguintes dados:

- Tag, ID numérico e avatar em alta resolução.
- Data de criação da conta e data de entrada no servidor atual.
- Lista de cargos e papel mais alto na hierarquia.
- Badges ativas (Discord HypeSquad, Nitro, Desenvolvedor, etc.).
- Nível de XP global e profissão cadastrada no sistema de economia.

### 2.2. `+serverinfo` (ou `/serverinfo`)

Compila a ficha técnica da guilda:

- Nome, ID e proprietário do servidor.
- Quantidade total de membros (discriminando humanos e bots).
- Contagem de canais (texto, voz, categorias e palcos).
- Quantidade de emojis personalizados e figurinhas.
- Nível de Boost e total de impulsos ativos.

## ⚙️ 3. Diagnósticos e Telemetria do Bot

Comandos dedicados ao acompanhamento operacional da aplicação:

| Comando    | Descrição                              | Dados Exibidos                                                                           |
| :--------- | :------------------------------------- | :--------------------------------------------------------------------------------------- |
| `+ping`    | Latência da conexão em tempo real.     | Latência do WebSocket Discord e tempo de resposta da API REST em milissegundos.          |
| `+botinfo` | Ficha técnica e métricas do processo.  | Tempo de atividade (_uptime_), consumo de memória RAM, versão do Python e do discord.py. |
| `+status`  | Integridade das dependências externas. | Conectividade com SQLite, Meilisearch, ChromaDB, nós Lavalink e provedores de LLM.       |
