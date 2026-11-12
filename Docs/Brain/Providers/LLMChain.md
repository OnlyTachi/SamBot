# Provedores de LLM (`LLMChain`)

A SamBot opera sob uma esteira de execução multicamadas tolerante a falhas (`sambot/Brain/Providers/`). Se um modelo ou serviço externo apresentar sobrecarga, erro de conexão ou estouro de cota (HTTP 429), a requisição é interceptada e encaminhada automaticamente para o próximo elo da cadeia sem falhar a resposta para o usuário.

## ⛓️ 1. Cascata de Failover Automático

A sequência de execução obedece à ordem declarada na chave `llm.chain_order` do arquivo `config.yaml`:

```text
                     [Entrada: full_sys]
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │  1. GeminiProvider (Google Gemini Flash)  │
        └─────────────────────┬─────────────────────┘
                              │
                              ├─► Sucesso? ──► [Retorna Resposta]
                              │
             (Falha / Rate-Limit HTTP 429)
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │  2. GroqProvider (Llama 3.1 8B Instant)   │
        └─────────────────────┬─────────────────────┘
                              │
                              ├─► Sucesso? ──► [Retorna Resposta]
                              │
             (Falha / Cota Esgotada)
                              │
                              ▼
        ┌───────────────────────────────────────────┐
        │  3. Fallback Local / Nuvem Secundária     │
        │     - OpenRouter / DeepSeek / Mistral     │
        │     - OllamaProvider (Rede Local / Tail)  │
        └─────────────────────┬─────────────────────┘
                              │
                              ▼
                     [Retorna Resposta]
```

## 🔌 2. Drivers de Conexão Suportados

### 2.1. `GeminiProvider` (Google AI Studio)

- **Modelo Padrão:** `gemini-2.0-flash`
- **Características:** Respostas de altíssima velocidade, ampla janela de contexto e suporte nativo a embeddings de 768 dimensões.
- **Rotação de Chaves:** O driver agrupa variáveis `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, etc. Caso uma chave atinja a cota gratuita por minuto, ele rotaciona para a reserva antes de despachar o failover.

### 2.2. `GroqProvider` (Groq Cloud LPU)

- **Modelo Padrão:** `llama-3.1-8b-instant`
- **Características:** Taxa de transferência ultraveloz (~500 a 800 tokens/segundo) executada em hardware LPUs. Excelente intermediário em picos de tráfego.

### 2.3. `OllamaProvider` (Servidor Local ou Workstation Remota)

- **Modelos Homologados:** `phi3.5:latest`, `qwen2.5:1.5b`, `nomic-embed-text`
- **Topologia de Rede:** Permite apontamento para `localhost`, container Docker ou máquina externa na malha **Tailscale** (`http://100.64.0.x:11434`), garantindo independência total de serviços de nuvem para operabilidade offline.

### 2.4. Provedores Opcionais Adicionais

- **`OpenRouterProvider`:** Acesso a modelos abertos unificados com roteamento de menor custo.
- **`DeepSeekProvider`:** Integração via API compatível com OpenAI apontando para os modelos `deepseek-chat` e `deepseek-reasoner`.
- **`MistralProvider`:** Integração com os modelos `mistral-small-latest` para processamento estilístico conciso.

## 🛡️ 3. Tratamento de Exceções e Resiliência

Cada conector herda de uma classe abstrata `BaseLLMProvider` que encapsula o tratamento de falhas:

1. **Timeout Controlado:** Cada chamada à API possui timeout individual estipulado (padrão: 12 segundos). Se excedido, o provedor é cancelado e marcado como indisponível temporariamente.
2. **Backoff e Quarentena:** Provedores que retornam erros de cota (429) entram em quarentena de 30 segundos, permitindo que requisições subsequentes sigam diretamente para o nó reserva sem desperdiçar tempo em retentativas fadadas ao erro.
3. **Log Sanitizado:** Chaves de API nunca são expostas em logs ou tracebacks em caso de falha de conexão.
