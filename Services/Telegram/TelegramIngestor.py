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
        self.enabled = str(AppConfig.get("TELEGRAM_ENABLED", "true")).lower() == "true"
        self.debug_mode = str(AppConfig.get("DEBUG_MODE", "false")).lower() == "true"

        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")

        owner_env = AppConfig.get("OWNER_ID")
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
        owner_id_str = str(self.owner_id)
        data_manager.set_user_data(owner_id_str, "status_ocupado", True)
        if not self.owner_id:
            self.logger.error("  OWNER_ID não configurado para autenticação via DM.")
            return False
        try:
            owner = await self.bot.fetch_user(self.owner_id)
            if not owner:
                self.logger.error(
                    f"Não foi possível encontrar o usuário {self.owner_id} no Discord."
                )
                return False
        except Exception as e:
            self.logger.error(f"  Erro ao buscar Owner no Discord: {e}")
            return False

        mensagens_bot = []

        # Validação robusta de DM (não depende de DMChannel cacheado)
        def check_dm(m: discord.Message):
            return m.guild is None and m.author.id == self.owner_id

        async def enviar_dm(texto: str, temporaria: bool = True):
            msg = await owner.send(texto)
            if temporaria:
                mensagens_bot.append(msg)
            return msg

        await enviar_dm(
            " Olá! A sessão do Telegram não está autorizada.\n"
            "Por favor, responda aqui com o seu **número de telefone** no formato internacional (Ex: `+5521999999999`):",
            temporaria=True,
        )
        try:
            msg_tel = await self.bot.wait_for("message", check=check_dm, timeout=300)
            telefone = msg_tel.content.strip()
        except asyncio.TimeoutError:
            await enviar_dm(
                "  Tempo esgotado para o envio do telefone. Autenticação cancelada."
            )
            return False

        try:
            sent_code = await self.client.send_code_request(telefone)
            phone_code_hash = sent_code.phone_code_hash
        except Exception as e:
            await enviar_dm(f"  Erro ao solicitar código para `{telefone}`: {e}")
            return False

        await enviar_dm(
            "  **Código enviado pelo Telegram!**\n"
            "Por favor, digite aqui o código de verificação que você acabou de receber no app:",
            temporaria=True,
        )
        try:
            msg_cod = await self.bot.wait_for("message", check=check_dm, timeout=300)
            codigo = msg_cod.content.strip()
        except asyncio.TimeoutError:
            await enviar_dm(
                "  Tempo esgotado para o envio do código. Autenticação cancelada."
            )
            return False

        try:
            await self.client.sign_in(telefone, codigo, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            await enviar_dm(
                "  **Autenticação de Duas Etapas (2FA) detectada.**\n"
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
                await enviar_dm("  Tempo esgotado para o envio da senha 2FA.")
                return False
            except Exception as e:
                await enviar_dm(f"  Erro ao validar senha 2FA: {e}")
                return False
            except Exception as e:
                await enviar_dm(f"  Falha na autenticação do Telegram: {e}")
                return False
            finally:
                data_manager.set_user_data(self.owner_id, "status_ocupado", False)

        await owner.send(
            "  **Telegram conectado com sucesso!**\n\n"
            "  *Por favor, apague as mensagens enviadas por você acima que contêm seu telefone e código.*"
        )
        for msg in mensagens_bot:
            asyncio.create_task(self._deletar_mensagem_apos(msg, delay=20))
        return True

    async def stop(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            self.logger.info("  Cliente Telethon desconectado com sucesso.")

    async def _processar_mensagem(self, event):
        """Handler executado ao receber novas mensagens nos canais escutados."""
        texto = event.raw_text
        texto_lower = texto.lower() if texto else ""

        if self.debug_mode:
            canal_origem = getattr(event.chat, "title", event.chat_id)
            self.logger.info(
                f"  [DEBUG TG] Mensagem de [{canal_origem}]: {texto[:60].strip()}..."
            )

        if not texto_lower or ("http" not in texto_lower and "r$" not in texto_lower):
            if self.debug_mode:
                self.logger.info("Descartada: Texto sem link ou indício de preço.")
            return

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
            self.logger.info("Módulo de Ingestão DESATIVADO, que fominha")
            return
        if not self.api_id or not self.api_hash:
            self.logger.warning(
                "Credenciais não configuradas no .env. Ingestão offline."
            )
            return
        self.canais = self._carregar_canais_monitorados()
        if not self.canais:
            self.logger.warning("Nenhum canal configurado. Ingestão offline.")
            return

        session_path = data_manager.get_persistence_path("sambot_telegram.session")
        self.client = TelegramClient(session_path, int(self.api_id), self.api_hash)

        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                self.logger.info(
                    "Sessão ausente/expirada. Iniciando login interativo via DM no Discord..."
                )
                # Joga a autenticação para segundo plano para NÃO bloquear o boot do bot
                asyncio.create_task(self._fluxo_autenticacao_background())
                return

            # Se já estiver autorizado, inicia direto
            self._ativar_handlers_e_rodar()

        except Exception as e:
            self.logger.error(f"Erro ao conectar cliente: {e}")
            return

    async def _fluxo_autenticacao_background(self):
        """Gerencia o login sem travar a thread principal do Discord.py"""
        sucesso = await self._autenticar_via_discord()
        if not sucesso:
            await self.client.disconnect()
            self.logger.error("Falha na autenticação do Telegram. Ingestão offline.")
            return

        # Concluiu a autenticação? Ativa os handlers e começa a rodar
        self._ativar_handlers_e_rodar()

    def _ativar_handlers_e_rodar(self):
        """Inicia os ouvintes do Telegram"""
        self.client.add_event_handler(
            self._processar_mensagem, events.NewMessage(chats=self.canais)
        )
        status_debug = " [MODO DEBUG ATIVO]" if self.debug_mode else ""
        self.logger.info(
            f"Scraper ONLINE. Monitorando {len(self.canais)} canais/grupos{status_debug}"
        )
        asyncio.create_task(self.client.run_until_disconnected())


class TelegramIngestionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(TelegramIngestionCog(bot))
