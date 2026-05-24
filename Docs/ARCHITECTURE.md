# 🧠 Arquitetura do Sistema — SamBot

Este documento descreve a arquitetura de software, o fluxo de dados e os padrões de design aplicados no ecossistema cognitivo da **SamBot**. O projeto evoluiu de uma estrutura monolítica rasa para um design modular inspirado em **Domain-Driven Design (DDD)**, isolando regras de negócio, persistência física, interfaces de comunicação e pipelines de inteligência artificial.

---

## 1. Visão Geral do Design Arquitetural

A arquitetura da SamBot é dividida em quatro pilares fundamentais, organizados dentro do diretório `/Brain`:

1. **Interfaces de Entrada/Saída (`Agent.py`):** Camada superficial acoplada ao ecossistema do Discord. Funciona puramente como um receptor de eventos e despachante de sinais.
2. **Orquestração Cognitiva (`Core/`):** O motor de pensamento descentralizado que higieniza entradas, toma decisões de roteamento de ferramentas e constrói o contexto semântico.
3. **Subdomínios de Memória (`Memory/`):** Camada segregada por tempo e afinidade lógica, separando RAM estática, persistência estruturada em disco, contexto imediato de chat e recuperação de vetores (RAG).
4. **Provedores de Infraestrutura (`Providers/`):** Fábrica centralizada de modelos de linguagem e falhas controladas (_failover_).

```text
       [ Discord Gateway ]
               │
               ▼
        [ Brain.Agent ] (Interface Leve)
               │
               ▼
     [ Core.CognitionPipeline ] ◄───► [ Core.Limpeza ]
               │
       ┌───────┴───────┬───────────────┐
       ▼               ▼               ▼
  [ShortTerm]     [LongTerm]    [SelfKnowledge]
  (Contexto/Humor) (ChromaDB/RAG) (Identidade)
       ▲               ▲               ▲
       └───────┬───────┴───────────────┘
               ▼
       [ Memory.DataManager ] ◄────────┐
       (Cache + JSON IO Protegido)     │
                                [ Core.NightCycle ] (Cron)

```

---

## 2. Estrutura de Diretórios e Componentes

### 📁 `Brain/Core/` (Núcleo de Processamento)

- **`Pipeline.py` (CognitionPipeline):** O cérebro real do bot. Centraliza a execução assíncrona, faz o parse de anexos visuais, invoca o RAG, orquestra o roteamento de ferramentas paralelas e divide as mensagens em blocos naturais (_smart chunks_) para respeitar os limites do Discord.
- **`Limpeza.py` (LimpezaManager):** Mecanismo de higienização linguística profunda. Realiza normalização Unicode (remoção de acentos), deduplicação de símbolos, substituição de gírias da internet em tempo de execução e classificação estatística de intenções brutas.
- **`NightCycle.py` (NightCycle):** Rotina assíncrona de manutenção executada em segundo plano. Simula o mercado financeiro (flutuação de ativos e pagamento de dividendos virtuais) e consolida os logs diários em vetores históricos.

### 📁 `Brain/Memory/` (Gestão de Estado e Persistência)

#### 🔹 `DataManager/` (Camada de I/O e Acesso Físico)

- **`Manager.py` (JsonProvider):** Orquestrador de dados estruturados. Expõe interfaces limpas para o restante do sistema através do contrato `DatabaseProvider`.
- **`_json_provider.py` (JsonIO):** Classe de baixo nível que lida exclusivamente com escrita e leitura física em disco, envelopada por travas de exclusão mútua (`threading.Lock`) para evitar concorrência destrutiva entre Cogs ou loops noturnos.
- **`_cache.py` (DataCache):** Gerenciador de cache na memória RAM, impedindo gargalos de leitura em disco para configurações estáticas (identidade, prompts e canais ativos).

#### 🔹 `ShortTerm/` (Contexto Imediato e Humores)

- **`Context.py` (HistoricoManager):** Retém a memória de trabalho do canal de texto. Implementa compressão dinâmica via IA: se a sessão de chat ultrapassar 10 mensagens, o módulo gera um resumo narrativo compacto do bloco antigo, liberando a janela de contexto da LLM.
- **`_expressions.py` (ExpressoesManager):** Analisa a carga emocional do input do usuário e injeta reações idiomáticas e comportamentais na resposta final, humanizando o tom da conversa.

#### 🔹 `LongTerm/` (Memória Episódica e RAG)

