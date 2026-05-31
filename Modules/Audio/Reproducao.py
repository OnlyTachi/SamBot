import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
import os


class AudioReproducao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🎶"
        self.owner_id = int(os.getenv("OWNER_ID", 0))

    async def _notify_owner(self, message: str):
        if self.owner_id == 0:
            return
        try:
            owner = self.bot.get_user(self.owner_id) or await self.bot.fetch_user(
                self.owner_id
            )
            if owner:
                await owner.send(message)
        except:
            pass

    @commands.hybrid_command(
        name="play", aliases=["p", "tocar"], description="Pesquisa e toca música."
    )
    @app_commands.describe(busca="Nome da música ou link (YouTube, Spotify, etc).")
    async def play(self, ctx: commands.Context, *, busca: str):
        if not ctx.author.voice:
            return await ctx.send(
                "❌ Precisa de estar num canal de voz.", ephemeral=True
            )

        if not ctx.guild.voice_client:
            try:
                vc: wavelink.Player = await ctx.author.voice.channel.connect(
                    cls=wavelink.Player
                )
            except Exception as e:
                await self._notify_owner(
                    f"🚨 **Erro de Conexão (Voice):**\nServidor: `{ctx.guild.name}`\nCanal: `{ctx.author.voice.channel.name}`\nErro: `{e}`"
                )
                return await ctx.send(f"❌ Erro ao ligar ao canal: {e}")
        else:
            vc: wavelink.Player = ctx.guild.voice_client

        vc.home = ctx.channel

        await ctx.defer()

        try:
            # Realiza a busca usando o Wavelink
            if busca.startswith("http"):
                tracks = await wavelink.Playable.search(busca)
            else:
                tracks = await wavelink.Playable.search(
                    busca, source=wavelink.TrackSource.SoundCloud
                )
        except Exception as e:
            return await ctx.send(f"❌ Erro na pesquisa: {e}")

        if not tracks:
            return await ctx.send(f"❌ Não encontrei resultados.")

        try:
            # 1. Se a busca retornar uma playlist direto (ex: link do Spotify/YouTube)
            if isinstance(tracks, wavelink.Playlist):
                added_count = 0
                for track in tracks.tracks:
                    vc.queue.put(track)
                    added_count += 1
                await ctx.send(
                    f"✅ Playlist **{tracks.name}** carregada ({added_count} músicas)."
                )

            # 2. Se for uma busca por texto puro ou link de música única
            else:
                # O Wavelink devolve um objeto Search, então usamos tracks.tracks para pegar a lista
                if hasattr(tracks, "tracks") and tracks.tracks:
                    track = tracks.tracks[0]
                else:
                    track = tracks[0]  # Fallback caso seja uma lista pura

                vc.queue.put(track)

                plataforma = (
                    "Spotify"
                    if getattr(track, "source", "") == "spotify"
                    else track.source.capitalize()
                )

                embed = discord.Embed(
                    description=f"🎵 **[{track.title}]({track.uri})** na fila via {plataforma}.",
                    color=discord.Color.green(),
                )
                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)
                await ctx.send(embed=embed)

            # Inicia a reprodução se o player estiver parado
            if not vc.playing:
                await vc.play(vc.queue.get())

        except Exception as e:
            await ctx.send(f"❌ Erro inesperado ao tocar: {e}")


async def setup(bot):
    await bot.add_cog(AudioReproducao(bot))
