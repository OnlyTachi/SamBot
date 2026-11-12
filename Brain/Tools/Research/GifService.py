# Brain/Tools/Research/GifService.py
import io
import random
import logging
from typing import Optional
from Brain.Core.NetworkManager import NetworkManager
from Core.ConfigLoader import AppConfig

logger = logging.getLogger("SamBot.GifService")


class GifService:
    def __init__(self):
        self.api_key = AppConfig.get("GIPHY_API_KEY") or AppConfig.get_secret(
            "GIPHY_API_KEY"
        )
        self.base_url = "https://api.giphy.com/v1/gifs/search"

        self.afeto_tags = {
            "hug": ["anime hug", "hug cute", "warm hug anime"],
            "pat": ["anime headpat", "pat pat anime", "cute pat"],
            "kiss": ["anime kiss cheek", "cute kiss anime"],
            "happy": ["anime happy dance", "excited anime gif"],
            "blush": ["anime blush", "cute shy anime"],
            "love": ["anime heart", "love anime cute"],
        }

    async def download_gif_bytes(self, url: str) -> io.BytesIO | None:
        """Baixa o GIF diretamente para a RAM sem salvar no disco."""
        if not url:
            return None
        session = NetworkManager.get_aio_session()
        try:
            async with session.get(url, timeout=5.0) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    buffer = io.BytesIO(data)
                    buffer.seek(0)
                    return buffer
        except Exception as e:
            logger.debug(f"Erro ao baixar GIF: {e}")
        return None

    async def get_reaction_gif(self, emotion_type: str) -> Optional[str]:
        """Busca um GIF aleatório baseado no tipo de afeto/reação."""
        if not self.api_key:
            logger.debug("GIPHY_API_KEY não configurada. Serviço de GIF inativo.")
            return None

        tags = self.afeto_tags.get(emotion_type, ["anime reaction cute"])
        tag_escolhida = random.choice(tags)

        params = {
            "api_key": self.api_key,
            "q": tag_escolhida,
            "limit": 10,
            "rating": "g",
            "lang": "pt",
        }

        session = NetworkManager.get_aio_session()
        try:
            async with session.get(self.base_url, params=params, timeout=4.0) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("data", [])
                    if results:
                        item = random.choice(results)
                        return item.get("images", {}).get("original", {}).get("url")
        except Exception as e:
            logger.debug(f"Aviso ao buscar GIF de reação: {e}")
        return None
