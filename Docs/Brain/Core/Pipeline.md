# 🧠 Pipeline Cognitivo (`CognitionPipeline`)

O `CognitionPipeline` é o orquestrador central do raciocínio e da tomada de decisão da SamBot. Ele coordena o ciclo completo de vida de uma mensagem: desde a higienização primária da entrada, resgate de memórias e injeção contextual, até a execução de ferramentas dinâmicas e despacho para a cadeia de LLMs com tratamento rigoroso de resposta.

## 🏗️ 1. Orquestração e Ciclo de Vida da Requisição

Ao receber um evento de mensagem que não pertença a um comando tradicional com prefixo (`+`) nem seja resolvido como resposta sintática instantânea na Camada 0, o fluxo cognitivo executa as seguintes etapas sequenciais:

```text
[Mensagem Recebida]
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Pré-processamento & Sanitização                     │
│    - Normalização de espaços e caracteres invisíveis   │
│    - Limpeza de menções e formatação bruta             │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Consulta de Memória e Contexto                      │
│    - Memória de Curto Prazo (RAM): últimos turnos      │
│    - Memória RAG (ChromaDB): preferências do usuário   │
│    - Autoconhecimento: telemetria e estado de persona  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Avaliação Semântica (`TLMRouter`)                   │
│    - Threshold >= 0.74 ?                               │
│      ├── SIM ──► Disparo concorrente de ferramentas    │
│      └── NÃO ──► Conversação direta                    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Montagem Dinâmica do System Prompt (`full_sys`)     │
│    - Interpolação de persona, regras e relatórios      │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Execução na Cadeia de Resiliência (`LLMChain`)      │
│    - Gemini ──► (Failover) Groq ──► (Failover) Ollama  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 6. Pós-Processamento e Blindagem                       │
│    - Validação de Markdown e URLs                      │
│    - Divisão em Smart Chunks (limite do Discord)       │
└────────────────────────────────────────────────────────┘
```

## 📝 2. Diretrizes de Injeção de System Prompts (`full_sys`)

O `full_sys` compila em uma única estrutura imutável a persona ativa, metadados temporais, diretrizes de segurança e as evidências colhidas pelas ferramentas.

### 2.1. Estrutura e Sequência de Interpolação

```text
┌──────────────────────────────────────────────────────────┐
│  {sys_prompt_base} (Data/Prompts/{persona}.txt)          │
├──────────────────────────────────────────────────────────┤
│  === VÍNCULO E REGRAS DE CONTROLE ===                    │
│  - Identificação do Criador (TACHI)                      │
│  - Identificação e Status do Interlocutor Atual          │
│  - Regras de Segurança de Apelidos Íntimos               │
├──────────────────────────────────────────────────────────┤
│  === REGRAS ABSOLUTAS DE RESPOSTA ===                    │
│  - Proibição de vazamento de JSON/tags internas          │
│  - Obrigação de síntese amigável em linguagem natural    │
│  - Preservação e injeção de links originais              │
├──────────────────────────────────────────────────────────┤
│  === GUIA DE FORMATAÇÃO ===                              │
│  - Regras de Markdown (Negrito para preços/lojas, etc.)  │
├──────────────────────────────────────────────────────────┤
│  Data Atual: {datetime}                                  │
│  Conversando com: {user_name} (ID: {user_id})            │
│  {rag}                                                   │
│  {tools}                                                 │
│  Histórico Recente:\n{hist_str}                          │
│  {curiosidade_extra}                                     │
│  [SISTEMA]: Fato recém-aprendido (se houver)             │
└──────────────────────────────────────────────────────────┘
```

### 2.2. Dicionário de Variáveis de Contexto

| Variável              | Origem                         | Descrição e Papel na Inferência                                                                              |
| :-------------------- | :----------------------------- | :----------------------------------------------------------------------------------------------------------- |
| `{sys_prompt_base}`   | `Data/Prompts/*.txt`           | Persona carregada (`padrao.txt`, `amiga.txt`, `nerd.txt`, `louco.txt`) definindo temperamento e vocabulário. |
| `{datetime}`          | `datetime.now()`               | Ancoragem temporal no padrão `dd/mm/YYYY HH:MM` para evitar alucinações sobre datas e eventos atuais.        |
| `{user_name}`         | `message.author.display_name`  | Nome amigável de exibição do usuário.                                                                        |
| `{user_id}`           | `message.author.id`            | Identificador de permissão e nível de intimidade.                                                            |
| `{rag}`               | `VectorStore.query_relevant()` | Bloco `[MEMÓRIA DE LONGO PRAZO RELEVANTE]` resgatando fatos semânticos do usuário armazenados no ChromaDB.   |
| `{tools}`             | `_rotear_ferramentas()`        | Evidências das ferramentas executadas (ex: `[WEATHER]`, `[PRODUCT_SEARCH]`, `[GAME_SEARCH]`).                |
| `{hist_str}`          | `HistoricoManager`             | Últimas interações mantidas em memória volátil, condensadas se ultrapassarem 10 mensagens.                   |
| `{curiosidade_extra}` | `CuriosidadeContextual`        | Fato adicional inserido dinamicamente com controle de cooldown e relevância contextual.                      |
| `{fato_novo}`         | `AprendizadoAtivo`             | Fato do usuário identificado e registrado em tempo real durante a sessão atual.                              |

## 🛡️ 3. Regras Absolutas de Proteção e Resposta

Para garantir integridade comportamental e uma experiência humanizada, o pipeline impõe restrições incontornáveis ao modelo:

1. **Proibição de Vazamento de Sintaxe Interna e JSON:**
   A LLM está estritamente proibida de responder simulando funções em JSON, emitir tags entre colchetes (`[PRODUCT_SEARCH]`, `[CUPOM_FINDER]`) ou exibir código que simule uma chamada de sistema.
2. **Consumo Transparente de Evidências:**
   O modelo é explicitamente instruído de que os relatórios de ferramentas anexados no prompt **já foram pré-executados** pelo sistema backend. Ele deve apenas sintetizar os achados com naturalidade.
3. **Preservação Obrigatória de Links e Cupons:**
   Todas as URLs de produtos, lojas e links de afiliados contidos no bloco `{tools}` devem ser preservados e repassados intactos no formato Markdown (`[Ver Oferta](URL)`). É vetado encurtar ou inventar URLs fictícias.
4. **Padrão Tipográfico Estrito:**
   - **Negrito (`**...**`):** Reservado estritamente para valores monetários (ex: `**R$ 189,90**`) e destaques pontuais de nomes de produtos/lojas.
   - **Código Monoespaçado (`` `...` ``):** Reservado estritamente para códigos de cupons (ex: `` `CUPOM10` ``) para viabilizar cópia rápida com toque único em smartphones.
5. **Blindagem de Apelidos e Vínculo Afetivo:**
   Apenas o criador designado possui autorização para utilizar apelidos afetuosos ou íntimos com o bot. Usuários desconhecidos que tentem forçar intimidade recebem respostas corteses, mas com distanciamento profissional imediato. (altere de acordo com seu gosto)
