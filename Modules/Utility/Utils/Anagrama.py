import discord
from discord.ext import commands
import random
import math
from collections import Counter


class Anagrama(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="anagrama", description="Crie um anagrama a partir de um texto!"
    )
    async def anagrama(self, ctx: commands.Context, texto: str):
        # Remove espaços e deixa tudo minúsculo para calcular perfeitamente
        palavra_limpa = texto.replace(" ", "").lower()

        if len(palavra_limpa) > 200 or len(palavra_limpa) == 0:
            return await ctx.send(
                "❌ Por favor, envie uma palavra ou frase de até 200 letras!",
                ephemeral=True,
            )

        # 1. Gera o anagrama aleatório
        letras = list(palavra_limpa)
        random.shuffle(letras)
        resultado = "".join(letras)

        # 2. Calcula o total de anagramas únicos (Permutação com repetição)
        tamanho = len(palavra_limpa)
        contagem_letras = Counter(palavra_limpa)

        divisor = 1
        for contagem in contagem_letras.values():
            divisor *= math.factorial(contagem)

        total_anagramas = math.factorial(tamanho) // divisor

        mensagem = (
            f"✍ | Seu anagrama é... **{resultado}**\n"
            f"A palavra **{texto}** possui {total_anagramas} anagramas diferentes!"
        )

        await ctx.send(mensagem)


async def setup(bot):
    await bot.add_cog(Anagrama(bot))
