# Documentação Técnica: Guia Arquitetural & Cognitivo

## O Cérebro da SamBot

Este guia une a visão geral da nossa arquitetura de software, a jornada de processamento dos dados e os truques de resiliência do sistema.

A SamBot evoluiu de um script monolítico simples para um ecossistema cognitivo descentralizado e modular. O objetivo principal? Criar uma inteligência que responda rápido, tenha memória de longo prazo, saiba consultar ferramentas no mundo real e nunca fique fora do ar, mesmo quando as APIs de IA falharem.

## 💡 A Filosofia por Trás do Design

Em vez de disparar qualquer texto cru do usuário diretamente para uma LLM (Modelo de Linguagem) cara e lenta, a SamBot funciona como o cérebro humano: possui **reflexos automáticos** (respostas instantâneas em 0ms), **memória de curto prazo** (contexto do chat), **memória de longo prazo** (banco vetorial para fatos e preferências) e **mãozinhas virtuais** para consultar dados ao vivo, como ofertas, cotações e animes.

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
   [ Intercepção Estática ]   [ Memória & RAG ]         [ Roteador de Tools ]
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

💡 **Curiosidade:** Sabia que quase 30% das interações em bots de chat são saudações simples como _"oi"_, _"bom dia"_ ou _"quem é você?"_? A SamBot intercepta esses padrões localmente usando processamento de texto ultrarrápido (com bibliotecas como `spaCy` e `RapidFuzz`). Isso significa que a resposta sai instantaneamente, economizando tempo e sem gastar um único centavo com tokens de API!

## 🗂️ Mapeamento do Cérebro (`/Brain`)

Toda a lógica inteligente reside no diretório `/Brain`, dividida em módulos autônomos para que a cognição não fique acoplada ao Discord:

```text
Brain/
├── Agent.py                     # Interface Receptor Discord (Cog)
├── Core/                        # Núcleo Cognitivo e Orquestração
│   ├── Pipeline.py              # Pipeline central da SamBot (CognitionPipeline)
│   ├── Limpeza.py               # Lematização local, gírias e casamento elástico
│   ├── NightCycle.py            # Ciclo de manutenção, resumos e mercado fictício
│   └── Router/                  # Roteador TLM (Tool Language Model)
│       ├── IntentClassifier.py  # Classificação por regras e spaCy/RapidFuzz
│       └── TLMRouter.py         # Roteamento semântico com vetorização local
├── Providers/                   # Abstração e Drivers de IAs
│   ├── BaseLLM.py               # Interface abstrata para drivers de IA
│   ├── LLMChainOrchestrator.py  # Orquestrador com failover automático
│   ├── LLMFactory.py            # Fábrica Singleton para instanciação de cadeias
│   └── Clients/
│       ├── GeminiProvider.py    # Driver Gemini
│       ├── GroqProvider.py      # Driver Groq
│       └── OllamaProvider.py    # Driver Ollama
├── Memory/                      # Sistema de Memória Multicamada
│   ├── DataManager/             # Abstração de I/O em disco com cache em RAM
│   ├── LongTerm/                # RAG e Banco Vetorial (ChromaDB)
│   ├── ShortTerm/               # Otimização de contexto e compressão histórica
│   └── SelfKnowledge/           # Mapeamento de identidade e autoconhecimento
└── Tools/                       # Módulos de Ferramentas do Ecossistema
    ├── Research/                # WebSearch, VisionTool e SearchImages
    ├── Shopping/                # ProductSearch, CouponFinder, PriceTracker e ShoppingList
    ├── Games/                   # IGDB, CheapShark, Currency e GameTool
    ├── Anime/                   # JikanSearch, TraceRecognizer e AnimeTool
    ├── PokemonTool.py           # PokAPI
    ├── WeatherTool.py           # OpenMeteo + Nominatim
    ├── JellyfinTool.py          # Catálogo e recomendações de mídia local
    └── MusicRecTool.py          # Recomendações de áudio

```

## 🧩 Os 4 Pilares da Cognição

### 1. Núcleo Inteligente (`Brain/Core/`)

- **`Pipeline.py`:** O maestro do sistema. Recebe a mensagem sanitizada, consulta as memórias, decide se precisa de ferramentas externas, orquestra o prompt final e divide a resposta em pedaços naturais (_smart chunks_) para não estourar o limite de caracteres do chat.

- **`Limpeza.py`:** Faz a higienização do texto. Remove acentos duplicados, limpa símbolos e converte gírias da internet em tempo real para ajudar na identificação correta das intenções do usuário.

- **`NightCycle.py`:** Uma rotina assíncrona que roda durante a madrugada. Enquanto o servidor descansa, o bot "sonha": consolida registros diários, calcula flutuações do mercado financeiro fictício do servidor e otimiza o banco de memórias.

💡 **Curiosidade — O "Sono" da IA:** Assim como seres humanos precisam dormir para consolidar memórias, sistemas **RAG** (_Retrieval-Augmented Generation_) sofrem degradação de performance se acumularem dados brutos indefinidamente. O `NightCycle` limpa dados temporários e cria resumos consolidados, garantindo buscas vetoriais extremamente rápidas mesmo após meses de uso.

---

### 2. Memória Inteligente (`Brain/Memory/`)

A memória é dividida rigorosamente para simular a cognição humana:

- **RAM e Disco Seguro (`DataManager/`):** Utiliza um cache em memória RAM para acessos ultrarrápidos a configurações. Para gravar dados em arquivo `.json`, aplica travas de exclusão mútua (`threading.Lock`), garantindo integridade total mesmo se várias conversas acontecerem exatamente no mesmo milissegundo.

