import discord
from discord.ext import commands
from .base import SocialBase


class InteracoesDiversas(SocialBase):
    """Módulo Sub: Comandos gerais e neutros."""

    @commands.hybrid_command(
        name="poke", aliases=["cutucar"], description="Cutuque alguém."
    )
    async def poke(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "poke")

    @commands.hybrid_command(
        name="feed", aliases=["alimentar"], description="Dê comida a alguém."
    )
    async def feed(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "feed")

    @commands.hybrid_command(
        name="highfive", aliases=["toca_aqui"], description="Dê um high-five em alguém."
    )
    async def highfive(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "highfive")

    # O comando dance é diferente pois não exige um "alvo" e não tem botão de retribuir
    @commands.hybrid_command(
        name="dance", aliases=["dancar"], description="Comece a dançar!"
    )
    async def dance(self, ctx):
        gif_url = await self.get_gif("dance")
        embed = discord.Embed(
            description=f"💃 **{ctx.author.name}** começou a dançar!",
            color=discord.Color.purple(),
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(InteracoesDiversas(bot))
