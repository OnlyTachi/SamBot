import os
import logging
from Brain.Core.NetworkManager import NetworkManager


class ImageSearchTool:
    def __init__(self):
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        self.logger = logging.getLogger("SamBot.ImageSearch")

    async def buscar_pixabay(self, query: str):
        """Busca imagens gratuitas no Pixabay de forma assíncrona."""
        if not self.pixabay_key:
            self.logger.warning("Chave do Pixabay não configurada.")
            return None
        try:
            url = f"https://pixabay.com/api/?key={self.pixabay_key}&q={query}&per_page=3&lang=pt"
            session = NetworkManager.get_aio_session()
            async with session.get(url, timeout=10) as res:
                if res.status == 200:
                    data = await res.json()
                    if data.get("hits"):
                        return data["hits"][0]["largeImageURL"]
        except Exception as e:
            self.logger.error(f"Erro ao buscar no Pixabay: {e}")
        return None

    async def obter_imagem(self, query: str):
        return await self.buscar_pixabay(query)
