import discord
from discord.ext import commands
import wavelink


class QueueInfoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="queue",
        aliases=["q", "fila"],
        description="Mostra a fila de músicas atual.",
    )
    async def queue(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.send(
                "❌ Não estou tocando nada no momento.", ephemeral=True
            )

        if player.queue.is_empty:
            return await ctx.send(
                "📋 A fila está vazia. Tocando apenas a música atual.", ephemeral=True
            )

        current = player.current
        descricao = f"**Tocando Agora:**\n🔹 [{current.title}]({current.uri})\n\n**Próximas Músicas:**\n"

        # Pega as próximas 10 músicas da fila nativa
        for i, track in enumerate(player.queue[:10], start=1):
            descricao += f"`{i}.` [{track.title}]({track.uri})\n"

        if player.queue.count > 10:
            descricao += f"\n*...e mais {player.queue.count - 10} músicas.*"

        embed = discord.Embed(
            title="📋 Fila do Servidor",
            description=descricao,
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(QueueInfoCommands(bot))
