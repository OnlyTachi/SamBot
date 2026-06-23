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
            "31": "Blizzard",
        }

    async def get_deals(self, game_name):
        """Busca preços em várias lojas usando uma abordagem em duas etapas e converte para BRL."""
        query = urllib.parse.quote(game_name)

        # 1ª Etapa: Busca o ID do jogo pelo título (Muito mais preciso)
        search_url = f"{self.base_url}/games?title={query}"
        usd_rate = await self.currency.get_usd_to_brl()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=5) as resp:
                    if resp.status != 200:
                        return (
                            "  *Não foi possível acessar a API de preços no momento.*"
                        )

                    search_results = await resp.json()
                    if not search_results:
                        return "  *Nenhuma oferta encontrada para este título.*"

                    # Pega o ID do primeiro resultado relevante
                    game_id = search_results[0].get("gameID")

                # 2ª Etapa: Puxa o relatório completo de ofertas daquele ID específico
                lookup_url = f"{self.base_url}/games?id={game_id}"
                async with session.get(lookup_url, timeout=5) as resp:
                    if resp.status != 200:
                        return "  *Erro ao detalhar os preços do jogo.*"

                    game_data = await resp.json()
                    deals = game_data.get("deals", [])
                    if not deals:
                        return "  *Nenhum preço listado para este jogo hoje.*"

                    deals_info = [f"💵 **Cotação Dólar ref.:** R$ {usd_rate:.2f}\n"]
                    count = 0

                    # Título oficial retornado pela API
                    title = game_data.get("info", {}).get("title", game_name)

                    for deal in deals:
                        store_id = deal.get("storeID")
                        store_name = self.stores.get(store_id)
                        if not store_name:
                            continue  # Pula lojas que não mapeamos

                        price_usd = float(deal.get("price", 0))
                        normal_usd = float(deal.get("retailPrice", 0))

                        # Converte a string de desconto com segurança
                        try:
                            savings = round(float(deal.get("savings", 0)))
                        except (ValueError, TypeError):
                            savings = 0

                        # Se a API marcar 0 mas houver diferença real de preços, calcula
                        if savings == 0 and normal_usd > price_usd:
                            savings = round(
                                ((normal_usd - price_usd) / normal_usd) * 100
                            )

                        price_brl = price_usd * usd_rate
                        normal_brl = normal_usd * usd_rate

                        # Define o visual baseado na presença de desconto
                        if savings > 0:
                            emoji = "🔥" if savings > 50 else "🏷️"
                            desconto_str = f" | -{savings}% OFF"
                            preco_antigo_str = f" (Era ~R$ {normal_brl:.2f})"
                        else:
                            emoji = "🔵"
                            desconto_str = ""
                            preco_antigo_str = ""

                        deals_info.append(
                            f"{emoji} **{title}** na **{store_name}**\n"
                            f"   R$ {price_brl:.2f}{preco_antigo_str}{desconto_str}"
                        )

                        count += 1
                        if count >= 5:
                            break

                    return "\n".join(deals_info)

        except Exception as e:
            return f"Erro no CheapShark: {e}"
