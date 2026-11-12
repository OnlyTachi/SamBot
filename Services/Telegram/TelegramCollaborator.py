import asyncio
import logging
import discord
from discord.ext import commands
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from rapidfuzz import process, fuzz
from Core.ConfigLoader import AppConfig
from Brain.Memory.DataManager.Connections import data_manager

logger = logging.getLogger("SamBot.TelegramCollaborator")


class TelegramCollaborator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        owner_env = AppConfig.get("bot.owner_id") or AppConfig.get("OWNER_ID")
        self.owner_id = int(owner_env) if owner_env else None
        self.active_sessions = {}
        self.telethon_clients = {}

    def _is_owner(self, user_id: int) -> bool:
        return self.owner_id is not None and user_id == self.owner_id

    async def _obter_cliente_telethon(
        self, account_id: str = "default"
    ) -> TelegramClient:
        """Gere instâncias do Telethon sem recorrer diretamente a variáveis de ambiente."""
        if (
            account_id in self.telethon_clients
            and self.telethon_clients[account_id].is_connected()
        ):
            return self.telethon_clients[account_id]

        api_id = AppConfig.get("telegram.api_id") or AppConfig.get("TELEGRAM_API_ID")
        api_hash = AppConfig.get("telegram.api_hash") or AppConfig.get(
            "TELEGRAM_API_HASH"
        )

        if not api_id or not api_hash:
            return None

        session_name = (
            "sambot_telegram.session"
            if account_id == "default"
            else f"sambot_telegram_{account_id}.session"
        )
        session_path = data_manager.get_persistence_path(session_name)
        client = TelegramClient(session_path, int(api_id), api_hash)
        await client.connect()
        self.telethon_clients[account_id] = client
        return client

    def _grupo_ja_observado(self, chat_identifier: str) -> bool:
        grupos_cadastrados = (
            data_manager.get_knowledge("monitored_telegram_channels") or {}
        )
        for gid, info in grupos_cadastrados.items():
            if str(gid) == str(chat_identifier) or info.get("username") == str(
                chat_identifier
            ).replace("@", ""):
                return True
        return False

    def _registrar_grupo_observado(
        self, chat_id: int, title: str, username: str, colaborador_id: int
    ):
        grupos_cadastrados = (
            data_manager.get_knowledge("monitored_telegram_channels") or {}
        )
        grupos_cadastrados[str(chat_id)] = {
            "title": title,
            "username": username,
            "added_by": colaborador_id,
            "active": True,
        }
        data_manager.save_knowledge("monitored_telegram_channels", grupos_cadastrados)

    async def _notificar_e_atualizar_scraper(self):
        if hasattr(self.bot, "services") and hasattr(self.bot.services, "telegram"):
            scraper = self.bot.services.telegram
            if scraper and hasattr(scraper, "atualizar_canais_escutados"):
                await scraper.atualizar_canais_escutados()
                return
        logger.warning(
            "Não foi possível localizar a instância ativa do TelegramScraper para atualização."
        )

    async def _buscar_grupo_proximo(self, client: TelegramClient, termo_busca: str):
        try:
            entity = await client.get_entity(termo_busca)
            return entity, None
        except Exception:
            pass
        try:
            dialogs = await client.get_dialogs()
            nomes_grupos = {
                d.name: d.entity for d in dialogs if d.is_group or d.is_channel
            }
            if not nomes_grupos:
                return None, "não encontrei nenhum grupo acessível na conta."
            match = process.extractOne(
                termo_busca, list(nomes_grupos.keys()), scorer=fuzz.WRatio
            )
            if match and match[1] > 50:
                nome_sugerido = match[0]
                return (
                    None,
                    f"hmm, não encontrei '{termo_busca}'. Talvez quisesse dizer **{nome_sugerido}**?",
                )
            return (
                None,
                f"não encontrei nada parecido com '{termo_busca}' entre os grupos acessíveis.",
            )
        except Exception as e:
            logger.error(f"Erro ao procurar diálogos no Telegram: {e}")
            return None, "ocorreu um erro ao consultar os seus grupos no Telegram."

    async def _deletar_mensagem_apos(self, msg: discord.Message, delay: int = 20):
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except (discord.HTTPException, discord.NotFound):
            pass

    async def _autenticar_colaborador_via_dm(
        self, client: TelegramClient, colaborador: discord.User
    ) -> bool:
        dm = await colaborador.create_dm()
        mensagens_bot = []

        def check_dm(m: discord.Message):
            return m.guild is None and m.author.id == colaborador.id

        async def enviar_dm(texto: str, temporaria: bool = True):
            msg = await dm.send(texto)
            if temporaria:
                mensagens_bot.append(msg)
            return msg

        await enviar_dm(
            "**Autenticação do Telegram Necessária!**\n"
            "A sua conta ainda não está conectada ao bot. Por favor, digite o seu **número de telefone** no formato internacional (Ex: `+5521999999999`):",
            temporaria=True,
        )
        try:
            msg_tel = await self.bot.wait_for("message", check=check_dm, timeout=120)
            telefone = msg_tel.content.strip()
        except asyncio.TimeoutError:
            await dm.send(
                "Tempo esgotado para o envio do telefone. Autenticação cancelada."
            )
            return False

        try:
            sent_code = await client.send_code_request(telefone)
            phone_code_hash = sent_code.phone_code_hash
        except Exception as e:
            await dm.send(f"Erro ao solicitar código para `{telefone}`: {e}")
            return False

        await enviar_dm(
            "**Código enviado no seu Telegram!**\n"
            "Digite aqui o código de verificação recebido na app:",
            temporaria=True,
        )
        try:
            msg_cod = await self.bot.wait_for("message", check=check_dm, timeout=120)
            codigo = msg_cod.content.strip()
        except asyncio.TimeoutError:
            await dm.send(
                "Tempo esgotado para o envio do código. Autenticação cancelada."
            )
            return False

        try:
            await client.sign_in(telefone, codigo, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            await enviar_dm(
                "**Autenticação de Duas Etapas (2FA) detetada.**\n"
                "Digite a sua password de nuvem do Telegram:",
                temporaria=True,
            )
            try:
                msg_pwd = await self.bot.wait_for(
                    "message", check=check_dm, timeout=120
                )
                senha = msg_pwd.content.strip()
                await client.sign_in(password=senha)
            except asyncio.TimeoutError:
                await dm.send("Tempo esgotado para o envio da password 2FA.")
                return False
            except Exception as e:
                await dm.send(f"Erro ao validar password 2FA: {e}")
                return False
        except Exception as e:
            await dm.send(f"Falha na autenticação do Telegram: {e}")
            return False

        await dm.send(
            "**Telegram conectado com sucesso!**\n\n"
            "*Por favor, apague as mensagens enviadas por si acima que contêm o seu telefone e código.*"
        )
        for msg in mensagens_bot:
            asyncio.create_task(self._deletar_mensagem_apos(msg, delay=20))
        return True

    @commands.command(name="colaborar")
    async def colaborar(
        self, ctx: commands.Context, subcomando: str = None, alvo: discord.User = None
    ):
        user_id = ctx.author.id
        if subcomando and subcomando.lower() == "cancelar":
            sessao_alvo = None
            target_uid = user_id
            if user_id in self.active_sessions:
                sessao_alvo = self.active_sessions[user_id]
            elif self._is_owner(user_id):
                if self.active_sessions:
                    target_uid = list(self.active_sessions.keys())[0]
                    sessao_alvo = self.active_sessions[target_uid]
            if sessao_alvo:
                sessao_alvo["task"].cancel()
                del self.active_sessions[target_uid]
                return await ctx.send(
                    "**Processo de colaboração cancelado com sucesso!**"
                )
            else:
                return await ctx.send(
                    "Nenhuma sessão de colaboração ativa foi encontrada."
                )

        if subcomando and subcomando.lower() == "promo":
            if not self._is_owner(user_id):
                return await ctx.send(
                    "**Apenas o dono do bot pode iniciar um processo de colaboração!**"
                )
            colaborador = alvo or ctx.author
            if colaborador.id in self.active_sessions:
                return await ctx.send(
                    "Este colaborador já possui uma configuração em andamento. Use `+colaborar cancelar` para interromper."
                )
            task = asyncio.create_task(self._rotina_perguntas_promo(ctx, colaborador))
            self.active_sessions[colaborador.id] = {"task": task, "owner_id": user_id}
            return

        await ctx.send(
            "Comando inválido! Use `+colaborar promo @user` ou `+colaborar cancelar`."
        )

    @colaborar.error
    async def colaborar_error(self, ctx, error):
        if isinstance(error, commands.UserNotFound):
            await ctx.send(
                f"Não consegui encontrar o utilizador **{error.argument}**. Verifique se escreveu o @ corretamente e tente novamente!"
            )
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"Não consegui encontrar o membro **{error.argument}** neste servidor. Tem a certeza de que está aqui?"
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Faltam argumentos! Use: `+colaborar promo @utilizador`")
        else:
            self.bot.logger.error(f"Erro não tratado no comando colaborar: {error}")

    async def _rotina_perguntas_promo(
        self, ctx: commands.Context, colaborador: discord.User
    ):
        colab_id = colaborador.id
        data_manager.set_user_data(str(colab_id), "status_ocupado", True)

        def check_dm(m: discord.Message):
            return m.author.id == colab_id and isinstance(m.channel, discord.DMChannel)

        try:
            dm = await colaborador.create_dm()
            await ctx.send(
                f"{colaborador.mention}, enviei as instruções de colaboração no seu **DM**!"
            )
            client = await self._obter_cliente_telethon("default")
            if client and not await client.is_user_authorized():
                sucesso_auth = await self._autenticar_colaborador_via_dm(
                    client, colaborador
                )
                if not sucesso_auth:
                    return
            if not client:
                await dm.send(
                    "Não foi possível inicializar o cliente do Telegram. Verifique as credenciais configuradas."
                )
                return

            dialogs = await client.get_dialogs()
            canais_observados = [d for d in dialogs if d.is_group or d.is_channel]
            if len(canais_observados) >= 5:
                await dm.send(
                    f"**Aviso de Capacidade:** A conta conectada já observa **{len(canais_observados)} grupos/canais**.\n"
                    "Certifique-se de adicionar apenas grupos com alto volume de promoções para evitar congestionamento."
                )

            await dm.send(
                "**Qual grupo do Telegram deseja observar?**\n"
                "Envie o link do canal/grupo (Ex: `https://t.me/OfertasePromos`) ou o `@username`:\n\n"
                "*Para cancelar a qualquer momento, digite `+colaborar cancelar` aqui no chat.*"
            )
            entidade_validada = None
            while not entidade_validada:
                msg_grupo = await self.bot.wait_for(
                    "message", check=check_dm, timeout=120
                )
                termo_grupo = msg_grupo.content.strip()
                if termo_grupo.lower() == "+colaborar cancelar":
                    await dm.send("Configuração cancelada.")
                    return
                if self._grupo_ja_observado(termo_grupo):
                    await dm.send(
                        f"**Este grupo (`{termo_grupo}`) já está a ser observado pela Sam!**\n"
                        "Não é permitido registar o mesmo grupo em duas contas. Por favor, envie outro grupo:"
                    )
                    continue
                entidade, erro_msg = await self._buscar_grupo_proximo(
                    client, termo_grupo
                )
                if entidade:
                    chat_id = getattr(entidade, "id", None)
                    username = getattr(entidade, "username", "")
                    if self._grupo_ja_observado(chat_id):
                        await dm.send(
                            "**Este grupo já está registado no sistema!**\nPor favor, envie outro grupo:"
                        )
                        continue
                    entidade_validada = entidade
                    nome_chat = getattr(entidade, "title", termo_grupo)
                    self._registrar_grupo_observado(
                        chat_id, nome_chat, username, colab_id
                    )
                    await self._notificar_e_atualizar_scraper()
                    await dm.send(f"**Grupo encontrado e registado:** {nome_chat}")
                else:
                    await dm.send(
                        f"{erro_msg}\nPor favor, digite o nome/link correto novamente:"
                    )

            await dm.send(
                "**Envie um exemplo de como a mensagem de oferta costuma ser enviada nesse grupo:**\n"
                "(Copie e cole uma mensagem padrão do grupo aqui para testarmos)."
            )
            msg_exemplo = await self.bot.wait_for(
                "message", check=check_dm, timeout=180
            )
            texto_exemplo = msg_exemplo.content.strip()
            if texto_exemplo.lower() == "+colaborar cancelar":
                await dm.send("Configuração cancelada.")
                return
            oferta_teste = data_manager.parse_and_process_telegram_offer(
                texto_exemplo, 999
            )
            if oferta_teste:
                await dm.send(
                    f"**Excelente! O analisador conseguiu processar a oferta do grupo:**\n"
                    f"**Produto:** {oferta_teste['titulo']}\n"
                    f"**Preço:** R$ {oferta_teste['preco']:.2f}\n"
                    f"**Loja:** {oferta_teste['loja']}\n\n"
                    f"Configuração finalizada com sucesso para **{colaborador.display_name}**!"
                )
            else:
                await dm.send(
                    "O exemplo enviado não continha link ou preço reconhecível pelo sistema, "
                    "mas o grupo foi registado no monitoramento!"
                )
        except asyncio.CancelledError:
            pass
        except asyncio.TimeoutError:
            try:
                await colaborador.send(
                    "Tempo esgotado para responder. A colaboração foi cancelada."
                )
            except Exception:
                pass
        finally:
            data_manager.set_user_data(str(colab_id), "status_ocupado", False)
            if colab_id in self.active_sessions:
                del self.active_sessions[colab_id]


async def setup(bot):
    await bot.add_cog(TelegramCollaborator(bot))
