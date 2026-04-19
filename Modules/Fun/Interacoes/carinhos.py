import discord
from discord.ext import commands
from .base import SocialBase


class InteracoesCarinho(SocialBase):
    """Módulo Sub: Comandos focados em carinho e afeto."""

    @commands.hybrid_command(
        name="hug", aliases=["abraçar"], description="Dê um abraço em alguém."
    )
    async def hug(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "hug")

    @commands.hybrid_command(
        name="pat", aliases=["carinho"], description="Faça carinho em alguém."
    )
    async def pat(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "pat")

    @commands.hybrid_command(
        name="cuddle",
        aliases=["conchinha"],
        description="Fique de conchinha com alguém.",
    )
    async def cuddle(self, ctx, user: discord.Member):
        await self.execute_interaction(ctx, ctx.author, user, "cuddle")


# Esta função setup faz o bot identificar isso como um Cog válido e carregá-lo
async def setup(bot):
    await bot.add_cog(InteracoesCarinho(bot))
