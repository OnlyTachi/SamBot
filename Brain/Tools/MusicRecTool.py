# nao sei se esse arquivo sera usado futuramente
# vai ficar aqui por enquanto
import logging
from Brain.Tools.Research.WebSearch import BuscaTool


class MusicRecTool:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.MusicRecTool")
        self.busca_tool = BuscaTool()

    async def recommend_music(self, query: str):
        """
        Busca recomendações de música baseadas no pedido do usuário.
        """
        self.logger.info(f"🔎 Buscando recomendações para: {query}")

        search_query = f"melhores músicas de {query} recomendações youtube"

        try:
            resultados = await self.busca_tool.buscar_na_cascata(search_query)

            if "Nenhum resultado" in resultados:
                return "❌ Não consegui encontrar recomendações específicas para isso agora."

            report = (
                f"🎶 **Sugestões de Áudio para: {query.title()}**\n"
                f"Aqui está o que encontrei de relevante:\n\n"
                f"{resultados}\n"
                f"💡 *Dica: Você pode me pedir para tocar uma dessas usando o comando +play!*"
            )
            return report

        except Exception as e:
            self.logger.error(f"Erro ao recomendar música: {e}")
            return "⚠️ Ocorreu um erro ao tentar pesquisar essas músicas."
