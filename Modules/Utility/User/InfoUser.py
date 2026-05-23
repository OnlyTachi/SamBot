import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import format_dt

# Dicionário para traduzir as permissões do Discord para Português
PERMISSOES_TRADUCAO = {
    "administrator": "Administrador",
    "manage_guild": "Gerenciar servidor",
    "manage_channels": "Gerenciar canais",
    "manage_roles": "Gerenciar cargos",
    "manage_webhooks": "Gerenciar webhooks",
    "manage_expressions": "Gerenciar expressões",
    "manage_events": "Gerenciar eventos",
    "kick_members": "Expulsar membros",
    "ban_members": "Banir membros",
    "manage_nicknames": "Gerenciar apelidos",
    "moderate_members": "Membros de castigo",
    "view_audit_log": "Ver registro de auditoria",
    "view_guild_insights": "Ver desempenho do servidor",
    "create_instant_invite": "Criar um convite instantâneo",
    "change_nickname": "Mudar apelido",
    "add_reactions": "Adicionar reações",
    "send_messages": "Enviar mensagens",
    "send_tts_messages": "Enviar mensagens em TTS",
    "manage_messages": "Gerenciar mensagens",
    "embed_links": "Inserir links",
    "attach_files": "Anexar arquivos",
    "read_message_history": "Ler histórico de mensagem",
    "mention_everyone": "Mencionar todos",
    "use_external_emojis": "Usar emojis externos",
    "use_application_commands": "Usar comandos de aplicativo",
    "use_external_stickers": "Usar figurinhas externas",
    "send_voice_messages": "Enviar mensagens de voz",
    "create_polls": "Criar Enquetes",
    "use_external_apps": "Usar Aplicativos Externos",
    "manage_threads": "Gerenciar threads",
    "create_public_threads": "Criar threads públicas",
    "create_private_threads": "Criar threads privadas",
    "send_messages_in_threads": "Enviar mensagens em threads",
    "priority_speaker": "Voz prioritária",
    "stream": "Vídeo",
    "connect": "Conectar",
    "speak": "Falar",
    "mute_members": "Silenciar membros",
    "deafen_members": "Ensurdecer membros",
    "move_members": "Mover membros",
    "use_voice_activation": "Usar detecção de voz",
    "use_soundboard": "Usar efeitos sonoros",
    "use_external_sounds": "Usar sons externos",
    "request_to_speak": "Pedir para falar",
    "view_channel": "Ver canais",
    "send_polls": "Criar Enquetes",
}

# Dicionário para Insígnias (Badges) do Discord
FLAGS_TRADUCAO = {
    "staff": "🛠️ Staff do Discord",
    "partner": "🤝 Parceiro",
    "hypesquad": "🎊 Eventos HypeSquad",
    "bug_hunter": "🐛 Caçador de Bugs",
    "hypesquad_bravery": "🟣 HypeSquad Bravery",
    "hypesquad_brilliance": "🔴 HypeSquad Brilliance",
    "hypesquad_balance": "🟢 HypeSquad Balance",
    "early_supporter": "💎 Apoiador Inicial",
    "bug_hunter_level_2": "🐛 Caçador de Bugs Nível 2",
    "verified_bot_developer": "⚙️ Desenvolvedor de Bot Verificado",
    "discord_certified_moderator": "🛡️ Moderador Certificado",
    "active_developer": "💻 Desenvolvedor Ativo",
}


