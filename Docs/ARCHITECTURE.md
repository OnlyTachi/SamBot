## 📂 Estrutura de Diretórios

A arquitetura segue o padrão de **Cogs** do Discord.py, mas expande a lógica de IA em um módulo dedicado chamado `Brain`.

```text
sambot/
├── Core/                 # Infraestrutura Base (O "Corpo")
│   ├── Bot.py            # Gerencia conexão Discord, Sharding e Events.
│   └── Logger.py         # Sistema de logs centralizado e formatado.
│
├── Brain/                # O "Cérebro" Cognitivo (IA e RAG)
│   ├── Agent.py          # Orquestrador: Recebe msg -> Decide Ferramenta -> Gera Resposta.
│   ├── Providers/
│   │   └── LLMFactory.py # Singleton: Gerencia rotação de chaves e escolha de modelo.
│   ├── Memory/
│   │   ├── VectorStore.py    # RAG: Gerencia ChromaDB e Embeddings Híbridos.
│   │   ├── DataManager.py    # I/O Thread-safe para arquivos JSON.
│   │   └── AutoConhecimento.py # Guardrails: Identidade e limites da IA.
│   └── Tools/            # Tool-calling: Ferramentas que a IA pode acionar.
│
├── Modules/              # Cogs Tradicionais (Comandos Modularizados)
│   ├── Admin/            # Gestão, Segurança e Auditoria
│   │   ├── Auditoria.py  # Logs de eventos (Níveis 1-6)
│   │   ├── AutoMod.py    # Proteção automática configurável
│   │   ├── Avisos.py     # Mural público de punições
│   │   └── Moderacao.py  # Comandos manuais (ban, mute, etc.)
│   ├── Audio/            # Sistema de Música (Wavelink/Lavalink)
│   ├── Economy/          # Ecossistema Financeiro
│   │   ├── Cosmeticos/   # Loja e gestão de fundos de perfil
│   │   ├── Diversao/     # Casino e Bolsa de Valores
│   │   └── Recompensas/  # Work, Daily e Sistema de Níveis
│   ├── Fun/              # Interações Sociais, Dados e Ações RP
│   ├── Utility/          # Informações e Help Dinâmico
│   └── Developer/        # Ferramentas de infraestrutura (Dono)
│
├── Data/                 # Persistência e Assets
│   ├── Knowledge/        # JSONs de conhecimento (fatos, atividades)
│   ├── Persistence/      # DB Vetorial e configurações de canais
│   ├── Prompts/          # Personas e System Messages (padrao.txt)
│   └── Assets/           # Imagens, fontes e recursos visuais
│
└── main.py               # Entry point da aplicação

```

---

## 🧠 O Pipeline Cognitivo

Quando um usuário menciona o bot, o seguinte fluxo ocorre:

1. **Percepção (`Agent.py`):**

- A mensagem é recebida e higienizada (limpeza de menções e IDs).
- O sistema diferencia se é um comando prefixado (ex: `!play`) ou uma interação de linguagem natural.

2. **Recuperação de Memória (`VectorStore.py`):**

- O texto é convertido em um **Embedding**.
- **Failover de Embedding:** O sistema prioriza o **Ollama (Local)**. Se houver timeout de 2s, alterna automaticamente para a **API do Google**.
- O **ChromaDB** recupera os 3 fatos mais relevantes para o contexto atual.

3. **Deliberação (`LLMFactory.py`):**

- **Montagem do Prompt:** Combina `[Persona]` + `[Memória]` + `[Histórico Recente]` + `[Mensagem Atual]`.
- **Gestão de Chaves:** Se a API retornar erro `429` (Rate Limit), o Factory rotaciona a chave e reenvia a requisição instantaneamente.

4. **Ação/Resposta:**

- Se a IA decidir que precisa de dados externos (ex: Clima), ela gera um JSON de _Function Calling_.
- O `Agent.py` executa a ferramenta, anexa o resultado e solicita a resposta final em linguagem natural.

---

## 🔄 Ciclo de Status Dinâmico

O `Bot.py` mantém um loop de controle de presença (`status_loop`) que prioriza a atividade atual do bot:

- **Prioridade 1 (Música):** Se `is_music_playing` for `True`, o status exibe a faixa atual via Wavelink.
- **Prioridade 2 (Aleatório):** Caso contrário, o bot consulta `Data/Knowledge/atividades.json` e escolhe uma frase baseada nas listas de atividades disponíveis.

---

## 🛡️ Camadas de Segurança

| Camada          | Função                                                        | Implementação                           |
| --------------- | ------------------------------------------------------------- | --------------------------------------- |
| **Identidade**  | Impede que a IA saia do personagem ou revele o sistema.       | Prompt System + `identity.json`         |
| **Integridade** | Evita corrupção de dados em acessos simultâneos.              | `threading.Lock` no `DataManager.py`    |
| **Redundância** | Garante que o bot responda mesmo sem internet (parcialmente). | Failover automático para Ollama (Local) |

---
