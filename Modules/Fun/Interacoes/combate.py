import discord
from discord.ext import commands
from .base import SocialBase


class InteracoesCombate(SocialBase):
    """Módulo Sub: Comandos focados em socos, tapas, etc."""

    @commands.hybrid_command(
        name="slap", aliases=["tapa"], description="Dê um tapa em alguém."
    )
    async def slap(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "slap")

    @commands.hybrid_command(name="punch", description="Dê um soco em alguém.")
    async def punch(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "punch")

    @commands.hybrid_command(name="shoot", description="Atire em alguém.")
    async def shoot(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "shoot")

    @commands.hybrid_command(name="yeet", description="Arremesse alguém para longe!")
    async def yeet(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "yeet")

    @commands.hybrid_command(
        name="chutar", description="Chute o bot para ver o que acontece."
    )
    async def chutar(self, ctx):
        await self.execute_interaction(ctx, ctx.author, self.bot.user, "yeet")


async def setup(bot):
    await bot.add_cog(InteracoesCombate(bot))
