import os
import secrets
import hashlib
import logging
import aiohttp
import wavelink
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger("SamBot.SearchManager")


class SearchManager:
    """
    Controlador de fluxo simplificado (LOCAL ou ONLINE com sistema de Failover).
    """

    def __init__(self):
        self.mode = os.getenv("MUSIC_SOURCE_MODE", "ONLINE").upper()
        self.navi_url = os.getenv("NAVIDROME_URL", "").rstrip("/")
        self.navi_user = os.getenv("NAVIDROME_USER", "")
        self.navi_password = os.getenv("NAVIDROME_PASSWORD", "")
        self.node_cooldowns = {}

    def _auth_params(self):
        """Gera o token de segurança para a API do Navidrome (Subsonic)."""
        salt = secrets.token_hex(6)
        token = hashlib.md5(f"{self.navi_password}{salt}".encode()).hexdigest()
        return {
            "u": self.navi_user,
            "t": token,
            "s": salt,
            "v": "1.16.1",
            "c": "SamBot",
            "f": "json",
        }

    def mark_node_offline(self, node_id: str):
        """Coloca um Node de castigo por 1 hora."""
        unban_time = datetime.now() + timedelta(hours=1)
        self.node_cooldowns[node_id] = unban_time
        logger.warning(
            f"Node '{node_id}' falhou e entrou em CASTIGO por 1 hora (ativo novamente às {unban_time.strftime('%H:%M:%S')})."
        )

    def is_node_available(self, node_id: str) -> bool:
        """Verifica se o Node não está em tempo de castigo/cooldown."""
        if node_id in self.node_cooldowns:
            if datetime.now() < self.node_cooldowns[node_id]:
                return False
            del self.node_cooldowns[node_id]
            logger.info(
                f"Node '{node_id}' cumpriu o castigo de 1 hora e talvez voltou a ficar disponível."
            )
        return True

    def get_available_nodes(self, required_type: str) -> list[wavelink.Node]:
        available = []
        for node in wavelink.Pool.nodes.values():
            if node.identifier.startswith(required_type) and self.is_node_available(
                node.identifier
            ):
                available.append(node)
        return available

    async def test_navidrome_connection(self) -> bool:
        """Verifica se o servidor Navidrome local está online e respondendo."""
        if not self.navi_url:
            logger.warning("Navidrome não configurado para testes de conexão no .env")
            return False
        url = f"{self.navi_url}/rest/ping.view"
        params = self._auth_params()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("subsonic-response", {}).get("status")
                        if status == "ok":
                            logger.info(
                                "  Conexão com Navidrome (Subsonic API) estabelecida com sucesso!"
                            )
                            return True
            logger.error("Falha na autenticação ou resposta inesperada do Navidrome.")
            return False
        except Exception as e:
            logger.error(f"Não foi possível conectar ao Navidrome local: {e}")
            return False

    async def search_navidrome(self, query: str) -> Optional[str]:
        """Pesquisa e retorna a URL de stream direto (.mp3/.flac) do Navidrome."""
        if not self.navi_url:
            return None
        params = self._auth_params()
        params.update({"query": query, "songCount": 1})
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.navi_url}/rest/search3.view", params=params, timeout=5
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        songs = (
                            data.get("subsonic-response", {})
                            .get("searchResult3", {})
                            .get("song", [])
                        )
                        if songs:
                            s = songs[0]
                            stream_params = self._auth_params()
                            stream_params["id"] = s["id"]
                            qs = "&".join(f"{k}={v}" for k, v in stream_params.items())
                            logger.info(
                                f"  Encontrado no Navidrome: {s.get('title')} - {s.get('artist')}"
                            )
                            return f"{self.navi_url}/rest/stream.view?{qs}"
        except Exception as e:
            logger.error(f"Erro ao consultar Navidrome: {e}")
        return None

    async def intelligent_search(
        self, query: str
    ) -> Tuple[Optional[wavelink.Search], str]:
        prefix = "LOCAL" if self.mode == "LOCAL" else "ONLINE"

        if query.startswith("http"):
            for node in self.get_available_nodes(prefix):
                try:
                    track = await wavelink.Playable.search(query, node=node)
                    if track:
                        return track, "LINK"
                except Exception:
                    self.mark_node_offline(node.identifier)
            return None, "ALL_OFFLINE"

        if self.mode == "LOCAL":
            local_stream = await self.search_navidrome(query)
            if local_stream:
                local_nodes = self.get_available_nodes("LOCAL")
                if local_nodes:
                    try:
                        track = await wavelink.Playable.search(
                            local_stream, node=local_nodes[0]
                        )
                        return track, "NAVIDROME"
                    except Exception as e:
                        logger.error(f"Erro ao processar URL do Navidrome: {e}")
            return None, "NOT_FOUND_LOCAL"

        if self.mode == "ONLINE":
            online_nodes = self.get_available_nodes("ONLINE")
            if not online_nodes:
                return None, "ALL_ONLINE_OFFLINE"

            for node in online_nodes:
                try:
                    track = await wavelink.Playable.search(query, node=node)
                    if track:
                        return track, "LAVALINK (Internet)"
                except Exception as e:
                    logger.error(f"Falha ao buscar no node {node.identifier}: {e}")
                    self.mark_node_offline(node.identifier)

            return None, "ALL_ONLINE_OFFLINE"


search_manager = SearchManager()
