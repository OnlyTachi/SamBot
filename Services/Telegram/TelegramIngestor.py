import os
import logging
import asyncio
import discord
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from discord.ext import commands
from Core.ConfigLoader import AppConfig

from Brain.Memory.DataManager.Connections import data_manager


class TelegramScraper:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.TelegramScraper")

        # Controle de Ativação e Debug
        self.enabled = AppConfig.get("TELEGRAM_ENABLED", "true").lower() == "true"
        self.debug_mode = AppConfig.get("DEBUG_MODE", "false").lower() == "true"

        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")

        owner_env = AppConfig.get("OWNER_ID", "845016606571626498")
        self.owner_id = int(owner_env) if owner_env else None

        self.canais = []
        self.client = None

    def _carregar_canais_monitorados(self) -> list:
        """Carrega a união dos canais do .env com os cadastrados no banco de dados."""
        canais_set = set()

        canais_env = AppConfig.get("TELEGRAM_CHANNELS", "")
        if canais_env:
            for c in canais_env.split(","):
                c_clean = c.strip()
                if c_clean:
                    canais_set.add(c_clean)

        grupos_cadastrados = (
            data_manager.get_knowledge("monitored_telegram_channels") or {}
        )
        for gid, info in grupos_cadastrados.items():
            if info.get("active", True):
                if str(gid).lstrip("-").isdigit():
                    canais_set.add(int(gid))
                elif info.get("username"):
                    canais_set.add(info["username"])

        return list(canais_set)

    async def _deletar_mensagem_apos(self, msg: discord.Message, delay: int = 20):
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except (discord.HTTPException, discord.NotFound):
            pass

    async def _autenticar_via_discord(self) -> bool:
        if not self.owner_id:
            self.logger.error("❌ OWNER_ID não configurado para autenticação via DM.")
            return False

        try:
            owner = await self.bot.fetch_user(self.owner_id)
            if not owner:
                self.logger.error(
                    f"❌ Não foi possível encontrar o usuário {self.owner_id} no Discord."
                )
                return False
        except Exception as e:
            self.logger.error(f"❌ Erro ao buscar Owner no Discord: {e}")
            return False

        mensagens_bot = []

        def check_dm(m: discord.Message):
            return m.author.id == self.owner_id and isinstance(
                m.channel, discord.DMChannel
            )

        async def enviar_dm(texto: str, temporaria: bool = True):
            msg = await owner.send(texto)
            if temporaria:
                mensagens_bot.append(msg)
            return msg

        await enviar_dm(
            "📲 Olá! A sessão do Telegram não está autorizada.\n"
            "Por favor, responda aqui com o seu **número de telefone** no formato internacional (Ex: `+5521999999999`):",
            temporaria=True,
        )

        try:
            msg_tel = await self.bot.wait_for("message", check=check_dm, timeout=300)
            telefone = msg_tel.content.strip()
        except asyncio.TimeoutError:
            await enviar_dm(
                "⏳ Tempo esgotado para o envio do telefone. Autenticação cancelada."
            )
            return False

        try:
            sent_code = await self.client.send_code_request(telefone)
            phone_code_hash = sent_code.phone_code_hash
        except Exception as e:
            await enviar_dm(f"❌ Erro ao solicitar código para `{telefone}`: {e}")
            return False

        await enviar_dm(
            "📩 **Código enviado pelo Telegram!**\n"
            "Por favor, digite aqui o código de verificação que você acabou de receber no app:",
            temporaria=True,
        )

        try:
            msg_cod = await self.bot.wait_for("message", check=check_dm, timeout=300)
            codigo = msg_cod.content.strip()
        except asyncio.TimeoutError:
            await enviar_dm(
                "⏳ Tempo esgotado para o envio do código. Autenticação cancelada."
            )
            return False

        try:
            await self.client.sign_in(telefone, codigo, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            await enviar_dm(
                "🔐 **Autenticação de Duas Etapas (2FA) detectada.**\n"
                "Digite a sua senha de nuvem do Telegram:",
                temporaria=True,
            )
            try:
                msg_pwd = await self.bot.wait_for(
                    "message", check=check_dm, timeout=300
                )
                senha = msg_pwd.content.strip()
                await self.client.sign_in(password=senha)
            except asyncio.TimeoutError:
                await enviar_dm("⏳ Tempo esgotado para o envio da senha 2FA.")
                return False
            except Exception as e:
                await enviar_dm(f"❌ Erro ao validar senha 2FA: {e}")
                return False
        except Exception as e:
            await enviar_dm(f"❌ Falha na autenticação do Telegram: {e}")
            return False

        await owner.send(
            "✅ **Telegram conectado com sucesso!**\n\n"
            "⚠️ *Por favor, apague as mensagens enviadas por você acima que contêm seu telefone e código.*"
        )

        for msg in mensagens_bot:
            asyncio.create_task(self._deletar_mensagem_apos(msg, delay=20))

        return True

    async def _processar_mensagem(self, event):
        """Handler executado ao receber novas mensagens nos canais escutados."""
        texto = event.raw_text

        if self.debug_mode:
            canal_origem = getattr(event.chat, "title", event.chat_id)
            self.logger.info(
                f"🔍 [DEBUG TG] Mensagem recebida de [{canal_origem}]: {texto[:60].strip()}..."
            )

        if not texto or ("http" not in texto and "R$" not in texto):
            if self.debug_mode:
                self.logger.info(
                    "   └── ❌ Descartada: Texto sem link ou indício de preço."
                )
            return

        oferta = data_manager.parse_and_process_telegram_offer(texto, event.message.id)

        if oferta:
            try:
                await data_manager.save_offers([oferta])
                self.logger.info(
                    f"  [Ingestão TG] Oferta salva: {oferta['titulo'][:30]}... | R$ {oferta['preco']} ({oferta['loja']})"
                )
            except Exception as e:
                self.logger.error(
                    f"  [Ingestão TG] Erro ao salvar oferta no Meilisearch: {e}"
                )
        elif self.debug_mode:
            self.logger.info("   └── ❌ Descartada no parse do DataManager.")

    async def atualizar_canais_escutados(self):
        """Atualiza dinamicamente os handlers do Telethon com novos canais adicionados."""
        if not self.client or not self.client.is_connected():
            return

        self.canais = self._carregar_canais_monitorados()
        if not self.canais:
            self.logger.warning("Nenhum canal para monitorar após atualização.")
            return

        self.client.remove_event_handler(self._processar_mensagem)
        self.client.add_event_handler(
            self._processar_mensagem, events.NewMessage(chats=self.canais)
        )
        self.logger.info(
            f"🔄 Lista de escuta do Telegram atualizada em tempo real! Canais ativos: {len(self.canais)}"
        )

    async def start(self):
        if not self.enabled:
            self.logger.info(
                "Módulo de Ingestão DESATIVADO no .env (TELEGRAM_ENABLED=false)."
            )
            return

        if not self.api_id or not self.api_hash:
            self.logger.warning(
                "Credenciais não configuradas no .env. Ingestão offline."
            )
            return

        self.canais = self._carregar_canais_monitorados()
        if not self.canais:
            self.logger.warning(
                "Nenhum canal configurado (.env ou banco). Ingestão offline."
            )
            return

        session_path = str(data_manager.folders["config"] / "sambot_telegram.session")
        self.client = TelegramClient(session_path, int(self.api_id), self.api_hash)

        try:
            await self.client.connect()

            if not await self.client.is_user_authorized():
                self.logger.info(
                    "Sessão ausente/expirada. Iniciando login interativo via DM no Discord..."
                )
                sucesso = await self._autenticar_via_discord()
                if not sucesso:
                    self.logger.error(
                        "❌ Não foi possível autenticar o cliente. Ingestão offline."
                    )
                    await self.client.disconnect()
                    return

            # Registra o handler para os canais
            self.client.add_event_handler(
                self._processar_mensagem, events.NewMessage(chats=self.canais)
            )

            status_debug = " [MODO DEBUG ATIVO]" if self.debug_mode else ""
            self.logger.info(
                f"Scraper ONLINE. Monitorando {len(self.canais)} canais/grupos{status_debug}"
            )
        except Exception as e:
            self.logger.error(f"Erro ao conectar cliente: {e}")
            return

        asyncio.create_task(self.client.run_until_disconnected())


class TelegramIngestionCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.scraper = TelegramScraper(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.scraper.start()


async def setup(bot):
    await bot.add_cog(TelegramIngestionCog(bot))
