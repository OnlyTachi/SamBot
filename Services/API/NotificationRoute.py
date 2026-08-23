from fastapi import APIRouter, HTTPException, Header, Depends, Request
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uuid
import discord
from Brain.Memory.DataManager.Connections import data_manager
from Services.Notifications.WebhookDispatcher import WebhookDispatcher

router = APIRouter(prefix="/api/v1", tags=["Notificações & Webhooks"])
dispatcher = WebhookDispatcher()

# --- MODELOS PYDANTIC ---


class PromoNotificationRequest(BaseModel):
    target_type: str  # "server" ou "dm"
    target_id: str  # ID do canal/servidor ou ID do usuário
    titulo: str
    preco: float
    loja: str
    link: str
    imagem_url: Optional[str] = None


class WebhookCreateRequest(BaseModel):
    name: str
    url: HttpUrl
    guild_id: str
    events: List[str] = ["promo_alert", "price_drop"]
    secret_token: Optional[str] = None


# --- AUTENTICAÇÃO SIMPLES STAFF/ADM ---


def verificar_autenticacao_staff(x_api_token: str = Header(...)):
    # Valide contra sua chave de ambiente ou token de sessão do site
    admin_secret = data_manager.get_knowledge("api_security") or {}
    token_esperado = admin_secret.get("staff_token", "default_secret_change_me")
    if x_api_token != token_esperado:
        raise HTTPException(
            status_code=403, detail="Acesso não autorizado para Staff/Admin."
        )


# --- 1. NOTIFICAÇÕES PROMO (SERVER OU DM) ---


@router.post("/notifications/promo")
async def enviar_notificacao_promo(
    payload: PromoNotificationRequest,
    request: Request,
    auth: None = Depends(verificar_autenticacao_staff),
):
    bot = request.app.state.bot
    notifier = bot.services.notifier
    if not notifier:
        raise HTTPException(status_code=503, detail="Serviço PromoNotifier offline.")

    await notifier.notificar_promo(
        titulo=payload.titulo,
        preco=payload.preco,
        loja=payload.loja,
        link=payload.link,
        imagem_url=payload.imagem_url,
        target_type=payload.target_type,
        target_id=payload.target_id,
    )
    return {"status": "enqueued", "message": "Promoção enfileirada com sucesso."}


# --- 2. CONFIGURAR WEBHOOKS (ADMIN / STAFF) ---


@router.get("/webhooks")
async def get_webhooks(
    guild_id: Optional[str] = None, auth: None = Depends(verificar_autenticacao_staff)
):
    return {"webhooks": dispatcher.listar_webhooks(guild_id)}


@router.post("/webhooks")
async def criar_webhook(
    req: WebhookCreateRequest, auth: None = Depends(verificar_autenticacao_staff)
):
    hook_id = str(uuid.uuid4())[:8]
    data = {
        "id": hook_id,
        "name": req.name,
        "url": str(req.url),
        "guild_id": req.guild_id,
        "events": req.events,
        "secret_token": req.secret_token,
    }
    dispatcher.salvar_webhook(data)
    return {"status": "created", "webhook": data}


@router.delete("/webhooks/{webhook_id}")
async def deletar_webhook(
    webhook_id: str, auth: None = Depends(verificar_autenticacao_staff)
):
    dispatcher.remover_webhook(webhook_id)
    return {"status": "deleted", "webhook_id": webhook_id}


@router.post("/webhooks/{webhook_id}/test")
async def testar_webhook(
    webhook_id: str, auth: None = Depends(verificar_autenticacao_staff)
):
    hooks = [h for h in dispatcher.listar_webhooks() if h["id"] == webhook_id]
    if not hooks:
        raise HTTPException(status_code=404, detail="Webhook não encontrado.")

    payload_teste = {
        "event": "ping",
        "message": "Teste de conexão com o painel SamBot.",
    }
    await dispatcher.disparar_evento("ping", payload_teste)
    return {"status": "dispatched", "target": hooks[0]["name"]}
