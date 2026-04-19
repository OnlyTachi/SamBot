import discord
from discord.ext import commands
from .base import SocialBase


class InteracoesRomance(SocialBase):
    """Módulo Sub: Comandos focados em romance e afeto íntimo."""

    @commands.hybrid_command(
        name="kiss", aliases=["beijar"], description="Dê um beijo em alguém."
    )
    async def kiss(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "kiss")

    @commands.hybrid_command(
        name="handhold", aliases=["maos"], description="Segure a mão de alguém."
    )
    async def handhold(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "handhold")

    @commands.hybrid_command(
        name="bite",
        aliases=["morder", "nhac"],
        description="Dê uma mordida (carinhosa ou não) em alguém.",
    )
    async def bite(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "bite")


async def setup(bot):
    await bot.add_cog(InteracoesRomance(bot))
