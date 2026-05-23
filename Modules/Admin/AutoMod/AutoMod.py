import discord
from discord.ext import commands
import logging

from Brain.Memory.DataManager import data_manager

try:
    from ._spam import SpamHandler
    from ._link import LinkHandler
    from ._palavras import WordsHandler
    from ._convite import InviteHandler
except ImportError as e:
    logging.getLogger("SamBot.AutoMod").warning(
        f"⚠️ Handlers ainda não criados completamente: {e}"
    )


# --- UI DE CONFIGURAÇÃO (O PAINEL VISUAL) ---


class AddWordModal(discord.ui.Modal, title="Adicionar Palavra Bloqueada"):
    palavra = discord.ui.TextInput(
        label="Palavra ou Frase",
        style=discord.TextStyle.short,
        placeholder="Ex: boboca",
        required=True,
    )

    def __init__(self, guild_id, bot):
        super().__init__()
        self.guild_id = guild_id
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}
        if "automod" not in configs[self.guild_id]:
            configs[self.guild_id]["automod"] = {}
        if "blocked_words" not in configs[self.guild_id]["automod"]:
            configs[self.guild_id]["automod"]["blocked_words"] = []

        palavra_nova = self.palavra.value.lower().strip()
        lista_palavras = configs[self.guild_id]["automod"]["blocked_words"]

        if palavra_nova not in lista_palavras:
            lista_palavras.append(palavra_nova)
            data_manager.save_knowledge("guild_configs", configs)
            await interaction.response.send_message(
                f"✅ A palavra **{palavra_nova}** foi adicionada à lista negra!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⚠️ Esta palavra já está bloqueada.", ephemeral=True
            )


