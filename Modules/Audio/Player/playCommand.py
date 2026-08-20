import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import logging
from ..Lavalink._search_manager import search_manager

logger = logging.getLogger("SamBot.PlayCommands")


class PlayCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🎵"

    @commands.hybrid_command(
        name="play", aliases=["p", "tocar"], description="Pesquisa e toca música."
    )
    @app_commands.describe(busca="Nome da música ou link.")
    async def play(self, ctx: commands.Context, *, busca: str):
        if not ctx.author.voice:
            return await ctx.send(
                "❌ Você precisa estar em um canal de voz.", ephemeral=True
            )

        player: wavelink.Player = ctx.voice_client
        if not player:
            try:
                player = await ctx.author.voice.channel.connect(
                    cls=wavelink.Player, self_deaf=True
                )
                if hasattr(wavelink, "AutoPlayMode"):
                    player.autoplay = wavelink.AutoPlayMode.enabled
                elif hasattr(wavelink, "AutoPlay"):
                    player.autoplay = wavelink.AutoPlay.enabled
            except discord.ClientException:
                player = ctx.guild.voice_client
            except Exception as e:
                logger.error(f"Erro ao conectar ao canal de voz: {e}", exc_info=True)
                return await ctx.send(
                    "❌ Não consegui conectar ao canal de voz. Verifique se possuo permissões."
                )

        if player.channel != ctx.author.voice.channel:
            return await ctx.send(
                "❌ Já estou tocando em outro canal de voz neste servidor!",
                ephemeral=True,
            )

        player.reply_channel = ctx.channel
        await ctx.defer()

        try:
            tracks, origem = await search_manager.intelligent_search(busca)

            if not tracks:
                if origem == "NOT_FOUND_LOCAL":
                    return await ctx.send(
                        "Eu estou configurada apenas para musica local, e não encontrei nada com essa busca. Tente outro termo ou verifique se a música está na sua biblioteca local."
                    )
                elif origem in ["ALL_ONLINE_OFFLINE", "ALL_OFFLINE"]:
                    return await ctx.send(
                        "Sinto muito, Todos os servidores de música estão offline no momento. Tente novamente mais tarde :("
                    )
                return await ctx.send("❌ Nenhuma música encontrada com essa busca.")

            if isinstance(tracks, wavelink.Playlist):
                added = 0
                for track in tracks.tracks:
                    player.queue.put(track)
                    added += 1
                if not player.playing:
                    await player.play(player.queue.get())
                embed = discord.Embed(
                    description=f"✅ Carregadas **{added}** músicas da playlist **{tracks.name}** na fila.",
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)

            else:
                track = tracks[0]
                txt_origem = (
                    "🎵 Biblioteca Local" if "NAVIDROME" in origem else "🌐 Internet"
                )

                if player.playing:
                    player.queue.put(track)
                    embed = discord.Embed(
                        description=f"📌 **[{track.title}]({track.uri})** adicionada à fila (Posição: {player.queue.count}).",
                        color=discord.Color.orange(),
                    )
                    embed.set_footer(text=f"Fonte: {txt_origem}")
                    await ctx.send(embed=embed)
                else:
                    await player.play(track)
                    await ctx.send(
                        f"🎶 Carregando sua música ({txt_origem})...", delete_after=3
                    )

        except Exception as e:
            logger.error(f"Erro no comando play: {e}")
            await ctx.send("❌ Ocorreu um erro ao tentar processar a música.")


async def setup(bot):
    await bot.add_cog(PlayCommands(bot))
