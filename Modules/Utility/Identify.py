import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import format_dt

class Identity(commands.Cog):
    def __init__(self, bot):
        """Comandos relacionados a usuários e servidores."""
        self.bot = bot
        self.emoji = "👤"

    # --- Comandos de Usuário ---

    @commands.hybrid_command(name="avatar", description="Mostra o avatar de um usuário.")
    @app_commands.describe(user="O usuário para ver o avatar (padrão: você)")
    async def avatar(self, ctx: commands.Context, user: discord.Member = None):
        """Exibe o avatar em alta resolução de um usuário."""
        user = user or ctx.author
        
        embed = discord.Embed(title=f"Avatar de {user.name}", color=user.color)
        embed.set_image(url=user.display_avatar.url)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Link Direto", url=user.display_avatar.url))
        
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="userinfo", description="Mostra informações detalhadas sobre um usuário.")
    @app_commands.describe(user="O usuário para ver as informações")
    async def userinfo(self, ctx: commands.Context, user: discord.Member = None):
        """Exibe detalhes da conta do usuário e do membro no servidor."""
        user = user or ctx.author

        embed_user = discord.Embed(
            title="Informações sobre o Usuário",
            description=f"👤 {user.mention} **{user.name}**",
            color=0x5865F2 
        )
        
        # Identificadores
        embed_user.add_field(
            name="🆔 ID do Discord", 
            value=f"`{user.id}`", 
            inline=True
        )
        embed_user.add_field(
            name="🏷️ Tag do Discord", 
            value=f"`@{user.name}`", 
            inline=True
        )
        
        created_at_str = format_dt(user.created_at, style="f")
        created_at_rel = format_dt(user.created_at, style="R")
        embed_user.add_field(
            name="🗓️ Data de Criação da Conta",
            value=f"{created_at_str} ({created_at_rel})",
            inline=False
        )
        
        embed_user.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)

        embed_member = discord.Embed(
            title="Informações sobre o Membro",
            description=f"**{user.display_name}**",
            color=0xED4245
        )
        
        joined_at_str = format_dt(user.joined_at, style="f")
        joined_at_rel = format_dt(user.joined_at, style="R")
        embed_member.add_field(
            name="🗓️ Data de Entrada no Servidor",
            value=f"{joined_at_str} ({joined_at_rel})",
            inline=True
        )
    
        embed_member.add_field(
            name="🎭 Maior cargo",
            value=user.top_role.mention if user.top_role else "@everyone",
            inline=True
        )
        screening_status = "✅ Completou" if not user.pending else "❌ Não completou"
        timeout_status = "✅ Sim" if user.timed_out_until else "❌ Não"

        curiosidades = (
            f"✅ **Completou a Avaliação de Associação:** {screening_status}\n"
            f"🚫 **Castigado:** {timeout_status}"
        )
        embed_member.add_field(name="🙋 Curiosidades Interessantes", value=curiosidades, inline=False)
        
        embed_member.set_thumbnail(url=user.display_avatar.url)

        # --- BOTÕES (VIEW) ---
        class UserInfoView(discord.ui.View):
            def __init__(self, target_user: discord.Member):
                super().__init__()
                self.target_user = target_user
                
                # Botão Avatar Global
                btn_global = discord.ui.Button(
                    label="Ver o avatar global do usuário",
                    style=discord.ButtonStyle.blurple,
                    url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url
                )
                self.add_item(btn_global)
                
                # Botão Avatar de Perfil no Servidor
                btn_server = discord.ui.Button(
                    label="Ver o avatar do perfil do usuário no servidor",
                    style=discord.ButtonStyle.blurple,
                    url=target_user.display_avatar.url
                )
                self.add_item(btn_server)

                btn_perms = discord.ui.Button(
                    label="Permissões do Membro",
                    style=discord.ButtonStyle.secondary,
                    disabled=True # Apenas para visual, ou pode implementar lógica de exibição
                )
                self.add_item(btn_perms)

        view = UserInfoView(user)

        await ctx.send(embeds=[embed_user, embed_member], view=view)

    # --- Comandos de Servidor ---

    @commands.hybrid_command(name="servericon", description="Mostra o ícone do servidor atual.")
    async def servericon(self, ctx: commands.Context):
        """Exibe o ícone do servidor em alta qualidade."""
        if not ctx.guild.icon:
            return await ctx.send("Este servidor não possui um ícone.")

        embed = discord.Embed(title=f"Ícone de {ctx.guild.name}", color=discord.Color.gold())
        embed.set_image(url=ctx.guild.icon.url)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Link Direto", url=ctx.guild.icon.url))

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="serverinfo", description="Mostra informações sobre o servidor.")
    async def serverinfo(self, ctx: commands.Context):
        """Exibe estatísticas e detalhes do servidor"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"<:discord:123456789012345678> {guild.name}",
            color=0x35393e
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Campo ID e Shard
        embed.add_field(name="💻 ID", value=f"`{guild.id}`", inline=True)
        shard_id = guild.shard_id if guild.shard_id is not None else 0
        embed.add_field(name="💻 Shard ID", value=f"{shard_id} — Cluster Principal", inline=True)
        
        # Campo Dono (Menção, Nome#Discrim e ID entre parênteses)
        owner = guild.owner
        owner_info = f"{owner.mention}\n`{owner}`\n({owner.id})"
        embed.add_field(name="👑 Dono", value=owner_info, inline=True)

        # Canais e Membros
        total_channels = len(guild.channels)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        
        channels_desc = (
            f"📝 **Texto:** {text_channels}\n"
            f"🔊 **Voz:** {voice_channels}"
        )
        embed.add_field(name=f"💬 Canais ({total_channels})", value=channels_desc, inline=True)
        
        
        created_str = f"{format_dt(guild.created_at, style='f')} ({format_dt(guild.created_at, style='R')})"
        embed.add_field(name="📅 Criado em", value=created_str, inline=True)
        
        joined_str = f"{format_dt(ctx.author.joined_at, style='f')} ({format_dt(ctx.author.joined_at, style='R')})"
        embed.add_field(name="🌟 Entrei aqui em", value=joined_str, inline=True)

        embed.add_field(name=f"👥 Membros ({guild.member_count})", value="\u200b", inline=False)

        await ctx.send(content=f"{ctx.author.mention}", embed=embed)

async def setup(bot):
    await bot.add_cog(Identity(bot))