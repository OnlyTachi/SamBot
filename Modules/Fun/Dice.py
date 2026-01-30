import discord
from discord.ext import commands
from discord import app_commands
import random
import re

class Dice(commands.Cog):
    def __init__(self, bot):
        """Rola dados baseados em notação padrão de RPG."""
        self.bot = bot
        self.emoji = "🎲"

    @commands.hybrid_command(name="roll", description="Rola dados (ex: 1d20, 2d6+3).")
    @app_commands.describe(expressao="A expressão de dados (ex: 1d20+5)")
    async def roll(self, ctx: commands.Context, expressao: str = "1d20"):
        """
        Rola dados baseados em uma notação padrão de RPG (NdX+Mod).
        Exemplos: 1d20, 2d6+4, d100.
        """
        expressao = expressao.lower().replace(" ", "")
        
        # Regex para validar e capturar grupos: (Quantidade)d(Lados)+(Modificador opcional)
        match = re.match(r"^(\d*)d(\d+)([-+]\d+)?$", expressao)
        
        if not match:
            return await ctx.send("❌ Formato inválido! Use algo como `1d20`, `2d6` ou `1d20+5`.")

        qtd_str, lados_str, mod_str = match.groups()

        quantidade = int(qtd_str) if qtd_str else 1
        lados = int(lados_str)
        modificador = int(mod_str) if mod_str else 0

        # Limites de segurança
        if quantidade > 50:
            return await ctx.send("❌ Você só pode rolar até 50 dados por vez.")
        if lados > 1000:
            return await ctx.send("❌ O dado não pode ter mais de 1000 lados.")

        rolagens = [random.randint(1, lados) for _ in range(quantidade)]
        total = sum(rolagens) + modificador

        # Montagem da resposta
        detalhes = f"[{', '.join(map(str, rolagens))}]"
        if mod_str:
            detalhes += f" {mod_str}"
        
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(name=f"{ctx.author.name} rolou {expressao}", icon_url=ctx.author.display_avatar.url)
        
        # Destaque para Crítico (apenas em d20 único)
        if lados == 20 and quantidade == 1:
            if rolagens[0] == 20:
                embed.description = f"# **CRÍTICO!** 🌟\n# **{total}**"
                embed.color = discord.Color.gold()
            elif rolagens[0] == 1:
                embed.description = f"# **FALHA CRÍTICA!** 💀\n# **{total}**"
                embed.color = discord.Color.red()
            else:
                 embed.description = f"🎲 Resultado: **{total}**\n*Detalhes: {detalhes}*"
        else:
            embed.description = f"🎲 Resultado: **{total}**\n*Detalhes: {detalhes}*"

        await ctx.send(embed=embed)

    # nao sei porque eu fiz um arquivo separado so pra isso 

async def setup(bot):
    await bot.add_cog(Dice(bot))