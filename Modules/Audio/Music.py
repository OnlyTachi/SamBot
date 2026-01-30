import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import random
import asyncio
import os

# Helpers internos
from ._YoutubeHelper import YoutubeHelper
from ._PlaylistManager import PlaylistManager

class Music(commands.Cog):
    def __init__(self, bot):
        """Comandos de música"""
        self.bot = bot
        self.playlist_manager = PlaylistManager()
        self.yt_helper = YoutubeHelper()
        self.bot.loop.create_task(self.connect_nodes())
        self.emoji = "🎵"

    async def connect_nodes(self):
        """Conecta ao Lavalink (Docker/Local)."""
        await self.bot.wait_until_ready()
        nodes = [wavelink.Node(uri=os.getenv("WAVE_URI"), password=os.getenv("WAVE_PASSWORD"))]
        try:
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            self.bot.log.info("Lavalink conectado.")
        except Exception as e:
            self.bot.log.error(f"Erro Lavalink: {e}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Evento disparado quando uma música termina."""
        player = payload.player
        if not player: return
        if player.queue.mode == wavelink.QueueMode.loop:
            await player.play(payload.track)
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload):
        """Evento disparado quando uma música começa a tocar."""
        
        player = payload.player
        track = payload.track

        if not player: return

        self.bot.is_music_playing = True

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, 
                name=f"{track.title[:120]}" 
            )
        )

    @commands.Cog.listener()
    async def on_wavelink_queue_end(self, player):
        """Evento disparado quando a fila acaba."""
        
        self.bot.is_music_playing = False

        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.listening, 
                name="suas ordens..."
            )
        )
        
        if self.bot.status_loop.is_running():
            self.bot.status_loop.restart()

    # --- Comandos Principais ---

    @commands.hybrid_command(name="play", aliases=["p"], description="Toca música (YouTube/Link).")
    @app_commands.describe(busca="URL ou nome da música")
    async def play(self, ctx: commands.Context, *, busca: str):
        """Toca música. Suporta playlists do YouTube. """
        if not ctx.author.voice:
            return await ctx.send("❌ Entre em um canal de voz primeiro.", ephemeral=True)

        if not ctx.guild.voice_client:
            try:
                vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                return await ctx.send(f"❌ Erro ao conectar: {e}")
        else:
            vc: wavelink.Player = ctx.guild.voice_client

        await ctx.defer()

        playlist_id = self.yt_helper.extract_playlist_id(busca)
        
        if playlist_id:
            urls = self.yt_helper.get_playlist_items(playlist_id, max_items=50)
            if urls:
                added = 0
                for url in urls:
                    tracks = await wavelink.Playable.search(url)
                    if tracks:
                        await vc.queue.put_wait(tracks[0])
                        added += 1
                await ctx.send(f"✅ Playlist resolvida via API: **{added}** músicas adicionadas à fila.")
                if not vc.playing: await vc.play(vc.queue.get())
                return
            else:
                pass

        if "https://" in busca:
            tracks = await wavelink.Playable.search(busca)
        else:
            results = await self.yt_helper.search(busca)
            if not results:
                return await ctx.send("❌ Não encontrado via API.")
            video_info = results[0] # Pega o primeiro da lista
            tracks = await wavelink.Playable.search(video_info['url'])
        if not tracks:
            return await ctx.send("❌ Erro ao carregar música.")

        if isinstance(tracks, wavelink.Playlist):
            for t in tracks: await vc.queue.put_wait(t)
            await ctx.send(f"✅ Playlist **{tracks.name}** adicionada.")
        else:
            track = tracks[0]
            await vc.queue.put_wait(track)
            embed = discord.Embed(description=f"🎵 **{track.title}** adicionado.", color=discord.Color.green())
            if hasattr(track, 'artwork'): embed.set_thumbnail(url=track.artwork)
            await ctx.send(embed=embed)

        if not vc.playing:
            await vc.play(vc.queue.get())

    @commands.hybrid_command(name="stop", aliases=["leave", "sair"], description="Para e sai.")
    async def stop(self, ctx: commands.Context):
        """Para e sai do canal de voz."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            await vc.disconnect()
            await ctx.send("👋 Desconectado.")

    @commands.hybrid_command(name="skip", aliases=["s", "pular"], description="Pula música.")
    async def skip(self, ctx: commands.Context):
        """Pula a música atual."""
        vc = ctx.guild.voice_client
        if vc and vc.playing:
            await vc.skip(force=True)
            await ctx.send("⏭️ Pulado.")

    @commands.hybrid_command(name="pause", aliases=["pausar"], description="Pausa/Despausa.")
    async def pause(self, ctx: commands.Context):
        """Pausa ou retoma a música."""
        vc = ctx.guild.voice_client
        if vc:
            await vc.pause(not vc.paused)
            status = "Pausado" if vc.paused else "Retomado"
            await ctx.send(f"⏯️ {status}.")

    @commands.hybrid_command(name="volume", aliases=["vol"], description="Volume 0-100.")
    async def volume(self, ctx: commands.Context, nivel: int):
        """Ajusta o volume do bot."""
        vc = ctx.guild.voice_client
        if vc:
            await vc.set_volume(max(0, min(100, nivel)))
            await ctx.send(f"🔊 Volume: {nivel}%")

    @commands.hybrid_command(name="shuffle", aliases=["misturar"], description="Embaralha a fila.")
    async def shuffle(self, ctx: commands.Context):
        """Embaralha a fila de reprodução."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc and vc.queue:
            random.shuffle(vc.queue)
            await ctx.send("🔀 Fila embaralhada!")

    @commands.hybrid_command(name="nowplaying", aliases=["np", "tocando"], description="O que está tocando?")
    async def nowplaying(self, ctx: commands.Context):
        """Mostra a música que está tocando agora."""
        vc: wavelink.Player = ctx.guild.voice_client
        if not vc or not vc.current:
            return await ctx.send("🔇 Nada tocando.")
        
        track = vc.current
        bar = self.yt_helper.create_progress_bar(vc.position, track.length)
        dur = self.yt_helper.parse_duration(track.length)
        
        embed = discord.Embed(title="Tocando Agora", description=f"[{track.title}]({track.uri})", color=discord.Color.blue())
        embed.add_field(name="Progresso", value=f"`{bar}` [{dur}]")
        embed.set_thumbnail(url=track.artwork or "")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="queue", aliases=["q", "fila"], description="Mostra a fila.")
    async def queue(self, ctx: commands.Context):
        """Mostra as próximas músicas na fila."""
        vc = ctx.guild.voice_client
        if not vc or not vc.queue: return await ctx.send("📭 Fila vazia.")
        
        embed = discord.Embed(title="Fila de Reprodução", color=discord.Color.blue())
        items = list(vc.queue)[:10]
        desc = "\n".join([f"`{i+1}.` {t.title}" for i, t in enumerate(items)])
        embed.description = desc
        if len(vc.queue) > 10: embed.set_footer(text=f"+ {len(vc.queue)-10} músicas")
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name="loop", description="Alterna loop (track/queue).")
    async def loop(self, ctx: commands.Context, modo: str = "track"):
        """Define o modo de loop: 'track' para música, 'queue' para fila, ou 'off' para desligar."""
        vc = ctx.guild.voice_client
        if not vc: return
        
        if modo in ["queue", "fila", "all"]:
            vc.queue.mode = wavelink.QueueMode.loop
            msg = "🔁 Loop: **Fila**"
        elif modo in ["track", "musica", "single"]:
            vc.queue.mode = wavelink.QueueMode.track
            msg = "🔂 Loop: **Música**"
        else:
            vc.queue.mode = wavelink.QueueMode.normal
            msg = "➡️ Loop: **Desligado**"
        await ctx.send(msg)

    # --- Comandos Administrativos de Auth ---
    @commands.command(name="auth_yt", hidden=True)
    @commands.is_owner()
    async def auth_yt(self, ctx):
        """Comando manual para gerar token do dono se expirou."""
        if self.yt_helper.auth_new_user(ctx.author.id):
            await ctx.send("✅ Autenticação iniciada no console/browser do servidor.")
        else:
            await ctx.send("❌ client_secret.json não encontrado.")
    # essas coisas de autenticação são raramente necessárias... talvez no proximo update eu mexa mais nisso

async def setup(bot):
    await bot.add_cog(Music(bot))