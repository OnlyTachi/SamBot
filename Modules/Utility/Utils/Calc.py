import discord
from discord.ext import commands
import re


class Calculadora(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="calc", description="Calcule expressões matemáticas de forma inteligente!"
    )
    async def calc(self, ctx: commands.Context, expressao: str):
        expressao_limpa = expressao.strip()

        if re.search(r"/\s*0(\.0*)?($|[^0-9])", expressao_limpa):
            return await ctx.send(" | Resultado: ∞")

        try:
            if not re.match(r"^[0-9\s\+\-\*\/\(\)\.\,]+$", expressao_limpa):
                raise ValueError("Caracteres inválidos")

            expressao_eval = expressao_limpa.replace(",", ".")
            resultado = eval(expressao_eval, {"__builtins__": None}, {})

            if isinstance(resultado, float):
                if resultado.is_integer():
                    resultado = int(resultado)
                else:
                    resultado = round(resultado, 10)

            resultado_formatado = str(resultado).replace(".", ",")
            await ctx.send(f"Resultado: {resultado_formatado}")

        except Exception:
            mensagem_erro = (
                f" | Olha, eu posso até estar matando aula para ficar no Discord,\n"
                f"mas tenho certeza de que `{expressao_limpa}` não é uma conta matemática que faça sentido. Dá uma revisada aí!"
            )
            await ctx.send(mensagem_erro)


async def setup(bot):
    await bot.add_cog(Calculadora(bot))
