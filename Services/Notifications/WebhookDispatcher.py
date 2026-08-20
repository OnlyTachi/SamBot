import logging
import httpx
from typing import List, Dict, Any
from Brain.Core.NetworkManager import NetworkManager
from Brain.Memory.DataManager.Connections import data_manager

logger = logging.getLogger("SamBot.WebhookDispatcher")


class WebhookDispatcher:
    def __init__(self):
        self.logger = logger

    def listar_webhooks(self, guild_id: str = None) -> List[Dict[str, Any]]:
        dados = data_manager.get_knowledge("webhooks_config") or {}
        hooks = dados.get("webhooks", [])
        if guild_id:
            return [h for h in hooks if h.get("guild_id") == str(guild_id)]
        return hooks

    def salvar_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        dados = data_manager.get_knowledge("webhooks_config") or {"webhooks": []}
        hooks = dados.get("webhooks", [])
        # Atualiza existente ou insere novo
        hooks = [h for h in hooks if h.get("id") != webhook_data["id"]]
        hooks.append(webhook_data)
        dados["webhooks"] = hooks
        data_manager.save_knowledge("webhooks_config", dados)
        return True

    def remover_webhook(self, webhook_id: str) -> bool:
        dados = data_manager.get_knowledge("webhooks_config") or {"webhooks": []}
        hooks = [h for h in dados.get("webhooks", []) if h.get("id") != webhook_id]
        dados["webhooks"] = hooks
        data_manager.save_knowledge("webhooks_config", dados)
        return True

    async def disparar_evento(self, evento: str, payload: dict, guild_id: str = None):
        """Envia o payload para todos os webhooks inscritos no evento."""
        hooks = self.listar_webhooks(guild_id)
        client = NetworkManager.get_httpx_client()

        for hook in hooks:
            eventos_inscritos = hook.get("events", [])
            if evento in eventos_inscritos or "*" in eventos_inscritos:
                try:
                    headers = {"X-Event-Type": evento}
                    if hook.get("secret_token"):
                        headers["Authorization"] = f"Bearer {hook['secret_token']}"

                    await client.post(
                        hook["url"], json=payload, headers=headers, timeout=5.0
                    )
                except Exception as e:
                    self.logger.error(
                        f"Falha ao disparar webhook '{hook.get('name')}': {e}"
                    )
