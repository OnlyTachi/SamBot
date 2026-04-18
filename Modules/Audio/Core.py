import discord
from discord.ext import commands
import wavelink
import os
import logging


class AudioCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🔌"
        self.logger = logging.getLogger("SamBot.AudioCore")
        self.owner_id = int(os.getenv("OWNER_ID", 0))
        self.bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        await self.bot.wait_until_ready()
        uri = os.getenv("WAVE_URI", "http://lavalink:2333")
        password = os.getenv("WAVE_PASSWORD", "youshallnotpass")

        nodes = [wavelink.Node(uri=uri, password=password)]
        try:
            # Ativamos o suporte a "resuming" para tentar recuperar sessões caídas
            await wavelink.Pool.connect(
                nodes=nodes, client=self.bot, cache_capacity=100
            )
            self.logger.info("Lavalink conectado com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao conectar ao Lavalink: {e}")
            await self._notify_owner(
                f"🚨 **Erro Crítico:** Falha ao conectar ao Lavalink na inicialização.\nErro: `{e}`"
            )

    async def _notify_owner(self, message: str):
        """Envia uma DM para o dono do bot configurado no .env."""
        if self.owner_id == 0:
            return

        try:
            owner = self.bot.get_user(self.owner_id) or await self.bot.fetch_user(
                self.owner_id
            )
            if owner:
                await owner.send(message)
        except Exception as e:
            self.logger.error(f"Não foi possível enviar DM ao dono: {e}")

    # --- Eventos de Monitoramento ---

    @commands.Cog.listener()
    async def on_wavelink_node_closed(self, node: wavelink.Node, disconnected: bool):
        """Detecta quando a conexão com o servidor Lavalink cai."""
        status = "desconectado" if disconnected else "fechado"
        msg = f"⚠️ **Aviso de Áudio:** O nó do Lavalink (`{node.uri}`) foi **{status}** inesperadamente."
        self.logger.warning(msg)
        await self._notify_owner(msg)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(
        self, payload: wavelink.TrackExceptionEventPayload
    ):
        """Avisa se uma música específica falhar ao carregar (ex: vídeo privado)."""
        msg = f"❌ **Erro de Reprodução:** Falha ao tocar `{payload.track.title}`.\nMotivo: `{payload.exception}`"
        await self._notify_owner(msg)

    # --- Eventos de Fluxo ---

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return
        if player.queue.mode == wavelink.QueueMode.loop:
            await player.play(payload.track)
            return
        if not player.queue.is_empty:
            await player.play(player.queue.get())
            await player.set_pause(False)
        else:
            self.bot.dispatch("wavelink_queue_end", player)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        self.bot.is_music_playing = True
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=f"{payload.track.title[:120]}"
            )
        )

    @commands.Cog.listener()
    async def on_wavelink_queue_end(self, player: wavelink.Player):
        self.bot.is_music_playing = False
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="suas ordens..."
            ),
        )


async def setup(bot):
    await bot.add_cog(AudioCore(bot))
