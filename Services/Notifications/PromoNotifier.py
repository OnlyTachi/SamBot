import asyncio
import logging
import discord
from typing import Optional, Dict, Any, List
from Brain.Memory.DataManager.Connections import data_manager
from Services.Notifications.WebhookDispatcher import WebhookDispatcher

logger = logging.getLogger("SamBot.PromoNotifier")


class PromoNotifier:
    """
    Serviço autônomo responsável pelo processamento de fila e envio de
    notificações de promoções tanto para servidores (canais de promo)
    quanto para DMs de membros e Webhooks externos.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.queue: asyncio.Queue = asyncio.Queue()
        self.dispatcher = WebhookDispatcher()
        self.is_running: bool = False
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Inicializa a task em segundo plano para consumir a fila de notificações."""
        if self.is_running:
            return
        self.is_running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        self.logger.info("  PromoNotifier inicializado e ouvindo fila.")

    async def stop(self):
        """Encerra a rotina em segundo plano de forma graciosa."""
        if not self.is_running:
            return
        self.is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self.logger.info("  PromoNotifier finalizado com sucesso.")

    async def notificar_promo(
        self,
        titulo: str,
        preco: float,
        loja: str,
        link: str,
        imagem_url: Optional[str] = None,
        target_type: str = "server",  # 'server', 'dm' ou 'all'
        target_id: Optional[str] = None,
        guild_id: Optional[str] = None,
    ):
        """Adiciona uma nova notificação de promoção na fila de processamento."""
        payload = {
            "titulo": titulo,
            "preco": preco,
            "loja": loja,
            "link": link,
            "imagem_url": imagem_url,
            "target_type": target_type,
            "target_id": target_id,
            "guild_id": guild_id,
        }
        await self.queue.put(payload)

    def _criar_embed(self, promo: Dict[str, Any]) -> discord.Embed:
        """Monta o Embed padrão do Discord para promoções."""
        embed = discord.Embed(
            title=f"🔥 Oferta: {promo['titulo']}",
            url=promo["link"],
            color=discord.Color.from_rgb(255, 87, 34),
        )
        embed.add_field(
            name="🏷️ Preço", value=f"**R$ {promo['preco']:.2f}**", inline=True
        )
        embed.add_field(name="🏬 Loja", value=promo["loja"], inline=True)
        embed.add_field(
            name="🔗 Link", value=f"[Acessar Promoção]({promo['link']})", inline=False
        )

        if promo.get("imagem_url"):
            embed.set_image(url=promo["imagem_url"])

        embed.set_footer(text="SamBot Promo Tracker • Alerta Automático")
        return embed

    async def _enviar_para_canal(self, channel_id: int, embed: discord.Embed) -> bool:
        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(
                channel_id
            )
            if channel:
                await channel.send(embed=embed)
                return True
        except Exception as e:
            self.logger.error(f"Erro ao enviar promoção para canal {channel_id}: {e}")
        return False

    async def _enviar_para_dm(self, user_id: int, embed: discord.Embed) -> bool:
        try:
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            if user:
                await user.send(embed=embed)
                return True
        except discord.Forbidden:
            self.logger.warning(f"DM bloqueada para o usuário {user_id}.")
        except Exception as e:
            self.logger.error(
                f"Erro ao enviar promoção na DM do usuário {user_id}: {e}"
            )
        return False

    async def _process_queue(self):
        """Loop contínuo que processa a fila de disparos."""
        while self.is_running:
            try:
                promo = await self.queue.get()
                embed = self._criar_embed(promo)
                target_type = promo.get("target_type")
                target_id = promo.get("target_id")
                guild_id = promo.get("guild_id")

                # 1. Envio específico para Servidor (Canal)
                if target_type == "server" and target_id:
                    await self._enviar_para_canal(int(target_id), embed)

                # 2. Envio específico para Membro (DM)
                elif target_type == "dm" and target_id:
                    await self._enviar_para_dm(int(target_id), embed)

                # 3. Disparo Global ou Dinâmico (Lê os canais configurados na memória)
                elif target_type == "all":
                    config_canais = data_manager.load_active_channels() or {}
                    for ch_id in config_canais.keys():
                        if str(ch_id).isdigit():
                            await self._enviar_para_canal(int(ch_id), embed)
                            await asyncio.sleep(0.5)

                # 4. Disparo em Webhooks cadastrados
                await self.dispatcher.disparar_evento(
                    evento="promo_alert", payload=promo, guild_id=guild_id
                )

                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Erro inesperado no loop do PromoNotifier: {e}", exc_info=True
                )
                await asyncio.sleep(1)
