# 🧠 Arquitetura do Sistema

Este guia consolida a visão estrutural do software, o fluxo detalhado de processamento de mensagens e as camadas de resiliência e failover implementadas.

A SamBot adota uma arquitetura desacoplada, assíncrona e orientada a microsserviços e eventos, inspirada em princípios de **Domain-Driven Design (DDD)**. O objetivo é assegurar respostas em baixa latência, memória associativa de longo prazo, integração autônoma com ferramentas externas e alta disponibilidade ininterrupta.

## 💡 Filosofia de Design e Camadas

Em vez de despachar qualquer entrada de texto diretamente para um modelo de linguagem (LLM) pesado, o sistema estrutura-se como um pipeline hierárquico com reflexos rápidos (0ms), memória de curto prazo, banco vetorial e execução assíncrona de ferramentas:

```text
               ┌─────────────────────────────────────────┐
               │     Entrada de Texto (Discord/Outros)   │
               └────────────────────┬────────────────────┘
                                    │
                                    ▼
                         [ Camada 0: Filtro e Limpeza ]
                       (Trata gírias, acentos e bordões)
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
   [ Intercepção Estática ]   [ Memória & RAG ]      [ Roteador de Tools ]
   (Responde sem gastar API)  (Busca fatos no ChromaDB) (Sabe se deve buscar algo)
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    │
                                    ▼
                         [ Orquestrador de LLMs ]
                (Gemini ──► Groq/Llama ──► Ollama Local)
                                    │
                                    ▼
                          [ Pós-Processamento ]
               (Aplica o humor atual e divide em blocos)

```

> 💡 **Camada 0 (Reflexos Rápidos):** Interações frequentes e triviais (cumprimentos, perguntas fixas de identidade) são interceptadas localmente via algoritmos leves (`spaCy` e `RapidFuzz`), entregando retorno imediato com consumo zero de tokens.

## 🗂️ Mapeamento Modular (`sambot/Brain`)

A inteligência da SamBot é desacoplada da camada visual do Discord e reside no módulo `Brain`:

- ⚙️ **`Core/`**: Núcleo de orquestração do pipeline cognitivo (`Pipeline.py`), rotinas noturnas assíncronas (`NightCycle.py`) e roteador semântico de intenções (`TLMRouter.py`).
- 🧠 **`Memory/`**: Camada de persistência híbrida e memória episódica:
  - `DataManager/`: Fachada transacional protegida por locks concorrentes, integrando SQLite e Meilisearch.
  - `ShortTerm/`: Contexto de conversas recentes com sumarização automática após 10 mensagens.
  - `LongTerm/`: Memória associativa vetorial indexada no **ChromaDB**.
  - `SelfKnowledge/`: Monitoramento de telemetria, estado de personas e identidade imutável.

- 🔌 **`Providers/`**: Fábrica de clientes (`LLMFactory`) e orquestrador de failover em cascata (`LLMChainOrchestrator`).
- 🛠️ **`Tools/`**: Módulos práticos de busca e automação (E-commerce, Jogos, Cultura Pop, Clima e Utilitários).

## 🧩 Os 4 Pilares da Cognição

### 1. Núcleo Inteligente (`Brain/Core/`)

- **`Pipeline.py`**: O maestro do sistema. Sanitiza a entrada, resgata contextos de memória, despacha ferramentas dinâmicas e monta o prompt mestre (`full_sys`) antes da inferência.
- **`TLMRouter.py`**: Compara o vetor da mensagem contra a base `rotas_intencoes` no ChromaDB via distância de cosseno. Se atingir o threshold calibrado ($\ge 0.74$), extrai os argumentos limpos e aciona a ferramenta sem gastar chamadas de LLM.
- **`NightCycle.py`**: Rotina de manutenção agendada para horários de baixa atividade: purga ofertas expiradas no Meilisearch, desfragmenta tabelas SQLite e consolida resumos na memória vetorial.

