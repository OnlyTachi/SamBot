from .Currency import CurrencyService
from .CheapShark import CheapSharkService
from .IGDB import IGDBService

class GameTool:
    def __init__(self):
        self.currency = CurrencyService()
        self.cheapshark = CheapSharkService(self.currency)
        self.igdb = IGDBService()

    async def search_game(self, query: str):
        """
        Realiza o fluxo completo de busca de jogo:
        1. Busca Metadados (IGDB)
        2. Busca Preços (CheapShark + Currency)
        """
        report = f"🎮 **Relatório de Jogo: {query.title()}**\n"
        
        try:
            igdb_info = await self.igdb.get_game_info(query)
            if igdb_info:
                report += f"\n{igdb_info}\n"
        except Exception as e:
            print(f"Erro IGDB no fluxo: {e}")

        report += "\n💸 **Comparativo de Preços (Estimado BRL):**\n"
        try:
            deals = await self.cheapshark.get_deals(query)
            report += deals
        except Exception as e:
            report += f"Erro ao buscar preços: {e}"

        return report