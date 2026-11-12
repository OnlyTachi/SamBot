import logging
import wavelink
from typing import Dict, Any, List
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger("SamBot.Maestro")


class PlayerMaestro:
    """
    O cérebro central da fila de áudio.
    Lê o estado nativo do Lavalink/Wavelink, traduz para o formato da Web UI
    e faz o broadcast via WebSocket.
    """

    @staticmethod
    def _extract_track_id(track: wavelink.Playable) -> str:
        """
        Extrai o ID limpo da faixa caso seja um stream do Navidrome/Subsonic,
        evitando propagar a URL completa com parâmetros de autenticação no campo 'id'.
        """
        uri = str(getattr(track, "uri", "") or "")
        if "stream.view" in uri:
            try:
                parsed = urlparse(uri)
                qs = parse_qs(parsed.query)
                if "id" in qs and qs["id"]:
                    return str(qs["id"][0])
            except Exception:
                pass
        return str(getattr(track, "identifier", uri))

    @classmethod
    async def sync_player_state(cls, bot, player: wavelink.Player):
        """
        Captura o estado exato do player neste milissegundo e avisa a Dashboard.
        """
        if not player or not player.guild:
            return

        guild_id = str(player.guild.id)

        # 1. Faixa Atual
        current_track_data = None
        if player.current:
            t = player.current

            artist_name = getattr(t, "author", "Desconhecido")
            if not isinstance(artist_name, str):
                artist_name = str(artist_name)

            album_name = getattr(t, "album", "Album Cria")
            if not isinstance(album_name, (str, int, float)) or album_name is None:
                album_name = "Album Cria"
            else:
                album_name = str(album_name)

            track_bitrate = getattr(t, "bitrate", None) or getattr(t, "bitRate", None)
            if not track_bitrate and hasattr(t, "raw_data"):
                track_bitrate = t.raw_data.get("bitRate")

            current_track_data = {
                "id": cls._extract_track_id(t),
                "title": str(t.title or "Desconhecido"),
                "artist": artist_name,
                "album": album_name,
                "duration": int(t.length / 1000) if t.length else 0,
                "artwork": str(getattr(t, "artwork", "")) or None,
                "source": "NAVIDROME" if "stream.view" in str(t.uri) else "ONLINE",
                "bitRate": track_bitrate,
                "requester": getattr(
                    t, "requester", {"name": "Sistema", "id": "usr_system"}
                ),
            }

        # 2. Itens da Fila
        queue_data: List[Dict[str, Any]] = []
        for i, t in enumerate(player.queue):
            queue_id = getattr(t, "queue_id", f"q_{guild_id}_{i}_{int(t.length or 0)}")

            artist_name = getattr(t, "author", "Desconhecido")
            if not isinstance(artist_name, str):
                artist_name = str(artist_name)

            album_name = getattr(t, "album", "Album Cria")
            if not isinstance(album_name, (str, int, float)) or album_name is None:
                album_name = "Album Cria"
            else:
                album_name = str(album_name)
            t_bitrate = getattr(t, "bitrate", None) or getattr(t, "bitRate", None)
            if not t_bitrate and hasattr(t, "raw_data"):
                t_bitrate = t.raw_data.get("bitRate")

            queue_data.append(
                {
                    "queueId": str(queue_id),
                    "id": cls._extract_track_id(t),
                    "title": str(t.title or "Desconhecido"),
                    "artist": artist_name,
                    "album": album_name,
                    "duration": int(t.length / 1000) if t.length else 0,
                    "artwork": str(getattr(t, "artwork", "")) or None,
                    "source": "NAVIDROME" if "stream.view" in str(t.uri) else "ONLINE",
                    "bitRate": t_bitrate,
                    "requester": getattr(
                        t, "requester", {"name": "Sistema", "id": "usr_system"}
                    ),
                }
            )

        # 3. Descobrir o Modo de Repetição
        repeat_mode = "OFF"
        if player.queue.mode == wavelink.QueueMode.loop:
            repeat_mode = "TRACK"
        elif player.queue.mode == wavelink.QueueMode.loop_all:
            repeat_mode = "QUEUE"

        listeners_count = 0
        channel_name = "Desconectado"
        bitrate_kbps = 64
        ping_ms = 0

        if player.channel:
            channel_name = player.channel.name
            bitrate_kbps = (
                int(player.channel.bitrate / 1000)
                if hasattr(player.channel, "bitrate")
                else 64
            )
            listeners_count = len([m for m in player.channel.members if not m.bot])
            ping_ms = (
                round(player.ping)
                if hasattr(player, "ping") and player.ping > 0
                else 18
            )

        payload = {
            "op": "EVENT",
            "event": "PLAYER_STATE_UPDATE",
            "guildId": guild_id,
            "data": {
                "isPlaying": player.playing and not player.paused,
                "isPaused": player.paused,
                "volume": player.volume,
                "position": int(player.position / 1000),
                "currentTrack": current_track_data,
                "queue": queue_data,
                "repeatMode": repeat_mode,
                "voiceSession": {
                    "id": str(player.channel.id) if player.channel else "",
                    "name": channel_name,
                    "guildName": player.guild.name,
                    "userCount": listeners_count,
                    "bitrateKbps": bitrate_kbps,
                    "pingMs": ping_ms,
                    "connected": bool(player.channel),
                },
            },
        }

        if hasattr(bot, "ws_manager") and bot.ws_manager:
            await bot.ws_manager.broadcast_to_guild(guild_id, payload)


maestro = PlayerMaestro()
