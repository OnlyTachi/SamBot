from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands
from discord.http import Route
from discord.utils import format_dt

MESES_PTBR = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

FLAGS_TRADUCAO = {
    "staff": "👨‍💼 Staff do Discord",
    "partner": "🤝 Parceiro",
    "hypesquad": "🎉 Eventos HypeSquad",
    "bug_hunter": "🐛 Caçador de Bugs",
    "hypesquad_bravery": "🛡️ HypeSquad Bravery",
    "hypesquad_brilliance": "✨ HypeSquad Brilliance",
    "hypesquad_balance": "⚖️ HypeSquad Balance",
    "early_supporter": "💎 Apoiador Inicial",
    "bug_hunter_level_2": "🐛 Caçador de Bugs Nível 2",
    "verified_bot_developer": "🤖 Desenvolvedor de Bot Verificado",
    "discord_certified_moderator": "🛡️ Moderador Certificado",
    "active_developer": "💻 Desenvolvedor Ativo",
}

TRADUCAO_PERMISSOES = {
    "administrator": "Administrador",
    "view_audit_log": "Ver Registro de Auditoria",
    "manage_guild": "Gerenciar Servidor",
    "manage_roles": "Gerenciar Cargos",
    "manage_channels": "Gerenciar Canais",
    "kick_members": "Expulsar Membros",
    "ban_members": "Banir Membros",
    "create_instant_invite": "Criar Convite",
    "change_nickname": "Alterar Apelido",
    "manage_nicknames": "Gerenciar Apelidos",
    "manage_emojis": "Gerenciar Emojis e Figurinhas",
    "manage_webhooks": "Gerenciar Webhooks",
    "view_channel": "Ver Canais",
    "send_messages": "Enviar Mensagens",
    "send_messages_in_threads": "Enviar Mensagens em Tópicos",
    "create_public_threads": "Criar Tópicos Públicos",
    "create_private_threads": "Criar Tópicos Privados",
    "embed_links": "Inserir Links",
    "attach_files": "Anexar Arquivos",
    "read_message_history": "Ver Histórico de Mensagens",
    "mention_everyone": "Mencionar @everyone e @here",
    "use_external_emojis": "Usar Emojis Externos",
    "add_reactions": "Adicionar Reações",
    "connect": "Conectar no Canal de Voz",
    "speak": "Falar no Canal de Voz",
    "mute_members": "Silenciar Membros",
    "deafen_members": "Ensurdecer Membros",
    "move_members": "Mover Membros",
    "manage_messages": "Gerenciar Mensagens",
    "moderate_members": "Moderar Membros (Castigo)",
}

APP_FLAG_GATEWAY_PRESENCE = 1 << 12
APP_FLAG_GATEWAY_PRESENCE_LIMITED = 1 << 13
APP_FLAG_GATEWAY_GUILD_MEMBERS = 1 << 14
APP_FLAG_GATEWAY_GUILD_MEMBERS_LIMITED = 1 << 15
APP_FLAG_GATEWAY_MESSAGE_CONTENT = 1 << 18
APP_FLAG_GATEWAY_MESSAGE_CONTENT_LIMITED = 1 << 19


def formatar_data_ptbr(data: datetime) -> str:
    mes = MESES_PTBR.get(data.month, "")
    return f"{data.day} de {mes} de {data.year} às {data.strftime('%H:%M')}"


def calcular_tempo_passado(data: datetime) -> str:
    agora = datetime.now(timezone.utc)
    delta = agora - data
    dias = delta.days
    anos = dias // 365
    meses = (dias % 365) // 30

    if anos > 0:
        return f"há {anos} ano{'s' if anos > 1 else ''}"
    if meses > 0:
        return f"há {meses} mês{'es' if meses > 1 else ''}"
    if dias > 0:
        return f"há {dias} dia{'s' if dias > 1 else ''}"
    horas = delta.seconds // 3600
    if horas > 0:
        return f"há {horas} hora{'s' if horas > 1 else ''}"
    minutos = (delta.seconds % 3600) // 60
    return f"há {max(1, minutos)} minuto{'s' if minutos > 1 else ''}"