### 2. Memória Inteligente & Persistência (`Brain/Memory/`)

- **Padrão Facade (`DataManager`)**: Ponto de contato unificado que abstrai a complexidade do SQLite (`database.db`), dos índices tipotolerantes do Meilisearch e do armazenamento vetorial.
- **Memória de Curto Prazo (`ShortTerm/Context.py`)**: Retém os turnos recentes do chat. Conversas que excedem 10 mensagens são condensadas em resumos narrativos por modelos auxiliares para preservar a janela de contexto.
- **RAG & Aprendizado Ativo (`LongTerm/`)**: Extrai e indexa preferências e declarações pessoais relevantes no **ChromaDB** em lote assíncrono, resgatando esse contexto em interações futuras.

### 3. Provedores & Resiliência em Cascata (`Brain/Providers/`)

Quando ocorrem bloqueios por limite de taxa (_HTTP 429 - Rate Limit_), latência excessiva ou falhas de conectividade, a esteira executa o failover de forma transparente:

```text
[ Requisição ] ──► 1. Google Gemini ──(Erro 429)──► 2. Groq Cloud ──(Timeout)──► 3. Ollama Local
```

- **Quarentena de Chaves de API**: O conector do Gemini rotaciona chaves ativas (`GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`). Em caso de sobrecarga temporária, a chave afetada entra em resfriamento automático sem interromper a sessão.
- **Via Verde de Embeddings (_Fast-Track_)**: O sistema mapeia o provedor e modelo de vetorização funcional mais rápido em `embedding_state.json`, reutilizando a rota prioritária por até 7 dias para evitar testes de latência repetitivos.

### 4. Ferramentas Integradas (`Brain/Tools/`)

A SamBot não inventa dados contextuais ou voláteis:

- 🛒 **Shopping:** Comparador de preços multilojas (`ProductSearch`), extrator de cupons ativos (`CupomFinder`) e vigilância noturna de metas de preço (`PriceTracker`).
- 🎮 **Games & Animes:** Catálogo IGDB via OAuth2, cotações digitais via CheapShark, fichas técnicas no MyAnimeList (Jikan) e reconhecimento visual de cenas pelo Trace.moe.
- 🌦️ **Pesquisa & Utilitários:** Geocodificação OpenStreetMap + Open-Meteo, cálculo matemático seguro baseado em árvore sintática (AST) e buscas encadeadas na Web (Google Custom Search e Brave).

---

## ⚡ Ciclo de Vida de uma Resposta

```text
[Mensagem do Usuário]
         │
         ▼
1. Recepção & Higienização (spaCy / Limpeza léxica)
         │
         ▼
2. Avaliação da Camada 0 (Retorno em 0ms caso seja intenção estática)
         │
         ▼
3. Recuperação Contextual (Histórico recente na RAM + RAG no ChromaDB)
         │
         ▼
4. Roteamento Semântico (TLMRouter dispara Tools se score >= 0.74)
         │
         ▼
5. Composição do full_sys (Persona + Regras + Evidências de Ferramentas)
         │
         ▼
6. Inferência Resiliente (Gemini ➔ Groq ➔ Ollama local/remoto)
         │
         ▼
7. Entrega Formatada (Markdown estrito, proteção de links e Smart Chunks)

```

## 🔗 Guias Técnicos Relacionados

Para aprofundar-se nos detalhes de implementação de cada componente:

- 🧠 **[Pipeline Cognitivo e Prompts](https://www.google.com/search?q=Brain/Core/Pipeline.md)** — Regras do `full_sys`, formatação de evidências e segurança.
- 🎯 **[Roteamento Semântico](Docs/Brain/Core/Pipeline.md)** — Mecanismo vetorial do `TLMRouter` e gatilhos declarativos.
- 🗄️ **[Camada de Persistência](Docs/Brain/Database/Persistence.md)** — Estruturas do SQLite, Meilisearch e ChromaDB.
