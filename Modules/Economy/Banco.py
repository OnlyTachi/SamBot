import discord
from discord.ext import commands
import logging

from Brain.Memory.DataManager import data_manager


class Banco(commands.Cog):
    """
    Cog de Banco: Sistema financeiro seguro para guardar moedas e fazer transferências.
    Prepara o terreno para o futuro mercado de ações e investimentos.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Banco")
        self.moeda_emoji = "🪙"

    async def _converter_valor(self, ctx, saldo_origem, valor_str):
        """Função interna para converter 'all', 'tudo' ou números."""
        if valor_str.lower() in ["all", "tudo", "max"]:
            return saldo_origem

        try:
            valor = int(valor_str)
            if valor <= 0:
                await ctx.send("❌ **Erro:** O valor deve ser maior que zero!")
                return None
            return valor
        except ValueError:
            await ctx.send("❌ **Erro:** Digita um número válido ou 'tudo'.")
            return None

    @commands.hybrid_command(
        name="depositar",
        aliases=["dep"],
        description="Guarda o teu dinheiro no banco com segurança.",
    )
    async def depositar(self, ctx: commands.Context, valor: str):
        user_id = str(ctx.author.id)

        carteira = data_manager.get_user_data(user_id, "carteira", 0)
        banco = data_manager.get_user_data(user_id, "banco", 0)

        # Trata o valor (se é número ou "tudo")
        quantia = await self._converter_valor(ctx, carteira, valor)
        if not quantia:
            return

        if quantia > carteira:
            return await ctx.send(
                f"❌ **Saldo Insuficiente!** Voce so possui {self.moeda_emoji} {carteira:,} na sua carteira."
            )

        # Efetua a transação
        data_manager.set_user_data(user_id, "carteira", carteira - quantia)
        data_manager.set_user_data(user_id, "banco", banco + quantia)

        embed = discord.Embed(
            title="🏦 Depósito Concluído", color=discord.Color.green()
        )
        embed.description = f"Depositou **{quantia:,}** {self.moeda_emoji} com sucesso!\nO seu dinheiro agora está seguro."
        embed.set_footer(text=f"Novo saldo bancário: {banco + quantia:,}")

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="sacar",
        aliases=["with", "levantar"],
        description="Retira o dinheiro do banco para a carteira.",
    )
    async def sacar(self, ctx: commands.Context, valor: str):
        user_id = str(ctx.author.id)

        carteira = data_manager.get_user_data(user_id, "carteira", 0)
        banco = data_manager.get_user_data(user_id, "banco", 0)

        quantia = await self._converter_valor(ctx, banco, valor)
        if not quantia:
            return

        if quantia > banco:
            return await ctx.send(
                f"❌ **Saldo Insuficiente!** So possui {self.moeda_emoji} {banco:,} no banco."
            )

        # Efetua a transação
        data_manager.set_user_data(user_id, "banco", banco - quantia)
        data_manager.set_user_data(user_id, "carteira", carteira + quantia)

        embed = discord.Embed(
            title="🏧 Levantamento Concluído", color=discord.Color.blue()
        )
        embed.description = (
            f"Levantaste **{quantia:,}** {self.moeda_emoji} do teu banco."
        )
        embed.set_footer(text=f"Nova carteira: {carteira + quantia:,}")

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="pagar",
        aliases=["pay", "transferir"],
        description="Transfere SamCoints da sua carteira para outro membro.",
    )
    async def pagar(self, ctx: commands.Context, membro: discord.Member, valor: int):
        if membro.id == ctx.author.id:
            return await ctx.send(
                "❌ Não pode transferir dinheiro para vc mesmo boboca!!"
            )

        if membro.bot:
            return await ctx.send("❌ Os bots não precisam de dinheiro. Durr")

        if valor <= 0:
            return await ctx.send("❌ O valor deve ser maior que zero!")

        user_id = str(ctx.author.id)
        target_id = str(membro.id)

        carteira_remetente = data_manager.get_user_data(user_id, "carteira", 0)

        if valor > carteira_remetente:
            return await ctx.send(
                f"❌ **Saldo Insuficiente!** Tem apenas {self.moeda_emoji} {carteira_remetente:,} na sua carteira. Use `+sacar` primeiro se o dinheiro estiver no banco."
            )

        # Pega a carteira do destinatário (cria com 0 se ele não existir ainda)
        carteira_destinatario = data_manager.get_user_data(target_id, "carteira", 0)

        # Transação segura (deduz de um, adiciona noutro)
        data_manager.set_user_data(user_id, "carteira", carteira_remetente - valor)
        data_manager.set_user_data(target_id, "carteira", carteira_destinatario + valor)

        await ctx.send(
            f"💸 **Transferência Sucesso!** O utilizador {ctx.author.mention} enviou **{valor:,}** {self.moeda_emoji} para {membro.mention}!"
        )


async def setup(bot):
    await bot.add_cog(Banco(bot))
