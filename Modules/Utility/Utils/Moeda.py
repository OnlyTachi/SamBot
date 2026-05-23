import discord
from discord.ext import commands
from discord import app_commands
import aiohttp


class Conversor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="moeda", description="Converte o valor de uma moeda para outra."
    )
    @app_commands.describe(
        de="Moeda de origem (ex: USD)",
        para="Moeda de destino (ex: BRL)",
        valor="Valor a ser convertido (ex: 9.99)",
    )
    async def moeda(
        self, interaction: discord.Interaction, de: str, para: str, valor: float
    ):
        await interaction.response.defer()

        de = de.upper().strip()
        para = para.upper().strip()

        url = f"https://economia.awesomeapi.com.br/last/{de}-{para}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return await interaction.followup.send(
                            f"❌ Não encontrei a cotação de `{de}` para `{para}`. Verifique se as siglas estão corretas!"
                        )
                    dados = await response.json()
            except Exception:
                return await interaction.followup.send(
                    "❌ Ops! A API de moedas está fora do ar no momento."
                )

        chave_api = f"{de}{para}"

        if chave_api not in dados:
            return await interaction.followup.send(
                "❌ Houve um erro ao ler os dados da conversão."
            )

        cotacao = float(dados[chave_api]["bid"])
        resultado = valor * cotacao

        valor_formatado = f"{valor:.2f}".replace(".", ",")
        resultado_formatado = f"{resultado:.2f}".replace(".", ",")

        mensagem = f" | {valor_formatado} {de} em {para}: {resultado_formatado} {para}"

        await interaction.followup.send(mensagem)


async def setup(bot):
    await bot.add_cog(Conversor(bot))
