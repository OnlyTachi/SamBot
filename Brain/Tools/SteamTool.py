import aiohttp

class SteamTool:
    def __init__(self):
        self.store_api = "https://store.steampowered.com/api"

    async def get_featured_deals(self):
        """Retorna texto com as principais ofertas."""
        url = f"{self.store_api}/featuredcategories?cc=BR&l=portuguese"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200: return "Steam indisponível."
                    data = await resp.json()
                    specials = data.get('specials', {}).get('items', [])[:5] # Top 5
                    
                    text = "Principais promoções Steam BR agora:\n"
                    for item in specials:
                        final = item.get('final_price', 0) / 100
                        original = item.get('original_price', 0) / 100
                        discount = item.get('discount_percent', 0)
                        text += f"- {item['name']}: R${final:.2f} (Era R${original:.2f}, -{discount}%)\n"
                    return text
        except Exception as e:
            return f"Erro ao buscar promoções: {e}"

    async def search_game_details(self, query):
        """Busca detalhes de um jogo específico."""
        try:
            term = query.replace(" ", "+")
            search_url = f"{self.store_api}/storesearch/?term={term}&l=portuguese&cc=BR"
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as resp:
                    data = await resp.json()
                    if data['total'] == 0: return "Jogo não encontrado."
                    app_id = data['items'][0]['id']

            details_url = f"{self.store_api}/appdetails?appids={app_id}&cc=BR&l=portuguese"
            async with aiohttp.ClientSession() as session:
                async with session.get(details_url) as resp:
                    d_data = await resp.json()
                    if not d_data[str(app_id)]['success']: return "Erro ao ler detalhes."
                    
                    game = d_data[str(app_id)]['data']
                    price = game.get('price_overview', {})
                    price_str = f"R${price.get('final', 0)/100:.2f}" if price else "Grátis/Não listado"
                    
                    info = (
                        f"Jogo: {game['name']}\n"
                        f"Preço: {price_str}\n"
                        f"Descrição: {game['short_description']}\n"
                        f"Metacritic: {game.get('metacritic', {}).get('score', 'N/A')}\n"
                        f"Requisitos PC: {game.get('pc_requirements', {}).get('minimum', 'Não listado')}"
                    )
                    return info
        except Exception as e:
            return f"Erro SteamTool: {e}"