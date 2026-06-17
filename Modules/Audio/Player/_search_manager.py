import os
import secrets
import hashlib
import logging
import aiohttp
import wavelink
from typing import Optional, Tuple

logger = logging.getLogger("SamBot.SearchManager")


class SearchManager:
    def __init__(self):
        self.mode = os.getenv("MUSIC_SOURCE_MODE", "ONLINE").upper()

        self.navi_url = os.getenv("NAVIDROME_URL", "").rstrip("/")
        self.navi_user = os.getenv("NAVIDROME_USER", "")
        self.navi_password = os.getenv("NAVIDROME_PASSWORD", "")
        self.api_version = "1.16.1"
        self.client_name = "SamBot"

    def _generate_auth_params(self) -> dict:
        """Gera os parâmetros de autenticação dinâmicos (Salt e Token MD5) para a API Subsonic."""
        salt = secrets.token_hex(6)  # Gera um salt aleatório para cada requisição
        token_source = f"{self.navi_password}{salt}"
        token = hashlib.md5(token_source.encode("utf-8")).hexdigest()

        return {
            "u": self.navi_user,
            "t": token,
            "s": salt,
            "v": self.api_version,
            "c": self.client_name,
            "f": "json",  # Garante o retorno em formato JSON estruturado
        }

    async def test_navidrome_connection(self) -> bool:
        """Verifica se o servidor Navidrome está online e com credenciais válidas."""
        if not self.navi_url or not self.navi_user or not self.navi_password:
            logger.warning("Navidrome não configurado para testes de conexão.")
            return False

        url = f"{self.navi_url}/rest/ping.view"
        params = self._generate_auth_params()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status != 200:
                        logger.error(
                            f"Falha no ping do Navidrome: Status HTTP {response.status}"
                        )
                        return False

                    data = await response.json()
                    subsonic_response = data.get("subsonic-response", {})

                    if subsonic_response.get("status") == "ok":
                        logger.info(
                            "🔌 Conexão com Navidrome (Subsonic API) estabelecida com sucesso!"
                        )
                        return True
                    else:
                        error_info = subsonic_response.get("error", {})
                        logger.error(
                            f"Erro de autenticação no Navidrome: {error_info.get('message')}"
                        )
                        return False
        except Exception as e:
            logger.error(f"Não foi possível conectar ao Navidrome: {e}")
            return False

    async def _search_navidrome(self, query: str) -> Optional[str]:
        """Pesquisa uma música na biblioteca do Navidrome e retorna a URL de streaming se encontrada."""
        if not self.navi_url or not self.navi_user or not self.navi_password:
            logger.warning(
                "⚠️ Navidrome não configurado corretamente no .env Pulando busca local."
            )
            return None

        url = f"{self.navi_url}/rest/search3.view"
        params = self._generate_auth_params()
        params["query"] = query
        params["songCount"] = (
            1  # Limita a busca para retornar apenas a melhor correspondência para otimizar performance
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status != 200:
                        logger.error(
                            f"❌ Erro HTTP ao conectar no Navidrome: Status {response.status}"
                        )
                        return None

                    data = await response.json()
                    subsonic_response = data.get("subsonic-response", {})

                    if subsonic_response.get("status") == "failed":
                        error_info = subsonic_response.get("error", {})
                        logger.error(
                            f"❌ Erro na API do Navidrome: {error_info.get('message')}"
                        )
                        return None

                    search_result = subsonic_response.get("searchResult3", {})
                    songs = search_result.get("song", [])

                    if songs:
                        best_match = songs[0]
                        song_id = best_match.get("id")
                        title = best_match.get("title")
                        artist = best_match.get("artist", "Desconhecido")

                        logger.info(
                            f"🎯 Localizado no Navidrome: {title} - {artist} (ID: {song_id})"
                        )

                        stream_params = self._generate_auth_params()
                        stream_params["id"] = song_id

                        query_string = "&".join(
                            [f"{k}={v}" for k, v in stream_params.items()]
                        )
                        stream_url = f"{self.navi_url}/rest/stream.view?{query_string}"

                        return stream_url

                    logger.info(
                        f"🔍 Nenhuma correspondência local para '{query}' no Navidrome."
                    )
                    return None

        except Exception as e:
            logger.error(f"💥 Falha crítica na requisição ao Navidrome: {e}")
            return None

    async def intelligent_search(
        self, query: str
    ) -> Tuple[Optional[wavelink.Search], str]:
        """
        Orquestra a busca de acordo com o modo definido no .env (ONLINE, LOCAL, HIBRIDO).
        Retorna uma tupla: (Resultado_Do_Wavelink, Origem_Do_Audio)
        """
        if query.startswith("http://") or query.startswith("https://"):
            result = await wavelink.Playable.search(query)
            return result, "ONLINE"

        # --- FLUXO LOCAL ---
        if self.mode == "LOCAL":
            stream_url = await self._search_navidrome(query)
            if stream_url:
                result = await wavelink.Playable.search(stream_url)
                return result, "LOCAL"
            return None, "LOCAL_NOT_FOUND"

        # --- FLUXO ONLINE ---
        elif self.mode == "ONLINE":
            result = await wavelink.Playable.search(query)
            return result, "ONLINE"

        # --- FLUXO HÍBRIDO (Padrão) ---
        else:
            # Passo 1: Tenta a sorte na biblioteca local
            stream_url = await self._search_navidrome(query)
            if stream_url:
                result = await wavelink.Playable.search(stream_url)
                return result, "LOCAL"

            # Passo 2: Fallback silencioso para a internet se não achar localmente
            logger.info(f"🌐 Ativando fallback online para: '{query}'")
            result = await wavelink.Playable.search(query)
            return result, "ONLINE"


# Instância única global do gerenciador
search_manager = SearchManager()
