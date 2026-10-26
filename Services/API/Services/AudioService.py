# Services/API/services/audio_service.py
import hashlib
import logging
import random
import string
from urllib.parse import parse_qs, urlparse
from typing import Optional

from fastapi import HTTPException
import wavelink

from Core.ConfigLoader import AppConfig
from Modules.Audio.Lavalink._maestro import maestro

logger = logging.getLogger("SamBot.Services.Audio")


class AudioService:
    @staticmethod
    def build_subsonic_stream_url(track_id: str) -> str:
        if track_id.startswith("http://") or track_id.startswith("https://"):
            parsed = urlparse(track_id)
            qs = parse_qs(parsed.query)
            if "id" in qs and qs["id"]:
                track_id = qs["id"][0]
            else:
                return track_id

        nav_url = AppConfig.get("NAVIDROME_URL", "http://127.0.0.1:4533").rstrip("/")
        user = AppConfig.get("NAVIDROME_USER", "sambot")
        password = AppConfig.get("NAVIDROME_PASSWORD", "sambot123")
        salt = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        token = hashlib.md5(f"{password}{salt}".encode("utf-8")).hexdigest()
        return f"{nav_url}/rest/stream.view?u={user}&t={token}&s={salt}&v=1.16.1&c=SamBot&id={track_id}"

    @classmethod
    async def play(
        cls,
        bot,
        vc: wavelink.Player,
        track_id: Optional[str],
        user_id: str,
        bit_rate: Optional[int] = None,
    ):
        if not track_id:
            if vc.paused:
                await vc.pause(False)
                await maestro.sync_player_state(bot, vc)
            return

        stream_url = cls.build_subsonic_stream_url(track_id)
        tracks: wavelink.Search = await wavelink.Playable.search(stream_url)
        if not tracks:
            raise HTTPException(
                status_code=404,
                detail="Lavalink não conseguiu resolver o stream do Navidrome.",
            )

        track = tracks[0]
        track.requester = {"id": user_id, "name": "Dashboard"}
        if bit_rate:
            track.bitRate = bit_rate

        await vc.play(track)
        await maestro.sync_player_state(bot, vc)
        return track

    @classmethod
    async def enqueue(cls, bot, vc: wavelink.Player, track_id: str, user_id: str):
        stream_url = cls.build_subsonic_stream_url(track_id)
        tracks: wavelink.Search = await wavelink.Playable.search(stream_url)
        if not tracks:
            raise HTTPException(status_code=404, detail="Faixa não localizada.")
        track = tracks[0]
        track.requester = {"id": user_id, "name": "Dashboard"}
        await vc.queue.put_wait(track)
        await maestro.sync_player_state(bot, vc)
        return track

    @staticmethod
    async def pause(bot, vc: wavelink.Player):
        if vc.playing and not vc.paused:
            await vc.pause(True)
            await maestro.sync_player_state(bot, vc)

    @staticmethod
    async def resume(bot, vc: wavelink.Player):
        if vc.paused:
            await vc.pause(False)
            await maestro.sync_player_state(bot, vc)

    @staticmethod
    async def skip(vc: wavelink.Player):
        await vc.skip(force=True)

    @staticmethod
    async def seek(bot, vc: wavelink.Player, position_seconds: float):
        pos_ms = int(position_seconds * 1000)
        await vc.seek(pos_ms)
        await maestro.sync_player_state(bot, vc)

    @staticmethod
    async def set_volume(bot, vc: wavelink.Player, volume: int):
        await vc.set_volume(max(0, min(100, volume)))
        await maestro.sync_player_state(bot, vc)

    @staticmethod
    async def set_loop(bot, vc: wavelink.Player, mode: str):
        mode_upper = mode.upper()
        if hasattr(wavelink, "QueueMode"):
            if mode_upper == "TRACK":
                vc.queue.mode = wavelink.QueueMode.loop
            elif mode_upper in ("QUEUE", "PLAYLIST"):
                vc.queue.mode = wavelink.QueueMode.loop_all
            else:
                vc.queue.mode = wavelink.QueueMode.normal
        else:
            setattr(vc, "loop", mode_upper == "TRACK")
            setattr(vc, "loop_queue", mode_upper in ("QUEUE", "PLAYLIST"))

        await maestro.sync_player_state(bot, vc)

    @staticmethod
    async def shuffle(bot, vc: wavelink.Player):
        if hasattr(vc.queue, "shuffle"):
            vc.queue.shuffle()
        else:
            items = list(vc.queue)
            random.shuffle(items)
            vc.queue.clear()
            for item in items:
                vc.queue.put(item)
        await maestro.sync_player_state(bot, vc)
