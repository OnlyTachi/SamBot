# Services/API/Routes/JellyfinRoute.py
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, status

logger = logging.getLogger("SamBot.API.Jellyfin")
router = APIRouter(prefix="/api/v1/jellyfin", tags=["Jellyfin Webhook"])


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def jellyfin_webhook_endpoint(payload: Dict[str, Any], request: Request):
    """
    Recebe eventos em tempo real do Jellyfin (ItemAdded, etc.)
    e repassa para o JellyfinTool processar o catálogo e notificações.
    """
    bot = getattr(request.app.state, "bot", None)
    if not bot:
        logger.warning("Instância do Bot não localizada no estado da aplicação.")
        return {"status": "ignored", "reason": "bot_offline"}

    pipeline = getattr(getattr(bot, "pipeline", None), "tools", None)
    jellyfin_tool = None

    if pipeline and "jellyfin" in pipeline:
        jellyfin_tool = pipeline["jellyfin"]
    elif hasattr(bot, "get_cog"):
        # Alternativa caso esteja acoplado ao Cog CerebroIA
        cerebro = bot.get_cog("CerebroIA")
        if cerebro and hasattr(cerebro, "pipeline"):
            jellyfin_tool = cerebro.pipeline.tools.get("jellyfin")

    if not jellyfin_tool:
        logger.warning("JellyfinTool não está carregado ou disponível no pipeline.")
        return {"status": "ignored", "reason": "tool_not_found"}

    # Processa o evento assincronamente sem bloquear a resposta do webhook
    processado = await jellyfin_tool.handle_webhook_event(payload)
    return {"status": "processed" if processado else "ignored"}
