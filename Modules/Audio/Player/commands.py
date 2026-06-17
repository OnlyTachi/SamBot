import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import logging
import datetime

# Funções externas
from ._core import setup_wavelink
from ._search_manager import search_manager

logger = logging.getLogger("SamBot.PlayerCommands")


def create_progress_bar(current: int, total: int, length: int = 15) -> str:
    """Gera uma barra de progresso visual em texto."""
    if total <= 0:
        return "🔘" + "▬" * (length - 1)

    percent = current / total
    filled = int(length * percent)
    filled = max(0, min(filled, length))

    bar = "▬" * filled + "🔘" + "▬" * (length - filled)
    return bar


def parse_duration(ms: int) -> str:
    """Converte milissegundos para o formato HH:MM:SS."""
    seconds = ms // 1000
    return str(datetime.timedelta(seconds=seconds))


# --- View Interativa dos Botões ---
class PlayerControlView(discord.ui.View):
    """View interativa com botões para o Player de Música."""

    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            not interaction.user.voice
            or interaction.user.voice.channel != self.player.channel
        ):
            await interaction.response.send_message(
                "❌ Você precisa estar no meu canal de voz para usar os botões.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="btn_play_pause"
    )
    async def btn_play_pause(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.player.paused:
            await self.player.pause(False)
            await interaction.response.send_message(
                "▶️ Música retomada.", ephemeral=True
            )
        elif self.player.playing:
            await self.player.pause(True)
            await interaction.response.send_message(
                "⏸️ Música pausada.", ephemeral=True
            )

    @discord.ui.button(
        emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="btn_skip"
    )
    async def btn_skip(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.player.playing:
            await self.player.skip(force=True)
            await interaction.response.send_message(
                "⏭️ Pulando para a próxima música...", ephemeral=True
            )
        else:
            await interaction.response.defer()

    @discord.ui.button(
        emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="btn_loop"
    )
    async def btn_loop(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.player.queue.mode == wavelink.QueueMode.normal:
            self.player.queue.mode = wavelink.QueueMode.loop
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                "🔂 Modo de repetição: **Música Atual**.", ephemeral=True
            )
        elif self.player.queue.mode == wavelink.QueueMode.loop:
            self.player.queue.mode = wavelink.QueueMode.loop_all
            button.style = discord.ButtonStyle.primary
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                "🔁 Modo de repetição: **Toda a Fila**.", ephemeral=True
            )
        else:
            self.player.queue.mode = wavelink.QueueMode.normal
            button.style = discord.ButtonStyle.secondary
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                "➡️ Modo de repetição: **Desativado**.", ephemeral=True
            )

    @discord.ui.button(
        emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="btn_stop"
    )
    async def btn_stop(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.player.queue.clear()
        await self.player.disconnect()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            "⏹️ Player parado e desconectado.", ephemeral=True
        )


