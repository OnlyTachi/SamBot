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

class PlaylistSetupView(discord.ui.View):
    """View para perguntar configurações ao carregar uma playlist."""
    def __init__(self, ctx, player):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.player = player
        self.loop = False
        self.shuffle = False
        self.step = "loop" # loop ou shuffle

    async def update_message(self, interaction: discord.Interaction, text: str):
        if self.step == "done":
            await interaction.response.edit_message(content=text, view=None)
            self.stop()
        else:
            await interaction.response.edit_message(content=text, view=self)

    @discord.ui.button(label="Sim", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.step == "loop":
            self.player.queue.mode = wavelink.QueueMode.loop
            self.step = "shuffle"
            await self.update_message(interaction, "🔁 **Loop da Fila** ativado! Deseja **embaralhar** as músicas agora?")
        elif self.step == "shuffle":
            random.shuffle(self.player.queue)
            self.step = "done"
            await self.update_message(interaction, "🔀 Fila **embaralhada** com sucesso! Aproveite a música.")

    @discord.ui.button(label="Não", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.step == "loop":
            self.step = "shuffle"
            await self.update_message(interaction, "➡️ Loop ignorado. Deseja **embaralhar** as músicas da playlist?")
        elif self.step == "shuffle":
            self.step = "done"
            await self.update_message(interaction, "✅ Configurações finalizadas. Playlist carregada normalmente.")

class Music(commands.Cog):
    def __init__(self, bot):
        """Módulo de música com auto-recuperação, retries e suporte a playlists extensas."""
        self.bot = bot
        self.playlist_manager = PlaylistManager()
        self.yt_helper = YoutubeHelper()
        self.bot.loop.create_task(self.connect_nodes())
        self.emoji = "🎵"

    async def connect_nodes(self):
        """Estabelece conexão com o servidor Lavalink utilizando as variáveis de ambiente."""
        await self.bot.wait_until_ready()
        
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
        """Gerencia a transição de faixas e os modos de repetição."""
        player = payload.player
        if not player: return

        if player.queue.mode == wavelink.QueueMode.loop:
            await player.play(payload.track)
            return

        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
            await player.set_pause(False) 
        else:
            self.bot.dispatch("wavelink_queue_end", player)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """Atualiza a atividade do bot com a faixa atual."""
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
    async def on_wavelink_queue_end(self, player: wavelink.Player):
        """Restaura o estado do bot quando a fila termina."""
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
        """Relata faixas que não puderam ser carregadas."""
        if not error_tracks: return
        embed = discord.Embed(
            title="⚠️ Músicas Ignoradas",
            description="As seguintes faixas falharam após 2 tentativas de carregamento:",
            color=discord.Color.red()
        )
        lista_formatada = "\n".join([f"• {str(t)[:60]}" for t in error_tracks[:10]])
        if len(error_tracks) > 10:
            lista_formatada += f"\n*... e mais {len(error_tracks) - 10} músicas.*"
        embed.add_field(name="Problemas detectados:", value=lista_formatada or "Erro desconhecido")
        await ctx.send(embed=embed)

    # --- Comandos Musicais ---

    @commands.hybrid_command(
        name="play", 
        aliases=["p", "tocar"], 
        description="Pesquisa e toca música ou playlists (YouTube, Spotify, SoundCloud)."
    )
    @app_commands.describe(busca="Nome da música ou link da playlist/vídeo.")
    async def play(self, ctx: commands.Context, *, busca: str):
        """Toca música com sistema de retry e configuração automática de playlists."""
        if not ctx.author.voice:
            return await ctx.send("❌ Você precisa estar em um canal de voz.", ephemeral=True)

        if not ctx.guild.voice_client:
            try:
                vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                return await ctx.send(f"❌ Erro ao conectar ao canal: {e}")
        else:
            vc: wavelink.Player = ctx.guild.voice_client

        await ctx.defer()
        error_tracks = []
        added_count = 0
        is_playlist = False
        
        playlist_id = self.yt_helper.extract_playlist_id(busca)
        if playlist_id:
            is_playlist = True
            await ctx.send("⏳ Processando playlist grande... Aguarde um instante.")
            urls = self.yt_helper.get_playlist_items(playlist_id, max_items=100)
            if urls:
                for url in urls:
                    success = False
                    for attempt in range(1, 3):
                        try:
                            res = await wavelink.Playable.search(url)
                            if res:
                                await vc.queue.put_wait(res[0])
                                added_count += 1
                                success = True
                                break 
                        except:
                            if attempt < 2: await asyncio.sleep(1) 
                    if not success: error_tracks.append(url)
                
                await ctx.send(f"✅ Playlist carregada: **{added_count}** músicas adicionadas.")
                if not vc.playing: await vc.play(vc.queue.get())
                
                view = PlaylistSetupView(ctx, vc)
                await ctx.send("⚙️ **Configuração de Playlist:** Deseja ativar o **Loop da Fila**?", view=view)
                
                if error_tracks: await self._send_error_report(ctx, error_tracks)
                return

        try:
            if "https://" not in busca:
                results = await self.yt_helper.search(busca)
                if not results: return await ctx.send("❌ Não encontrei nenhum resultado para essa busca.")
                busca = results[0]['url']

            tracks = await wavelink.Playable.search(busca)
            if not tracks: return await ctx.send("❌ Erro ao carregar a música ou link inválido.")

            # Playlist nativa do Wavelink
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
                            if attempt < 2: await asyncio.sleep(1)
                    if not success: error_tracks.append(t.title)
                
                await ctx.send(f"✅ Playlist **{tracks.name}** adicionada à fila.")
                view = PlaylistSetupView(ctx, vc)
                await ctx.send("⚙️ **Configuração de Playlist:** Deseja ativar o **Loop da Fila**?", view=view)
                
                if error_tracks: await self._send_error_report(ctx, error_tracks)
            
            # Música única
            else:
                track = tracks[0]
                success = False
                for attempt in range(1, 3):
                    try:
                        await vc.queue.put_wait(track)
                        success = True
                        break
                    except:
                        if attempt < 2: await asyncio.sleep(1)
                
                if success:
                    embed = discord.Embed(description=f"🎵 **{track.title}** adicionado à fila.", color=discord.Color.green())
                    if hasattr(track, 'artwork'): embed.set_thumbnail(url=track.artwork)
                    await ctx.send(embed=embed)
                else:
                    return await ctx.send(f"❌ Falha ao carregar a música após 2 tentativas.")

            if not vc.playing and not vc.queue.is_empty:
                await vc.play(vc.queue.get())
        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro: {e}")

    @commands.hybrid_command(
        name="stop", 
        aliases=["leave", "sair", "parar"], 
        description="Para a música, limpa a fila e sai do canal de voz."
    )
    async def stop(self, ctx: commands.Context):
        """Para a reprodução atual, limpa a fila de músicas e desconecta o bot do canal de voz."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            await vc.disconnect()
            await ctx.send("👋 Reprodução finalizada. Até mais!")

    @commands.hybrid_command(
        name="skip", 
        aliases=["s", "pular", "proxima"], 
        description="Pula a música atual."
    )
    async def skip(self, ctx: commands.Context):
        """Pula a faixa que está tocando no momento e inicia a próxima música da fila."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc and vc.playing:
            await vc.skip(force=True)
            await ctx.send("⏭️ Música pulada.")

    @commands.hybrid_command(
        name="pause", 
        aliases=["resume", "pausar", "retomar"], 
        description="Pausa ou retoma a música."
    )
    async def pause(self, ctx: commands.Context):
        """Alterna o estado de reprodução do player entre pausado e em execução."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            await vc.pause(not vc.paused)
            estado = 'Pausado' if vc.paused else 'Retomado'
            await ctx.send(f"⏯️ O player foi **{estado}**.")

    @commands.hybrid_command(
        name="volume", 
        aliases=["vol"], 
        description="Ajusta o volume (0-100)."
    )
    @app_commands.describe(nivel="Nível de volume de 0 a 100.")
    async def volume(self, ctx: commands.Context, nivel: int):
        """Define o volume de saída do áudio para um valor específico entre 0 e 100."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc:
            nivel = max(0, min(100, nivel))
            await vc.set_volume(nivel)
            await ctx.send(f"🔊 Volume ajustado para **{nivel}%**.")

    @commands.hybrid_command(
        name="shuffle", 
        aliases=["misturar", "embaralhar", "random", "sh"], 
        description="Embaralha a ordem das músicas na fila."
    )
    async def shuffle(self, ctx: commands.Context):
        """Reorganiza aleatoriamente todas as músicas que estão aguardando na fila de reprodução."""
        vc: wavelink.Player = ctx.guild.voice_client
        if vc and not vc.queue.is_empty:
            random.shuffle(vc.queue)
            await ctx.send("🔀 A fila foi embaralhada!")

    @commands.hybrid_command(
        name="loop", 
        description="Configura a repetição da música ou da fila."
    )
    @app_commands.describe(modo="Modos: track (música), queue (fila) ou off (desligar).")
    async def loop(self, ctx: commands.Context, modo: str = "track"):
        """Altera o comportamento de repetição do bot para uma única música, a fila inteira ou desligado."""
        vc: wavelink.Player = ctx.guild.voice_client
        if not vc: return
        
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

    @commands.hybrid_command(
        name="nowplaying", 
        aliases=["np", "tocando"], 
        description="Mostra detalhes da música que está tocando agora."
    )
    async def nowplaying(self, ctx: commands.Context):
        """Exibe um resumo detalhado da faixa atual, incluindo título, duração e barra de progresso."""
        vc: wavelink.Player = ctx.guild.voice_client
        if not vc or not vc.current:
            return await ctx.send("🔇 Não há nada tocando no momento.")
        
        track = vc.current
        bar = self.yt_helper.create_progress_bar(vc.position, track.length)
        dur = self.yt_helper.parse_duration(track.length)
        
        embed = discord.Embed(title="Tocando Agora", description=f"[{track.title}]({track.uri})", color=discord.Color.blue())
        embed.add_field(name="Progresso", value=f"`{bar}` [{dur}]")
        if track.artwork: embed.set_thumbnail(url=track.artwork)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="queue", 
        aliases=["fila", "q"], 
        description="Exibe as próximas músicas e estatísticas da fila."
    )
    async def queue(self, ctx: commands.Context):
        """Exibe a lista das próximas 10 músicas na fila, o tempo total estimado e o modo de repetição atual."""
        vc: wavelink.Player = ctx.guild.voice_client
        
        if not vc or (not vc.current and vc.queue.is_empty):
            return await ctx.send("📭 A fila está vazia.")

        embed = discord.Embed(title="📋 Fila de Reprodução", color=0x2b2d31)
        
        if vc.current:
            current = vc.current
            loop_status = "🔂 Música" if vc.queue.mode == wavelink.QueueMode.track else ("🔁 Fila" if vc.queue.mode == wavelink.QueueMode.loop else "➡️ Normal")
            embed.add_field(
                name="🎧 Tocando Agora", 
                value=f"**[{current.title}]({current.uri})**\n*Duração: {self.yt_helper.parse_duration(current.length)}*", 
                inline=False
            )
            if current.artwork:
                embed.set_thumbnail(url=current.artwork)

        if not vc.queue.is_empty:
            upcoming = list(vc.queue)[:10] 
            queue_list = ""
            for i, track in enumerate(upcoming):
                dur = self.yt_helper.parse_duration(track.length)
                queue_list += f"`{i+1}.` {track.title[:50]}... **[{dur}]**\n"
            
            embed.add_field(name="📜 Próximas na Fila", value=queue_list, inline=False)
            
            total_ms = sum(t.length for t in vc.queue)
            total_time = self.yt_helper.parse_duration(total_ms)
            
            footer_text = f"Músicas: {len(vc.queue)} | Tempo total: {total_time} | Loop: {loop_status}"
            embed.set_footer(text=footer_text)
        else:
            embed.add_field(name="📜 Próximas na Fila", value="*Nenhuma música na sequência.*", inline=False)
            embed.set_footer(text=f"Loop: {loop_status}")

        await ctx.send(embed=embed)

    @commands.command(name="auth_yt", hidden=True)
    @commands.is_owner()
    async def auth_yt(self, ctx):
        """Comando administrativo para autenticação do YouTube."""
        if self.yt_helper.auth_new_user(ctx.author.id):
            await ctx.send("✅ Autenticação iniciada com sucesso.")
        else:
            await ctx.send("❌ Arquivo client_secret.json não encontrado.")
# isso ainda e experimental..
async def setup(bot):
    await bot.add_cog(Music(bot))