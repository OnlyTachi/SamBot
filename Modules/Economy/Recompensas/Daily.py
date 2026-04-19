import discord
from discord.ext import commands
import logging
import time

from Brain.Memory.DataManager import data_manager


class Daily(commands.Cog):
    """
    Cog de Recompensas: Gerencia o bônus diário e sistema de ofensivas (Streaks).
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Daily")
        self.moeda_emoji = "🪙"
        self.recompensa_base = 500
        self.bonus_por_dia = 50  # Bônus adicional por dia consecutivo
        self.bonus_maximo = 1000  # Limite máximo do bônus de streak

    @commands.hybrid_command(
        name="daily",
        aliases=["diario", "recompensa"],
        description="Resgata o seu bônus financeiro diário!",
    )
    async def daily(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        agora = time.time()

        # Busca os dados antigos no banco
        ultimo_daily = data_manager.get_user_data(user_id, "ultimo_daily", 0)
        streak_atual = data_manager.get_user_data(user_id, "daily_streak", 0)

        # 1. Verifica o Cooldown (24 horas = 86400 segundos)
        tempo_passado = agora - ultimo_daily
        if tempo_passado < 86400:
            faltam = 86400 - tempo_passado
            horas = int(faltam // 3600)
            minutos = int((faltam % 3600) // 60)
            return await ctx.send(
                f"⏳ **Calma lá, milionário!** Você já resgatou seu bônus hoje.\nVolte em **{horas}h e {minutos}m**."
            )

        # 2. Lógica de Streak (Ofensiva)
        # Se passou mais de 48 horas (172800 seg), o usuário perde a ofensiva
        if tempo_passado > 172800 and ultimo_daily != 0:
            streak_atual = 0
            aviso_streak = "\n💔 *Você perdeu a sua ofensiva de dias seguidos!*"
        else:
            streak_atual += 1
            aviso_streak = f"\n🔥 **Ofensiva:** {streak_atual} dias seguidos!"

        # 3. Cálculo do Dinheiro
        bonus_calculado = min(streak_atual * self.bonus_por_dia, self.bonus_maximo)
        total_ganho = self.recompensa_base + bonus_calculado

        # 4. Salva tudo no DataManager
        carteira_atual = data_manager.get_user_data(user_id, "carteira", 0)
        data_manager.set_user_data(user_id, "carteira", carteira_atual + total_ganho)
        data_manager.set_user_data(user_id, "ultimo_daily", agora)
        data_manager.set_user_data(user_id, "daily_streak", streak_atual)

        # 5. Interface Visual
        embed = discord.Embed(
            title="🎁 Recompensa Diária",
            color=discord.Color.brand_green(),
            description=f"Você recebeu **{total_ganho:,}** {self.moeda_emoji}!{aviso_streak}",
        )
        embed.add_field(name="Base", value=f"{self.recompensa_base:,}", inline=True)
        embed.add_field(name="Bônus Streak", value=f"+{bonus_calculado:,}", inline=True)
        embed.set_footer(text=f"Saldo atual: {carteira_atual + total_ganho:,}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Daily(bot))
