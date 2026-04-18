import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import random


class AudioControles(commands.Cog):
    def __init__(self, bot):
        """Módulo de Controlos de Áudio: Pausar, pular, volume, etc."""
        self.bot = bot
        self.emoji = "⏯️"

    @commands.hybrid_command(
        name="stop",
        aliases=["leave", "sair", "parar"],
        description="Para a música, limpa a fila e sai do canal de voz.",
    )
    async def stop(self, ctx: commands.Context):
        """Para a reprodução atual, limpa a fila de músicas e desconecta o bot do canal de voz."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            await vc.disconnect()
            await ctx.send("Foi um prazer ouvir musica com você! Bye Bye 👋")
        else:
            await ctx.send(
                "❌ Não estou ligado a nenhum canal de voz no momento.", ephemeral=True
            )

    @commands.hybrid_command(
        name="skip",
        aliases=["s", "pular", "proxima"],
        description="Pula a música atual.",
    )
    async def skip(self, ctx: commands.Context):
        """Pula a faixa que está a tocar no momento e inicia a próxima música da fila."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc and vc.playing:
            await vc.skip(force=True)
            await ctx.send("⏭️ Música pulada.")
        else:
            await ctx.send(
                "❌ Não há nenhuma música a tocar para ser pulada.", ephemeral=True
            )

    @commands.hybrid_command(
        name="pause",
        aliases=["resume", "pausar", "retomar"],
        description="Pausa ou retoma a música.",
    )
    async def pause(self, ctx: commands.Context):
        """Alterna o estado de reprodução do player entre pausado e em execução."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            await vc.pause(not vc.paused)
            estado = "Pausado" if vc.paused else "Retomado"
            await ctx.send(f"⏯️ O player foi **{estado}**.")
        else:
            await ctx.send("❌ Não estou a tocar nada neste momento.", ephemeral=True)

    @commands.hybrid_command(
        name="volume", aliases=["vol"], description="Ajusta o volume (0-100)."
    )
    @app_commands.describe(nivel="Nível de volume de 0 a 100.")
    async def volume(self, ctx: commands.Context, nivel: int):
        """Define o volume de saída do áudio para um valor específico entre 0 e 100."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            nivel = max(0, min(100, nivel))
            await vc.set_volume(nivel)
            await ctx.send(f"🔊 Volume ajustado para **{nivel}%**.")
        else:
            await ctx.send(
                "❌ O bot precisa estar num canal de voz para ajustar o volume.",
                ephemeral=True,
            )

    @commands.hybrid_command(
        name="shuffle",
        aliases=["misturar", "embaralhar", "random", "sh"],
        description="Embaralha a ordem das músicas na fila.",
    )
    async def shuffle(self, ctx: commands.Context):
        """Reorganiza aleatoriamente todas as músicas que estão a aguardar na fila de reprodução."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc and not vc.queue.is_empty:
            random.shuffle(vc.queue)
            await ctx.send("🔀 A fila foi embaralhada!")
        else:
            await ctx.send(
                "❌ A fila está vazia ou não há músicas suficientes para embaralhar.",
                ephemeral=True,
            )

    @commands.hybrid_command(
        name="loop", description="Configura a repetição da música ou da fila."
    )
    @app_commands.describe(
        modo="Modos: track (música), queue (fila) ou off (desligar)."
    )
    async def loop(self, ctx: commands.Context, modo: str = "track"):
        """Altera o comportamento de repetição do bot para uma única música, a fila inteira ou desligado."""
        vc: wavelink.Player = ctx.guild.voice_client
        if not vc:
            return await ctx.send("❌ Não estou num canal de voz.", ephemeral=True)

        modo = modo.lower()
        if modo in ["queue", "fila", "all"]:
            vc.queue.mode = wavelink.QueueMode.loop
            txt = "🔁 Fila"
        elif modo in ["track", "musica", "single"]:
            vc.queue.mode = wavelink.QueueMode.track
            txt = "🔂 Música"
        else:
            vc.queue.mode = wavelink.QueueMode.normal
            txt = "➡️ Desativado"

        await ctx.send(f"🔁 Modo de repetição: **{txt}**.")


async def setup(bot):
    await bot.add_cog(AudioControles(bot))
