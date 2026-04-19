import discord
from discord.ext import commands
import logging

from Brain.Memory.DataManager import data_manager


class Investimentos(commands.Cog):
    """
    Cog de Investimentos: Compra e venda de Ações e FIIs na bolsa da SamBot.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Investimentos")
        self.moeda_emoji = "🪙"

    @commands.hybrid_command(
        name="mercado",
        aliases=["bolsa", "ativos"],
        description="Veja as cotações atuais da bolsa de valores.",
    )
    async def mercado(self, ctx: commands.Context):
        ativos = data_manager.get_knowledge("mercado") or {}

        if not ativos:
            return await ctx.send("❌ A bolsa de valores está fechada no momento.")

        embed = discord.Embed(
            title="📊 Bolsa de Valores Sam",
            description="Cotações em tempo real do mercado financeiro.",
            color=discord.Color.dark_purple(),
        )

        for ticker, info in ativos.items():
            tipo_icon = "🏢" if info["tipo"] == "FII" else "📈"
            desc = f"**Preço:** {self.moeda_emoji} {info['preco_atual']}\n*{info['descricao']}*"

            if info["tipo"] == "FII":
                desc += f"\n💰 *Dividend Yield Est.*: {self.moeda_emoji} {info['dividendo_estimado']} por cota"

            embed.add_field(
                name=f"{tipo_icon} {ticker} - {info['nome']}", value=desc, inline=False
            )

        embed.set_footer(
            text="Use +comprar <ticker> <quantidade> para investir o dinheiro do seu Banco."
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="comprar",
        aliases=["buy"],
        description="Compre cotas de FIIs ou Ações usando o saldo do seu banco.",
    )
    async def comprar(self, ctx: commands.Context, ticker: str, quantidade: int):
        ticker = ticker.upper()
        if quantidade <= 0:
            return await ctx.send("❌ Você precisa comprar pelo menos 1 cota!")

        ativos = data_manager.get_knowledge("mercado") or {}
        if ticker not in ativos:
            return await ctx.send(
                f"❌ O ticker **{ticker}** não existe na nossa bolsa. Use `+mercado` para ver as opções."
            )

        user_id = str(ctx.author.id)
        banco = data_manager.get_user_data(user_id, "banco", 0)

        preco_unidade = ativos[ticker]["preco_atual"]
        custo_total = preco_unidade * quantidade

        if custo_total > banco:
            return await ctx.send(
                f"❌ **Saldo Bancário Insuficiente!** A compra custa {self.moeda_emoji} {custo_total:,}, mas você só tem {self.moeda_emoji} {banco:,} no banco."
            )

        # Deduz o dinheiro do banco
        data_manager.set_user_data(user_id, "banco", banco - custo_total)

        # Atualiza o portfólio (Lógica de Preço Médio)
        portfolio = data_manager.get_user_data(user_id, "portfolio", {})

        if ticker not in portfolio:
            portfolio[ticker] = {"quantidade": quantidade, "preco_medio": preco_unidade}
        else:
            qtd_atual = portfolio[ticker]["quantidade"]
            pm_atual = portfolio[ticker]["preco_medio"]

            # Fórmula do Preço Médio
            novo_pm = ((qtd_atual * pm_atual) + (quantidade * preco_unidade)) / (
                qtd_atual + quantidade
            )

            portfolio[ticker]["quantidade"] += quantidade
            portfolio[ticker]["preco_medio"] = round(novo_pm, 2)

        data_manager.set_user_data(user_id, "portfolio", portfolio)

        embed = discord.Embed(title="🧾 Ordem Executada", color=discord.Color.green())
        embed.description = f"Você comprou **{quantidade}x {ticker}** com sucesso!\nCusto Total: {self.moeda_emoji} {custo_total:,}"
        embed.set_footer(
            text=f"Seu novo Preço Médio em {ticker}: {portfolio[ticker]['preco_medio']}"
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="vender",
        aliases=["sell"],
        description="Venda os seus ativos e receba o dinheiro de volta no banco.",
    )
    async def vender(self, ctx: commands.Context, ticker: str, quantidade: int):
        ticker = ticker.upper()
        if quantidade <= 0:
            return await ctx.send("❌ Quantidade inválida.")

        ativos = data_manager.get_knowledge("mercado") or {}
        if ticker not in ativos:
            return await ctx.send(f"❌ Ticker desconhecido.")

        user_id = str(ctx.author.id)
        portfolio = data_manager.get_user_data(user_id, "portfolio", {})

        if ticker not in portfolio or portfolio[ticker]["quantidade"] < quantidade:
            qtd_posse = portfolio.get(ticker, {}).get("quantidade", 0)
            return await ctx.send(
                f"❌ Você não tem cotas suficientes para vender! Você possui apenas **{qtd_posse}** de {ticker}."
            )

        preco_mercado = ativos[ticker]["preco_atual"]
        valor_venda = preco_mercado * quantidade

        # Adiciona o dinheiro no banco
        banco = data_manager.get_user_data(user_id, "banco", 0)
        data_manager.set_user_data(user_id, "banco", banco + valor_venda)

        # Calcula Lucro/Prejuízo da operação para mostrar na tela
        preco_medio = portfolio[ticker]["preco_medio"]
        lucro_prejuizo = (preco_mercado - preco_medio) * quantidade

        # Atualiza a carteira
        portfolio[ticker]["quantidade"] -= quantidade
        if portfolio[ticker]["quantidade"] == 0:
            del portfolio[ticker]  # Limpa o ativo se vendeu tudo

        data_manager.set_user_data(user_id, "portfolio", portfolio)

        cor = discord.Color.green() if lucro_prejuizo >= 0 else discord.Color.red()
        sinal = "+" if lucro_prejuizo >= 0 else ""

        embed = discord.Embed(title="🧾 Ordem de Venda Executada", color=cor)
        embed.description = f"Você vendeu **{quantidade}x {ticker}** por {self.moeda_emoji} {valor_venda:,}."
        embed.add_field(
            name="Resultado da Operação (P&L)",
            value=f"**{sinal}{round(lucro_prejuizo, 2)}** {self.moeda_emoji}",
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="carteira",
        aliases=["portfolio"],
        description="Mostra todos os seus investimentos atuais.",
    )
    async def carteira(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        portfolio = data_manager.get_user_data(user_id, "portfolio", {})
        ativos = data_manager.get_knowledge("mercado") or {}

        if not portfolio:
            return await ctx.send(
                "🕸️ A sua carteira de investimentos está vazia. Use `+mercado` para começar a investir!"
            )

        embed = discord.Embed(
            title=f"💼 Custódia de {ctx.author.display_name}",
            color=discord.Color.brand_green(),
        )

        patrimonio_total = 0

        for ticker, dados in portfolio.items():
            qtd = dados["quantidade"]
            pm = dados["preco_medio"]

            # Pega o preço atual no mercado para ver se está ganhando ou perdendo
            preco_atual = ativos.get(ticker, {}).get("preco_atual", pm)
            valor_total_ativo = qtd * preco_atual
            patrimonio_total += valor_total_ativo

            rentabilidade = ((preco_atual - pm) / pm) * 100
            sinal_rent = "🟢" if rentabilidade >= 0 else "🔴"

            texto = f"**Quantidade:** {qtd} cotas\n**Preço Médio:** {self.moeda_emoji} {pm}\n**Cotação Atual:** {self.moeda_emoji} {preco_atual}\n**Total:** {self.moeda_emoji} {valor_total_ativo:,} ({sinal_rent} {rentabilidade:.2f}%)"
            embed.add_field(name=f"🏷️ {ticker}", value=texto, inline=False)

        embed.add_field(
            name="💰 Patrimônio Total Investido",
            value=f"**{self.moeda_emoji} {patrimonio_total:,}**",
            inline=False,
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Investimentos(bot))
