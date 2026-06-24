import discord
from discord.ext import commands
import wavelink
import logging

from ..Lavalink._node_manager import setup_nodes
from ..Lavalink._search_manager import search_manager

logger = logging.getLogger("SamBot.ControlCommands")


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


# --- Cog de Gerenciamento e Controle ---
class ControlCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Listeners de Eventos Globais ---
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

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await setup_nodes(self.bot)
        except Exception as e:
            logger.error(f"🚨 Erro isolado ao conectar os nós do Lavalink: {e}")

        # Testa a conexão com o Navidrome opcionalmente
        try:
            await search_manager.test_navidrome_connection()
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível testar a conexão com o Navidrome: {e}")

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


async def setup(bot):
    await bot.add_cog(ControlCommands(bot))
