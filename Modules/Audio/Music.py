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
        """Módulo de música com sistema de auto-recuperação e retries."""
        self.bot = bot
        self.playlist_manager = PlaylistManager()
        self.yt_helper = YoutubeHelper()
        self.bot.loop.create_task(self.connect_nodes())
        self.emoji = "🎵"

    async def connect_nodes(self):
        """Conecta ao Lavalink (Docker/Local)."""
        await self.bot.wait_until_ready()
        
        # Pega as configs do .env
        uri = os.getenv("WAVE_URI", "http://lavalink:2333")
        password = os.getenv("WAVE_PASSWORD", "youshallnotpass")
        
        nodes = [wavelink.Node(uri=uri, password=password)]
        try:
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            self.bot.log.info("Lavalink conectado com sucesso.")
        except Exception as e:
            self.bot.log.error(f"Erro ao conectar ao Lavalink: {e}")

    # --- Eventos do Wavelink ---

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Evento disparado quando uma música termina. Gerencia a fila automaticamente."""
        player = payload.player
        if not player:
            return

        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
            await player.set_pause(False) 
        else:
            self.bot.dispatch("wavelink_queue_end", player)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """Atualiza a presença do bot quando uma música começa."""
        player = payload.player
        track = payload.track
        
        self.bot.is_music_playing = True
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, 
                name=f"{track.title[:120]}" 
            )
        )

    @commands.Cog.listener()
    async def on_wavelink_queue_end(self, player: wavelink.Player):
        """Limpa o status do bot quando a música para."""
        self.bot.is_music_playing = False
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.listening, 
                name="suas ordens..."
            )
        )
        if hasattr(self.bot, 'status_loop') and self.bot.status_loop.is_running():
            self.bot.status_loop.restart()

    # --- Helper Interno ---

    async def _send_error_report(self, ctx, error_tracks):
        """Envia um embed resumindo as músicas que falharam após os retries."""
        if not error_tracks:
            return

        embed = discord.Embed(
            title="⚠️ Músicas Ignoradas",
            description="As seguintes faixas falharam (deletadas, privadas ou erro de rede) após 2 tentativas:",
            color=discord.Color.red()
        )
        
        lista_formatada = "\n".join([f"• {str(t)[:60]}" for t in error_tracks[:10]])
        if len(error_tracks) > 10:
            lista_formatada += f"\n*... e mais {len(error_tracks) - 10} músicas.*"
            
        embed.add_field(name="Músicas com problema:", value=lista_formatada or "Erro desconhecido")
        await ctx.send(embed=embed)

    # --- Comandos Musicais ---

    @commands.hybrid_command(name="play", aliases=["p"], description="Toca música ou playlists do YouTube.")
    @app_commands.describe(busca="URL da música/playlist ou nome para busca")
    async def play(self, ctx: commands.Context, *, busca: str):
        """Toca música com sistema de retry e tratamento de links mortos."""
        if not ctx.author.voice:
            return await ctx.send("❌ Você precisa estar em um canal de voz.", ephemeral=True)

        if not ctx.guild.voice_client:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.guild.voice_client

        await ctx.defer()
        
        error_tracks = []
        added_count = 0
        
        playlist_id = self.yt_helper.extract_playlist_id(busca)
        
        if playlist_id:
            await ctx.send("⏳ Extraindo músicas da playlist... Isso pode levar um momento.")
            urls = self.yt_helper.get_playlist_items(playlist_id, max_items=100)
            
            if urls:
                for url in urls:
                    success = False
                    # TENTATIVAS (Retry System)
                    for attempt in range(1, 3):
                        try:
                            search_result = await wavelink.Playable.search(url)
                            if search_result:
                                track = search_result[0]
                                await vc.queue.put_wait(track)
                                added_count += 1
                                success = True
                                break 
                        except Exception:
                            if attempt < 2:
                                await asyncio.sleep(1) 
                    
                    if not success:
                        error_tracks.append(url)
                
                await ctx.send(f"✅ Adicionadas **{added_count}** músicas da playlist.")
                if not vc.playing:
                    await vc.play(vc.queue.get())
                
                if error_tracks:
                    await self._send_error_report(ctx, error_tracks)
                return

        try:
            if "https://" not in busca:
                results = await self.yt_helper.search(busca)
                if not results:
                    return await ctx.send("❌ Nenhum resultado encontrado.")
                busca = results[0]['url']

            tracks = await wavelink.Playable.search(busca)
            if not tracks:
                return await ctx.send("❌ Não foi possível carregar esta música.")

            # Se for uma Playlist Nativa do Wavelink
            if isinstance(tracks, wavelink.Playlist):
                for t in tracks:
                    success = False
                    for attempt in range(1, 3):
                        try:
                            await vc.queue.put_wait(t)
                            added_count += 1
                            success = True
                            break
                        except:
                            await asyncio.sleep(1)
                    if not success:
                        error_tracks.append(t.title)
                
                await ctx.send(f"✅ Playlist **{tracks.name}** adicionada.")
                if error_tracks:
                    await self._send_error_report(ctx, error_tracks)
            
            # Se for música única
            else:
                track = tracks[0]
                success = False
                for attempt in range(1, 3):
                    try:
                        await vc.queue.put_wait(track)
                        success = True
                        break
                    except:
                        await asyncio.sleep(1)
                
                if success:
                    embed = discord.Embed(description=f"🎵 **{track.title}** adicionado à fila.", color=discord.Color.green())
                    if hasattr(track, 'artwork'): embed.set_thumbnail(url=track.artwork)
                    await ctx.send(embed=embed)
                else:
                    return await ctx.send(f"❌ Falha crítica ao carregar **{track.title}**.")

            if not vc.playing and not vc.queue.is_empty:
                await vc.play(vc.queue.get())
                await vc.set_pause(False)

        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro: {e}")

    @commands.hybrid_command(name="stop", aliases=["leave", "sair"], description="Para a música e limpa a fila.")
    async def stop(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            await vc.disconnect()
            await ctx.send("👋 Música parada e desconectado.")

    @commands.hybrid_command(name="skip", aliases=["s", "pular"], description="Pula para a próxima música.")
    async def skip(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.guild.voice_client
        if vc and vc.playing:
            await vc.skip(force=True)
            await ctx.send("⏭️ Música pulada.")

    @commands.hybrid_command(name="pause", aliases=["resume"], description="Pausa ou retoma a música.")
    async def pause(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            await vc.pause(not vc.paused)
            status = "Pausado" if vc.paused else "Retomado"
            await ctx.send(f"⏯️ Player {status}.")

    @commands.hybrid_command(name="shuffle", description="Embaralha as músicas da fila.")
    async def shuffle(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.guild.voice_client
        if vc and not vc.queue.is_empty:
            random.shuffle(vc.queue)
            await ctx.send("🔀 Fila misturada!")

    @commands.hybrid_command(name="nowplaying", aliases=["np"], description="Mostra o que está tocando.")
    async def nowplaying(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.guild.voice_client
        if not vc or not vc.current:
            return await ctx.send("🔇 Nada tocando no momento.")
        
        track = vc.current
        bar = self.yt_helper.create_progress_bar(vc.position, track.length)
        
        embed = discord.Embed(title="Tocando Agora", description=f"[{track.title}]({track.uri})", color=discord.Color.blue())
        embed.add_field(name="Progresso", value=f"`{bar}`")
        if track.artwork: embed.set_thumbnail(url=track.artwork)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="queue", aliases=["fila"], description="Mostra a fila atual.")
    async def queue(self, ctx: commands.Context):
        vc: wavelink.Player = ctx.guild.voice_client
        if not vc or vc.queue.is_empty:
            return await ctx.send("📭 A fila está vazia.")
        
        items = list(vc.queue)[:10] # Mostra apenas os 10 primeiros
        desc = "\n".join([f"`{i+1}.` {t.title}" for i, t in enumerate(items)])
        
        embed = discord.Embed(title="Fila de Reprodução", description=desc, color=discord.Color.blue())
        if len(vc.queue) > 10:
            embed.set_footer(text=f"E mais {len(vc.queue) - 10} músicas...")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))