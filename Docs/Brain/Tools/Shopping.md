# 🛒 Ferramentas de Compras & Monitoramento de Preços

O ecossistema de compras da SamBot integra três ferramentas essenciais: **`ProductSearch`**, **`CupomFinder`** e **`PriceTracker`**, proporcionando consulta de promoções em tempo real, orçamentos automáticos de listas de compras e vigilância noturna de preços-alvo.

## 🔍 1. `ProductSearch` (Busca Multilojas)

O `ProductSearch` executa varreduras concorrentes e paralelas em múltiplas fontes para encontrar o menor valor de mercado de um produto desejado.

### Fontes Integradas:

- **Pelando:** Scraping assíncrono de promoções votadas pela comunidade de ofertas.
- **Mercado Livre:** Varredura em tempo real dos melhores resultados com entrega Full/confiável.
- **Meilisearch Cache:** Consulta direta ao índice interno de ofertas já capturadas pelo bot.

### Isolamento de Falhas:

As buscas são despachadas via `asyncio.gather` com captura de exceções individual. Se o scraping do Pelando oscilar ou sofrer bloqueio temporário por captcha, os resultados do Mercado Livre e Meilisearch continuam sendo compilados e retornados normalmente.

## 🏷️ 2. `CupomFinder` (Localizador de Cupons)

O `CupomFinder` varre a base de dados em busca de códigos promocionais ativos aplicáveis a lojas específicas (Amazon, KaBuM!, Mercado Livre, Shopee, etc.):

- **Consulta ao Meilisearch:** Varre registros onde o atributo `coupon` não seja nulo, aplicando filtros pela loja solicitada.
- **Formatação Automatizada:** Entrega o código em formato de código inline (`` `CUPOM` ``) juntamente com as regras de uso extraídas da postagem original.

## 📋 3. `ShoppingListManager` (Listas de Desejos e Cotações)

Cada usuário pode manter sua lista de compras pessoal gerenciada via SQLite:

- **Estrutura dos Itens:**
  - `nome`: Descrição do item (ex.: "Monitor 24 IPS").
  - `preco_alvo`: Preço teto desejado pelo usuário em R$.
  - `notificado`: Flag booleana (`True`/`False`) de controle para evitar spam de alertas.

### Métodos Principais:

- `adicionar_item(user_id, item, preco_alvo)`: Insere novo produto à lista do usuário.
- `remover_item(user_id, nome_item)`: Remove o item especificado.
- `listar_itens(user_id)`: Exibe o inventário de desejos do usuário.
- `orcar_lista(user_id)`: Dispara uma cotação completa, chamando o `ProductSearch` para cada item cadastrado e gerando um relatório financeiro com a melhor combinação de lojas.

## 🌙 4. `PriceTracker` & Rotina de Alertas Noturnos

O `PriceTracker` é o serviço em segundo plano executado de forma não obstrutiva durante a madrugada dentro do ciclo **`NightCycle`**:

```text
       [ NightCycle (Madrugada) ]
                   │
                   ▼
     [ PriceTracker.verificar_alertas_noturnos() ]
                   │
    ┌──────────────┴──────────────┐
    ▼                             ▼
[ Lê SQLite: users ]        [ Busca Assíncrona ]
(Filtra itens com alvo      (Consulta valor atual ao vivo)
 e não notificados)               │
    │                             ▼
    └──────────────► [ Preço Atual <= Preço Alvo? ]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
          [ SIM ]                     [ NÃO ]
    1. Marca `notificado = True`   (Mantém na fila de
    2. Atualiza banco SQLite        observação)
    3. Envia DM rica ao usuário
```

### Regras de Despacho na DM:

Quando o preço atual cai para um valor menor ou igual ao `preco_alvo`:

1. Um alerta formatado em Rich Embed contendo o nome da loja, link original, preço encontrado e valor economizado é enviado na mensagem direta do usuário.
2. O campo `notificado` é alterado para `True`, impedindo reenvios até que o usuário resete ou altere o valor do alvo.
