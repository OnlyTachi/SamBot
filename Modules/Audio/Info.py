import discord
from discord.ext import commands
import wavelink

# Importa as funções úteis
from ._utils import create_progress_bar, parse_duration


class AudioInfo(commands.Cog):
    def __init__(self, bot):
        """Módulo de Informações: Fila de reprodução, música atual, etc."""
        self.bot = bot
        self.emoji = "📋"

    @commands.hybrid_command(
        name="nowplaying",
        aliases=["np", "tocando"],
        description="Mostra detalhes da música que está tocando agora.",
    )
    async def nowplaying(self, ctx: commands.Context):
        """Exibe um resumo detalhado da faixa atual, incluindo título, duração e barra de progresso."""
        vc: wavelink.Player = ctx.guild.voice_client
        if not vc or not vc.current:
            return await ctx.send("🔇 Não há nada tocando no momento.", ephemeral=True)

        track = vc.current
        bar = create_progress_bar(vc.position, track.length)
        dur = parse_duration(track.length)

        embed = discord.Embed(
            title="🎧 Tocando Agora",
            description=f"**[{track.title}]({track.uri})**",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Progresso", value=f"`{bar}` [{dur}]")

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="queue",
        aliases=["fila", "q"],
        description="Exibe as próximas músicas e estatísticas da fila.",
    )
    async def queue(self, ctx: commands.Context):
        """Exibe a lista das próximas 10 músicas na fila, o tempo total estimado e o modo de repetição atual."""
        vc: wavelink.Player = ctx.guild.voice_client

        if not vc or (not vc.current and vc.queue.is_empty):
            return await ctx.send("📭 A fila está vazia no momento.")

        embed = discord.Embed(title="📋 Fila de Reprodução", color=0x2B2D31)

        # Define o status do loop para o rodapé
        loop_status = "➡️ Normal"
        if vc.queue.mode == wavelink.QueueMode.track:
            loop_status = "🔂 Música"
        elif vc.queue.mode == wavelink.QueueMode.loop:
            loop_status = "🔁 Fila"

        # Música atual
        if vc.current:
            current = vc.current
            embed.add_field(
                name="🎧 Tocando Agora",
                value=f"**[{current.title}]({current.uri})**\n*Duração: {parse_duration(current.length)}*",
                inline=False,
            )
            if current.artwork:
                embed.set_thumbnail(url=current.artwork)

        # Próximas músicas
        if not vc.queue.is_empty:
            upcoming = list(vc.queue)[:10]
            queue_list = ""
            for i, track in enumerate(upcoming):
                dur = parse_duration(track.length)
                queue_list += f"`{i+1}.` {track.title[:50]}... **[{dur}]**\n"

            embed.add_field(name="📜 Próximas na Fila", value=queue_list, inline=False)

            total_ms = sum(t.length for t in vc.queue)
            total_time = parse_duration(total_ms)

            footer_text = f"Músicas na fila: {len(vc.queue)} | Tempo total: {total_time} | Loop: {loop_status}"
            embed.set_footer(text=footer_text)
        else:
            embed.add_field(
                name="📜 Próximas na Fila",
                value="*Nenhuma música na sequência.*",
                inline=False,
            )
            embed.set_footer(text=f"Loop: {loop_status}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AudioInfo(bot))
