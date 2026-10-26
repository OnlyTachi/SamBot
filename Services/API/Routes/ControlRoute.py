# Services/API/Routes/ControlRoute.py
from fastapi import APIRouter, Depends, HTTPException, Request
from Services.API.Security import verify_bot_token
from Services.API.Services.AudioService import AudioService
from Services.API.Services.TelemetryService import TelemetryService
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter(prefix="/api/control", tags=["SamNya"])


class PlayerActionRequest(BaseModel):
    action: str
    payload: Optional[Dict[str, Any]] = None
    voiceChannelId: Optional[str] = None
    guildId: Optional[str] = None
    userId: Optional[str] = None


@router.get("/ping-matrix", dependencies=[Depends(verify_bot_token)])
async def get_ping_matrix(request: Request):
    return await TelemetryService.calculate_ping_matrix(request.app.state.bot)


@router.get("/status", dependencies=[Depends(verify_bot_token)])
async def get_bot_status(request: Request, guildId: Optional[str] = None):
    return TelemetryService.get_system_status(request.app.state.bot, guildId)


@router.post("/player", dependencies=[Depends(verify_bot_token)])
async def control_player(payload: PlayerActionRequest, request: Request):
    bot = request.app.state.bot
    action = payload.action.upper()

    # 1. Recupera o Player alvo
    target_vc = None
    if payload.guildId:
        for vc in bot.voice_clients:
            if hasattr(vc, "guild") and str(vc.guild.id) == str(payload.guildId):
                target_vc = vc
                break
    elif bot.voice_clients:
        target_vc = bot.voice_clients[0]

    if not target_vc or not target_vc.channel:
        raise HTTPException(
            status_code=404, detail="A SamBot não está conectada a nenhum canal de voz."
        )

    # 2. Anti-Ghost DJ check
    if not payload.userId or payload.userId == "usr_guest":
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: Modo Convidado está restrito a leitura.",
        )

    # 3. Encaminha para o AudioService
    p = payload.payload or {}
    if action == "PLAY":
        track = await AudioService.play(
            bot, target_vc, p.get("trackId"), payload.userId, p.get("bitRate")
        )
        return {
            "success": True,
            "action": "PLAY",
            "title": track.title if track else None,
        }
    elif action == "ENQUEUE":
        track = await AudioService.enqueue(
            bot, target_vc, p.get("trackId"), payload.userId
        )
        return {"success": True, "action": "ENQUEUE", "title": track.title}
    elif action == "PAUSE":
        await AudioService.pause(bot, target_vc)
    elif action == "RESUME":
        await AudioService.resume(bot, target_vc)
    elif action == "SKIP":
        await AudioService.skip(target_vc)
    elif action == "SEEK":
        await AudioService.seek(bot, target_vc, p.get("position", 0))
    elif action == "SET_VOLUME":
        await AudioService.set_volume(bot, target_vc, int(p.get("volume", 80)))
    elif action == "SET_LOOP":
        await AudioService.set_loop(bot, target_vc, str(p.get("mode", "OFF")))
    elif action == "SHUFFLE":
        await AudioService.shuffle(bot, target_vc)
    elif action == "CLEAR_QUEUE":
        target_vc.queue.clear()

    return {"success": True, "action": action}
