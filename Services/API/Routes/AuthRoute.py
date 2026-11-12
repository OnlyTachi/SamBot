# Services/API/Routes/AuthRoute.py
import os
import httpx
from fastapi import APIRouter, HTTPException, Header, Depends, Request
from pydantic import BaseModel
from typing import Optional
from Core.ConfigLoader import AppConfig
from Services.API.Security import verify_bot_token

router = APIRouter(prefix="/api/auth/discord", tags=["Discord Auth"])

DISCORD_API_URL = "https://discord.com/api/v10"


class TokenExchangeRequest(BaseModel):
    code: str
    redirect_uri: str


@router.post("/exchange")
async def exchange_discord_code(payload: TokenExchangeRequest, request: Request):
    """Troca o authorization code pelo access token oficial do Discord."""
    client_id = AppConfig.get("DISCORD_CLIENT_ID") or os.getenv("DISCORD_CLIENT_ID")
    client_secret = AppConfig.get("DISCORD_CLIENT_SECRET") or os.getenv(
        "DISCORD_CLIENT_SECRET"
    )

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Credenciais do Discord OAuth2 não configuradas no servidor.",
        )

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": payload.code,
        "redirect_uri": payload.redirect_uri,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Troca o código pelo access_token
        res = await client.post(
            f"{DISCORD_API_URL}/oauth2/token", data=data, headers=headers
        )
        if res.status_code != 200:
            raise HTTPException(
                status_code=400, detail=f"Erro Discord OAuth: {res.text}"
            )

        token_data = res.json()
        access_token = token_data.get("access_token")

        # 2. Resgata os dados reais do usuário
        user_res = await client.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(
                status_code=400, detail="Falha ao obter perfil do usuário no Discord."
            )

        user_profile = user_res.json()

    # 3. Cruzamento em tempo real com os canais de voz da Sam
    bot = request.app.state.bot
    user_id = str(user_profile["id"])
    voice_session = None
    if bot:
        for guild in bot.guilds:
            member = guild.get_member(int(user_id))
            if member and member.voice and member.voice.channel:
                ch = member.voice.channel
                voice_session = {
                    "connected": True,
                    "id": str(ch.id),
                    "name": ch.name,
                    "guildId": str(guild.id),
                    "guildName": guild.name,
                    "bitrateKbps": (
                        int(ch.bitrate / 1000) if hasattr(ch, "bitrate") else 64
                    ),
                    "pingMs": 18,
                }
                break

    if bot and bot.voice_clients:
        for vc in bot.voice_clients:
            if vc.channel and any(
                str(member.id) == user_id for member in vc.channel.members
            ):
                voice_session = {
                    "connected": True,
                    "id": str(vc.channel.id),
                    "name": vc.channel.name,
                    "guildId": str(vc.guild.id),
                    "guildName": vc.guild.name,
                    "bitrateKbps": (
                        int(vc.channel.bitrate / 1000)
                        if hasattr(vc.channel, "bitrate")
                        else 384
                    ),
                    "pingMs": (
                        round(vc.latency * 1000) if hasattr(vc, "latency") else 18
                    ),
                }
                break

    avatar_hash = user_profile.get("avatar")
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
        if avatar_hash
        else "https://cdn.discordapp.com/embed/avatars/0.png"
    )

    return {
        "success": True,
        "token": access_token,
        "user": {
            "id": user_id,
            "username": user_profile.get("username"),
            "discriminator": user_profile.get("discriminator", "0"),
            "avatar": avatar_url,
            "currentVoiceChannel": voice_session,
        },
    }


@router.get("/session")
async def get_discord_session(
    request: Request, authorization: Optional[str] = Header(None)
):
    """Valida o token salvo no navegador e atualiza o status de voz ativo."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente ou inválido.")

    access_token = authorization.replace("Bearer ", "").strip()

    async with httpx.AsyncClient(timeout=8.0) as client:
        user_res = await client.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Sessão expirada no Discord.")
        user_profile = user_res.json()

    bot = request.app.state.bot
    user_id = str(user_profile["id"])
    voice_session = None
    if bot:
        for guild in bot.guilds:
            member = guild.get_member(int(user_id))
            if member and member.voice and member.voice.channel:
                ch = member.voice.channel
                voice_session = {
                    "connected": True,
                    "id": str(ch.id),
                    "name": ch.name,
                    "guildId": str(guild.id),
                    "guildName": guild.name,
                    "bitrateKbps": (
                        int(ch.bitrate / 1000) if hasattr(ch, "bitrate") else 64
                    ),
                    "pingMs": 18,
                }
                break

    if bot and bot.voice_clients:
        for vc in bot.voice_clients:
            if vc.channel and any(
                str(member.id) == user_id for member in vc.channel.members
            ):
                voice_session = {
                    "connected": True,
                    "id": str(vc.channel.id),
                    "name": vc.channel.name,
                    "guildId": str(vc.guild.id),
                    "guildName": vc.guild.name,
                    "bitrateKbps": (
                        int(vc.channel.bitrate / 1000)
                        if hasattr(vc.channel, "bitrate")
                        else 384
                    ),
                    "pingMs": (
                        round(vc.latency * 1000) if hasattr(vc, "latency") else 18
                    ),
                }
                break

    avatar_hash = user_profile.get("avatar")
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
        if avatar_hash
        else "https://cdn.discordapp.com/embed/avatars/0.png"
    )

    return {
        "authenticated": True,
        "user": {
            "id": user_id,
            "username": user_profile.get("username"),
            "avatar": avatar_url,
            "currentVoiceChannel": voice_session,
        },
    }
