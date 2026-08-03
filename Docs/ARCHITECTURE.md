# 🧠 Arquitetura do Sistema — SamBot

Este guia une a visão geral da nossa arquitetura de software, a jornada de processamento dos dados e os truques de resiliência do sistema.

A SamBot evoluiu de uma estrutura simples para um ecossistema cognitivo descentralizado e modular inspirado em **Domain-Driven Design (DDD)**. O objetivo? Uma inteligência rápida, com memória de longo prazo, capaz de usar ferramentas no mundo real e que **nunca fica fora do ar** (eu acho).

## 💡 A Filosofia por Trás do Design

Em vez de disparar qualquer texto para uma IA cara e lenta, a SamBot funciona exatamente como um cérebro: possui **reflexos automáticos** (0ms de resposta), **memória de curto prazo** (contexto do chat), **memória de longo prazo** (banco vetorial para fatos) e **mãozinhas virtuais** para consultar APIs em tempo real.

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

💡 **Curiosidade — Camada 0:** Quase 30% das mensagens enviadas a bots são cumprimentos simples ("oi", "bom dia"). A SamBot intercepta esses padrões localmente com algoritmos de busca rápida (`spaCy` e `RapidFuzz`). A resposta sai instantaneamente sem gastar um único centavo de API!

> 📖 Quer entender o fluxo completo de dados em detalhe? [saiba mais](./Extra/CerebroSam.md).

## 🗂️ Estrutura Resumida do Cérebro (`/Brain`)

Organizado em subdomínios totalmente desacoplados da interface visual:

- ⚙️ **`Core/`**: O motor central. Trata entradas, faz o roteamento inteligente de ferramentas e orquestra os ciclos de pensamento.
- 🧠 **`Memory/`**: A camada de lembranças. Separa dados em tempo real (RAM), arquivos persistentes em disco com trava de segurança (`threading.Lock`), histórico recente e banco vetorial.
- 🔌 **`Providers/`**: A fábrica de conexões com IAs que garante resiliência e redundância.
- 🛠️ **`Tools/`**: As habilidades práticas (pesquisa web, rastreador de ofertas, animes e games).

> 📄 Para mapeamentos de arquivos e diretrizes de expansão, [saiba mais](./Extra/CerebroSam.md).

## 🧩 Os 4 Pilares da Cognição

### 1. Núcleo Inteligente (`Brain/Core/`)

- **Pipeline:** O maestro do sistema. Sanitiza o texto, consulta memórias, invoca ferramentas e formata a resposta em blocos ideais (_smart chunks_).
- **Limpeza:** Remove acentos, trata gírias e deduplica símbolos para facilitar o entendimento da IA.
- **NightCycle:** Rotina assíncrona noturna onde a bot "sonha": organiza arquivos, roda a economia fictícia do servidor e consolida memórias antigas.

---

### 2. Memória Inteligente (`Brain/Memory/`)

- **RAM & Disco Protegido (`DataManager/`):** Gravações em arquivos `.json` envoltadas em travas de segurança para evitar que o arquivo corrompa se duas mensagens chegarem no mesmo milissegundo.
- **Curto Prazo (`ShortTerm/`):** Guarda as últimas falas. Se a conversa passar de 10 mensagens, o sistema gera um resumo automático para economizar a memória da IA.
- **Longo Prazo & RAG (`LongTerm/`):** Utiliza **ChromaDB** para transformar conversas em coordenadas numéricas. Se você mencionar algo pessoal (_"adoro pizza"_), o módulo guarda essa preferência em segundo plano automaticamente!

---

### 3. Provedores & Resiliência (`Brain/Providers/`)

Se a IA principal falhar ou atingir limites de uso (_Rate Limit - HTTP 429_), a SamBot aciona o plano de contingência (_Failover_) sem parar a conversa:

```text
[ Requisição ] ──► 1. Google Gemini ──(Erro 429)──► 2. Groq Cloud ──(Timeout)──► 3. Ollama Local (HomeLab)
```

💡 **Curiosidade — O Castigo de Chaves & a Via Verde:**

1. **Castigo de APIs:** Se o Gemini bloquear uma chave por excesso de uso, o sistema a coloca de "molho" por 60 segundos e muda para a chave reserva sem nenhum travamento para o usuário.
2. **Via Verde (Fast-Track):** Para vetorizar textos sem perder tempo testando chaves fora do ar, o bot memoriza o caminho funcional mais rápido em `embedding_state.json` por até 7 dias.
   > ⚡ Deseja detalhes de como a cascata e o Fast-Track funcionam? [saiba mais](./Extra/CerebroSam.md).

### 4. As Ferramentas (`Brain/Tools/`)

A SamBot não chuta respostas sobre fatos atuais; ela pesquisa! Módulos especializados trazem dados em tempo real:

- 🔍 **Research:** Buscas encadeadas na Web (Google/Brave/DuckDuckGo) e análise multimodal de imagens.
- 🛒 **Shopping:** Rastreador de ofertas, buscador de cupons e comparação de preços.
- 🎮 **Games & Animes:** Cotação na Steam, banco de dados do IGDB, consulta no MyAnimeList e identificação de animes por prints de cenas!
- 🌦️ **Utilidades:** Previsão do tempo local, consulta Pokémon e servidor de mídia pessoal.

## ⚡ O Ciclo de Vida de uma Resposta

1. **Recepção:** Captura e limpa a mensagem de entrada.
2. **Camada 0:** Devolve respostas instantâneas em saudações ou dúvidas de identidade.
3. **Resgate de Memória:** Busca o contexto do chat e fatos marcantes sobre o usuário.
4. **Ferramentas:** O roteador avalia e pesquisa na internet caso necessário.
5. **Invocação:** Concatena tudo em um prompt rico e envia para a fila de IAs com _Failover_.
6. **Entrega:** Aplica o tom comportamental e responde no chat em pedaços organizados.
