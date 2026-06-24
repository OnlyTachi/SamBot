# Brain/Tools/Anime/AnimeTool.py
from .JikanSearch import JikanSearch
from .TraceRecognizer import TraceRecognizer


class AnimeTool:
    def __init__(self):
        self.search_engine = JikanSearch()
        self.recognizer_engine = TraceRecognizer()

    async def search_anime(self, query: str) -> str:
        """Encaminha para a engine de busca textual."""
        if query.lower().strip() in ["top", "ranking", "melhores"]:
            return await self.search_engine.get_top_anime()
        return await self.search_engine.search(query)

    async def identify_anime_by_image(self, image_url: str) -> str:
        """Encaminha para a engine de reconhecimento por imagem."""
        return await self.recognizer_engine.identify(image_url)
