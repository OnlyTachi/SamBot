import discord
from discord.ext import commands
import logging

from Brain.Memory.DataManager import data_manager

# Importação dos Handlers (usando try/except para não quebrar enquanto construímos)
try:
    from ._audit_msg import MsgAuditHandler
    from ._audit_cargo import CargoAuditHandler
    from ._audit_voz import VozAuditHandler
    from ._audit_membro import MembroAuditHandler
except ImportError as e:
    logging.getLogger("SamBot.Auditoria").warning(
        f"⚠️ Handlers de Auditoria pendentes: {e}"
    )

# --- UI DE CONFIGURAÇÃO (O PAINEL VISUAL - INTACTO) ---


class AuditoriaPresetSelect(discord.ui.Select):
    def __init__(self, guild_id):
        self.guild_id = guild_id
        options = [
            discord.SelectOption(
                label="Nível 1: Básico",
                value="1",
                description="Mensagens (Apagadas/Editadas)",
                emoji="🟢",
            ),
            discord.SelectOption(
                label="Nível 2: Cargos",
                value="2",
                description="Nível 1 + Edição/Criação de Cargos",
                emoji="🟡",
            ),
            discord.SelectOption(
                label="Nível 3: Servidor",
                value="3",
                description="Nível 2 + Modificações no Servidor e Bot",
                emoji="🟠",
            ),
            discord.SelectOption(
                label="Nível 4: Usuários",
                value="4",
                description="Nível 3 + Modificações de Usuários (Nick, Foto)",
                emoji="🔴",
            ),
            discord.SelectOption(
                label="Nível 5: Máximo",
                value="5",
                description="Nível 4 + Canais de Voz e Entradas/Saídas",
                emoji="🔥",
            ),
            discord.SelectOption(
                label="Nível 6: Personalizado",
                value="6",
                description="Escolha manualmente no menu abaixo.",
                emoji="⚙️",
            ),
        ]
        super().__init__(
            placeholder="Selecione a intensidade dos Logs...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}
        if "auditoria" not in configs[self.guild_id]:
            configs[self.guild_id]["auditoria"] = {}

        nivel = int(self.values[0])
        configs[self.guild_id]["auditoria"]["preset"] = nivel
        data_manager.save_knowledge("guild_configs", configs)
        await interaction.response.send_message(
            f"✅ Preset de Auditoria atualizado para o **Nível {nivel}**.",
            ephemeral=True,
        )


class AuditoriaCustomSelect(discord.ui.Select):
    def __init__(self, guild_id, ativados_antes):
        self.guild_id = guild_id
        options = [
            discord.SelectOption(
                label="Mensagens",
                value="mensagens",
                default=("mensagens" in ativados_antes),
            ),
            discord.SelectOption(
                label="Cargos do Servidor",
                value="cargos",
                default=("cargos" in ativados_antes),
            ),
            discord.SelectOption(
                label="Atualizações de Usuário",
                value="usuarios",
                default=("usuarios" in ativados_antes),
            ),
            discord.SelectOption(
                label="Canais de Voz (Máximo)",
                value="voz",
                default=("voz" in ativados_antes),
            ),
        ]
        super().__init__(
            placeholder="[Apenas Nível 6] Marque os logs que deseja...",
            min_values=0,
            max_values=4,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}
        if "auditoria" not in configs[self.guild_id]:
            configs[self.guild_id]["auditoria"] = {}

        configs[self.guild_id]["auditoria"]["custom_flags"] = self.values
        data_manager.save_knowledge("guild_configs", configs)
        await interaction.response.send_message(
            "✅ Filtros personalizados salvos!", ephemeral=True
        )


class AuditoriaCanalSelect(discord.ui.ChannelSelect):
    def __init__(self, guild_id):
        self.guild_id = guild_id
        super().__init__(
            placeholder="Selecione o canal para os Logs...",
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}
        if "auditoria" not in configs[self.guild_id]:
            configs[self.guild_id]["auditoria"] = {}

        canal = self.values[0]
        configs[self.guild_id]["auditoria"]["canal_id"] = canal.id
        data_manager.save_knowledge("guild_configs", configs)
        await interaction.response.send_message(
            f"✅ Logs configurados para o canal {canal.mention}.", ephemeral=True
        )


class AuditoriaConfigView(discord.ui.View):
    def __init__(self, guild_id, custom_flags):
        super().__init__(timeout=180)
        self.add_item(AuditoriaCanalSelect(guild_id))
        self.add_item(AuditoriaPresetSelect(guild_id))
        self.add_item(AuditoriaCustomSelect(guild_id, custom_flags))


# --- O MOTOR DO ORQUESTRADOR ---


class AuditoriaCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Auditoria")

        # Inicialização Dinâmica dos Handlers
        self.msg_handler = (
            globals().get("MsgAuditHandler")()
            if "MsgAuditHandler" in globals()
            else None
        )
        self.cargo_handler = (
            globals().get("CargoAuditHandler")()
            if "CargoAuditHandler" in globals()
            else None
        )
        self.voz_handler = (
            globals().get("VozAuditHandler")()
            if "VozAuditHandler" in globals()
            else None
        )
        self.membro_handler = (
            globals().get("MembroAuditHandler")()
            if "MembroAuditHandler" in globals()
            else None
        )

    @commands.hybrid_command(
        name="configauditoria",
        aliases=["logs"],
        description="[Admin] Painel avançado de Auditoria.",
    )
    @commands.has_permissions(manage_guild=True)
    async def configauditoria(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        configs = data_manager.get_knowledge("guild_configs") or {}
        audit_config = configs.get(guild_id, {}).get("auditoria", {})

        canal_id = audit_config.get("canal_id")
        preset = audit_config.get("preset", 1)
        custom_flags = audit_config.get("custom_flags", [])

        canal_txt = f"<#{canal_id}>" if canal_id else "⚠️ Não configurado"

        embed = discord.Embed(
            title="🕵️ Central de Auditoria e Logs", color=discord.Color.dark_grey()
        )
        embed.add_field(name="Canal de Envio", value=canal_txt, inline=True)
        embed.add_field(name="Preset Ativo", value=f"Nível {preset}", inline=True)

        if preset == 6:
            embed.add_field(
                name="Filtros Ativos",
                value=", ".join(custom_flags).title() if custom_flags else "Nenhum",
                inline=False,
            )

        await ctx.send(embed=embed, view=AuditoriaConfigView(guild_id, custom_flags))

    async def _should_log(
        self, guild_id: int, event_level: int, flag_name: str
    ) -> tuple:
        configs = data_manager.get_knowledge("guild_configs") or {}
        config = configs.get(str(guild_id), {}).get("auditoria", {})
        canal_id = config.get("canal_id")

        if not canal_id:
            return None, False
        preset = config.get("preset", 1)

        if preset == 6:
            return canal_id, (flag_name in config.get("custom_flags", []))
        return canal_id, (preset >= event_level)

    async def enviar_log(
        self, guild: discord.Guild, canal_id: int, embed: discord.Embed
    ):
        canal = guild.get_channel(canal_id)
        if canal:
            try:
                await canal.send(embed=embed)
            except discord.Forbidden:
                pass

    # ================= EVENTOS DELEGAÇÃO =================

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        canal_id, pode = await self._should_log(message.guild.id, 1, "mensagens")
        if pode and self.msg_handler:
            # Pede para o especialista criar o Embed e depois o envia
            embed = await self.msg_handler.on_delete(message)
            if embed:
                await self.enviar_log(message.guild, canal_id, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        canal_id, pode = await self._should_log(before.guild.id, 1, "mensagens")
        if pode and self.msg_handler:
            embed = await self.msg_handler.on_edit(before, after)
            if embed:
                await self.enviar_log(before.guild, canal_id, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        canal_id, pode = await self._should_log(role.guild.id, 2, "cargos")
        if pode and self.cargo_handler:
            embed = await self.cargo_handler.on_create(role)
            if embed:
                await self.enviar_log(role.guild, canal_id, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        canal_id, pode = await self._should_log(role.guild.id, 2, "cargos")
        if pode and self.cargo_handler:
            embed = await self.cargo_handler.on_delete(role)
            if embed:
                await self.enviar_log(role.guild, canal_id, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        canal_id, pode = await self._should_log(after.guild.id, 4, "usuarios")
        if pode and self.membro_handler:
            embed = await self.membro_handler.on_update(before, after)
            if embed:
                await self.enviar_log(after.guild, canal_id, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return
        canal_id, pode = await self._should_log(member.guild.id, 5, "voz")
        if pode and self.voz_handler:
            embed = await self.voz_handler.on_update(member, before, after)
            if embed:
                await self.enviar_log(member.guild, canal_id, embed)


async def setup(bot):
    await bot.add_cog(AuditoriaCore(bot))
