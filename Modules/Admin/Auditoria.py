import discord
from discord.ext import commands
import logging
from datetime import datetime

from Brain.Memory.DataManager import data_manager

# --- UI DE CONFIGURAÇÃO (PAINEL INTERATIVO) ---


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
    """Menu múltiplo que só tem efeito se o servidor estiver no Nível 6."""

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
                label="Configurações do Servidor",
                value="servidor",
                default=("servidor" in ativados_antes),
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
            max_values=5,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}
        if "auditoria" not in configs[self.guild_id]:
            configs[self.guild_id]["auditoria"] = {}

        # Guarda a lista do que o admin selecionou
        configs[self.guild_id]["auditoria"]["custom_flags"] = self.values
        data_manager.save_knowledge("guild_configs", configs)

        await interaction.response.send_message(
            "✅ Filtros personalizados salvos! (Lembre-se de ativar o Nível 6 no menu de Presets)",
            ephemeral=True,
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


# --- O MOTOR DE ESPIONAGEM ESCALONADO ---


class Auditoria(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Auditoria")

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
                name="Filtros Personalizados",
                value=", ".join(custom_flags).title() if custom_flags else "Nenhum",
                inline=False,
            )

        embed.set_footer(text="Use os menus abaixo para configurar seu servidor.")

        await ctx.send(embed=embed, view=AuditoriaConfigView(guild_id, custom_flags))

    async def _should_log(
        self, guild_id: int, event_level: int, flag_name: str
    ) -> tuple:
        """
        O Roteador Genial: Retorna (canal_id, booleano_se_deve_logar).
        Se for nível 1 a 5, compara os números. Se for 6, checa a flag.
        """
        configs = data_manager.get_knowledge("guild_configs") or {}
        config = configs.get(str(guild_id), {}).get("auditoria", {})

        canal_id = config.get("canal_id")
        if not canal_id:
            return None, False

        preset = config.get("preset", 1)

        if preset == 6:
            custom_flags = config.get("custom_flags", [])
            return canal_id, (flag_name in custom_flags)
        else:
            return canal_id, (preset >= event_level)

    async def enviar_log(
        self, guild: discord.Guild, canal_id: int, embed: discord.Embed
    ):
        canal = guild.get_channel(canal_id)
        if canal:
            try:
                await canal.send(embed=embed)
            except:
                pass

    # ==========================================
    # NÍVEL 1: MENSAGENS (Flag: "mensagens")
    # ==========================================

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        canal_id, pode_logar = await self._should_log(message.guild.id, 1, "mensagens")
        if not pode_logar:
            return

        embed = discord.Embed(
            title="🗑️ Mensagem Apagada",
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )
        embed.description = (
            f"**Autor:** {message.author.mention}\n**Canal:** {message.channel.mention}"
        )
        embed.add_field(
            name="Conteúdo", value=message.content[:1024] or "*Sem texto*", inline=False
        )
        await self.enviar_log(message.guild, canal_id, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        canal_id, pode_logar = await self._should_log(before.guild.id, 1, "mensagens")
        if not pode_logar:
            return

        embed = discord.Embed(
            title="✏️ Mensagem Editada",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        embed.description = (
            f"**Autor:** {before.author.mention} no canal {before.channel.mention}"
        )
        embed.add_field(
            name="Antes", value=before.content[:1024] or "Vazio", inline=False
        )
        embed.add_field(
            name="Depois", value=after.content[:1024] or "Vazio", inline=False
        )
        await self.enviar_log(before.guild, canal_id, embed)

    # ==========================================
    # NÍVEL 2: CARGOS DO SERVIDOR (Flag: "cargos")
    # ==========================================

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        canal_id, pode_logar = await self._should_log(role.guild.id, 2, "cargos")
        if not pode_logar:
            return
        embed = discord.Embed(
            title="🔰 Cargo Criado",
            description=f"O cargo **{role.name}** foi criado.",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        await self.enviar_log(role.guild, canal_id, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        canal_id, pode_logar = await self._should_log(role.guild.id, 2, "cargos")
        if not pode_logar:
            return
        embed = discord.Embed(
            title="🗑️ Cargo Deletado",
            description=f"O cargo **{role.name}** foi deletado.",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(),
        )
        await self.enviar_log(role.guild, canal_id, embed)

    # ==========================================
    # NÍVEL 3: SERVIDOR E BOT (Flag: "servidor")
    # ==========================================

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        canal_id, pode_logar = await self._should_log(after.id, 3, "servidor")
        if not pode_logar:
            return

        embed = discord.Embed(
            title="⚙️ Servidor Modificado",
            color=discord.Color.orange(),
            timestamp=datetime.now(),
        )
        if before.name != after.name:
            embed.add_field(
                name="Nome do Servidor",
                value=f"De: {before.name}\nPara: {after.name}",
                inline=False,
            )
        if before.icon != after.icon:
            embed.add_field(
                name="Ícone Alterado",
                value="O avatar do servidor foi modificado.",
                inline=False,
            )

        if (
            len(embed.fields) > 0
        ):  # Só envia se realmente achar uma alteração importante
            await self.enviar_log(after, canal_id, embed)

    # ==========================================
    # NÍVEL 4: USUÁRIOS (Flag: "usuarios")
    # ==========================================

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        canal_id, pode_logar = await self._should_log(after.guild.id, 4, "usuarios")
        if not pode_logar:
            return

        embed = discord.Embed(timestamp=datetime.now())
        enviar = False

        if before.nick != after.nick:
            embed.title = "🏷️ Apelido Modificado"
            embed.color = discord.Color.light_grey()
            embed.description = f"{after.mention} mudou o nickname."
            embed.add_field(name="Antes", value=before.nick or before.name, inline=True)
            embed.add_field(name="Depois", value=after.nick or after.name, inline=True)
            enviar = True

        elif before.roles != after.roles:
            embed.title = "🔰 Atualização de Cargos do Usuário"
            embed.color = discord.Color.purple()
            embed.description = f"{after.mention} teve cargos alterados."
            enviar = True

        # Discord.py recente dispara avatar de servidor aqui
        elif before.guild_avatar != after.guild_avatar:
            embed.title = "🖼️ Avatar do Servidor Modificado"
            embed.color = discord.Color.blurple()
            embed.description = (
                f"{after.mention} mudou a foto de perfil neste servidor."
            )
            enviar = True

        if enviar:
            await self.enviar_log(after.guild, canal_id, embed)

    # ==========================================
    # NÍVEL 5: VOZ E MAXIMO (Flag: "voz")
    # ==========================================

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return
        canal_id, pode_logar = await self._should_log(member.guild.id, 5, "voz")
        if not pode_logar:
            return

        if before.channel != after.channel:
            embed = discord.Embed(timestamp=datetime.now())
            if before.channel is None and after.channel is not None:
                embed.title, embed.color = "🎙️ Entrou no Canal", discord.Color.green()
                embed.description = (
                    f"{member.mention} conectou-se em {after.channel.mention}."
                )
            elif before.channel is not None and after.channel is None:
                embed.title, embed.color = "🔇 Saiu do Canal", discord.Color.red()
                embed.description = (
                    f"{member.mention} saiu de {before.channel.mention}."
                )
            elif before.channel is not None and after.channel is not None:
                embed.title, embed.color = "🔄 Trocou de Canal", discord.Color.gold()
                embed.description = f"{member.mention} mudou de {before.channel.mention} para {after.channel.mention}."

            await self.enviar_log(member.guild, canal_id, embed)


async def setup(bot):
    await bot.add_cog(Auditoria(bot))
