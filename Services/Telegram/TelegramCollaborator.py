import asyncio
import logging
import os
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
        owner_env = AppConfig.get("OWNER_ID")
        self.owner_id = int(owner_env) if owner_env else None

        self.active_sessions = {}
        self.telethon_clients = {}

    def _is_owner(self, user_id: int) -> bool:
        return self.owner_id is not None and user_id == self.owner_id

    async def _obter_cliente_telethon(
        self, account_id: str = "default"
    ) -> TelegramClient:
        """Gerencia instâncias do Telethon utilizando por padrão a sessão principal do bot."""
        if (
            account_id in self.telethon_clients
            and self.telethon_clients[account_id].is_connected()
        ):
            return self.telethon_clients[account_id]

        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")

        if not api_id or not api_hash:
            return None

        # Utiliza o nome de sessão padronizado
        session_name = (
            "sambot_telegram.session"
            if account_id == "default"
            else f"sambot_telegram_{account_id}.session"
        )
        session_path = str(data_manager.folders["config"] / session_name)

        client = TelegramClient(session_path, int(api_id), api_hash)
        await client.connect()

        self.telethon_clients[account_id] = client
        return client

    def _grupo_ja_observado(self, chat_identifier: str) -> bool:
        """Verifica no banco de dados se algum grupo já está cadastrado para escuta."""
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
        """Salva a associação do grupo para evitar duplicação por outras contas."""
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
        """Notifica o cog do Scraper para atualizar sua lista de escuta sem reiniciar o bot."""
        scraper_cog = self.bot.get_cog("TelegramIngestionCog")
        if scraper_cog and hasattr(scraper_cog, "scraper"):
            if hasattr(scraper_cog.scraper, "atualizar_canais_escutados"):
                await scraper_cog.scraper.atualizar_canais_escutados()

    async def _buscar_grupo_proximo(self, client: TelegramClient, termo_busca: str):
        """Busca no Telegram ou sugere um nome próximo de grupos acessíveis."""
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
                    f"hmm, não encontrei '{termo_busca}'. Talvez você quis dizer **{nome_sugerido}**?",
                )

            return (
                None,
                f"não encontrei nada parecido com '{termo_busca}' entre os grupos acessíveis.",
            )
        except Exception as e:
            logger.error(f"Erro ao buscar diálogos no Telegram: {e}")
            return None, "ocorreu um erro ao consultar seus grupos no Telegram."

    async def _deletar_mensagem_apos(self, msg: discord.Message, delay: int = 20):
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except (discord.HTTPException, discord.NotFound):
            pass

    async def _autenticar_colaborador_via_dm(
        self, client: TelegramClient, colaborador: discord.User
    ) -> bool:
        """Realiza o login interativo via DM do Discord com limpeza de mensagens sensíveis."""
        dm = await colaborador.create_dm()
        mensagens_bot = []

        def check_dm(m: discord.Message):
            return m.author.id == colaborador.id and isinstance(
                m.channel, discord.DMChannel
            )

        async def enviar_dm(texto: str, temporaria: bool = True):
            msg = await dm.send(texto)
            if temporaria:
                mensagens_bot.append(msg)
            return msg

        # 1. Pede o telefone
        await enviar_dm(
            "📲 **Autenticação do Telegram Necessária!**\n"
            "Sua conta ainda não está conectada ao bot. Por favor, digite o seu **número de telefone** no formato internacional (Ex: `+5521999999999`):",
            temporaria=True,
        )

        try:
            msg_tel = await self.bot.wait_for("message", check=check_dm, timeout=120)
            telefone = msg_tel.content.strip()
        except asyncio.TimeoutError:
            await dm.send(
                "⏳ Tempo esgotado para o envio do telefone. Autenticação cancelada."
            )
            return False

        # 2. Solicita código no Telegram
        try:
            sent_code = await client.send_code_request(telefone)
            phone_code_hash = sent_code.phone_code_hash
        except Exception as e:
            await dm.send(f"❌ Erro ao solicitar código para `{telefone}`: {e}")
            return False

        # 3. Pede o código recebido no Telegram
        await enviar_dm(
            "📩 **Código enviado no seu Telegram!**\n"
            "Digite aqui o código de verificação que você acabou de receber no app:",
            temporaria=True,
        )

        try:
            msg_cod = await self.bot.wait_for("message", check=check_dm, timeout=120)
            codigo = msg_cod.content.strip()
        except asyncio.TimeoutError:
            await dm.send(
                "⏳ Tempo esgotado para o envio do código. Autenticação cancelada."
            )
            return False

        # 4. Tenta autenticar
        try:
            await client.sign_in(telefone, codigo, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            await enviar_dm(
                "🔐 **Autenticação de Duas Etapas (2FA) detectada.**\n"
                "Digite a sua senha de nuvem do Telegram:",
                temporaria=True,
            )
            try:
                msg_pwd = await self.bot.wait_for(
                    "message", check=check_dm, timeout=120
                )
                senha = msg_pwd.content.strip()
                await client.sign_in(password=senha)
            except asyncio.TimeoutError:
                await dm.send("⏳ Tempo esgotado para o envio da senha 2FA.")
                return False
            except Exception as e:
                await dm.send(f"❌ Erro ao validar senha 2FA: {e}")
                return False
        except Exception as e:
            await dm.send(f"❌ Falha na autenticação do Telegram: {e}")
            return False

        # 5. Aviso de Segurança e Agendamento da Exclusão
        await dm.send(
            "✅ **Telegram conectado com sucesso!**\n\n"
            "⚠️ *Por favor, apague as mensagens enviadas por você acima que contêm seu telefone e código.*"
        )

        for msg in mensagens_bot:
            asyncio.create_task(self._deletar_mensagem_apos(msg, delay=20))

        return True

    @commands.command(name="colaborar")
    async def colaborar(
        self, ctx: commands.Context, subcomando: str = None, alvo: discord.User = None
    ):
        """
        Sintaxe:
        +colaborar promo @user  -> Inicia a rotina (Apenas Owner ID)
        +colaborar cancelar    -> Cancela a rotina (Owner ID ou o Colaborador)
        """
        user_id = ctx.author.id

        # --- SUBCOMANDO: CANCELAR ---
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
                    "❌ **Processo de colaboração cancelado com sucesso!**"
                )
            else:
                return await ctx.send(
                    "⚠️ Nenhuma sessão de colaboração ativa foi encontrada."
                )

        # --- SUBCOMANDO: PROMO ---
        if subcomando and subcomando.lower() == "promo":
            if not self._is_owner(user_id):
                return await ctx.send(
                    "⛔ **Apenas o dono do bot pode iniciar um processo de colaboração!**"
                )

            colaborador = alvo or ctx.author

            if colaborador.id in self.active_sessions:
                return await ctx.send(
                    "⚠️ Este colaborador já possui uma configuração em andamento. Use `+colaborar cancelar` para interromper."
                )

            task = asyncio.create_task(self._rotina_perguntas_promo(ctx, colaborador))
            self.active_sessions[colaborador.id] = {"task": task, "owner_id": user_id}
            return

        await ctx.send(
            "⚠️ Comando inválido! Use `+colaborar promo @user` ou `+colaborar cancelar`."
        )

    async def _rotina_perguntas_promo(
        self, ctx: commands.Context, colaborador: discord.User
    ):
        colab_id = colaborador.id

        def check_dm(m: discord.Message):
            return m.author.id == colab_id and isinstance(m.channel, discord.DMChannel)

        try:
            dm = await colaborador.create_dm()
            await ctx.send(
                f"📩 {colaborador.mention}, enviei as instruções de colaboração no seu **DM**!"
            )

            # 1. Obter Cliente Telethon Ativo
            client = await self._obter_cliente_telethon("default")

            # Se não estiver autorizado, executa o fluxo interativo via DM
            if client and not await client.is_user_authorized():
                sucesso_auth = await self._autenticar_colaborador_via_dm(
                    client, colaborador
                )
                if not sucesso_auth:
                    return

            if not client:
                await dm.send(
                    "❌ Não foi possível inicializar o cliente do Telegram. Verifique as credenciais no .env."
                )
                return

            # 2. Alerta sobre Múltiplos Grupos Observados
            dialogs = await client.get_dialogs()
            canais_observados = [d for d in dialogs if d.is_group or d.is_channel]

            if len(canais_observados) >= 5:
                await dm.send(
                    f"⚠️ **Aviso de Capacidade:** A conta conectada já observa **{len(canais_observados)} grupos/canais**.\n"
                    "Certifique-se de adicionar apenas grupos com alto volume de promoções para evitar congestionamento."
                )

            # 3. Pergunta: Grupo a Observar
            await dm.send(
                "💬 **Qual grupo do Telegram você deseja observar?**\n"
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
                    await dm.send("❌ Configuração cancelada.")
                    return

                if self._grupo_ja_observado(termo_grupo):
                    await dm.send(
                        f"🚫 **Este grupo (`{termo_grupo}`) já está sendo observado pela Sam!**\n"
                        "Não é permitido cadastrar o mesmo grupo em duas contas. Por favor, envie outro grupo:"
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
                            "🚫 **Este grupo já está cadastrado no sistema!**\nPor favor, envie outro grupo:"
                        )
                        continue

                    entidade_validada = entidade
                    nome_chat = getattr(entidade, "title", termo_grupo)

                    # Registra o grupo no banco
                    self._registrar_grupo_observado(
                        chat_id, nome_chat, username, colab_id
                    )

                    # Notifica o Scraper para atualizar os handlers dinamicamente
                    await self._notificar_e_atualizar_scraper()

                    await dm.send(f"✅ **Grupo encontrado e registrado:** {nome_chat}")
                else:
                    await dm.send(
                        f"⚠️ {erro_msg}\nPor favor, digite o nome/link correto novamente:"
                    )

            # 4. Pergunta: Exemplo de envio
            await dm.send(
                "📝 **Envie um exemplo de como a mensagem de oferta costuma ser enviada nesse grupo:**\n"
                "(Copie e cole uma mensagem padrão do grupo aqui para testarmos as regras do parser)."
            )

            msg_exemplo = await self.bot.wait_for(
                "message", check=check_dm, timeout=180
            )
            texto_exemplo = msg_exemplo.content.strip()

            if texto_exemplo.lower() == "+colaborar cancelar":
                await dm.send("❌ Configuração cancelada.")
                return

            oferta_teste = data_manager.parse_and_process_telegram_offer(
                texto_exemplo, 999
            )

            if oferta_teste:
                await dm.send(
                    f"🎉 **Excelente! O parser conseguiu entender a oferta do grupo:**\n"
                    f"• **Produto:** {oferta_teste['titulo']}\n"
                    f"• **Preço:** R$ {oferta_teste['preco']:.2f}\n"
                    f"• **Loja:** {oferta_teste['loja']}\n\n"
                    f"Configuração finalizada com sucesso para **{colaborador.display_name}**!"
                )
            else:
                await dm.send(
                    "⚠️ O exemplo enviado não continha link ou preço reconhecível pelo sistema, "
                    "mas o grupo foi registrado no monitoramento!"
                )

        except asyncio.CancelledError:
            pass
        except asyncio.TimeoutError:
            try:
                await colaborador.send(
                    "⏳ Tempo esgotado para responder. A colaboração foi cancelada."
                )
            except Exception:
                pass
        finally:
            if colab_id in self.active_sessions:
                del self.active_sessions[colab_id]


async def setup(bot):
    await bot.add_cog(TelegramCollaborator(bot))
