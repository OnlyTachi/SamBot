# Modules/Audio/Player/controlCommand.py
import logging
import time
import discord
from discord.ext import commands
import wavelink

from ..Lavalink._maestro import maestro
from ..Lavalink._node_manager import setup_nodes
from ..Lavalink._search_manager import search_manager
from Brain.Memory.DataManager.Connections import data_manager

logger = logging.getLogger("SamBot.ControlCommands")


# --- View Interativa dos Botões ---
class PlayerControlView(discord.ui.View):
    """View interativa com botões de controle para o Player de Música."""

    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=None)
        self.player = player

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            not interaction.user.voice
            or interaction.user.voice.channel != self.player.channel
        ):
            await interaction.response.send_message(
                "❌ Você precisa estar no mesmo canal de voz para interagir com os botões.",
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
        else:
            await interaction.response.defer()

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
        queue_mode = getattr(self.player.queue, "mode", wavelink.QueueMode.normal)

        if queue_mode == wavelink.QueueMode.normal:
            self.player.queue.mode = wavelink.QueueMode.loop
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                "🔂 Modo de repetição: **Música Atual**.", ephemeral=True
            )
        elif queue_mode == wavelink.QueueMode.loop:
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


# --- Cog de Gerenciamento e Controle ---
class ControlCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._voice_sessions = {}

    # --- Listeners de Conexão e Nodes Lavalink ---
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await setup_nodes(self.bot)
        except Exception as e:
            logger.error(f"Erro isolado ao conectar os nós do Lavalink: {e}")

        try:
            await search_manager.test_navidrome_connection()
        except Exception as e:
            logger.warning(f"Não foi possível testar a conexão com o Navidrome: {e}")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"Lavalink Node conectado com sucesso: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_node_closed(self, node: wavelink.Node):
        logger.warning(
            f"Node {node.identifier} fechou a conexão e foi colocado em castigo."
        )
        search_manager.mark_node_offline(node.identifier)

    # --- Telemetria de Presença em Voz ---
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Rastreia com precisão de relógio o tempo real do usuário em call com a Sam."""
        if member.bot:
            return

        guild = member.guild
        vc = guild.voice_client
        bot_channel = vc.channel if vc and hasattr(vc, "channel") else None
        session_key = f"{guild.id}_{member.id}"
        now = time.time()

        # 1. Usuário entrou no canal onde o bot está
        if after.channel and bot_channel and after.channel.id == bot_channel.id:
            if session_key not in self._voice_sessions:
                self._voice_sessions[session_key] = now

        # 2. Usuário saiu do canal onde o bot está (ou trocou de sala)
        elif before.channel and bot_channel and before.channel.id == bot_channel.id:
            if session_key in self._voice_sessions:
                join_time = self._voice_sessions.pop(session_key)
                elapsed_minutes = int((now - join_time) / 60)
                if elapsed_minutes > 0:
                    data_manager.increment_contribution(
                        str(member.id), "userListenedMinutes", elapsed_minutes
                    )
                    logger.debug(
                        f"[CallTime] Computados {elapsed_minutes} min para {member.display_name}"
                    )

    # --- Ciclo de Vida de Áudio Wavelink ---
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        if not player or not player.guild:
            return

        track_title = getattr(payload.track, "title", "Música")
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=track_title[:120]
            )
        )

        if hasattr(player, "now_playing_message") and player.now_playing_message:
            try:
                await player.now_playing_message.delete()
            except Exception:
                pass

        if hasattr(player, "reply_channel") and player.reply_channel:
            embed = discord.Embed(
                title="🎵 Tocando Agora",
                description=f"**[{track_title}]({getattr(payload.track, 'uri', '')})**",
                color=discord.Color.brand_green(),
            )
            artwork = getattr(payload.track, "artwork", None)
            if artwork:
                embed.set_thumbnail(url=artwork)

            author = getattr(payload.track, "author", None)
            if author:
                embed.set_footer(text=f"Autor: {author}")

            view = PlayerControlView(player)
            message = await player.reply_channel.send(embed=embed, view=view)
            player.now_playing_message = message

        await maestro.sync_player_state(self.bot, player)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player: wavelink.Player = payload.player
        if not player:
            return

        reason = str(getattr(payload, "reason", "")).upper()
        if reason in ("REPLACED", "CLEANUP"):
            return

        if reason == "FINISHED":
            try:
                track = payload.track
                if track:
                    requester_id = getattr(track, "requester_id", None)
                    if (
                        not requester_id
                        and hasattr(track, "requester")
                        and isinstance(track.requester, dict)
                    ):
                        requester_id = track.requester.get("id")

                    if requester_id:
                        data_manager.increment_contribution(
                            str(requester_id), "communityPlaysCount", 1
                        )

                    if player.channel:
                        for member in player.channel.members:
                            if not member.bot and not member.voice.deaf:
                                data_manager.increment_contribution(
                                    str(member.id), "userListenedTracksCount", 1
                                )
            except Exception as e:
                logger.error(f"Erro ao computar estatísticas de áudio no banco: {e}")

        repeat_mode = maestro.get_repeat_mode(player)

        if repeat_mode == "TRACK" and reason == "FINISHED":
            if payload.track:
                await player.play(payload.track)
                await maestro.sync_player_state(self.bot, player)
                return

        if repeat_mode == "QUEUE":
            if payload.track:
                player.queue.put(payload.track)

        # Avanço da Fila
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
        else:
            await self.bot.change_presence(status=discord.Status.online)
            if hasattr(player, "now_playing_message") and player.now_playing_message:
                try:
                    view = discord.ui.View.from_message(player.now_playing_message)
                    for child in view.children:
                        child.disabled = True
                    await player.now_playing_message.edit(view=view)
                except Exception:
                    pass

        await maestro.sync_player_state(self.bot, player)

    # --- Comandos Híbridos de Controle ---
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
            return await ctx.send("⚠️ O player já está pausado.", ephemeral=True)
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
            return await ctx.send("⚠️ A música já está tocando.", ephemeral=True)
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


async def setup(bot):
    await bot.add_cog(ControlCommands(bot))
