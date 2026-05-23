import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
import datetime


# ==========================================
# FUNÇÃO AUXILIAR: PARSER DE TEMPO
# ==========================================
def extrair_tempo(entrada: str):
    """
    Extrai o tempo do final de uma string (ex: 'lembrar de beber água 10m 30s').
    Retorna o motivo (texto) e o total de segundos.
    """
    padrao_tempo = r"\s+((?:\d+[smhd]\s*)+)$"
    match = re.search(padrao_tempo, entrada, re.IGNORECASE)

    if not match:
        return entrada, 0

    string_tempo = match.group(1).lower()
    motivo = entrada[: match.start()].strip()

    multiplicadores = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    segundos_totais = sum(
        int(valor) * multiplicadores[unidade]
        for valor, unidade in re.findall(r"(\d+)([smhd])", string_tempo)
    )

    return motivo if motivo else "Lembrete", segundos_totais


# ==========================================
# VIEWS INTERATIVAS (SNOOZE / CANCELAR)
# ==========================================
class SnoozeModal(discord.ui.Modal, title="Adiar Lembrete"):
    tempo_input = discord.ui.TextInput(
        label="Quanto tempo deseja adiar?",
        placeholder="Ex: 10m, 1h, 30s",
        default="10m",
        required=True,
    )

    def __init__(
        self, cog, user: discord.User, motivo: str, channel: discord.abc.Messageable
    ):
        super().__init__()
        self.cog = cog
        self.user = user
        self.motivo = motivo
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        _, segundos = extrair_tempo(f" {self.tempo_input.value}")
        if segundos <= 0:
            return await interaction.response.send_message(
                "❌ Tempo inválido!", ephemeral=True
            )

        await interaction.response.edit_message(
            content=f"| 💤 Lembrete **adiado**! Avisarei novamente.", view=None
        )

        self.cog.bot.loop.create_task(
            self.cog.iniciar_lembrete(self.user, self.motivo, segundos, self.channel)
        )


class LembreteView(discord.ui.View):
    def __init__(
        self, cog, user: discord.User, motivo: str, channel: discord.abc.Messageable
    ):
        super().__init__(timeout=None)
        self.cog = cog
        self.user = user
        self.motivo = motivo
        self.channel = channel

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user.id:
            return True
        await interaction.response.send_message(
            "❌ Esse lembrete não é seu!", ephemeral=True
        )
        return False

    @discord.ui.button(
        label="Snooze (10m)", style=discord.ButtonStyle.secondary, emoji="💤"
    )
    async def btn_snooze_10m(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="| 💤 Lembrete adiado para daqui a 10 minutos!", view=None
        )
        self.cog.bot.loop.create_task(
            self.cog.iniciar_lembrete(self.user, self.motivo, 600, self.channel)
        )

    @discord.ui.button(
        label="Snooze Personalizado", style=discord.ButtonStyle.secondary, emoji="🕒"
    )
    async def btn_snooze_custom(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            SnoozeModal(self.cog, self.user, self.motivo, self.channel)
        )

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="| ✅ Reminder cancelled!", view=None
        )