class AutoModConfigView(discord.ui.View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.bot = bot
        self.guild_id = str(ctx.guild.id)

    async def toggle_feature(self, interaction: discord.Interaction, feature: str):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}
        if "automod" not in configs[self.guild_id]:
            configs[self.guild_id]["automod"] = {}

        atual = configs[self.guild_id]["automod"].get(feature, False)
        configs[self.guild_id]["automod"][feature] = not atual
        data_manager.save_knowledge("guild_configs", configs)

        estado = "LIGADO 🟢" if not atual else "DESLIGADO 🔴"
        await interaction.response.send_message(
            f"Filtro `{feature}` agora está **{estado}**.", ephemeral=True
        )

    @discord.ui.button(label="Anti-Link", style=discord.ButtonStyle.primary, emoji="🔗")
    async def btn_link(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.toggle_feature(interaction, "anti_link")

    @discord.ui.button(
        label="Anti-Convite", style=discord.ButtonStyle.primary, emoji="🎫"
    )
    async def btn_invite(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.toggle_feature(interaction, "anti_invite")

    @discord.ui.button(
        label="Filtro Palavras", style=discord.ButtonStyle.primary, emoji="🤬"
    )
    async def btn_words(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.toggle_feature(interaction, "anti_words")

    @discord.ui.button(label="Anti-Spam", style=discord.ButtonStyle.primary, emoji="🔁")
    async def btn_spam(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.toggle_feature(interaction, "anti_spam")

    @discord.ui.button(
        label="+ Add Palavra", style=discord.ButtonStyle.success, emoji="➕", row=1
    )
    async def btn_add_word(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(AddWordModal(self.guild_id, self.bot))


# --- O MOTOR DO AUTOMOD (ORQUESTRADOR) ---


class AutoModCore(commands.Cog):
    """Sistema invisível de moderação automática com arquitetura modular."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.AutoMod")

        # Inicializa os Handlers Especialistas
        self.spam_handler = (
            globals().get("SpamHandler")() if "SpamHandler" in globals() else None
        )
        self.link_handler = (
            globals().get("LinkHandler")() if "LinkHandler" in globals() else None
        )
        self.words_handler = (
            globals().get("WordsHandler")() if "WordsHandler" in globals() else None
        )
        self.invite_handler = (
            globals().get("InviteHandler")() if "InviteHandler" in globals() else None
        )

    @commands.hybrid_command(
        name="configautomod",
        aliases=["automod"],
        description="[Admin] Painel de configuração do AutoMod.",
    )
    @commands.has_permissions(manage_guild=True)
    async def configautomod(self, ctx: commands.Context):
        configs = data_manager.get_knowledge("guild_configs") or {}
        guild_id = str(ctx.guild.id)
        am_config = configs.get(guild_id, {}).get("automod", {})

        anti_link = "🟢" if am_config.get("anti_link", False) else "🔴"
        anti_invite = "🟢" if am_config.get("anti_invite", False) else "🔴"
        anti_words = "🟢" if am_config.get("anti_words", False) else "🔴"
        anti_spam = "🟢" if am_config.get("anti_spam", False) else "🔴"

        lista_palavras = am_config.get("blocked_words", [])
        palavras_txt = ", ".join(lista_palavras) if lista_palavras else "Nenhuma."

        embed = discord.Embed(
            title="🛡️ Painel de Segurança (AutoMod)", color=discord.Color.dark_theme()
        )
        embed.add_field(name="🔗 Anti-Link Geral", value=anti_link, inline=True)
        embed.add_field(name="🎫 Anti-Convites", value=anti_invite, inline=True)
        embed.add_field(name="🤬 Filtro de Palavras", value=anti_words, inline=True)
        embed.add_field(name="🔁 Anti-Spam", value=anti_spam, inline=True)
        embed.add_field(name="📝 Lista Negra", value=f"*{palavras_txt}*", inline=False)
        embed.set_footer(text="SamBot • Configure nos botões")

        await ctx.send(embed=embed, view=AutoModConfigView(ctx, self.bot))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Ignora Administradores e Moderadores
        if message.author.guild_permissions.manage_messages:
            return

        guild_id = str(message.guild.id)
        configs = data_manager.get_knowledge("guild_configs") or {}
        am_config = configs.get(guild_id, {}).get("automod", {})

        if not am_config:
            return

        motivo_infracao = None

        if am_config.get("anti_words") and self.words_handler and not motivo_infracao:
            motivo_infracao = await self.words_handler.analisar(message, am_config)

        if am_config.get("anti_invite") and self.invite_handler and not motivo_infracao:
            motivo_infracao = await self.invite_handler.analisar(message, am_config)

        if am_config.get("anti_link") and self.link_handler and not motivo_infracao:
            motivo_infracao = await self.link_handler.analisar(message, am_config)

        if am_config.get("anti_spam") and self.spam_handler and not motivo_infracao:
            motivo_infracao = await self.spam_handler.analisar(message, am_config)

        if motivo_infracao:
            await self.aplicar_punicao(message, motivo_infracao)

    async def aplicar_punicao(self, message: discord.Message, motivo: str):
        """Lida com a exclusão e notificação de forma centralizada"""
        try:
            await message.delete()

            # Avisa o usuário no chat
            aviso = await message.channel.send(
                f"⚠️ {message.author.mention}, sua mensagem foi retida. **Motivo:** {motivo}"
            )
            await aviso.delete(delay=6.0)

            # Aciona o mural público de Avisos (Auditoria/Log)
            avisos_cog = self.bot.get_cog("Avisos")
            if avisos_cog:
                await avisos_cog.enviar_aviso(
                    message.guild,
                    "AUTOMOD",
                    message.author,
                    self.bot.user,
                    f"Mensagem retida no canal {message.channel.mention}.\n**Motivo:** {motivo}\n**Conteúdo:** `{message.content[:800]}`",
                )

        except discord.Forbidden:
            self.logger.warning(
                f"Sem permissão para deletar mensagem ou notificar AutoMod no servidor {message.guild.name}."
            )


async def setup(bot):
    await bot.add_cog(AutoModCore(bot))
