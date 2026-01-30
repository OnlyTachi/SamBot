import discord
from discord.ext import commands
import aiohttp
import json

class SteamStore(commands.Cog):
    def __init__(self, bot):
        """Pesquisa jogos na loja da Steam e exibe informações."""
        self.bot = bot
        # URL da API pública da Steam para pesquisa
        self.search_url = "https://store.steampowered.com/api/storesearch"
        self.app_details_url = "https://store.steampowered.com/api/appdetails"
        self.emoji = "🎮"

    @commands.hybrid_command(name="steam", description="Pesquisa um jogo na loja da Steam.")
    async def steam(self, ctx: commands.Context, *, jogo: str):
        """Pesquisa informações e preços de um jogo na Steam."""
        await ctx.defer() # Importante para evitar timeout em Slash Commands

        params = {
            "term": jogo,
            "l": "brazilian",
            "cc": "BR"
        }

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Buscar ID do jogo
                async with session.get(self.search_url, params=params) as resp:
                    if resp.status != 200:
                        return await ctx.send("Erro ao conectar com a Steam API.")
                    
                    data = await resp.json()
                    
                    if data['total'] == 0:
                        return await ctx.send(f"Não encontrei nenhum jogo com o nome: `{jogo}`")
                    
                    first_result = data['items'][0]
                    app_id = first_result['id']
                    
                # 2. Buscar Detalhes do Jogo usando o AppID
                details_params = {"appids": app_id, "cc": "BR", "l": "brazilian"}
                async with session.get(self.app_details_url, params=details_params) as resp_details:
                    details_data = await resp_details.json()
                    
                    if not details_data[str(app_id)]['success']:
                         return await ctx.send("Erro ao obter detalhes do jogo.")
                    
                    game_info = details_data[str(app_id)]['data']

                    # Extração de dados com fallback
                    name = game_info.get('name', 'Desconhecido')
                    short_desc = game_info.get('short_description', 'Sem descrição.')
                    header_img = game_info.get('header_image', '')
                    website = game_info.get('website', '')
                    
                    price_text = "Gratuito / Indisponível"
                    if 'price_overview' in game_info:
                        price_text = game_info['price_overview']['final_formatted']
                    elif game_info.get('is_free', False):
                        price_text = "Gratuito para Jogar"

                    # Montar Embed
                    embed = discord.Embed(title=name, description=short_desc, color=0x1b2838)
                    embed.set_image(url=header_img)
                    embed.add_field(name="💰 Preço (BR)", value=f"**{price_text}**", inline=True)
                    
                    if 'metacritic' in game_info:
                        embed.add_field(name="⭐ Metacritic", value=str(game_info['metacritic']['score']), inline=True)

                    if website:
                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(label="Site Oficial", url=website))
                        view.add_item(discord.ui.Button(label="Ver na Steam", url=f"https://store.steampowered.com/app/{app_id}/"))
                        await ctx.send(embed=embed, view=view)
                    else:
                        await ctx.send(embed=embed)

            except Exception as e:
                self.bot.log.error(f"Erro no comando Steam: {e}")
                await ctx.send(f"Ocorreu um erro ao buscar na Steam: {str(e)}")

async def setup(bot):
    await bot.add_cog(SteamStore(bot))