# Brain/Tools/Anime/JikanSearch.py
import aiohttp
import urllib.parse
import logging


class JikanSearch:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Anime.Jikan")
        self.base_url = "https://api.jikan.moe/v4"

    async def search(self, query: str) -> str:
        """Busca um anime pelo nome e traz informações detalhadas."""
        if not query:
            return "Forneça o nome de um anime para pesquisar."

        encoded = urllib.parse.quote(query)
        url = f"{self.base_url}/anime?q={encoded}&limit=1"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        return (
                            "⚠️ Taxa limite atingida na API Jikan. Aguarde um instante."
                        )
                    if resp.status != 200:
                        return f"Erro na Jikan API (Status: {resp.status})."

                    data = await resp.json()
                    results = data.get("data", [])
                    if not results:
                        return f"🔍 Não encontrei nenhum anime com o nome '{query}'."

                    anime = results[0]
                    genres = ", ".join([g.get("name") for g in anime.get("genres", [])])
                    synopsis = anime.get("synopsis", "Sem sinopse disponível.")
                    if len(synopsis) > 350:
                        synopsis = synopsis[:350] + "..."

                    return (
                        f"⛩️ **Anime:** {anime.get('title_english') or anime.get('title')}\n"
                        f"⭐ **Nota:** {anime.get('score', 'N/A')}/10\n"
                        f"📺 **Formato:** {anime.get('type')} | **Eps:** {anime.get('episodes', 'N/A')}\n"
                        f"🧬 **Gêneros:** {genres}\n"
                        f"📖 **Sinopse:** {synopsis}\n"
                        f"🔗 **MAL Link:** {anime.get('url')}"
                    )
        except Exception as e:
            self.logger.error(f"Erro Jikan Search: {e}")
            return "⚠️ Erro ao processar a busca do anime."

    async def get_top_anime(self) -> str:
        """Recurso Extra: Traz os animes mais bem avaliados/em alta."""
        url = f"{self.base_url}/top/anime?limit=5"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return "Não consegui obter o ranking de animes agora."
                    data = await resp.json()
                    top_list = data.get("data", [])

                    report = "🏆 **Top 5 Animes Mais Votados (MyAnimeList):**\n"
                    for i, anime in enumerate(top_list, 1):
                        title = anime.get("title_english") or anime.get("title")
                        report += f"{i}. **{title}** — ⭐ {anime.get('score')}/10\n"
                    return report
        except Exception as e:
            self.logger.error(f"Erro Jikan Top: {e}")
            return "⚠️ Erro ao carregar o ranking."
