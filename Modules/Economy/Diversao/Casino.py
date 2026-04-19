import discord
from discord.ext import commands
import logging
import random
import asyncio

from Brain.Memory.DataManager import data_manager


class Cassino(commands.Cog):
    """
    Cog de Cassino: Jogos de azar para arriscar SamCoins.
    Atenção: A casa sempre tem uma pequena vantagem!
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Cassino")
        self.moeda_emoji = "🪙"

    async def _validar_aposta(self, ctx, valor: int) -> bool:
        """Função interna de segurança para evitar trapaças."""
        if valor <= 0:
            await ctx.send(
                "❌ **Erro:** Você não pode apostar valores negativos ou zero!"
            )
            return False

        user_id = str(ctx.author.id)
        carteira = data_manager.get_user_data(user_id, "carteira", 0)

        if valor > carteira:
            await ctx.send(
                f"❌ **Saldo Insuficiente!** Você tem apenas {self.moeda_emoji} {carteira:,} na carteira."
            )
            return False

        return True

    @commands.hybrid_command(
        name="coinflip",
        aliases=["cf", "moeda"],
        description="Aposte no Cara ou Coroa! Dobre ou perca tudo.",
    )
    async def coinflip(self, ctx: commands.Context, escolha: str, valor: int):
        escolha = escolha.lower()
        if escolha not in ["cara", "coroa"]:
            return await ctx.send(
                "❌ **Escolha inválida!** Use `+coinflip cara <valor>` ou `+coinflip coroa <valor>`."
            )

        if not await self._validar_aposta(ctx, valor):
            return

        user_id = str(ctx.author.id)
        carteira = data_manager.get_user_data(user_id, "carteira", 0)

        # O suspense da rolagem!
        msg = await ctx.send(f"🪙 **Lançando a moeda ao ar...** (Apostando {valor:,})")
        await asyncio.sleep(1.5)

        # 50% de chance (Pode ajustar para 45% se quiser que a "casa" ganhe mais)
        resultado = random.choice(["cara", "coroa"])

        if escolha == resultado:
            # Vitória (Dobra o valor)
            novo_saldo = carteira + valor
            data_manager.set_user_data(user_id, "carteira", novo_saldo)
            embed = discord.Embed(title="🎉 Você Venceu!", color=discord.Color.green())
            embed.description = f"A moeda caiu em **{resultado.capitalize()}**!\nVocê ganhou **{valor:,}** {self.moeda_emoji}!"
        else:
            # Derrota (Perde o valor)
            novo_saldo = carteira - valor
            data_manager.set_user_data(user_id, "carteira", novo_saldo)
            embed = discord.Embed(title="💸 Você Perdeu!", color=discord.Color.red())
            embed.description = f"A moeda caiu em **{resultado.capitalize()}**...\nVocê perdeu os seus **{valor:,}** {self.moeda_emoji}."

        embed.set_footer(text=f"Saldo atual: {novo_saldo:,}")
        await msg.edit(content=None, embed=embed)

    @commands.hybrid_command(
        name="roleta",
        aliases=["slots", "girar"],
        description="Gire a roleta de multiplicadores! Alto risco, alta recompensa.",
    )
    async def roleta(self, ctx: commands.Context, valor: int):
        if not await self._validar_aposta(ctx, valor):
            return

        user_id = str(ctx.author.id)
        carteira = data_manager.get_user_data(user_id, "carteira", 0)

        msg = await ctx.send(f"🎰 **Girando a Roleta...** (Apostando {valor:,})")
        await asyncio.sleep(2)

        # Tabela de probabilidades da Roleta
        # 50% chance de perder tudo (0x)
        # 30% chance de recuperar metade (0.5x)
        # 12% chance de lucro leve (1.5x)
        # 7% chance de lucro bom (3x)
        # 1% chance de JACKPOT (10x)
        opcoes = [0, 0.5, 1.5, 3, 10]
        pesos = [50, 30, 12, 7, 1]

        multiplicador = random.choices(opcoes, weights=pesos, k=1)[0]

        # Remove o valor apostado e adiciona o prêmio
        premio = int(valor * multiplicador)
        lucro_liquido = premio - valor
        novo_saldo = carteira + lucro_liquido

        data_manager.set_user_data(user_id, "carteira", novo_saldo)

        if multiplicador == 0:
            cor = discord.Color.red()
            titulo = "💀 Deu Ruim!"
            texto = f"A roleta parou no **0x**.\nVocê perdeu tudo."
        elif multiplicador < 1:
            cor = discord.Color.orange()
            titulo = "⚠️ Quase!"
            texto = f"A roleta parou no **{multiplicador}x**.\nVocê recuperou {premio:,} {self.moeda_emoji}."
        elif multiplicador == 10:
            cor = discord.Color.gold()
            titulo = "💎 JACKPOT!!!"
            texto = f"INACREDITÁVEL! A roleta parou no **{multiplicador}x**!\nVocê ganhou exorbitantes **{premio:,}** {self.moeda_emoji}!"
        else:
            cor = discord.Color.green()
            titulo = "🎰 Vitória!"
            texto = f"A roleta parou no **{multiplicador}x**.\nVocê ganhou **{premio:,}** {self.moeda_emoji}!"

        embed = discord.Embed(title=titulo, description=texto, color=cor)
        embed.set_footer(text=f"Saldo atual: {novo_saldo:,}")

        await msg.edit(content=None, embed=embed)


async def setup(bot):
    await bot.add_cog(Cassino(bot))
