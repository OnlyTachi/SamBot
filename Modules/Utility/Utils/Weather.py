import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

# Importa o DataManager para ler a sua base de dados centralizada
from Brain.Memory.DataManager import data_manager


class Clima(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="clima",
        aliases=["tempo", "previsao", "weather"],
        description="Mostra a previsão do tempo atual para uma cidade!",
    )
    @app_commands.describe(
        cidade="O nome da cidade que você deseja consultar (ex: Rio de Janeiro)"
    )
    async def clima(self, ctx: commands.Context, *, cidade: str):
        await ctx.defer()

        cidade_formatada = cidade.strip()
        cidade_lower = cidade_formatada.lower()

        nlp_config = data_manager.get_knowledge("nlp_data") or {}
        cfg_weather = nlp_config.get("intents", {}).get("weather", {})
        mapeamento_estados = cfg_weather.get("state_mapping", {})

        if cidade_lower in mapeamento_estados:
            cidade_formatada = mapeamento_estados[cidade_lower]
        # ───────────────────────────────────

        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={cidade_formatada}&count=1&language=pt"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(geo_url) as geo_resp:
                    if geo_resp.status != 200:
                        return await ctx.send(
                            "❌ Não consegui consultar o serviço de localização no momento."
                        )
                    geo_dados = await geo_resp.json()
            except Exception:
                return await ctx.send(
                    "❌ Ops! O serviço de geocodificação está fora do ar."
                )

            if not geo_dados.get("results"):
                return await ctx.send(
                    f"❌ A cidade **{cidade}** não foi encontrada. Verifique a ortografia!"
                )

            resultado = geo_dados["results"][0]
            lat = resultado["latitude"]
            lon = resultado["longitude"]
            nome_cidade = resultado["name"]
            pais = resultado.get("country", "")

            clima_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code&timezone=auto"

            try:
                async with session.get(clima_url) as clima_resp:
                    if clima_resp.status != 200:
                        return await ctx.send(
                            "❌ Não consegui obter os dados climáticos para essa região."
                        )
                    clima_dados = await clima_resp.json()
            except Exception:
                return await ctx.send(
                    "❌ Ops! A API de clima está fora do ar no momento... Tente novamente mais tarde."
                )

        atual = clima_dados.get("current", {})
        if not atual:
            return await ctx.send("❌ Houve um erro ao ler os dados meteorológicos.")

        temp = atual.get("temperature_2m")
        sensacao = atual.get("apparent_temperature")
        umidade = Parcel = atual.get("relative_humidity_2m")
        codigo_clima = atual.get("weather_code", 0)

        mapeamento_wmo = {
            0: ("Céu limpo", "☀️"),
            1: ("Principalmente limpo", "🌤️"),
            2: ("Parcialmente nublado", "⛅"),
            3: ("Encoberto", "☁️"),
            45: ("Nevoeiro", "🌫️"),
            48: ("Nevoeiro com formação de geada", "🌫️"),
            51: ("Chuvisco leve", "🌧️"),
            53: ("Chuvisco moderado", "🌧️"),
            55: ("Chuvisco denso", "🌧️"),
            61: ("Chuva fraca", "🌧️"),
            63: ("Chuva moderada", "🌧️"),
            65: ("Chuva forte", "🌧️"),
            71: ("Neve leve", "❄️"),
            73: ("Neve moderada", "❄️"),
            75: ("Neve forte", "❄️"),
            77: ("Granizo", "🌨️"),
            80: ("Pancadas de chuva leves", "🌦️"),
            81: ("Pancadas de chuva moderadas", "🌦️"),
            82: ("Pancadas de chuva violentas", "🌧️"),
            95: ("Trovoada leve ou moderada", "⛈️"),
            96: ("Trovoada com granizo leve", "⛈️"),
            97: ("Trovoada com granizo forte", "⛈️"),
        }

        condicao, emoji = mapeamento_wmo.get(codigo_clima, ("Desconhecido", "🌡️"))

        embed = discord.Embed(
            title=f"{emoji} Clima em {nome_cidade}, {pais}", color=0x3498DB
        )
        embed.add_field(name="Condição Atual", value=condicao, inline=False)
        embed.add_field(name="Temperatura", value=f"{temp}°C", inline=True)
        embed.add_field(name="Sensação Térmica", value=f"{sensacao}°C", inline=True)
        embed.add_field(name="Umidade do Ar", value=f"{umidade}%", inline=True)
        embed.set_footer(text="Fonte: Open-Meteo")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Clima(bot))
