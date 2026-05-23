import discord
from discord.ext import commands
from discord import app_commands
import random
import re


class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🎲"

    @commands.hybrid_command(
        name="roll",
        aliases=["dado", "rolar", "r"],
        description="Rola dados de RPG (ex: 1d20) ou dados comuns apenas digitando o número de lados (ex: 4).",
    )
    @app_commands.describe(
        expressao="O dado a ser rolado. Pode ser '1d20' ou apenas o número de lados '4'."
    )
    async def roll(self, ctx: commands.Context, expressao: str = "1d20"):
        expressao_limpa = expressao.lower().replace(" ", "")

        if expressao_limpa.isdigit():
            expressao_limpa = f"1d{expressao_limpa}"

        # Validação por Regex
        match = re.match(r"^(\d*)d(\d+)([-+]\d+)?$", expressao_limpa)

        if not match:
            embed_erro = discord.Embed(
                title="⚠️ Formato de Dado Inválido",
                description=(
                    f"Olha, **{ctx.author.name}**, eu tentei procurar esse dado, mas não achei!\n\n"
                    f"⚙️ **Formatos aceitos:**\n"
                    f"• `{ctx.prefix}dado 4` (Rola um dado comum de 4 lados)\n"
                    f"• `{ctx.prefix}dado 1d20` (Notação de RPG: 1 dado de 20 lados)\n"
                    f"• `{ctx.prefix}dado 2d6+4` (2 dados de 6 lados com bônus de +4)\n"
                    f"• `{ctx.prefix}dado` (Rola 1d20 por padrão)"
                ),
                color=discord.Color.orange(),
            )
            return await ctx.send(embed=embed_erro, delete_after=20)

        qtd_str, lados_str, mod_str = match.groups()

        quantidade = int(qtd_str) if qtd_str else 1
        lados = int(lados_str)
        modificador = int(mod_str) if mod_str else 0

        if quantidade > 50:
            return await ctx.send(
                "❌ Você só pode rolar até 50 dados por vez.", ephemeral=True
            )
        if lados > 1000:
            return await ctx.send(
                "❌ O dado não pode ter mais de 1000 lados.", ephemeral=True
            )

        rolagens = [random.randint(1, lados) for _ in range(quantidade)]
        total = sum(rolagens) + modificador

        detalhes = f"[{', '.join(map(str, rolagens))}]"
        if mod_str:
            detalhes += f" {mod_str}"

        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(
            name=f"{ctx.author.name} rolou {expressao_limpa}",
            icon_url=ctx.author.display_avatar.url,
        )

        # Destaque para Crítico em d20
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


async def setup(bot):
    await bot.add_cog(Dice(bot))
