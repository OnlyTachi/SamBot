import discord
from discord.ext import commands
import logging
import re
import time

from Brain.Memory.DataManager import data_manager

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
        label="Palavras Bloqueadas", style=discord.ButtonStyle.primary, emoji="🤬"
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
        label="+ Adicionar Palavra",
        style=discord.ButtonStyle.success,
        emoji="➕",
        row=1,
    )
    async def btn_add_word(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(AddWordModal(self.guild_id, self.bot))


# --- O MOTOR DO AUTOMOD ---


class AutoMod(commands.Cog):
    """Sistema invisível de moderação automática (Anti-spam, Anti-link e Filtro de Palavras)."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.AutoMod")
        # Expressão regular para encontrar links
        self.link_regex = re.compile(r"(https?://\S+|discord\.gg/\S+)", re.IGNORECASE)
        # Dicionário para rastrear mensagens recentes (Anti-Spam)
        self.spam_tracker = {}

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

        anti_link = "🟢 Ligado" if am_config.get("anti_link", False) else "🔴 Desligado"
        anti_words = (
            "🟢 Ligado" if am_config.get("anti_words", False) else "🔴 Desligado"
        )
        anti_spam = "🟢 Ligado" if am_config.get("anti_spam", False) else "🔴 Desligado"

        lista_palavras = am_config.get("blocked_words", [])
        palavras_txt = ", ".join(lista_palavras) if lista_palavras else "Nenhuma."

        embed = discord.Embed(
            title="🛡️ Painel do AutoMod", color=discord.Color.dark_theme()
        )
        embed.add_field(name="🔗 Anti-Link", value=anti_link, inline=True)
        embed.add_field(name="🤬 Filtro de Palavras", value=anti_words, inline=True)
        embed.add_field(name="🔁 Anti-Spam", value=anti_spam, inline=True)
        embed.add_field(
            name="📝 Palavras na Lista Negra", value=f"*{palavras_txt}*", inline=False
        )
        embed.set_footer(
            text="Use os botões abaixo para configurar o filtro do servidor."
        )

        await ctx.send(embed=embed, view=AutoModConfigView(ctx, self.bot))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Ignora Administradores e Moderadores (Eles podem mandar links)
        if message.author.guild_permissions.manage_messages:
            return

        guild_id = str(message.guild.id)
        configs = data_manager.get_knowledge("guild_configs") or {}
        am_config = configs.get(guild_id, {}).get("automod", {})

        if not am_config:
            return  # AutoMod não está configurado

        content_lower = message.content.lower()
        motivo_infracao = None

        # 1. FILTRO DE PALAVRAS BLOQUEADAS
        if am_config.get("anti_words", False):
            palavras_bloqueadas = am_config.get("blocked_words", [])
            for palavra in palavras_bloqueadas:
                if palavra in content_lower:
                    motivo_infracao = f"Uso de palavra bloqueada: `{palavra}`"
                    break

        # 2. FILTRO ANTI-LINK
        if not motivo_infracao and am_config.get("anti_link", False):
            if self.link_regex.search(content_lower):
                motivo_infracao = "Envio de link não autorizado."

        # 3. FILTRO ANTI-SPAM (Máximo de 5 mensagens a cada 5 segundos)
        if not motivo_infracao and am_config.get("anti_spam", False):
            user_id = str(message.author.id)
            agora = time.time()

            if user_id not in self.spam_tracker:
                self.spam_tracker[user_id] = []

            # Remove mensagens antigas (mais velhas que 5 segundos)
            self.spam_tracker[user_id] = [
                t for t in self.spam_tracker[user_id] if agora - t < 5.0
            ]
            self.spam_tracker[user_id].append(agora)

            if len(self.spam_tracker[user_id]) >= 5:
                motivo_infracao = "Spam excessivo (Flood)."
                self.spam_tracker[user_id] = (
                    []
                )  # Limpa para não punir múltiplas vezes seguidas

        # --- APLICAÇÃO DA PUNIÇÃO ---
        if motivo_infracao:
            try:
                await message.delete()  # Apaga a mensagem irregular

                # Avisa o usuário (Aviso rápido de 5 segundos que some sozinho)
                aviso = await message.channel.send(
                    f"⚠️ {message.author.mention}, a sua mensagem foi apagada pelo AutoMod. **Motivo:** {motivo_infracao}"
                )
                await aviso.delete(delay=5.0)

                # Aciona o mural público de Avisos (se estiver configurado)
                avisos_cog = self.bot.get_cog("Avisos")
                if avisos_cog:
                    await avisos_cog.enviar_aviso(
                        message.guild,
                        "AVISO",
                        message.author,
                        self.bot.user,
                        motivo_infracao,
                    )

            except discord.Forbidden:
                self.logger.warning("Sem permissão para deletar mensagens no AutoMod.")


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