class PainelUsuarioView(discord.ui.View):
    def __init__(
        self,
        target_user: discord.User | discord.Member,
        command_author: discord.User | discord.Member,
        user_completo: discord.User,
    ):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.command_author = command_author
        self.user_completo = user_completo

        # Desabilita botões específicos de acordo com o contexto do alvo
        if not isinstance(target_user, discord.Member) or not target_user.guild_avatar:
            self.btn_guild_avatar.disabled = True

        if not getattr(user_completo, "banner", None):
            self.btn_banner.disabled = True

        if not isinstance(target_user, discord.Member):
            self.btn_permissoes.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.command_author.id:
            await interaction.response.send_message(
                "❌ Apenas quem usou o comando pode interagir com os botões!",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Avatar Global", style=discord.ButtonStyle.secondary, emoji="🌐"
    )
    async def btn_global_avatar(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        url_avatar = (
            self.target_user.avatar.url
            if self.target_user.avatar
            else self.target_user.default_avatar.url
        )
        embed = discord.Embed(
            title=f"🌐 Avatar Global de {self.target_user.name}",
            color=discord.Color.from_rgb(88, 101, 242),
        )
        embed.set_image(url=url_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Avatar Servidor", style=discord.ButtonStyle.secondary, emoji="🏠"
    )
    async def btn_guild_avatar(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if (
            isinstance(self.target_user, discord.Member)
            and self.target_user.guild_avatar
        ):
            embed = discord.Embed(
                title=f"🏠 Avatar no Servidor de {self.target_user.display_name}",
                color=discord.Color.from_rgb(88, 101, 242),
            )
            embed.set_image(url=self.target_user.guild_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ O usuário não possui avatar específico neste servidor.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Ver Banner", style=discord.ButtonStyle.secondary, emoji="🎨"
    )
    async def btn_banner(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.user_completo.banner:
            embed = discord.Embed(
                title=f"🎨 Banner de {self.target_user.display_name}",
                color=discord.Color.from_rgb(88, 101, 242),
            )
            embed.set_image(url=self.user_completo.banner.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Este usuário não possui um banner configurado.", ephemeral=True
            )

    @discord.ui.button(
        label="Permissões", style=discord.ButtonStyle.primary, emoji="🛡️"
    )
    async def btn_permissoes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not isinstance(self.target_user, discord.Member):
            await interaction.response.send_message(
                "❌ O usuário não está neste servidor.", ephemeral=True
            )
            return

        perms = self.target_user.guild_permissions
        if perms.administrator:
            texto_perms = "👑 **Administrador** (Possui controle total no servidor)"
        else:
            permissoes_ativas = [
                f"✅ {TRADUCAO_PERMISSOES.get(nome, nome.replace('_', ' ').title())}"
                for nome, valor in perms
                if valor and nome in TRADUCAO_PERMISSOES
            ]
            texto_perms = (
                "\n".join(permissoes_ativas)
                if permissoes_ativas
                else "*Nenhuma permissão especial configurada.*"
            )

        embed = discord.Embed(
            title=f"🛡️ Permissões de {self.target_user.display_name}",
            description=texto_perms,
            color=discord.Color.from_rgb(88, 101, 242),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class UserProfile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="userinfo",
        aliases=["user", "uinfo"],
        description="Mostra informações detalhadas sobre uma conta, membro ou bot.",
    )
    @app_commands.describe(usuario="Usuário, menção ou ID para inspecionar")
    async def userinfo(
        self, ctx: commands.Context, usuario: discord.User | discord.Member = None
    ):
        await ctx.defer()

        target_user = usuario or ctx.author

        if ctx.guild and not isinstance(target_user, discord.Member):
            membro = ctx.guild.get_member(target_user.id)
            if membro:
                target_user = membro

        try:
            user_completo = await self.bot.fetch_user(target_user.id)
        except discord.HTTPException:
            user_completo = target_user

        cor_embed = discord.Color.from_rgb(88, 101, 242)

        # =====================================================================
        # 1. EMBED: Informações sobre o Usuário
        # =====================================================================
        embed_user = discord.Embed(title="Informações sobre o Usuário", color=cor_embed)
        embed_user.description = f"### **{target_user.name}**"

        flags_badges = [
            FLAGS_TRADUCAO.get(flag[0], flag[0].title())
            for flag in target_user.public_flags
            if flag[1]
        ]
        if target_user.bot:
            flags_badges.insert(0, "🤖 `BOT`")

        embed_user.add_field(
            name="🧒 Insígnias",
            value=" • ".join(flags_badges) if flags_badges else "Nenhuma",
            inline=False,
        )
        embed_user.add_field(
            name="🆔 ID do Discord", value=f"`{target_user.id}`", inline=True
        )

        discriminator = getattr(target_user, "discriminator", "0")
        tag_formatada = (
            f"`{target_user.name}#{discriminator}`"
            if discriminator and discriminator != "0"
            else f"`@{target_user.name}`"
        )
        embed_user.add_field(name="🏷️ Tag do Discord", value=tag_formatada, inline=True)

        criado_em = target_user.created_at
        embed_user.add_field(
            name="📅 Data de Criação da Conta",
            value=f"{formatar_data_ptbr(criado_em)} `({calcular_tempo_passado(criado_em)})`",
            inline=False,
        )
        embed_user.set_thumbnail(url=target_user.display_avatar.url)

        fila_embeds = [embed_user]

        # =====================================================================
        # 2. EMBED: Informações sobre o Membro (se estiver no servidor)
        # =====================================================================
        if isinstance(target_user, discord.Member) and ctx.guild:
            embed_member = discord.Embed(
                title="Informações sobre o Membro", color=cor_embed
            )
            embed_member.description = f"### **{target_user.display_name}**"

            if target_user.joined_at:
                embed_member.add_field(
                    name="📥 Data de Entrada no Servidor",
                    value=f"{formatar_data_ptbr(target_user.joined_at)} `({calcular_tempo_passado(target_user.joined_at)})`",
                    inline=False,
                )

            top_role = (
                target_user.top_role.mention
                if target_user.top_role and target_user.top_role.name != "@everyone"
                else "Nenhum cargo"
            )
            embed_member.add_field(name="📌 Maior Cargo", value=top_role, inline=False)

            curiosidades_member = []
            if target_user.timed_out_until:
                curiosidades_member.append(
                    f"🔇 De Castigo até {format_dt(target_user.timed_out_until, style='R')}"
                )

            if target_user.premium_since:
                curiosidades_member.append(
                    f"💎 Impulsionando {format_dt(target_user.premium_since, style='R')}"
                )

            embed_member.add_field(
                name="💡 Curiosidades Interessantes",
                value="\n".join(curiosidades_member),
                inline=False,
            )
            embed_member.set_thumbnail(url=target_user.display_avatar.url)
            fila_embeds.append(embed_member)

        # =====================================================================
        # 3. EMBED: Informações sobre o Aplicativo (se for BOT)
        # =====================================================================
        if target_user.bot:
            app_data = None
            try:
                route = Route("GET", f"/applications/{target_user.id}/rpc")
                app_data = await self.bot.http.request(route)
            except discord.HTTPException:
                pass

            embed_app = discord.Embed(
                title="Informações sobre o Aplicativo", color=cor_embed
            )
            embed_app.set_thumbnail(url=target_user.display_avatar.url)

            if app_data:
                app_name = app_data.get("name", target_user.name)
                app_desc = (
                    app_data.get("description", "").strip()
                    or "*Sem descrição definida.*"
                )
                embed_app.description = f"### **{app_name}**\n{app_desc}"

                guild_id = app_data.get("guild_id")
                if guild_id:
                    embed_app.add_field(
                        name="🆔 ID do Servidor de Suporte",
                        value=f"`{guild_id}`",
                        inline=False,
                    )

                is_public = app_data.get("bot_public", True)
                requires_code_grant = app_data.get("bot_require_code_grant", False)
                uses_http_interactions = bool(app_data.get("interactions_endpoint_url"))
                app_flags = app_data.get("flags", 0)

                curiosidades_bot = [
                    f"{'✅' if is_public else '❌'} Público",
                    f"{'✅' if requires_code_grant else '❌'} Requer Código OAuth2",
                    f"{'✅' if uses_http_interactions else '❌'} Usa Interações via HTTP",
                    f"{'✅' if app_flags & (APP_FLAG_GATEWAY_PRESENCE | APP_FLAG_GATEWAY_PRESENCE_LIMITED) else '❌'} Intent de Presenças",
                    f"{'✅' if app_flags & (APP_FLAG_GATEWAY_GUILD_MEMBERS | APP_FLAG_GATEWAY_GUILD_MEMBERS_LIMITED) else '❌'} Intent de Membros",
                    f"{'✅' if app_flags & (APP_FLAG_GATEWAY_MESSAGE_CONTENT | APP_FLAG_GATEWAY_MESSAGE_CONTENT_LIMITED) else '❌'} Intent de Conteúdo de Mensagens",
                ]
                embed_app.add_field(
                    name="⚙️ Configurações da Aplicação",
                    value="\n".join(curiosidades_bot),
                    inline=False,
                )

                public_key = app_data.get("verify_key")
                if public_key:
                    embed_app.add_field(
                        name="💻 Chave Pública de Verificação de Requisições HTTP",
                        value=f"```{public_key}```",
                        inline=False,
                    )
            else:
                embed_app.description = (
                    f"### **{target_user.name}**\n*Dados da aplicação indisponíveis.*"
                )

            fila_embeds.append(embed_app)

        # =====================================================================
        # ENVIO INDIVIDUAL: Garante que os botões fiquem NO ÚLTIMO embed
        # =====================================================================
        view = PainelUsuarioView(
            target_user=target_user,
            command_author=ctx.author,
            user_completo=user_completo,
        )

        total_embeds = len(fila_embeds)
        for index, embed in enumerate(fila_embeds):
            eh_o_ultimo = index == total_embeds - 1

            if index == 0:
                if eh_o_ultimo:
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send(embed=embed)
            else:
                if eh_o_ultimo:
                    await ctx.channel.send(embed=embed, view=view)
                else:
                    await ctx.channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(UserProfile(bot))
