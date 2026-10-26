# Services/API/Services/NotificationService.py
import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from pydantic import HttpUrl

from Services.Notifications.WebhookDispatcher import WebhookDispatcher

logger = logging.getLogger("SamBot.Services.Notification")


class NotificationService:
    dispatcher = WebhookDispatcher()

    @classmethod
    async def enqueue_promo(
        cls,
        bot: Any,
        titulo: str,
        preco: float,
        loja: str,
        link: str,
        imagem_url: Optional[str] = None,
        target_type: str = "server",
        target_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Encaminha o envio de promoção para a fila do PromoNotifier ativo no bot."""
        notifier = getattr(getattr(bot, "services", None), "notifier", None)
        if not notifier:
            raise HTTPException(
                status_code=503, detail="Serviço PromoNotifier offline."
            )

        await notifier.notificar_promo(
            titulo=titulo,
            preco=preco,
            loja=loja,
            link=link,
            imagem_url=imagem_url,
            target_type=target_type,
            target_id=target_id,
        )
        return {"status": "enqueued", "message": "Promoção enfileirada com sucesso."}

    @classmethod
    def list_webhooks(cls, guild_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista os webhooks cadastrados para uma guilda ou globalmente."""
        return cls.dispatcher.listar_webhooks(guild_id)

    @classmethod
    def create_webhook(
        cls,
        name: str,
        url: HttpUrl,
        guild_id: str,
        events: List[str],
        secret_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cria e persiste um novo webhook no sistema."""
        hook_id = str(uuid.uuid4())[:8]
        data = {
            "id": hook_id,
            "name": name,
            "url": str(url),
            "guild_id": guild_id,
            "events": events,
            "secret_token": secret_token,
        }
        cls.dispatcher.salvar_webhook(data)
        return data

    @classmethod
    def delete_webhook(cls, webhook_id: str) -> None:
        """Remove o webhook especificado."""
        cls.dispatcher.remover_webhook(webhook_id)

    @classmethod
    async def test_webhook(cls, webhook_id: str) -> Dict[str, str]:
        """Envia um evento de ping para validar a conectividade do webhook cadastrado."""
        hooks = [h for h in cls.dispatcher.listar_webhooks() if h["id"] == webhook_id]
        if not hooks:
            raise HTTPException(status_code=404, detail="Webhook não encontrado.")

        payload_teste = {
            "event": "ping",
            "message": "Teste de conexão com o painel SamBot.",
        }
        await cls.dispatcher.disparar_evento("ping", payload_teste)
        return {"status": "dispatched", "target": hooks[0]["name"]}
