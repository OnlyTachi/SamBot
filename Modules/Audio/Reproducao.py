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
        self.owner_id = int(os.getenv("OWNER_ID", 0))  # Carrega o ID do dono

    async def _notify_owner(self, message: str):
        """Método auxiliar para notificar o dono via DM."""
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
    @app_commands.describe(busca="Nome da música ou link.")
    async def play(self, ctx: commands.Context, *, busca: str):
        """Toca música com sistema de retry e pesquisa nativa."""
        if not ctx.author.voice:
            return await ctx.send(
                "❌ Precisas de estar num canal de voz.", ephemeral=True
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

        await ctx.defer()

        tracks = None
        try:
            # 2. Pesquisa de Música
            try:
                tracks = await wavelink.Playable.search(busca)
            except Exception as e:
                await self._notify_owner(
                    f"⚠️ **Falha na Pesquisa:**\nBusca: `{busca}`\nErro: `{e}`"
                )
                return await ctx.send(
                    f"❌ Erro durante a pesquisa: {e}"
                )  # Adicionado o RETURN aqui

            if not tracks:
                return await ctx.send(f"❌ Não encontrei resultados para: `{busca}`")

            # 3. Lógica para Playlists
            if isinstance(tracks, wavelink.Playlist):
                added_count = 0
                for track in tracks:
                    await vc.queue.put_wait(track)
                    added_count += 1
                await ctx.send(
                    f"✅ Playlist **{tracks.name}** carregada ({added_count} músicas)."
                )

            # 4. Lógica para Música Única
            else:
                track = tracks[0]
                success = False
                for attempt in range(1, 3):
                    try:
                        await vc.queue.put_wait(track)
                        success = True
                        break
                    except:
                        if attempt < 2:
                            await asyncio.sleep(1)

                if success:
                    embed = discord.Embed(
                        description=f"🎵 **[{track.title}]({track.uri})** na fila.",
                        color=discord.Color.green(),
                    )
                    if track.artwork:
                        embed.set_thumbnail(url=track.artwork)
                    await ctx.send(embed=embed)
                else:
                    return await ctx.send("❌ Falha ao carregar a música.")

            if not vc.playing:
                await vc.play(vc.queue.get())

        except Exception as e:
            await ctx.send(f"❌ Erro inesperado: {e}")


async def setup(bot):
    await bot.add_cog(AudioReproducao(bot))
