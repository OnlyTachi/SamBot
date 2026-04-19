import discord
from discord.ext import commands
import logging
from pathlib import Path

from Brain.Memory.DataManager import data_manager


class ConfirmBuyView(discord.ui.View):
    """View com botões de confirmar ou cancelar compra do Fundo."""

    def __init__(self, user_id, produto, carteira_atual):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.produto = produto
        self.carteira = carteira_atual

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return str(interaction.user.id) == self.user_id

    @discord.ui.button(
        label="Confirmar Compra", style=discord.ButtonStyle.success, emoji="✅"
    )
    async def btn_confirmar(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        preco = self.produto["preco"]
        novo_fundo = self.produto["valor"]

        # Faz a transação
        novo_saldo = self.carteira - preco
        data_manager.set_user_data(self.user_id, "carteira", novo_saldo)

        comprados = data_manager.get_user_data(
            self.user_id, "backgrounds_comprados", ["padrao.png"]
        )
        comprados.append(novo_fundo)

        data_manager.set_user_data(self.user_id, "backgrounds_comprados", comprados)
        data_manager.set_user_data(self.user_id, "background_ativo", novo_fundo)

        embed = discord.Embed(
            title="🛍️ Compra Realizada com Sucesso!", color=discord.Color.green()
        )
        embed.description = f"O fundo **{self.produto['nome']}** foi adicionado à sua coleção e equipado automaticamente!\nUse `+perfil` para ver o resultado."
        embed.set_footer(text=f"Saldo restante: 🪙 {novo_saldo:,}")

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=None, embed=embed, view=self, attachments=[]
        )

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_cancelar(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="❌ **Compra cancelada.** O seu saldo não foi alterado.",
            view=self,
            attachments=[],
        )


class ShopDropdown(discord.ui.Select):
    def __init__(self, catalogo):
        options = []
        for item_id, info in catalogo.items():
            desc = f"🪙 {info['preco']} | {info['descricao'][:50]}"
            options.append(
                discord.SelectOption(
                    label=info["nome"], value=item_id, description=desc, emoji="🛒"
                )
            )

        super().__init__(
            placeholder="Selecione um item para comprar...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.catalogo = catalogo

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        produto = self.catalogo[item_id]
        preco = produto["preco"]
        user_id = str(interaction.user.id)

        carteira = data_manager.get_user_data(user_id, "carteira", 0)
        if carteira < preco:
            return await interaction.response.send_message(
                f"❌ **Saldo Insuficiente!** Você tem apenas 🪙 {carteira:,}, mas o item custa 🪙 {preco:,}.",
                ephemeral=True,
            )

        tipo = produto.get("tipo", "consumivel")

        # --- LÓGICA DE PREVIEW PARA FUNDOS ---
        if tipo == "background":
            comprados = data_manager.get_user_data(
                user_id, "backgrounds_comprados", ["padrao.png"]
            )
            novo_fundo = produto["valor"]

            if novo_fundo in comprados:
                return await interaction.response.send_message(
                    "⚠️ **Você já possui este fundo na sua coleção!**", ephemeral=True
                )

            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            caminho_bg = base_dir / "Data" / "Assets" / "Backgrounds" / novo_fundo

            if not caminho_bg.exists():
                return await interaction.response.send_message(
                    "❌ Erro interno: O arquivo da imagem não foi encontrado no servidor.",
                    ephemeral=True,
                )

            arquivo_img = discord.File(str(caminho_bg), filename="preview.png")
            view_confirmacao = ConfirmBuyView(user_id, produto, carteira)

            await interaction.response.send_message(
                content=f"👀 **PREVIEW DO ITEM:** {produto['nome']}\nPreço: 🪙 {preco:,}\n\nDeseja confirmar a compra?",
                file=arquivo_img,
                view=view_confirmacao,
                ephemeral=True,
            )
            return

        elif tipo == "emblema":
            emblemas_atuais = data_manager.get_user_data(
                user_id, "emblemas", ["🔰 Novato"]
            )
            novo_emblema = produto["valor"]

            if novo_emblema in emblemas_atuais:
                return await interaction.response.send_message(
                    "⚠️ **Você já possui este emblema!**", ephemeral=True
                )

            emblemas_atuais.append(novo_emblema)
            data_manager.set_user_data(user_id, "emblemas", emblemas_atuais)

            # Compra direta de emblema
            novo_saldo = carteira - preco
            data_manager.set_user_data(user_id, "carteira", novo_saldo)

            embed = discord.Embed(
                title="🛍️ Compra Realizada!", color=discord.Color.green()
            )
            embed.description = f"Você comprou **{produto['nome']}** por 🪙 {preco:,}!\n🏅 *O emblema já foi adicionado ao seu `+perfil`!*"
            embed.set_footer(text=f"Saldo restante: 🪙 {novo_saldo:,}")
            await interaction.response.edit_message(
                content=None, embed=embed, view=None
            )


class ShopView(discord.ui.View):
    def __init__(self, catalogo):
        super().__init__(timeout=120)
        self.add_item(ShopDropdown(catalogo))


class Loja(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="loja", aliases=["shop"], description="Abre a loja para gastar moedas."
    )
    async def loja(self, ctx: commands.Context):
        catalogo = data_manager.get_knowledge("shop") or {}
        if not catalogo:
            return await ctx.send("❌ A loja está fechada no momento.")

        embed = discord.Embed(
            title="🏪 Loja da SamBot",
            description="Use o menu abaixo para selecionar e comprar itens!",
            color=discord.Color.gold(),
        )
        for item_id, info in catalogo.items():
            icone = "🖼️" if info.get("tipo") == "background" else "🏅"
            embed.add_field(
                name=f"{icone} {info['nome']} — 🪙 {info['preco']:,}",
                value=f"*{info['descricao']}*",
                inline=False,
            )

        await ctx.send(embed=embed, view=ShopView(catalogo))


async def setup(bot):
    await bot.add_cog(Loja(bot))
