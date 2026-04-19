import discord
from discord.ext import commands
from Brain.Memory.DataManager import data_manager


class FundoSelect(discord.ui.Select):
    def __init__(self, backgrounds_comprados):
        options = [
            discord.SelectOption(label=bg, value=bg) for bg in backgrounds_comprados
        ]
        super().__init__(placeholder="Escolha o seu fundo ativo...", options=options)

    async def callback(self, interaction: discord.Interaction):
        escolha = self.values[0]
        data_manager.set_user_data(
            str(interaction.user.id), "background_ativo", escolha
        )
        await interaction.response.send_message(
            f"✅ Fundo **{escolha}** equipado com sucesso!", ephemeral=True
        )


class Fundos(commands.Cog):
    """Gerencia a coleção de planos de fundo do usuário."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="fundos", description="Veja e equipe os seus fundos de perfil."
    )
    async def fundos(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        comprados = data_manager.get_user_data(
            user_id, "backgrounds_comprados", ["padrao.png"]
        )

        if not comprados:
            return await ctx.send(
                "❌ Você ainda não possui fundos extras. Visite a `+loja`!"
            )

        view = discord.ui.View()
        view.add_item(FundoSelect(comprados))

        await ctx.send(
            "🖼️ **Sua Coleção de Fundos**\nEscolha qual deseja exibir no seu `+perfil`:",
            view=view,
        )


async def setup(bot):
    await bot.add_cog(Fundos(bot))
