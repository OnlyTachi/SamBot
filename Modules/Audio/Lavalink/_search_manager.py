import os
import secrets
import hashlib
import logging
import aiohttp
import wavelink
from typing import Optional, Tuple

logger = logging.getLogger("SamBot.SearchManager")


class SearchManager:
    """
    Controlador de fluxo: Navidrome -> Lavalink Local -> Lavalink Online
    """

    def __init__(self):
        self.mode = os.getenv("MUSIC_SOURCE_MODE", "HIBRIDO").upper()
        self.navi_url = os.getenv("NAVIDROME_URL", "").rstrip("/")
        self.navi_user = os.getenv("NAVIDROME_USER", "")
        self.navi_password = os.getenv("NAVIDROME_PASSWORD", "")

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
                                "🔌 Conexão com Navidrome (Subsonic API) estabelecida com sucesso!"
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
                                f"✅ Encontrado no Navidrome: {s.get('title')} - {s.get('artist')}"
                            )
                            return f"{self.navi_url}/rest/stream.view?{qs}"
        except Exception as e:
            logger.error(f"Erro ao consultar Navidrome: {e}")

        logger.info(f"❌ Não encontrado no Navidrome local: {query}")
        return None

    def get_best_node(self, required_type="LOCAL"):
        """Filtra o pool do Wavelink para pegar o nó específico (Local ou Online)."""
        for node in wavelink.Pool.nodes.values():
            if node.identifier.startswith(required_type):
                return node
        return None  # Se None, o Wavelink usa o melhor disponível por conta própria

    async def intelligent_search(
        self, query: str
    ) -> Tuple[Optional[wavelink.Search], str]:
        """Orquestrador do Fluxo Híbrido"""

        if query.startswith("http"):
            return await wavelink.Playable.search(query), "LINK"

        if self.mode in ["HIBRIDO", "LOCAL"]:
            local_stream = await self.search_navidrome(query)
            if local_stream:
                # Opcional: Força o processamento do link local pelo Lavalink Local
                node = self.get_best_node("LOCAL")
                track = await wavelink.Playable.search(local_stream, node=node)
                return track, "NAVIDROME"

            if self.mode == "LOCAL":
                return None, "NOT_FOUND_LOCAL"

        # 3. Fallback Online (Busca no YouTube/Soundcloud através dos Nodes externos)
        logger.info(f"🌐 Fallback Online Ativado. Buscando: {query}")
        node = self.get_best_node("ONLINE")
        track = await wavelink.Playable.search(query, node=node)
        return track, "LAVALINK (Internet)"


search_manager = SearchManager()
