
## 📂 Estrutura de Diretórios

A arquitetura segue o padrão de **Cogs** do Discord.py, mas expande a lógica de IA em um módulo dedicado chamado `Brain`.

```text
sambot/
├── Core/
│   ├── Bot.py            # O "Corpo". Gerencia conexão Discord, Sharding e Events.
│   └── Logger.py         # Sistema de logs centralizado e formatado.
├── Brain/                # O "Cérebro" Cognitivo
│   ├── Agent.py          # Orquestrador. Recebe msg -> Decide Ferramenta -> Gera Resposta.
│   ├── Providers/
│   │   └── LLMFactory.py # Factory Singleton. Gerencia rotação de chaves e escolha de modelo.
│   ├── Memory/
│   │   ├── VectorStore.py    # RAG. Gerencia ChromaDB e Embeddings Híbridos.
│   │   ├── DataManager.py    # I/O Thread-safe para arquivos JSON.
│   │   └── AutoConhecimento.py # Guardrails de identidade.
│   └── Tools/            # Ferramentas que a IA pode "chamar" (Weather, Search, etc).
├── Modules/              # Cogs Tradicionais (Comandos)
│   ├── Audio/            # Music.py e integração Lavalink.
│   ├── Fun/              # Dados, Ações RP.
│   └── Utility/          # Ajuda, Identificação.
├── Data/                 # Persistência de Dados
│   ├── Knowledge/        # JSONs de conhecimento (fatos, atividades).
│   ├── Persistence/      # Banco de dados Vetorial e configs de canais.
│   └── Prompts/          # Personas (padrao.txt, louco.txt).
└── main.py               # Entry point da aplicação.

```

---

## 🧠 O Pipeline Cognitivo

Quando um usuário menciona o bot, o seguinte fluxo ocorre:

1. **Percepção (`Agent.py`):**
* A mensagem é recebida e higienizada (limpeza de menções e IDs).
* O sistema diferencia se é um comando prefixado (ex: `!play`) ou uma interação de linguagem natural.


2. **Recuperação de Memória (`VectorStore.py`):**
* O texto é convertido em um **Embedding**.
* **Failover de Embedding:** O sistema prioriza o **Ollama (Local)**. Se houver timeout de 2s, alterna automaticamente para a **API do Google**.
* O **ChromaDB** recupera os 3 fatos mais relevantes para o contexto atual.


3. **Deliberação (`LLMFactory.py`):**
* **Montagem do Prompt:** Combina `[Persona]` + `[Memória]` + `[Histórico Recente]` + `[Mensagem Atual]`.
* **Gestão de Chaves:** Se a API retornar erro `429` (Rate Limit), o Factory rotaciona a chave e reenvia a requisição instantaneamente.


4. **Ação/Resposta:**
* Se a IA decidir que precisa de dados externos (ex: Clima), ela gera um JSON de *Function Calling*.
* O `Agent.py` executa a ferramenta, anexa o resultado e solicita a resposta final em linguagem natural.



---

## 🔄 Ciclo de Status Dinâmico

O `Bot.py` mantém um loop de controle de presença (`status_loop`) que prioriza a atividade atual do bot:

* **Prioridade 1 (Música):** Se `is_music_playing` for `True`, o status exibe a faixa atual via Wavelink.
* **Prioridade 2 (Aleatório):** Caso contrário, o bot consulta `Data/Knowledge/atividades.json` e escolhe uma frase baseada nas listas de atividades disponíveis.

---

## 🛡️ Camadas de Segurança

| Camada | Função | Implementação |
| --- | --- | --- |
| **Identidade** | Impede que a IA saia do personagem ou revele o sistema. | Prompt System + `identity.json` |
| **Integridade** | Evita corrupção de dados em acessos simultâneos. | `threading.Lock` no `DataManager.py` |
| **Redundância** | Garante que o bot responda mesmo sem internet (parcialmente). | Failover automático para Ollama (Local) |

---
