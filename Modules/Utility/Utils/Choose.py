import discord
from discord.ext import commands
from discord import app_commands
import random


class Escolher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="escolher",
        description="Precisando de ajuda para escolher algo? Deixe-me escolher para você!",
    )
    @app_commands.describe(
        opcoes="Separe as opções por vírgula (ex: Maçã, Banana, Uva)"
    )
    async def escolher(self, ctx: commands.Context, opcoes: str):
        lista_opcoes = [opcao.strip() for opcao in opcoes.split(",")]
        escolha = random.choice(lista_opcoes)
        await ctx.send(
            f"Eu escolho: **{escolha}**, eu espero que você esteja feliz com o resultado!"
        )


async def setup(bot):
    await bot.add_cog(Escolher(bot))
