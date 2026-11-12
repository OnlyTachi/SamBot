import os
import urllib.parse
import logging
from typing import Optional, Dict, Any, List
from Brain.Core.NetworkManager import NetworkManager
from Core.ConfigLoader import AppConfig


class JikanSearch:
    def __init__(self):
        self.logger: logging.Logger = logging.getLogger("SamBot.Anime.Jikan")
        self.base_url: str = "https://api.jikan.moe/v4"

        self.http_timeout: float = float(AppConfig.get("JIKAN_TIMEOUT", "10.0"))
        self.top_anime_limit: int = int(AppConfig.get("JIKAN_TOP_LIMIT", "5"))
        self.max_synopsis_chars: int = 350

    async def search(self, query: str) -> str:
        if not query:
            return "Forneça o nome de um anime para pesquisar."
        encoded = urllib.parse.quote(query)
        url = f"{self.base_url}/anime?q={encoded}&limit=1"
        session = NetworkManager.get_aio_session()
        try:
            async with session.get(url, timeout=self.http_timeout) as resp:
                if resp.status == 429:
                    return "Taxa limite atingida na API Jikan. Aguarde um instante."
                if resp.status != 200:
                    return f"Erro na Jikan API (Status: {resp.status})."
                data: Dict[str, Any] = await resp.json()
                results: List[Dict[str, Any]] = data.get("data", [])
                if not results:
                    return f"Não encontrei nenhum anime com o nome '{query}'."
                anime = results[0]
                genres = ", ".join([g.get("name", "") for g in anime.get("genres", [])])
                synopsis = anime.get("synopsis") or "Sem sinopse disponível."
                if len(synopsis) > self.max_synopsis_chars:
                    synopsis = synopsis[: self.max_synopsis_chars] + "..."
                return (
                    f"**Anime:** {anime.get('title_english') or anime.get('title')}\n"
                    f"**Nota:** {anime.get('score', 'N/A')}/10\n"
                    f"**Formato:** {anime.get('type')} | **Eps:** {anime.get('episodes', 'N/A')}\n"
                    f"**Gêneros:** {genres}\n"
                    f"**Sinopse:** {synopsis}\n"
                    f"**MAL Link:** {anime.get('url')}"
                )
        except Exception as e:
            self.logger.error(f"Erro Jikan Search: {e}")
            return "Erro ao processar a busca do anime."

    async def get_top_anime(self) -> str:
        url = f"{self.base_url}/top/anime?limit={self.top_anime_limit}"
        session = NetworkManager.get_aio_session()
        try:
            async with session.get(url, timeout=self.http_timeout) as resp:
                if resp.status != 200:
                    return "Não consegui obter o ranking de animes agora."
                data: Dict[str, Any] = await resp.json()
                top_list: List[Dict[str, Any]] = data.get("data", [])
                report = f"**Top {self.top_anime_limit} Animes Mais Votados (MyAnimeList):**\n"
                for i, anime in enumerate(top_list, 1):
                    title = anime.get("title_english") or anime.get("title")
                    report += f"{i}. **{title}** | ⭐ {anime.get('score')}/10\n"
                return report
        except Exception as e:
            self.logger.error(f"Erro Jikan Top: {e}")
            return "Erro ao carregar o ranking."
