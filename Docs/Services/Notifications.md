# 🔔 Módulo de Notificações — Dispatchers & Alertas

O subsistema de notificações (`sambot/Services/Notifications/`) gerencia a formatação, distribuição assíncrona e envio de mensagens proativas do bot para canais do Discord, DMs de usuários e endpoints externos de automação.

## 🏛️ 1. Componentes Centrais

O subsistema é dividido em dois motores interdependentes:

1. **`WebhookDispatcher`:** Despachante assíncrono genérico com controle de concorrência, retries com backoff exponencial e fila de mensagens em memória.
2. **`PromoNotifier`:** Motor especializado na formatação rica de ofertas de produtos, verificação de listas de desejos e envio segmentado por canal ou usuário.

## 🚀 2. `WebhookDispatcher`

O `WebhookDispatcher` padroniza o envio de payloads HTTP POST para webhooks do Discord ou servidores de terceiros.

### Características Operacionais

- **Pool de Conexões:** Utiliza sessão assíncrona única (`aiohttp.ClientSession`) compartilhada por todo o ciclo de vida.
- **Tratamento de Rate-Limit (HTTP 429):**
  - Identifica o cabeçalho `Retry-After` retornado pelo Discord.
  - Pausa a fila do webhook correspondente pelo tempo estipulado sem travar a execução geral do bot.
- **Mecanismo de Tentativas (Backoff):** Em falhas de rede transitórias (`ClientError`, `TimeoutError`), o despachante tenta até 3 vezes com intervalos graduais (1s, 2s, 4s).

## 🛒 3. `PromoNotifier`

O `PromoNotifier` monitora as oportunidades recém-ingeridas e cruza seus atributos com as preferências e listas de compras cadastradas no SQLite.
