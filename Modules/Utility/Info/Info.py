import discord
from discord.ext import commands
from discord import app_commands
import datetime
import time
import platform
import psutil
from discord.utils import format_dt


class PingView(discord.ui.View):
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
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(embed=self.performance_embed)

    @discord.ui.button(label="Sistema", style=discord.ButtonStyle.secondary, emoji="💻")
    async def system_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(embed=self.system_embed)

    @discord.ui.button(
        label="Estatísticas", style=discord.ButtonStyle.success, emoji="📊"
    )
    async def stats_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(embed=self.stats_embed)


class InfoBot(commands.Cog):
    """Módulo dedicado a informações, latência e status do bot."""

    def __init__(self, bot):
        self.bot = bot
        self.emoji = "ℹ️"

        if not hasattr(self.bot, "start_time"):
            self.bot.start_time = discord.utils.utcnow()

        self.messages_seen = 0
        self.commands_executed = 0
        self.voice_join_time = None
        self.voice_time_total = 0

    def get_uptime_str(self):
        delta = discord.utils.utcnow() - self.bot.start_time
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

    # Listeners para monitoramento do Bot
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

    @commands.hybrid_command(
        name="ping",
        description="Mostra latência, sistema e estatísticas detalhadas do bot.",
    )
    @discord.app_commands.describe(segredo="Não olhe para cá! Isso é um mistério...")
    async def ping(self, ctx: commands.Context, *, segredo: str = None):
        # Easter Egg caso usem o parâmetro "pong"
        if segredo and segredo.strip().lower() == "pong":
            return await ctx.send(
                "🤖 **Easter Egg:** Ei! Você achou que eu ia só dizer 'Pong' de volta? Na verdade, eu domino o tênis de mesa digital! 🏓⚡"
            )

        msg = await ctx.send("📡 Calculando a latência da rede...")

        gateway_latency = round(self.bot.latency * 1000)
        color = 0x2ECC71 if gateway_latency < 150 else 0xE67E22

        # 1. ABA: Performance
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

        # 2. ABA: Sistema
        ram = psutil.virtual_memory()
        cpu_usage = psutil.cpu_percent()
        ram_used = f"{ram.used / (1024**3):.2f}/{ram.total / (1024**3):.2f} GB ({ram.percent}%)"

        embed_sys = discord.Embed(title="💻 Informações do Sistema", color=0x3498DB)
        embed_sys.add_field(
            name="🐍 Python", value=f"`{platform.python_version()}`", inline=True
        )
        embed_sys.add_field(
            name="🔧 Discord.py", value=f"`{discord.__version__}`", inline=True
        )
        embed_sys.add_field(
            name="🖥️ SO",
            value=f"`{platform.system()} {platform.release()}`",
            inline=True,
        )
        embed_sys.add_field(name="🧠 CPU", value=f"`{cpu_usage}%`", inline=False)
        embed_sys.add_field(name="💾 RAM", value=f"`{ram_used}`", inline=False)

        # 3. ABA: Estatísticas
        embed_stats = discord.Embed(title="📊 Estatísticas da Sessão", color=0xF1C40F)
        embed_stats.add_field(
            name="📩 Mensagens Lidas", value=f"`{self.messages_seen}`", inline=True
        )
        embed_stats.add_field(
            name="🤖 Comandos Usados", value=f"`{self.commands_executed}`", inline=True
        )
        embed_stats.add_field(
            name="🎙️ Em Call",
            value=f"`{self.get_voice_time_str(ctx.guild)}`",
            inline=True,
        )
        embed_stats.set_footer(
            text=f"Servidores: {len(self.bot.guilds)} | Usuários: {len(self.bot.users)}"
        )

        view = PingView(embed_perf, embed_sys, embed_stats, ctx.author.id)
        view.message = msg
        await msg.edit(content=None, embed=embed_perf, view=view)

    @commands.hybrid_command(
        name="info",
        aliases=["botinfo"],
        description="Mostra informações detalhadas sobre mim!",
    )
    async def info(self, ctx: commands.Context):
        embed = discord.Embed(
            title=f"🤖 Informações da {self.bot.user.name}",
            description="Sou um bot focado em moderação, utilidades, diversão e até tenho um 'Cérebro' próprio para interagir com você!",
            color=0x5865F2,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        embed.add_field(name="💻 Meu ID", value=f"`{self.bot.user.id}`", inline=True)
        embed.add_field(name="👑 Criador", value="`OnlyTachi`", inline=True)
        embed.add_field(
            name="📅 Acordada a",
            value=format_dt(self.bot.start_time, style="R"),
            inline=True,
        )

        stats = f"🏠 **Servidores:** {len(self.bot.guilds)}\n👥 **Usuários:** {len(self.bot.users)}\n⚙️ **Comandos:** {len(self.bot.commands)}"
        embed.add_field(name="📊 Minha Escala Atual", value=stats, inline=False)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label="Criador", url="https://github.com/OnlyTachi")
        )

        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(InfoBot(bot))