- **`VectorStore.py` (VectorStore):** Wrapper de alto nível sobre o banco de dados vetorial **ChromaDB** persistente. Gerencia e pesquisa coleções analíticas utilizando distância por cosseno.
- **`_embeddings.py` (SmartEmbeddingFunction):** Motor otimizado de vetorização de texto. Implementa a **Via Verde (Fast Track)** com cache de estado de 7 dias, salvando o último provedor e par de chaves funcionais para mitigar os gargalos de latência causados por erros 404 em modelos antigos.
- **`_learning.py` (AprendizadoAtivo):** Analisa assincronamente as interações à procura de fatos biográficos permanentes do usuário através de filtros cognitivos baseados em LLM, salvando-os em tempo real e sinalizando o aprendizado visualmente no chat.

#### 🔹 `SelfKnowledge/` (Auto-Imagem e Persona)

- **`Identity.py` (AutoConhecimento):** Responsável por interceptar dúvidas sobre a natureza técnica, autoria ou stack do bot, construindo prompts baseados estritamente na configuração contida em `identity.json`.
- **`Curiosidades.py` (CuriosidadeManager):** Gerencia gatilhos probabilísticos para enriquecer os prompts do sistema com fatos interessantes ou curiosidades adicionais, quebrando a linearidade das respostas da IA.

---

## 3. Fluxo Cognitivo da Resposta (A Pipeline)

Quando uma mensagem é postada em um canal monitorado, o fluxo segue rigorosamente a seguinte linha do tempo assíncrona:

```text
[Mensagem] -> Agent (Filtra Comandos/Bots) -> Pipeline.Limpeza (Normaliza Input)
   │
   ├──> SelfKnowledge.Identity (Verifica Inquérito sobre Identidade) -> Resposta Direta
   │
   └──> Fluxo Geral:
         ├──> LongTerm._embeddings (Ativa Via Verde) -> VectorStore.query_relevant (RAG)
         ├──> Core.Pipeline (Analisa Imagens / Roteia Ferramentas Paralelas em JSON)
         ├──> ShortTerm.Context (Recupera e Comprime Histórico Recente se > 10 msgs)
         │
         ▼
   [Montagem do Prompt Final] -> Providers.LLMFactory (Invocação com Failover)
         │
         ▼
   [Pós-Processamento] -> ShortTerm._expressions (Injeta Humor) -> Envio via Smart Chunks

```

---

## 4. Resiliência de IA e Mecanismo Fast-Track

Para garantir que a SamBot opere com alta disponibilidade e latência reduzida, duas arquiteturas de contingência foram integradas:

### A. Cascata de Failover de LLM (`LLMFactory`)

Caso o provedor principal sofra instabilidades, o sistema rotaciona automaticamente sua execução em camadas descendentes:

1. **Google Gemini Cloud:** (Utilizando rotação automática de múltiplas chaves API em caso de Rate Limit - Erro 429).
2. **Ollama Remoto:** Instância secundária em nuvem privada.
3. **Ollama Local (Docker):** Modelo local compacto (`qwen2.5:1.5b`) rodando localmente no HomeLab, garantindo que o processamento lógico nunca seja interrompido por falta de internet.

### B. Via Verde de Embeddings (`_embeddings`)

Para mitigar os tempos de resposta que ultrapassavam 13 segundos devido à checagem sequencial de chaves e modelos depreciados, o sistema adota um padrão de estado preferencial persistido via `DataManager`:

- Ao encontrar uma rota de embedding válida (ex: `models/embedding-004` com a chave do índice `X` ou `Ollama Local`), o estado é gravado em `embedding_state.json`.
- As próximas requisições ignoram a busca em cascata e efetuam o bypass direto para o canal vitorioso.
- Uma janela temporal de **7 dias** força a revalidação do ecossistema, garantindo adaptabilidade caso chaves expirem ou modelos novos surjam.

---

## 5. Diretrizes para Expansão da Arquitetura

Ao adicionar novas funcionalidades ao ecossistema da bot, respeite os seguintes princípios:

- **Ferramentas externas (Tools):** Devem ser criadas na pasta `/Brain/Tools`, contendo tratamento de erro isolado, e mapeadas em `TOOL_CLASSES` dentro do arquivo `Brain/Core/Pipeline.py` para carregamento dinâmico.
- **Dados e Negócios:** Funções lógicas que alteram perfis, moedas ou economias devem interagir única e exclusivamente através das assinaturas expostas pelo `data_manager` vindo de `Brain/Memory/DataManager`, respeitando o isolamento do cache e as travas de thread do arquivo físico.
- **Mudanças na Persona:** Modificações comportamentais profundas devem ser alteradas adicionando arquivos `.txt` na pasta `Data/Prompts/` e alternando o nome da persona no banco de canais, sem tocar nas estruturas de código do `Pipeline`.

---
