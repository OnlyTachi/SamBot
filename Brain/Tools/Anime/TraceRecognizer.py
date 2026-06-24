# Brain/Tools/Anime/TraceRecognizer.py
import aiohttp
import urllib.parse
import logging


class TraceRecognizer:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Anime.Trace")
        self.base_url = "https://api.trace.moe"

    async def identify(self, image_url: str) -> str:
        """Identifica o anime a partir de uma imagem/print da internet."""
        if not image_url:
            return "Forneça o link de uma imagem válida."

        # Ativa o corte de bordas pretas automático e solicita informações adicionais do AniList
        encoded_img = urllib.parse.quote_plus(image_url)
        url = f"{self.base_url}/search?cutBorders&anilistInfo&url={encoded_img}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        return "⚠️ O servidor do Trace.moe está sobrecarregado. Tente novamente em instantes."
                    if resp.status != 200:
                        return f"Erro no reconhecimento visual (Status: {resp.status})."

                    data = await resp.json()
                    results = data.get("result", [])
                    if not results:
                        return (
                            "❌ Nenhum anime correspondente foi detectado nessa imagem."
                        )

                    match = results[0]
                    similarity = match.get("similarity", 0) * 100

                    # Filtro de confiança estrito conforme documentação (Recomendado >= 90%)
                    if similarity < 88:
                        return "🤔 Encontrei um padrão visual parecido, mas a taxa de certeza é muito baixa para afirmar o nome."

                    # Extração segura de títulos vindos do anilistInfo integrado
                    anilist_data = match.get("anilist", {})
                    if isinstance(anilist_data, dict):
                        title_dict = anilist_data.get("title", {})
                        anime_name = (
                            title_dict.get("english")
                            or title_dict.get("romaji")
                            or title_dict.get("native")
                        )
                    else:
                        anime_name = match.get("filename", "Desconhecido")

                    episode = match.get("episode") or "Filme/Especial/1"

                    # Converte segundos para formato MM:SS
                    from_seconds = int(match.get("from", 0))
                    time_stamp = f"{from_seconds // 60:02d}:{from_seconds % 60:02d}"

                    return (
                        f"📸 **Anime Identificado com Sucesso!**\n"
                        f"🎬 **Título:** {anime_name}\n"
                        f"🎞️ **Episódio:** {episode}\n"
                        f"⏱️ **Momento Exato:** {time_stamp}\n"
                        f"🎯 **Precisão:** {similarity:.2f}%\n"
                        f"🖼️ **Pré-visualização do frame:** {match.get('image')}"
                    )
        except Exception as e:
            self.logger.error(f"Erro Trace Identificacao: {e}")
            return "⚠️ Erro interno ao analisar a imagem do anime."