class UserInfoView(discord.ui.View):
    def __init__(self, target_user: discord.Member, command_author: discord.Member):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.command_author = command_author

    # Trava os botões apenas para quem executou o comando
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.command_author:
            await interaction.response.send_message(
                "❌ Apenas quem usou o comando pode interagir com estes botões! Boboca",
                ephemeral=True,
            )
            return False
        return True

    # Botão 1: Permissões e Cargos (Visível apenas para o executor)
    @discord.ui.button(
        label="Permissões e Cargos",
        style=discord.ButtonStyle.primary,
        custom_id="btn_perms",
    )
    async def btn_perms(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        perms = []
        for perm_name, value in self.target_user.guild_permissions:
            if value:  # Se o utilizador tiver a permissão ativa
                texto_traduzido = PERMISSOES_TRADUCAO.get(
                    perm_name, perm_name.replace("_", " ").title()
                )
                perms.append(texto_traduzido)

        if self.target_user.guild_permissions.administrator:
            perms_text = "👑 **Administrador** (Possui todas as permissões)"
        else:
            perms_text = ", ".join(perms) if perms else "Nenhuma permissão especial."

            if len(perms_text) > 1010:
                perms_text = perms_text[:1000] + "... e outras."

        roles = [
            role.mention
            for role in reversed(self.target_user.roles)
            if role.name != "@everyone"
        ]
        roles_text = ", ".join(roles) if roles else "Nenhum cargo."

        if len(roles_text) > 1010:
            roles_text = roles_text[:1000] + "... e outros cargos."

        embed = discord.Embed(color=self.target_user.color or 0x5865F2)
        embed.add_field(name="😇 Permissões", value=perms_text, inline=False)
        embed.add_field(name="😎 Cargos", value=roles_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Botão 2: Avatar (Visível apenas para o executor)
    @discord.ui.button(
        label="Ver Avatar e Detalhes",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_avatar",
    )
    async def btn_avatar(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = discord.Embed(
            title=f"Avatar de {self.target_user.display_name}",
            color=self.target_user.color or 0x5865F2,
        )
        embed.set_image(url=self.target_user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class UserProfile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. Comando principal do grupo transformado em Embed
    @commands.hybrid_group(
        name="user",
        invoke_without_command=True,
        description="Comandos relacionados ao perfil de usuários",
    )
    async def grupo_user(self, ctx: commands.Context):
        embed = discord.Embed(
            title="ℹ️ Opções disponíveis",
            description="Selecione um dos comandos abaixo para interagir com o perfil:",
            color=0x5865F2,
        )
        embed.add_field(
            name="`/user info`",
            value="Informações detalhadas sobre a conta e o membro.",
            inline=False,
        )
        embed.add_field(
            name="`/user avatar`",
            value="Mostra o avatar de perfil no servidor e global.",
            inline=False,
        )
        embed.add_field(
            name="`/user banner`", value="Mostra o banner do perfil.", inline=False
        )
        embed.set_footer(
            text=f"Requisitado por {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url,
        )

        await ctx.send(embed=embed)

    # 2. Comando Avatar (Híbrido)
    @grupo_user.command(
        name="avatar", description="Mostra o avatar do seu perfil ou de outro usuário."
    )
    @app_commands.describe(
        usuario="O usuário que deseja ver o avatar (deixe vazio para ver o seu)"
    )
    async def avatar(self, ctx: commands.Context, usuario: discord.Member = None):
        usuario = usuario or ctx.author
        embed = discord.Embed(
            title=f"🖼️ Avatar de {usuario.display_name}", color=usuario.color
        )
        avatar_url = usuario.display_avatar.url
        embed.set_image(url=avatar_url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Link Direto", url=avatar_url))

        await ctx.send(embed=embed, view=view)

    # 3. Comando Banner (Híbrido)
    @grupo_user.command(
        name="banner", description="Mostra o banner do seu perfil ou de outro usuário."
    )
    @app_commands.describe(
        usuario="O usuário que deseja ver o banner (deixe vazio para ver o seu)"
    )
    async def banner(self, ctx: commands.Context, usuario: discord.Member = None):
        usuario = usuario or ctx.author
        fetched_user = await self.bot.fetch_user(usuario.id)

        if not fetched_user.banner:
            return await ctx.send(
                f"❌ {usuario.mention} não possui um banner configurado!",
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"🎑 Banner de {fetched_user.display_name}",
            color=fetched_user.accent_color or discord.Color.blurple(),
        )
        embed.set_image(url=fetched_user.banner.url)

        await ctx.send(embed=embed)

    # 4. Comando Info reestruturado com formato de 2 Embeds
    @grupo_user.command(
        name="info", description="Mostra informações detalhadas sobre a conta."
    )
    @app_commands.describe(
        usuario="O usuário que deseja ver as informações (deixe vazio para ver o seu)"
    )
    @commands.guild_only()
    async def info(self, ctx: commands.Context, usuario: discord.Member = None):
        user = usuario or ctx.author

        # Pega as insígnias/badges da conta do usuário
        flags = [flag[0] for flag in user.public_flags if flag[1]]
        badges_str = " ".join(
            [FLAGS_TRADUCAO.get(f, f.replace("_", " ").title()) for f in flags]
        )
        if not badges_str:
            badges_str = "Nenhuma"

        # Embed 1: Conta Discord (Informações Globais)
        embed_user = discord.Embed(
            title="Informações sobre o Usuário",
            description=f"**{user.name}**",
            color=user.color or 0x5865F2,
        )
        embed_user.add_field(name="😃 Insígnias", value=badges_str, inline=False)
        embed_user.add_field(name="🆔 ID do Discord", value=str(user.id), inline=False)
        embed_user.add_field(
            name="🏷️ Tag do Discord", value=f"{user.mention}", inline=False
        )

        created_dt = f"{format_dt(user.created_at, style='F')} ({format_dt(user.created_at, style='R')})"
        embed_user.add_field(
            name="🗓️ Data de Criação da Conta", value=created_dt, inline=False
        )
        embed_user.set_thumbnail(url=user.display_avatar.url)

        # Embed 2: Dados no Servidor Específico
        embed_member = discord.Embed(
            title="Informações sobre o Membro",
            description=f"**{user.display_name}**",
            color=user.color or 0x5865F2,
        )

        if user.joined_at:
            joined_dt = f"{format_dt(user.joined_at, style='F')} ({format_dt(user.joined_at, style='R')})"
            embed_member.add_field(
                name="🗓️ Data de Entrada no Servidor", value=joined_dt, inline=False
            )

        top_role = (
            user.top_role.mention
            if user.top_role and user.top_role.name != "@everyone"
            else "Nenhum cargo"
        )
        embed_member.add_field(name="😎 Maior cargo", value=top_role, inline=False)

        # Checando fatos curiosos
        curiosidades = []

        if user.timed_out_until:
            curiosidades.append("❌ Castigado (De castigo/mutado no momento)")

        if user.premium_since:
            curiosidades.append(
                f"✨ Impulsionando o servidor desde {format_dt(user.premium_since, style='R')}"
            )

        if user.bot:
            curiosidades.append("🤖 É um aplicativo/bot")

        embed_member.add_field(
            name="⚡ Curiosidades Interessantes",
            value="\n".join(curiosidades),
            inline=False,
        )

        # Renderiza a View (Os botões que enviam info privada)
        view = UserInfoView(target_user=user, command_author=ctx.author)

        # Envia os dois embeds de uma só vez
        await ctx.send(embeds=[embed_user, embed_member], view=view)


async def setup(bot):
    await bot.add_cog(UserProfile(bot))
