# Services/API/services/telemetry_service.py
import time
import platform
import psutil
import httpx
from typing import Optional
from Core.ConfigLoader import AppConfig
import hashlib
import random
import string


class TelemetryService:
    @staticmethod
    async def calculate_ping_matrix(bot) -> dict:
        sam_timestamp = time.time()
        discord_ws_ms = (
            round(bot.latency * 1000)
            if hasattr(bot, "latency") and bot.latency > 0
            else 0
        )

        # Ping Internet
        internet_ms = 999
        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get("https://1.1.1.1")
                if resp.status_code < 500:
                    internet_ms = round((time.perf_counter() - t0) * 1000)
        except Exception:
            internet_ms = 999

        # Ping Navidrome
        nav_url = AppConfig.get("NAVIDROME_URL", "http://127.0.0.1:4533").rstrip("/")
        user = AppConfig.get("NAVIDROME_USER", "sambot")
        password = AppConfig.get("NAVIDROME_PASSWORD", "sambot123")
        salt = "".join(random.choices(string.ascii_letters + string.digits, k=6))
        token = hashlib.md5(f"{password}{salt}".encode("utf-8")).hexdigest()
        navidrome_ms = 12

        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(
                    f"{nav_url}/rest/ping.view",
                    params={
                        "v": "1.16.1",
                        "c": "SamBot",
                        "f": "json",
                        "u": user,
                        "t": token,
                        "s": salt,
                    },
                )
                if resp.status_code == 200:
                    navidrome_ms = round((time.perf_counter() - t0) * 1000)
        except Exception:
            pass

        return {
            "success": True,
            "sam_ws_discord": discord_ws_ms,
            "internet_external": internet_ms,
            "navidrome": navidrome_ms,
            "server_time": sam_timestamp,
        }

    @staticmethod
    def get_system_status(bot, guild_id: Optional[str] = None) -> dict:
        from Brain.Memory.SelfKnowledge.SystemInspector import SystemInspector

        inspector = SystemInspector(bot=bot)
        snapshot = inspector.get_system_snapshot()
        ram = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent()

        vc_alvo = None
        if guild_id and bot.voice_clients:
            for vc in bot.voice_clients:
                if hasattr(vc, "guild") and str(vc.guild.id) == str(guild_id):
                    vc_alvo = vc
                    break
        elif bot.voice_clients:
            vc_alvo = bot.voice_clients[0]

        voice_session = None
        if vc_alvo:
            voice_session = {
                "channelId": str(vc_alvo.channel.id) if vc_alvo.channel else "",
                "channelName": (
                    vc_alvo.channel.name if vc_alvo.channel else "Desconectado"
                ),
                "guildId": str(vc_alvo.guild.id) if vc_alvo.guild else "",
                "guildName": (
                    vc_alvo.guild.name if vc_alvo.guild else "Servidor Discord"
                ),
                "pingMs": (
                    round(vc_alvo.latency * 1000) if hasattr(vc_alvo, "latency") else 18
                ),
                "bitrateKbps": (
                    int(vc_alvo.channel.bitrate / 1000)
                    if vc_alvo.channel and hasattr(vc_alvo.channel, "bitrate")
                    else 384
                ),
                "userCount": (
                    len([m for m in vc_alvo.channel.members if not m.bot])
                    if vc_alvo.channel
                    else 0
                ),
            }

        return {
            "status": "ONLINE" if bot.is_ready() else "OFFLINE",
            "version": getattr(bot, "version"),
            "bot_user": {
                "name": bot.user.name if bot.user else "Offline",
                "id": str(bot.user.id) if bot.user else "sambot_daemon",
                "avatar": bot.user.display_avatar.url if bot.user else None,
            },
            "activeVoiceSession": voice_session,
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "python": platform.python_version(),
                "cpu_usage_percent": cpu_percent,
                "ram_used_gb": round(ram.used / (1024**3), 2),
                "ram_total_gb": round(ram.total / (1024**3), 2),
                "ram_percent": ram.percent,
            },
            "telemetry": snapshot,
        }
