import discord
from discord.ext import commands
import logging
import random
import time

from Brain.Memory.DataManager import data_manager

# --- UI DE CONFIGURAÇÃO (O PAINEL VISUAL) ---


class MsgModal(discord.ui.Modal, title="Mensagem de Level Up"):
    """Janela popup para o admin digitar a mensagem personalizada."""

    mensagem = discord.ui.TextInput(
        label="Mensagem (Use {user} e {level})",
        style=discord.TextStyle.paragraph,
        placeholder="🎉 Parabéns {user}!\nVoce acabou de subir para o nível {level}!",
        required=True,
        max_length=500,
    )

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}

        configs[self.guild_id]["mensagem"] = self.mensagem.value
        data_manager.save_knowledge("guild_configs", configs)

        await interaction.response.send_message(
            "✅ Mensagem de Level Up atualizada com sucesso!", ephemeral=True
        )


class ConfigXPView(discord.ui.View):
    """O painel interativo principal de configurações."""

    def __init__(self, ctx, bot):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.bot = bot
        self.guild_id = str(ctx.guild.id)

    # Botão 1: Ativar/Desativar
    @discord.ui.button(
        label="Ligar / Desligar", style=discord.ButtonStyle.primary, emoji="⚙️", row=0
    )
    async def btn_toggle(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {"enabled": True}

        atual = configs[self.guild_id].get("enabled", True)
        configs[self.guild_id]["enabled"] = not atual
        data_manager.save_knowledge("guild_configs", configs)

        estado = "LIGADO 🟢" if not atual else "DESLIGADO 🔴"
        await interaction.response.send_message(
            f"Sistema de XP passivo agora está **{estado}**.", ephemeral=True
        )

    # Botão 2: Modal de Mensagem
    @discord.ui.button(
        label="Editar Mensagem", style=discord.ButtonStyle.secondary, emoji="💬", row=0
    )
    async def btn_msg(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(MsgModal(self.guild_id))

    # Dropdown de Canal
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="Selecione o canal de anúncios...",
        channel_types=[discord.ChannelType.text],
        row=1,
    )
    async def select_channel(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        canal = select.values[0]
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}

        configs[self.guild_id]["canal_id"] = canal.id
        data_manager.save_knowledge("guild_configs", configs)

        await interaction.response.send_message(
            f"✅ Anúncios de nível serão enviados no canal {canal.mention}.",
            ephemeral=True,
        )

    # Dropdown de Cargo (Recompensa)
    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Adicionar Cargo como Recompensa...",
        row=2,
    )
    async def select_role(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        cargo = select.values[0]

        # Como o Select de Cargo não pede o nível junto, pedimos no chat após ele selecionar o cargo
        await interaction.response.send_message(
            f"Você selecionou o cargo **{cargo.name}**. Digite no chat agora em qual **Nível** o membro deve ganhar este cargo (ex: `10`):",
            ephemeral=True,
        )

        def check(m):
            return (
                m.author == interaction.user
                and m.channel == interaction.channel
                and m.content.isdigit()
            )

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            nivel_alvo = msg.content

            configs = data_manager.get_knowledge("guild_configs") or {}
            if self.guild_id not in configs:
                configs[self.guild_id] = {}
            if "roles" not in configs[self.guild_id]:
                configs[self.guild_id]["roles"] = {}

            configs[self.guild_id]["roles"][nivel_alvo] = cargo.id
            data_manager.save_knowledge("guild_configs", configs)

            await interaction.followup.send(
                f"✅ Feito! Quando alguém chegar no Nível {nivel_alvo}, ganhará o cargo {cargo.mention}.",
                ephemeral=True,
            )
            try:
                await msg.delete()
            except:
                pass  # Apaga a mensagem com o número do chat
        except:
            await interaction.followup.send(
                "⏳ Tempo esgotado para digitar o nível. Tente novamente.",
                ephemeral=True,
            )


# --- SISTEMA DE XP PASSIVO (O MOTOR) ---


class Niveis(commands.Cog):
    """Gerencia o ganho de XP por chat e recompensas de nível."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Niveis")
        self.cooldowns = {}  # Guarda quando a pessoa mandou a última mensagem

    @commands.hybrid_command(
        name="configxp",
        description="[Admin] Painel de configuração do sistema de Níveis.",
    )
    @commands.has_permissions(manage_guild=True)
    async def configxp(self, ctx: commands.Context):
        """Abre o painel visual de configurações para admins."""
        configs = data_manager.get_knowledge("guild_configs") or {}
        guild_id = str(ctx.guild.id)
        config_atual = configs.get(guild_id, {})

        estado = "🟢 Ligado" if config_atual.get("enabled", True) else "🔴 Desligado"
        canal_id = config_atual.get("canal_id")
        canal_txt = f"<#{canal_id}>" if canal_id else "No mesmo canal da mensagem"
        msg_txt = config_atual.get("mensagem", "🎉 Parabéns {user}! Nível **{level}**!")

        cargos = config_atual.get("roles", {})
        cargos_txt = (
            "\n".join([f"**Nv {lvl}**: <@&{r_id}>" for lvl, r_id in cargos.items()])
            if cargos
            else "Nenhum cargo configurado."
        )

        embed = discord.Embed(
            title="⚙️ Painel de Configuração: Níveis e XP", color=discord.Color.blue()
        )
        embed.add_field(name="Status do Sistema", value=estado, inline=True)
        embed.add_field(name="Canal de Anúncios", value=canal_txt, inline=True)
        embed.add_field(name="Mensagem Padrão", value=f"*{msg_txt}*", inline=False)
        embed.add_field(name="Recompensas (Cargos)", value=cargos_txt, inline=False)
        embed.set_footer(text="Use os menus abaixo para alterar as configurações.")

        view = ConfigXPView(ctx, self.bot)
        await ctx.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Ignora mensagens que são comandos da bot
        prefixos = await self.bot.get_prefix(message)
        if type(prefixos) == str:
            prefixos = [prefixos]
        if any(message.content.startswith(p) for p in prefixos):
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        # 1. Verifica se o sistema está ligado no servidor
        configs = data_manager.get_knowledge("guild_configs") or {}
        config_guild = configs.get(guild_id, {})
        if not config_guild.get("enabled", True):
            return

        # 2. Sistema de Cooldown (Ganha XP apenas a cada 60 segundos)
        agora = time.time()
        ultimo_xp = self.cooldowns.get(user_id, 0)

        if agora - ultimo_xp < 60:
            return  # Muito cedo para ganhar XP de novo (Evita spam)

        self.cooldowns[user_id] = agora

        # 3. Dá o XP e verifica Level Up
        xp_antigo = data_manager.get_user_data(user_id, "xp", 0)
        xp_ganho = random.randint(15, 25)  # Valor aleatório para dar dinamismo
        xp_novo = xp_antigo + xp_ganho

        data_manager.set_user_data(user_id, "xp", xp_novo)

        nivel_antigo = (xp_antigo // 1000) + 1
        nivel_novo = (xp_novo // 1000) + 1

        # 4. ACONTECEU UM LEVEL UP!
        if nivel_novo > nivel_antigo:
            # Puxa as configs do servidor
            msg_custom = config_guild.get(
                "mensagem", "🎉 Parabéns {user}! Você alcançou o nível **{level}**!"
            )
            texto_final = msg_custom.replace("{user}", message.author.mention).replace(
                "{level}", str(nivel_novo)
            )

            canal_id = config_guild.get("canal_id")
            canal_envio = (
                message.guild.get_channel(canal_id) if canal_id else message.channel
            )

            if canal_envio:
                try:
                    await canal_envio.send(texto_final)
                except:
                    pass

            # 5. Entrega de Cargos (Recompensas)
            roles_recompensa = config_guild.get("roles", {})
            str_nivel = str(nivel_novo)

            if str_nivel in roles_recompensa:
                cargo_id = roles_recompensa[str_nivel]
                cargo = message.guild.get_role(int(cargo_id))
                if cargo:
                    try:
                        await message.author.add_roles(
                            cargo, reason=f"Alcançou o nível {nivel_novo}"
                        )
                    except discord.Forbidden:
                        self.logger.warning(
                            f"Sem permissão para dar o cargo {cargo.name} no servidor {message.guild.name}."
                        )


async def setup(bot):
    await bot.add_cog(Niveis(bot))