- **Curto Prazo (`ShortTerm/`):** Mantém a linha de raciocínio da conversa. Quando o papo passa de 10 mensagens, o módulo aciona uma IA secundária para resumir o trecho antigo, economizando espaço na janela de contexto.

**Longo Prazo e RAG (`LongTerm/`):**

- **`VectorStore.py`:** Banco de dados vetorial baseado em **ChromaDB**. Transforma trechos de conversas e fatos em coordenadas matemáticas (vetores) através de distância por cosseno.

- **`_learning.py` (Aprendizado Ativo):** Se você disser _"Meu prato favorito é lasanha"_, o bot detecta em segundo plano que esta é uma informação pessoal permanente e a salva no banco de dados vetorial sem travar ou atrasar a resposta atual.

---

### 3. Provedores & Resiliência (`Brain/Providers/`)

O que acontece se o Gemini oscilar? Ou se você atingir o limite de chamadas gratuitas (_HTTP 429 - Rate Limit_)? A SamBot conta com um mecanismo de contingência em cascata (_Failover_):

```text
[ Requisição de Resposta ]
          │
          ▼
   1. Google Gemini Cloud  ──(Erro 429 ou Falha)──► Castigo temporário (60s)
          │                                              │
          ├──────────────────────────────────────────────┘
          ▼
   2. Groq Cloud (Llama 3.1) ──(Timeout ou Falha)──►
          │
          ▼
   3. Ollama Local (Docker / HomeLab) ──► Modelo local `qwen2.5:1.5b` (Garantia de 100% Uptime)

```

💡 **Curiosidade — O Castigo das Chaves API:** O driver do Gemini faz rotação automática entre múltiplas chaves de API. Caso a `chave_01` atinja o limite do plano gratuito, o sistema a coloca em um "castigo" de 60 segundos e alterna instantaneamente para a `chave_02` sem que o usuário final perceba qualquer gargalo.

#### A "Via Verde" de Embeddings (_Fast-Track_)

Converter texto em números (vetores) pode gerar latência se o serviço remoto demorar. Para resolver isso, foi criado o padrão **Fast-Track**:

1. Quando o sistema encontra uma rota de embedding funcional, ele salva esse atalho em um arquivo leve (`embedding_state.json`).

2. As requisições seguintes pulam os testes de conexão e vão direto pela **Via Verde**.

3. A cada **7 dias**, o sistema renova a checagem para descobrir se há opções mais rápidas disponíveis.

---

### 4. As Ferramentas (`Brain/Tools/`)

A SamBot não inventa informações sobre o mundo real; ela pesquisa! Módulos especializados são ativados pelo roteador semântico:

- 🔍 **Research:** Realiza buscas na web integrando Google, Brave e DuckDuckGo, além de interpretar imagens enviadas nos chats via `VisionTool`.

- 🛒 **Shopping:** Rastreador de ofertas, agregador de preços (Mercado Livre e raspagem de dados) e buscador de cupons de desconto.

- 🎮 **Games:** Consulta de preços de jogos via CheapShark/Steam, metadados do IGDB e cotação de moedas.

- 🍥 **Anime:** Integração com Jikan API (MyAnimeList) e busca por imagem no Trace.moe (descobre o nome do anime enviando apenas um frame da cena!).

- 🌦️ **Utilidades:** Previsão do tempo (OpenMeteo), catálogo de mídia local (Jellyfin) e dados da PokAPI.

---

## ⚡ O Ciclo de Vida de uma Resposta

Quando uma mensagem é enviada pelo usuário, o fluxo cognitivo executa os seguintes passos:

1. **Recepção (`Agent.py`):** Captura a mensagem e descarta interações com outros bots.

2. **Normalização (`Limpeza.py`):** Trata o texto, remove acentos e analisa o formato da entrada.

3. **Checagem Rápida (Camada 0):** Se for uma conversa padrão ou dúvida de identidade (`identity.json`), responde imediatamente sem acionar modelos pagos.

4. **Resgate de Memória & RAG (`LongTerm`):** Consulta fatos lembrados sobre o usuário e recupera o resumo contextual da conversa recente (`ShortTerm`).

5. **Roteador de Ferramentas (`TLMRouter`):** Identifica se a dúvida requer busca externa (ex: _"Qual a previsão do tempo para hoje?"_) e executa a ferramenta necessária.

6. **Invocação com Failover (`LLMFactory`):** Concatena o histórico, os fatos lembrados e o resultado das ferramentas em um único prompt enriquecido, enviando-o para a cadeia resiliente de LLMs.

7. **Humanização (`_expressions.py`):** Aplica a camada emocional e comportamental do bot e transmite o texto em blocos limpos para o chat.

## 💻 Como Executar o Cérebro em Outras Plataformas

💡 **Curiosidade:** Como a lógica do cérebro (`CognitionPipeline`) foi projetada de forma independente do Discord, você pode reutilizá-la em uma API REST com FastAPI, em bots do Telegram, WhatsApp ou scripts via terminal CLI

```python
import asyncio
from Brain.Core.Pipeline import CognitionPipeline

async def main():
    # Inicializa a cognição sem dependência de interface
    brain = CognitionPipeline(bot=None)

    usuario_id = "user_123"
    nome_usuario = "DevCurioso"
    mensagem = "Você lembra qual é o meu jogo favorito?"

    # Processa a mensagem por todo o fluxo cognitivo
    resposta = await brain.gerar_resposta_pura(
        user_id=usuario_id,
        user_name=nome_usuario,
        clean_text=mensagem
    )

    print(f"SamBot: {resposta}")

if __name__ == "__main__":
    asyncio.run(main())

```

---
