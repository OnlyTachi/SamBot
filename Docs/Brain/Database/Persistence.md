# 🗄️ Camada de Persistência Multimodal

A arquitetura de persistência da SamBot combina três tecnologias complementares: **SQLite** para integridade relacional, **Meilisearch** para buscas full-text e cache efêmero de alta velocidade, e **ChromaDB** para memória associativa e RAG vetorial.

```text
                 ┌────────────────────────────────┐
                 │     DataManager (Facade)       │
                 └───────────────┬────────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
┌──────────────┐          ┌──────────────┐            ┌──────────────┐
│  SQLite DB   │          │ Meilisearch  │            │   ChromaDB   │
│ (database.db)│          │ (Porta 7700) │            │ (Porta 8000/ │
├──────────────┤          ├──────────────┤            │    Local)    │
│  Relacional  │          │  Full-Text   │            ├──────────────┤
│ Transacional │          │  Cache TTL   │            │   Vetorial   │
└──────────────┘          └──────────────┘            │  768 Dimens. │
                                                      └──────────────┘
```

## 1. Banco Relacional: SQLite (`database.db`)

O SQLite armazena o estado transacional do bot através da facade `DataManager`. As leituras e gravações são protegidas por locks seguros de concorrência (`threading.Lock` / `asyncio.Lock`), evitando corrupção de banco sob acesso paralelo.

### Tabelas Principais

- **`users`:** Dados de perfil, saldo de XP global, nível, profissão e listas de compras (`shopping_list`).
- **`guild_configs`:** Configurações locais de cada servidor Discord (canais de notificação, prefixo customizado, personas ativas).
- **`system_metadata`:** Hashes MD5 de arquivos estáticos (`router_triggers.json`, personas, curiosidades) para controle de sincronização no boot.
- **`knowledge`:** Base declarativa de fatos gerais e autoconhecimento institucional da SamBot.

## 2. Motor Full-Text & Cache de Ofertas: Meilisearch

O **Meilisearch** atua como o motor de indexação e recuperação rápida de dados não estruturados, proporcionando busca tipotolerante (tolerante a erros ortográficos) em menos de 10ms.

### 2.1. Índice `offers` (Catálogo e Cache de Promoções)

- **Estrutura dos Documentos:**
  ```json
  {
    "id": "ml_MLB12345678",
    "title": "Monitor Gamer 144Hz IPS 24 Polegadas",
    "price": 689.9,
    "store": "Mercado Livre",
    "coupon": "MONITOR10",
    "link": "https://mercadolivre.com.br/...",
    "category": "hardware",
    "created_at": 1723984120,
    "expires_at": 1724070520
  }
  ```
- **Campos Ranqueáveis e Filtráveis:**
  - `filterableAttributes`: `["store", "category", "price", "coupon"]`
  - `sortableAttributes`: `["price", "created_at"]`

### 2.2. Política de Expiração e TTL Dinâmico

- Ofertas indexadas possuem ciclo de vida útil temporário.
- Durante a rotina noturna (`NightCycle`), documentos cujo timestamp `expires_at` seja menor que o momento presente são expurgados do índice, garantindo que buscas e orçamentos contenham apenas promoções vigentes.

## 3. Memória Vetorial

O **ChromaDB** gerencia coleções vetoriais normalizadas em **768 dimensões**, permitindo resgate de fatos contextuais e roteamento semântico.

### Coleções do Sistema

| Coleção                | Dimensões |      Métrica       | Finalidade                                                                                                 |
| :--------------------- | :-------: | :----------------: | :--------------------------------------------------------------------------------------------------------- |
| **`rotas_intencoes`**  |    768    | Cosseno (`cosine`) | Armazena gatilhos semânticos utilizados pelo `TLMRouter` para disparo de ferramentas.                      |
| **`user_memories`**    |    768    | Cosseno (`cosine`) | Memória RAG de longo prazo. Salva preferências, gostos, hobbies e fatos relevantes citados pelos usuários. |
| **`system_knowledge`** |    768    | Cosseno (`cosine`) | Conhecimento técnico e diretrizes de identidade para recuperação sob demanda.                              |

### Paridade e Equalização de Embeddings

O sistema emprega duas implementações com idêntica dimensionalidade (768d), viabilizando interoperabilidade sem necessidade de migrações estruturais:

- **Nuvem:** Google Gemini `models/text-embedding-004` (768 dimensões).
- **Local:** Ollama `nomic-embed-text` (768 dimensões).
