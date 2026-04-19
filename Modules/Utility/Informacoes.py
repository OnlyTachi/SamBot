import discord
from discord.ext import commands
from discord import app_commands
import datetime
import time
import platform
import psutil
from discord.ui import View, Button
from discord.utils import format_dt

# ==========================================
# VIEWS INTERATIVAS (BOTÕES)
# ==========================================


class PingView(View):
    def __init__(
        self,
        performance_embed,
        system_embed,
        stats_embed,
        original_author_id,
        timeout=120,
    ):
        super().__init__(timeout=timeout)
        self.performance_embed = performance_embed
        self.system_embed = system_embed
        self.stats_embed = stats_embed
        self.original_author_id = original_author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.original_author_id:
            return True
        await interaction.response.send_message(
            "❌ Apenas quem executou o comando pode interagir!", ephemeral=True
        )
        return False

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except:
                pass

    @discord.ui.button(
        label="Performance", style=discord.ButtonStyle.primary, emoji="🏓"
    )
    async def performance_button(
        self, interaction: discord.Interaction, button: Button
    ):
        await interaction.response.edit_message(embed=self.performance_embed)

    @discord.ui.button(label="Sistema", style=discord.ButtonStyle.secondary, emoji="💻")
    async def system_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=self.system_embed)

    @discord.ui.button(
        label="Estatísticas", style=discord.ButtonStyle.success, emoji="📊"
    )
    async def stats_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=self.stats_embed)


