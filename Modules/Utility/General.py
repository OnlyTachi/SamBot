import discord
from discord.ext import commands
from discord import app_commands
import datetime
import time
import platform
import psutil
from discord.ui import View, Button
from discord.utils import format_dt

# --- VIEW INTERATIVA (Botões do Ping) ---
class PingView(View):
    def __init__(self, performance_embed, system_embed, stats_embed, original_author_id, timeout=120):
        super().__init__(timeout=timeout)
        self.performance_embed = performance_embed
        self.system_embed = system_embed
        self.stats_embed = stats_embed
        self.original_author_id = original_author_id
        self.message = None
        self.emoji = "🤖"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.original_author_id:
            return True
        await interaction.response.send_message("Apenas quem executou o comando pode interagir!", ephemeral=True)
        return False

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except:
                pass

    @discord.ui.button(label="Performance", style=discord.ButtonStyle.primary, emoji="🏓")
    async def performance_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=self.performance_embed)

    @discord.ui.button(label="Sistema", style=discord.ButtonStyle.secondary, emoji="💻")
    async def system_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=self.system_embed)
    
    @discord.ui.button(label="Estatísticas", style=discord.ButtonStyle.success, emoji="📊")
    async def stats_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=self.stats_embed)


# --- COG PRINCIPAL ---
class General(commands.Cog):
    """Utilitários gerais e status do bot."""
    def __init__(self, bot):
        self.bot = bot
        # Define o tempo de início se o bot principal não tiver definido
        if not hasattr(self.bot, 'start_time'):
            self.bot.start_time = datetime.datetime.now(datetime.timezone.utc)
        
        # Inicializa contadores de estatísticas
        self.messages_seen = 0
        self.commands_executed = 0
        self.voice_join_time = None
        self.voice_time_total = 0 

    # --- HELPERS ---
    def get_uptime_str(self):
        delta = datetime.datetime.now(datetime.timezone.utc) - self.bot.start_time
        d, r = divmod(delta.total_seconds(), 86400)
        h, r = divmod(r, 3600)
        m, s = divmod(r, 60)
        return f"{int(d)}d {int(h)}h {int(m)}m {int(s)}s"

    def get_voice_time_str(self, guild=None):
        current_session = 0
        if self.voice_join_time and guild and guild.voice_client and guild.voice_client.is_connected():
            current_session = time.time() - self.voice_join_time
        
        total_seconds = self.voice_time_total + current_session
        vh, vr = divmod(total_seconds, 3600)
        vm, vs = divmod(vr, 60)
        return f"{int(vh)}h {int(vm)}m {int(vs)}s"

    async def generate_ping_content(self, target, author):
        gateway_latency = round(self.bot.latency * 1000)
        color = 0x2ecc71 if gateway_latency < 150 else 0xe67e22
        
        embed_perf = discord.Embed(title="🏓 Pong!", color=color)
        embed_perf.add_field(name="💓 Gateway", value=f"`{gateway_latency}ms`", inline=True)
        embed_perf.add_field(name="⏱️ Uptime", value=f"`{self.get_uptime_str()}`", inline=True)
        embed_perf.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed_perf.set_footer(text=f"Solicitado por {author.name}", icon_url=author.display_avatar.url)

        ram = psutil.virtual_memory()
        cpu_usage = psutil.cpu_percent()
        ram_used = f"{ram.used / (1024**3):.2f}/{ram.total / (1024**3):.2f} GB ({ram.percent}%)"

        embed_sys = discord.Embed(title="💻 Informações do Sistema", color=0x3498db)
        embed_sys.add_field(name="🐍 Python", value=f"`{platform.python_version()}`", inline=True)
        embed_sys.add_field(name="🔧 Discord.py", value=f"`{discord.__version__}`", inline=True)
        embed_sys.add_field(name="🧠 CPU", value=f"`{cpu_usage}%`", inline=False)
        embed_sys.add_field(name="💾 RAM", value=f"`{ram_used}`", inline=False)

        embed_stats = discord.Embed(title="📊 Estatísticas da Sessão", color=0xf1c40f)
        embed_stats.add_field(name="📩 Mensagens Lidas", value=f"`{self.messages_seen}`", inline=True)
        embed_stats.add_field(name="🤖 Comandos", value=f"`{self.commands_executed}`", inline=True)
        guild = target.guild if hasattr(target, 'guild') else None
        embed_stats.add_field(name="🎙️ Em Call", value=f"`{self.get_voice_time_str(guild)}`", inline=True)

        view = PingView(embed_perf, embed_sys, embed_stats, author.id)
        return embed_perf, view

    # --- LISTENERS ---
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

    # --- COMANDOS ---
    @commands.hybrid_command(name="ping", description="Mostra latência, sistema e estatísticas.")
    async def ping(self, ctx: commands.Context):
        """Mostra a latência do bot, informações do sistema e estatísticas de uso."""
        msg = await ctx.send("📡 Calculando latência...")
        embed, view = await self.generate_ping_content(ctx, ctx.author)
        view.message = msg
        await msg.edit(content=None, embed=embed, view=view)

    @commands.hybrid_command(name="botinfo", description="Mostra informações sobre a SamBot.")
    async def botinfo(self, ctx: commands.Context):
        """Exibe informações detalhadas sobre o bot."""
        embed = discord.Embed(
            title=f"🤖 Informações do {self.bot.user.name}",
            color=0x5865F2
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        embed.add_field(name="💻 ID", value=f"`{self.bot.user.id}`", inline=True)
        embed.add_field(name="👑 Criador", value="`Tachi`", inline=True)
        embed.add_field(name="📅 Online desde", value=format_dt(self.bot.start_time, style="R"), inline=True)
        
        stats = (
            f"🏠 **Servidores:** {len(self.bot.guilds)}\n"
            f"👥 **Usuários:** {len(self.bot.users)}\n"
            f"⚙️ **Comandos:** {len(self.bot.commands)}"
        )
        embed.add_field(name="📊 Estatísticas Gerais", value=stats, inline=False)
        
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        sys_info = (
            f"💾 **RAM:** {ram.percent}%\n"
            f"🧠 **CPU:** {cpu}%\n"
            f"🐍 **Python:** {platform.python_version()}"
        )
        embed.add_field(name="🖥️ Sistema", value=sys_info, inline=True)
        embed.add_field(name="⚡ Latência", value=f"`{round(self.bot.latency * 1000)}ms`", inline=True)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))