# ==========================================
# COG PRINCIPAL DE LEMBRETES
# ==========================================
class Lembrete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lembretes_ativos = {}

    async def iniciar_lembrete(
        self,
        user: discord.User,
        motivo: str,
        tempo_segundos: int,
        channel: discord.abc.Messageable,
    ):
        if user.id not in self.lembretes_ativos:
            self.lembretes_ativos[user.id] = []

        data_futura = discord.utils.utcnow() + datetime.timedelta(
            seconds=tempo_segundos
        )
        lembrete_info = {"motivo": motivo, "data": data_futura}
        self.lembretes_ativos[user.id].append(lembrete_info)

        await asyncio.sleep(tempo_segundos)

        if lembrete_info in self.lembretes_ativos.get(user.id, []):
            self.lembretes_ativos[user.id].remove(lembrete_info)

        view = LembreteView(self, user, motivo, channel)
        mensagem = f"| 🔔 {user.mention} Reminder! **{motivo}**\n*Click 💤 to snooze for 10 minutes, or click 🕒 to choose how long to snooze.*"

        try:
            await channel.send(mensagem, view=view)
        except discord.Forbidden:
            try:
                await user.send(mensagem, view=view)
            except:
                pass

    @commands.hybrid_group(
        name="lembrete",
        invoke_without_command=True,
        description="Gerencie seus lembretes",
    )
    async def lembrete_grupo(self, ctx: commands.Context):
        # Embed explicativo bem trabalhado ao digitar apenas o comando base
        embed = discord.Embed(
            title="❓ -lembrete criar",
            description="Cria um lembrete personalizado.",
            color=0x3498DB,
        )
        embed.add_field(
            name="💡 Como usar?",
            value="`-lembrete criar <motivo> <duração>`\n*Exemplo: `-lembrete criar tirar o lixo 30m`*",
            inline=False,
        )
        embed.add_field(
            name="🔀 Sinônimos / Comandos Relacionados",
            value="`/lembrete criar`, `-lembrete criar`, `-lembrete list`",
            inline=False,
        )
        embed.set_footer(
            text=f"{ctx.author.display_name} • Utilitários",
            icon_url=ctx.author.display_avatar.url,
        )

        await ctx.send(embed=embed)

    @lembrete_grupo.command(
        name="criar",
        description="Cria um lembrete (ex: /lembrete criar tirar lixo 10m)",
    )
    @app_commands.describe(
        entrada="O que eu devo te lembrar e quando? Ex: 'estudar 1h 30m'"
    )
    async def lembrete_criar(self, ctx: commands.Context, *, entrada: str = None):
        # Se o usuário não passou nenhum texto no comando de prefixo
        if entrada is None:
            return await ctx.send(
                "❌ Você precisa informar o motivo do lembrete! Uso: `-lembrete criar <motivo> <tempo>`"
            )

        motivo, segundos = extrair_tempo(entrada)

        # SE O TEMPO NÃO FOI DETECTADO: Entra no modo interativo (pergunta o tempo)
        if segundos <= 0:
            # Pergunta de forma bonita e amigável
            await ctx.send(
                f"⏰ | **{ctx.author.mention}**, quando você irá querer que eu te avise deste lembrete? *(Ex: 1h, 5m, 30s)*"
            )

            def check(m):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

            try:
                # Aguarda a resposta do usuário no chat por até 60 segundos
                msg_tempo = await self.bot.wait_for(
                    "message", check=check, timeout=60.0
                )
                _, segundos = extrair_tempo(f" {msg_tempo.content}")

                if segundos <= 0:
                    return await ctx.send(
                        "❌ Tempo inválido recebido. Operação cancelada."
                    )

            except asyncio.TimeoutError:
                return await ctx.send(
                    "❌ Tempo limite esgotado! Você demorou muito para responder."
                )

        # Fluxo normal de agendamento após descobrir o tempo
        data_futura = discord.utils.utcnow() + datetime.timedelta(seconds=segundos)
        texto_data = discord.utils.format_dt(data_futura, "f")
        texto_relativo = discord.utils.format_dt(data_futura, "R")

        self.bot.loop.create_task(
            self.iniciar_lembrete(ctx.author, motivo, segundos, ctx.channel)
        )

        await ctx.send(
            f"✅ | Eu irei te lembrar em **{texto_data}** ({texto_relativo})!"
        )

    @lembrete_grupo.command(
        name="list", aliases=["lista"], description="Mostra todos os seus lembretes"
    )
    async def lembrete_list(self, ctx: commands.Context):
        lembretes_do_user = self.lembretes_ativos.get(ctx.author.id, [])

        if not lembretes_do_user:
            return await ctx.send(f"📝 | Seus lembretes (0)")

        descricao = ""
        for i, lembrete in enumerate(lembretes_do_user, 1):
            tempo_relativo = discord.utils.format_dt(lembrete["data"], "R")
            descricao += f"**{i}.** {lembrete['motivo']} - {tempo_relativo}\n"

        embed = discord.Embed(
            title=f"📝 Seus lembretes ({len(lembretes_do_user)})",
            description=descricao,
            color=0x3498DB,
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Lembrete(bot))
