# Services/API/Routes/NotificationRoute.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, HttpUrl

from Services.API.Security import get_expected_token, verify_bot_token
from Services.API.Services.NotificationService import NotificationService

router = APIRouter(prefix="/api/v1", tags=["Notificações & Webhooks"])


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


def verificar_autenticacao_staff(x_api_token: str = Header(...)):
    token_esperado = get_expected_token()
    if not token_esperado:
        raise HTTPException(
            status_code=500, detail="Erro de configuração: Token de Staff não definido."
        )
    if x_api_token != token_esperado:
        raise HTTPException(
            status_code=403, detail="Acesso não autorizado para Staff/Admin."
        )


# --- 1. NOTIFICAÇÕES PROMO ---
@router.post("/notifications/promo")
async def enviar_notificacao_promo(
    payload: PromoNotificationRequest,
    request: Request,
    auth: None = Depends(verify_bot_token),
):
    return await NotificationService.enqueue_promo(
        bot=request.app.state.bot,
        titulo=payload.titulo,
        preco=payload.preco,
        loja=payload.loja,
        link=payload.link,
        imagem_url=payload.imagem_url,
        target_type=payload.target_type,
        target_id=payload.target_id,
    )


# --- 2. CONFIGURAR WEBHOOKS ---
@router.get("/webhooks")
async def get_webhooks(
    guild_id: Optional[str] = None,
    auth: None = Depends(verify_bot_token),
):
    return {"webhooks": NotificationService.list_webhooks(guild_id)}


@router.post("/webhooks")
async def criar_webhook(
    req: WebhookCreateRequest,
    auth: None = Depends(verify_bot_token),
):
    data = NotificationService.create_webhook(
        name=req.name,
        url=req.url,
        guild_id=req.guild_id,
        events=req.events,
        secret_token=req.secret_token,
    )
    return {"status": "created", "webhook": data}


@router.delete("/webhooks/{webhook_id}")
async def deletar_webhook(
    webhook_id: str,
    auth: None = Depends(verify_bot_token),
):
    NotificationService.delete_webhook(webhook_id)
    return {"status": "deleted", "webhook_id": webhook_id}


@router.post("/webhooks/{webhook_id}/test")
async def testar_webhook(
    webhook_id: str,
    auth: None = Depends(verify_bot_token),
):
    return await NotificationService.test_webhook(webhook_id)