class UserInfoView(View):
    def __init__(self, target_user: discord.Member):
        super().__init__()

        # Botão Avatar Global
        url_global = (
            target_user.avatar.url
            if target_user.avatar
            else target_user.default_avatar.url
        )
        btn_global = discord.ui.Button(
            label="Avatar Global", style=discord.ButtonStyle.blurple, url=url_global
        )
        self.add_item(btn_global)

        # Botão Avatar de Perfil no Servidor
        btn_server = discord.ui.Button(
            label="Avatar do Servidor",
            style=discord.ButtonStyle.blurple,
            url=target_user.display_avatar.url,
        )
        self.add_item(btn_server)

        # Botão visual (Desativado)
        btn_perms = discord.ui.Button(
            label="Permissões do Membro",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        self.add_item(btn_perms)


# ==========================================
# COG PRINCIPAL DE INFORMAÇÕES
# ==========================================


class Informacoes(commands.Cog):
    """Utilitários gerais de informações sobre o bot, utilizadores e servidores."""

    def __init__(self, bot):
        self.bot = bot
        self.emoji = "ℹ️"

        # Inicializa o tempo de início e contadores para as estatísticas
        if not hasattr(self.bot, "start_time"):
            self.bot.start_time = datetime.datetime.now(datetime.timezone.utc)

        self.messages_seen = 0
        self.commands_executed = 0
        self.voice_join_time = None
        self.voice_time_total = 0

    # --- HELPERS INTERNOS ---
    def get_uptime_str(self):
        delta = datetime.datetime.now(datetime.timezone.utc) - self.bot.start_time
        d, r = divmod(delta.total_seconds(), 86400)
        h, r = divmod(r, 3600)
        m, s = divmod(r, 60)
        return f"{int(d)}d {int(h)}h {int(m)}m {int(s)}s"

    def get_voice_time_str(self, guild=None):
        current_session = 0
        if (
            self.voice_join_time
            and guild
            and guild.voice_client
            and guild.voice_client.is_connected()
        ):
            current_session = time.time() - self.voice_join_time

        total_seconds = self.voice_time_total + current_session
        vh, vr = divmod(total_seconds, 3600)
        vm, vs = divmod(vr, 60)
        return f"{int(vh)}h {int(vm)}m {int(vs)}s"

    # --- LISTENERS DE ESTATÍSTICAS ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            self.messages_seen += 1

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.commands_executed += 1

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
            if before.channel is None and after.channel is not None:
                self.voice_join_time = time.time()
            elif before.channel is not None and after.channel is None:
                if self.voice_join_time:
                    self.voice_time_total += time.time() - self.voice_join_time
                    self.voice_join_time = None

    # ==========================================
    # COMANDOS DO BOT
    # ==========================================

    @commands.hybrid_command(
        name="ping", description="Mostra latência, sistema e estatísticas do bot."
    )
    async def ping(self, ctx: commands.Context):
        msg = await ctx.send("📡 A calcular a latência da rede...")

        gateway_latency = round(self.bot.latency * 1000)
        color = 0x2ECC71 if gateway_latency < 150 else 0xE67E22

        # Embed 1: Performance
        embed_perf = discord.Embed(title="🏓 Pong!", color=color)
        embed_perf.add_field(
            name="💓 Gateway", value=f"`{gateway_latency}ms`", inline=True
        )
        embed_perf.add_field(
            name="⏱️ Uptime", value=f"`{self.get_uptime_str()}`", inline=True
        )
        embed_perf.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed_perf.set_footer(
            text=f"Solicitado por {ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )

        # Embed 2: Sistema
        ram = psutil.virtual_memory()
        cpu_usage = psutil.cpu_percent()
        ram_used = f"{ram.used / (1024**3):.2f}/{ram.total / (1024**3):.2f} GB ({ram.percent}%)"

        embed_sys = discord.Embed(
            title="💻 Informações do Sistema (HomeLab)", color=0x3498DB
        )
        embed_sys.add_field(
            name="🐍 Python", value=f"`{platform.python_version()}`", inline=True
        )
        embed_sys.add_field(
            name="🔧 Discord.py", value=f"`{discord.__version__}`", inline=True
        )
        embed_sys.add_field(name="🧠 CPU", value=f"`{cpu_usage}%`", inline=False)
        embed_sys.add_field(name="💾 RAM", value=f"`{ram_used}`", inline=False)

        # Embed 3: Estatísticas
        embed_stats = discord.Embed(title="📊 Estatísticas da Sessão", color=0xF1C40F)
        embed_stats.add_field(
            name="📩 Mensagens Lidas", value=f"`{self.messages_seen}`", inline=True
        )
        embed_stats.add_field(
            name="🤖 Comandos", value=f"`{self.commands_executed}`", inline=True
        )
        embed_stats.add_field(
            name="🎙️ Em Call",
            value=f"`{self.get_voice_time_str(ctx.guild)}`",
            inline=True,
        )

        view = PingView(embed_perf, embed_sys, embed_stats, ctx.author.id)
        view.message = msg
        await msg.edit(content=None, embed=embed_perf, view=view)

    @commands.hybrid_command(
        name="botinfo", description="Mostra informações detalhadas sobre a SamBot."
    )
    async def botinfo(self, ctx: commands.Context):
        embed = discord.Embed(
            title=f"🤖 Informações da {self.bot.user.name}", color=0x5865F2
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        embed.add_field(name="💻 ID", value=f"`{self.bot.user.id}`", inline=True)
        embed.add_field(name="👑 Criador", value="`Tachi`", inline=True)
        embed.add_field(
            name="📅 Online desde",
            value=format_dt(self.bot.start_time, style="R"),
            inline=True,
        )

        stats = f"🏠 **Servidores:** {len(self.bot.guilds)}\n👥 **Utilizadores:** {len(self.bot.users)}\n⚙️ **Comandos:** {len(self.bot.commands)}"
        embed.add_field(name="📊 Escala Atual", value=stats, inline=False)

        await ctx.send(embed=embed)

    # ==========================================
    # COMANDOS DE IDENTIFICAÇÃO (USERS/GUILDS)
    # ==========================================

    @commands.hybrid_command(
        name="avatar", description="Mostra o avatar de um utilizador em alta resolução."
    )
    @app_commands.describe(user="O utilizador para ver o avatar (padrão: você)")
    async def avatar(self, ctx: commands.Context, user: discord.Member = None):
        user = user or ctx.author
        embed = discord.Embed(title=f"Avatar de {user.display_name}", color=user.color)
        embed.set_image(url=user.display_avatar.url)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label="Link Direto", url=user.display_avatar.url)
        )
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(
        name="userinfo", description="Mostra informações detalhadas sobre uma conta."
    )
    @commands.guild_only()
    async def userinfo(self, ctx: commands.Context, user: discord.Member = None):
        user = user or ctx.author

        # Embed 1: Conta Discord
        embed_user = discord.Embed(
            title="Informações da Conta",
            description=f"👤 {user.mention} **{user.name}**",
            color=0x5865F2,
        )
        embed_user.add_field(name="🆔 ID do Discord", value=f"`{user.id}`", inline=True)
        embed_user.add_field(
            name="🗓️ Data de Criação",
            value=f"{format_dt(user.created_at, style='R')}",
            inline=True,
        )
        embed_user.set_thumbnail(
            url=user.avatar.url if user.avatar else user.default_avatar.url
        )

        # Embed 2: Dados no Servidor
        embed_member = discord.Embed(title="Informações no Servidor", color=user.color)
        embed_member.add_field(
            name="🗓️ Data de Entrada",
            value=f"{format_dt(user.joined_at, style='R')}",
            inline=True,
        )
        embed_member.add_field(
            name="🎭 Cargo Mais Alto",
            value=user.top_role.mention if user.top_role else "@everyone",
            inline=True,
        )

        timeout_status = "✅ Mutado" if user.timed_out_until else "❌ Não"
        embed_member.add_field(
            name="🚫 Punições Ativas", value=timeout_status, inline=False
        )
        embed_member.set_thumbnail(url=user.display_avatar.url)

        await ctx.send(embeds=[embed_user, embed_member], view=UserInfoView(user))

    @commands.hybrid_command(
        name="servericon", description="Mostra o ícone do servidor atual."
    )
    @commands.guild_only()
    async def servericon(self, ctx: commands.Context):
        if not ctx.guild.icon:
            return await ctx.send("❌ Este servidor não possui um ícone.")

        embed = discord.Embed(
            title=f"Ícone de {ctx.guild.name}", color=discord.Color.gold()
        )
        embed.set_image(url=ctx.guild.icon.url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Link Direto", url=ctx.guild.icon.url))
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(
        name="serverinfo", description="Mostra as estatísticas gerais do servidor."
    )
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(title=f"🌐 {guild.name}", color=0x35393E)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="💻 ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👑 Dono", value=f"{guild.owner.mention}", inline=True)

        channels_desc = f"📝 **Texto:** {len(guild.text_channels)}\n🔊 **Voz:** {len(guild.voice_channels)}"
        embed.add_field(
            name=f"💬 Canais ({len(guild.channels)})", value=channels_desc, inline=True
        )

        embed.add_field(
            name="📅 Fundado em",
            value=format_dt(guild.created_at, style="R"),
            inline=True,
        )
        embed.add_field(
            name="👥 Total de Membros", value=f"**{guild.member_count}**", inline=True
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Informacoes(bot))
