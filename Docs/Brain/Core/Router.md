# 🧭 Roteamento Semântico (`TLMRouter` & `IntentClassifier`)

O subsistema de roteamento semântico da SamBot é responsável por identificar a intenção do usuário e disparar ferramentas especializadas (`tools`) **sem depender de chamadas preliminares de LLMs**. Isso zera o custo financeiro em tokens e reduz a latência de despacho para milissegundos.

## ⚙️ 1. Mecanismo de Decisão e Classificação

O roteador semântico é articulado através do `TLMRouter` em conjunto com o `IntentClassifier`:

```text
Entrada Textual: "onde compro rtx 4060 barata"
       │
       ▼
1. Vetorização Semântica (Embedding 768d)
   - Provedor Gemini (text-embedding-004) ou Ollama Local (nomic-embed-text)
       │
       ▼
2. Consulta na Coleção `rotas_intencoes` (ChromaDB)
   - Espaço métrico de Cosseno (Cosine Distance)
       │
       ▼
3. Cálculo do Score de Similaridade:
   Score = 1.0 - Distância_Cosseno
       │
       ├─────────────────────────────────────────┐
       │ (Score >= 0.74 - Calibrado)             │ (Score < 0.74)
       ▼                                         ▼
4. Rota Aprovada                              4. Rota Rejeitada
   - Limpeza de Ruídos via `config_ruidos`       - Prossegue para conversa livre
   - Extrai argumento: "rtx 4060"                  sem disparar ferramentas
   - Despacha execução assíncrona
```

## 🎯 2. Thresholds de Corte e Calibração

O threshold de similaridade define o rigor semântico para aceitação de um gatilho:

- **Threshold Padrão Calibrado:** **`0.74`**
- **Score $\ge 0.74$ (Match Confirmado):** O roteador assume certeza operacional na intenção do usuário, extrai a entidade da frase e dispara a ferramenta associada.
- **Score $< 0.74$ (Match Incerto / Ruído):** A mensagem é repassada intacta para a esteira principal de LLMs interpretar em contexto aberto, evitando falsos positivos que degradam a conversa.

## 📂 3. Base de Conhecimento: `router_triggers.json`

O arquivo `Data/Knowledge/router_triggers.json` armazena de forma declarativa os exemplos de treinamento sintético (_utterances_) e a lista de ruídos removíveis. O código Python não possui frases fixadas (_hardcoded_).

### Estrutura do Schema

```json
{
  "config_ruidos": [
    "quanto custa",
    "onde compro",
    "procure por",
    "pesquise",
    "preço de",
    "previsão do tempo em",
    "como está o clima em",
    "ache o menor preço de",
    "quero comprar"
  ],
  "weather": [
    "previsão do tempo",
    "vai chover hoje",
    "qual a temperatura",
    "está fazendo frio",
    "clima para amanhã"
  ],
  "product_search": [
    "onde comprar mais barato",
    "menor preço de",
    "ofertas de",
    "promoção de monitor",
    "quanto tá custando",
    "procure por",
    "ache o menor preço"
  ],
  "cupom_finder": [
    "tem cupom para",
    "cupom de desconto",
    "código promocional para a loja",
    "desconto na loja"
  ],
  "anime": [
    "qual o nome desse anime",
    "recomende um anime",
    "sinopse do anime",
    "top animes da temporada"
  ]
}
```

## 🔄 4. Reindexação Automática e Persistência de Hash

Para garantir que modificações manuais nos gatilhos entrem em vigor sem recriações completas de banco, o sistema emprega verificação por hash:

1. **Checagem de Hash MD5 no Boot:** O `DatabaseSeeder` calcula o MD5 de `router_triggers.json` e compara com o valor gravado em `router_hash.json` e na tabela SQLite.
2. **Sincronização Vetorial (`sincronizar_base_rotas`):**
   - Caso o hash divirja, a coleção `rotas_intencoes` no ChromaDB expurga os registros sob o prefixo `route_*`.
   - Gera os novos embeddings em lote para todas as frases cadastradas.
   - Persiste o novo hash, completando o ciclo com zero perda de dados.
3. **Persistência de Estado Ocupado:** Durante processos de configuração interativa via DM, a flag `status_ocupado` do `DataManager` suprime as ativações semânticas para evitar interrupções de fluxo.
