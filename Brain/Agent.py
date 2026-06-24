# Brain/Agent.py
import discord
from discord.ext import commands
import re
import random
import logging

from Brain.Core.Pipeline import CognitionPipeline
from Brain.Memory.DataManager import data_manager

logger = logging.getLogger("SamBot.Agent")


class CerebroIA(commands.Cog):
    """
    Interface do Discord para o Cérebro da SamBot.
    Atua como um receptor que repassa eventos para o Pipeline Cognitivo.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger

        # Instancia o novo cérebro
        self.pipeline = CognitionPipeline(bot)

        # Canais Ativos (Para Intervenções Aleatórias)
        self.active_channels = {}
        if hasattr(data_manager, "load_active_channels"):
            raw_channels = data_manager.load_active_channels()
            self.active_channels = (
                raw_channels if isinstance(raw_channels, dict) else {}
            )

        self.logger.info(
            "📡 Interface Discord (Agent) vinculada ao Pipeline com sucesso."
        )

    def _is_command(self, message: discord.Message, prefixes) -> bool:
        content = message.content.strip()
        if not content:
            return False
        if isinstance(prefixes, (str, list)) and any(
            content.startswith(p)
            for p in (prefixes if isinstance(prefixes, list) else [prefixes])
        ):
            return True
        common = ["!", "/", ".", "?", "+", "-", "$", "%", "*"]
        return (
            any(content.startswith(p) for p in common)
            and len(content) > 1
            and not content[1].isspace()
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.author.id == self.bot.user.id:
            return

        prefix = await self.bot.get_prefix(message)
        if self._is_command(message, prefix):
            return

        is_mentioned = self.bot.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_reply = (
            message.reference
            and message.reference.cached_message
            and message.reference.cached_message.author.id == self.bot.user.id
        )

        persona = self.active_channels.get(str(message.channel.id))
        should_reply = (
            is_mentioned or is_dm or is_reply or (persona and random.random() < 0.05)
        )

        if should_reply:
            async with message.channel.typing():
                clean_text = re.sub(r"<@!?\d+>", "", message.content).strip()
                if not clean_text and not message.attachments:
                    clean_text = "Olá!"

                input_text = clean_text
                try:
                    res = self.pipeline.limpeza.identify(clean_text)
                    input_text = (
                        res.get("normalized", clean_text)
                        if isinstance(res, dict)
                        else clean_text
                    )
                except Exception as e:
                    logger.error(
                        f"Erro crítico ao processar mensagem no canal {message.channel.id}: {e},",
                        exc_info=True,
                    )

                    try:
                        await message.channel.send(
                            "⚠️ Desculpe, ocorreu um erro interno ao processar seu comando."
                        )
                    except Exception:
                        logger.error(
                            "Não foi possível enviar a mensagem de erro para o canal do Discord."
                        )

                # Delega a cognição pesada para o Pipeline
                await self.pipeline.processar_cognicao(message, input_text, persona)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot or str(reaction.emoji) != "🧠":
            return
        frases = [
            "Guardado! 💾💜",
            "Memória salva! ✨",
            "Anotado no meu HD! 📝",
            "Adoro saber mais sobre ti! 🥰",
        ]
        try:
            await user.send(f"**SamBot Memória:** {random.choice(frases)}")
        except Exception as e:
            logger.error(
                f"⚠️ Não foi possível enviar DM de memória para o usuario {user.name} (ID: {user.id}). Erro: {e}"
            )

    async def run(self, message):
        await self.on_message(message)


async def setup(bot):
    await bot.add_cog(CerebroIA(bot))
