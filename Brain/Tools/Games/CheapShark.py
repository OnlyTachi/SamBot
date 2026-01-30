import aiohttp
import urllib.parse

class CheapSharkService:
    def __init__(self, currency_service):
        self.base_url = "https://www.cheapshark.com/api/1.0"
        self.currency = currency_service
        
        self.stores = {
            "1": "Steam",
            "7": "GOG",
            "8": "Origin/EA",
            "11": "Humble Store",
            "25": "Epic Games",
            "31": "Blizzard"
        }

    async def get_deals(self, game_name):
        """Busca preços em várias lojas e converte para BRL."""
        query = urllib.parse.quote(game_name)
        url = f"{self.base_url}/deals?title={query}&limit=10&exact=0"
        
        deals_info = []
        usd_rate = await self.currency.get_usd_to_brl()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        deals = await resp.json()
                        if not deals: return "Nenhuma oferta encontrada."
                        count = 0
                        deals_info.append(f"💵 **Cotação Dólar ref.:** R${usd_rate:.2f}\n")
                        
                        found_titles = set()

                        for deal in deals:
                            store_id = deal.get('storeID')
                            store_name = self.stores.get(store_id, "Outra Loja")
                            
                            if store_id not in self.stores: continue
                            
                            title = deal.get('title')
                            if title in found_titles and len(found_titles) > 2: continue
                            found_titles.add(title)

                            price_usd = float(deal.get('salePrice', 0))
                            normal_usd = float(deal.get('normalPrice', 0))
                            savings = float(deal.get('savings', 0))

                            price_brl = price_usd * usd_rate
                            normal_brl = normal_usd * usd_rate

                            emoji = "🟢" if savings > 50 else "🔵"
                            
                            deals_info.append(
                                f"{emoji} **{title}** na **{store_name}**\n"
                                f"   R${price_brl:.2f} (Era ~R${normal_brl:.2f}) | -{int(savings)}% OFF"
                            )
                            
                            count += 1
                            if count >= 5: break
                        
                        return "\n".join(deals_info)
        except Exception as e:
            return f"Erro no CheapShark: {e}"
        
        return "Nenhuma oferta encontrada."