# --- Cog de Comandos Híbridos do Player ---
class PlayerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🎵"

    @commands.Cog.listener()
    async def on_ready(self):
        await setup_wavelink(self.bot)
        await search_manager.test_navidrome_connection()

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(
            f"✅ Lavalink Node conectado com sucesso: {payload.node.identifier}"
        )

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player: wavelink.Player = payload.player
        if not player:
            return
        if player.queue.is_empty and player.queue.mode == wavelink.QueueMode.normal:
            await self.bot.change_presence(status=discord.Status.online)
            if hasattr(player, "now_playing_message") and player.now_playing_message:
                try:
                    view = discord.ui.View.from_message(player.now_playing_message)
                    for child in view.children:
                        child.disabled = True
                    await player.now_playing_message.edit(view=view)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        if not player:
            return
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=payload.track.title[:120]
            )
        )
        if hasattr(player, "now_playing_message") and player.now_playing_message:
            try:
                await player.now_playing_message.delete()
            except Exception:
                pass
        if hasattr(player, "reply_channel") and player.reply_channel:
            embed = discord.Embed(
                title="🎶 Tocando Agora",
                description=f"**[{payload.track.title}]({payload.track.uri})**",
                color=discord.Color.brand_green(),
            )
            embed.set_thumbnail(url=payload.track.artwork)
            if payload.track.author:
                embed.set_footer(text=f"Autor: {payload.track.author}")
            view = PlayerControlView(player)
            message = await player.reply_channel.send(embed=embed, view=view)
            player.now_playing_message = message

    @commands.hybrid_command(
        name="play", aliases=["p", "tocar"], description="Pesquisa e toca música."
    )
    @app_commands.describe(busca="Nome da música ou link (YouTube/Spotify/SoundCloud).")
    async def play(self, ctx: commands.Context, *, busca: str):
        if not ctx.author.voice:
            return await ctx.send(
                "❌ Você precisa estar em um canal de voz.", ephemeral=True
            )

        player: wavelink.Player = ctx.voice_client
        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                return await ctx.send(f"❌ Erro ao conectar no canal: {e}")

        player.reply_channel = ctx.channel
        await ctx.defer()

        try:
            tracks, origem = await search_manager.intelligent_search(busca)

            if not tracks:
                if origem == "LOCAL_NOT_FOUND":
                    return await ctx.send(
                        "❌ O bot está configurado em modo `LOCAL` e esta música não existe no Navidrome. Caso tenha errado na configuração, tente mudar o modo para `ONLINE` ou `HIBRIDO` no arquivo .env."
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
                    description=f"✅ Carregados **{added}** músicas da playlist **{tracks.name}** na fila.",
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)
            else:
                track = tracks[0]

                txt_origem = (
                    "🗄️ Biblioteca Local" if origem == "LOCAL" else "🌐 Internet"
                )

                if player.playing:
                    player.queue.put(track)
                    embed = discord.Embed(
                        description=f"📝 **[{track.title}]({track.uri})** adicionada à fila (Posição: {player.queue.count}).",
                        color=discord.Color.orange(),
                    )
                    embed.set_footer(text=f"Fonte: {txt_origem}")
                    await ctx.send(embed=embed)
                else:
                    await player.play(track)
                    await ctx.send(
                        f"🔍 Carregando sua música vinda do {txt_origem}...",
                        delete_after=3,
                    )

        except Exception as e:
            logger.error(f"Erro no comando play: {e}")
            await ctx.send(f"❌ Erro inesperado ao buscar a música. Verifique os logs.")

    @commands.hybrid_command(
        name="skip", aliases=["pular", "s"], description="Pula a música atual."
    )
    async def skip(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.send(
                "❌ Não há nenhuma música tocando no momento.", ephemeral=True
            )

        await player.skip(force=True)
        await ctx.send("⏭️ Música pulada com sucesso!")

    @commands.hybrid_command(
        name="pause", aliases=["pausar"], description="Pausa a música atual."
    )
    async def pause(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.send(
                "❌ Não estou tocando nada no momento.", ephemeral=True
            )
        if player.paused:
            return await ctx.send("⏸️ O player já está pausado.", ephemeral=True)

        await player.pause(True)
        await ctx.send("⏸️ Música pausada. Use `/resume` para voltar.")

    @commands.hybrid_command(
        name="resume", aliases=["retomar"], description="Retoma a música pausada."
    )
    async def resume(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send("❌ Não estou em um canal de voz.", ephemeral=True)
        if not player.paused:
            return await ctx.send("▶️ A música já está tocando.", ephemeral=True)

        await player.pause(False)
        await ctx.send("▶️ Música retomada!")

    @commands.hybrid_command(
        name="stop",
        aliases=["parar", "leave"],
        description="Para o player e limpa a fila.",
    )
    async def stop(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.send(
                "❌ Não estou conectado a nenhum canal de voz.", ephemeral=True
            )

        player.queue.clear()
        await player.disconnect()
        await ctx.send("⏹️ Fila limpa e bot desconectado com sucesso.")

    @commands.hybrid_command(
        name="nowplaying",
        aliases=["np", "atual"],
        description="Mostra detalhes da música atual.",
    )
    async def nowplaying(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.send(
                "❌ Não estou tocando nada no momento.", ephemeral=True
            )

        track = player.current
        posicao = player.position
        duracao = track.length

        barra = create_progress_bar(posicao, duracao, length=18)
        tempo_atual = parse_duration(posicao)
        tempo_total = parse_duration(duracao)

        embed = discord.Embed(
            title="🎵 Tocando Agora",
            description=f"**[{track.title}]({track.uri})**\n\n`{tempo_atual}` {barra} `{tempo_total}`",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=track.artwork)
        if track.author:
            embed.add_field(name="👤 Autor", value=track.author, inline=True)
        if player.queue.count > 0:
            embed.add_field(
                name="📋 Fila",
                value=f"`{player.queue.count}` músicas restantes",
                inline=True,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="volume", aliases=["vol"], description="Ajusta o volume do bot."
    )
    @app_commands.describe(nivel="Nível do volume de 0 a 100.")
    async def volume(self, ctx: commands.Context, nivel: int):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.send(
                "❌ O bot precisa estar tocando algo para ajustar o volume.",
                ephemeral=True,
            )

        nivel = max(0, min(100, nivel))
        await player.set_volume(nivel)
        await ctx.send(f"🔊 Volume ajustado para **{nivel}%**!")

    @app_commands.command(
        name="filtro",
        description="Aplica equalizações e filtros de áudio avançados na reprodução atual.",
    )
    @app_commands.choices(
        efeito=[
            app_commands.Choice(name="Desativar Filtros", value="clear"),
            app_commands.Choice(
                name="Nightcore (Áudio Rápido e Agudo)", value="nightcore"
            ),
            app_commands.Choice(
                name="Vaporwave (Áudio Lento e Grave)", value="vaporwave"
            ),
            app_commands.Choice(name="Bassboost (Graves Fortes)", value="bassboost"),
        ]
    )
    async def filtro(self, interaction: discord.Interaction, efeito: str):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message(
                "❌ O bot precisa estar reproduzining uma música para alterar os filtros.",
                ephemeral=True,
            )

        await interaction.response.defer()
        filters: wavelink.Filters = player.filters

        if efeito == "clear":
            filters.reset()
            await interaction.followup.send(
                "🎵 Todos os efeitos foram limpos. Áudio original restaurado!"
            )
        elif efeito == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1.0)
            await interaction.followup.send(
                "⚡ Filtro **Nightcore** aplicado com sucesso!"
            )
        elif efeito == "vaporwave":
            filters.timescale.set(pitch=0.8, speed=0.8, rate=1.0)
            await interaction.followup.send(
                "🔮 Filtro **Vaporwave** aplicado com sucesso!"
            )
        elif efeito == "bassboost":
            filters.equalizer.set(
                bands=[
                    wavelink.FilterBand(band=0, gain=0.30),
                    wavelink.FilterBand(band=1, gain=0.20),
                    wavelink.FilterBand(band=2, gain=0.10),
                ]
            )
            await interaction.followup.send(
                "🔊 Filtro **Bassboost** ativado! Graves reforçados."
            )

        await player.set_filters(filters)

    @app_commands.command(
        name="seek",
        description="Avança ou retrocede para um tempo específico da música atual.",
    )
    @app_commands.describe(
        segundos="Insira o tempo exato em segundos para onde quer pular (Ex: 90 para 1min30s)"
    )
    async def seek(self, interaction: discord.Interaction, segundos: int):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message(
                "❌ Não há nenhuma música tocando no momento.", ephemeral=True
            )

        posicao_ms = segundos * 1000
        if posicao_ms < 0 or posicao_ms > player.current.length:
            return await interaction.response.send_message(
                "❌ Tempo inválido! O valor excede a duração total da música.",
                ephemeral=True,
            )

        await player.seek(posicao_ms)
        await interaction.response.send_message(
            f"⏩ Posição da música alterada com sucesso para **{segundos} segundos**!"
        )

    @app_commands.command(
        name="remove",
        description="Remove uma música específica da fila com base em sua numeração.",
    )
    @app_commands.describe(numero="O número da música na fila (veja usando /queue)")
    async def remove(self, interaction: discord.Interaction, numero: int):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or player.queue.is_empty:
            return await interaction.response.send_message(
                "❌ A fila atual de reprodução está vazia.", ephemeral=True
            )

        index = (
            numero - 1
        )  # Ajusta a numeração humana (1,2,3) para índice interno (0,1,2)
        if index < 0 or index >= player.queue.count:
            return await interaction.response.send_message(
                f"❌ Posição inválida! Escolha um número entre 1 e {player.queue.count}.",
                ephemeral=True,
            )

        track = player.queue[index]
        del player.queue[index]
        await interaction.response.send_message(
            f"🗑️ A música **{track.title}** foi removida da fila."
        )

    @app_commands.command(
        name="skipto",
        description="Pula direto para uma música específica da fila, descartando as anteriores.",
    )
    @app_commands.describe(posicao="O número da música para a qual deseja saltar")
    async def skipto(self, interaction: discord.Interaction, posicao: int):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or player.queue.is_empty:
            return await interaction.response.send_message(
                "❌ A fila atual está vazia.", ephemeral=True
            )

        index = posicao - 1
        if index < 0 or index >= player.queue.count:
            return await interaction.response.send_message(
                f"❌ Posição inválida! Escolha uma música válida de 1 a {player.queue.count}.",
                ephemeral=True,
            )

        for _ in range(index):
            player.queue.delete(0)

        proxima_track = player.queue.get()
        await player.play(proxima_track)
        await interaction.response.send_message(
            f"⏭️ Fila adiantada! Pulando diretamente para: **{proxima_track.title}**."
        )


async def setup(bot):
    await bot.add_cog(PlayerCommands(bot))
