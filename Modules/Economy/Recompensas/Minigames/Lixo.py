import discord
import random
import asyncio


class SepararLixoView(discord.ui.View):
    def __init__(self, ctx, categoria_correta):
        # 10 segundos de tempo limite para responder!
        super().__init__(timeout=10.0)
        self.ctx = ctx
        self.categoria_correta = categoria_correta
        self.venceu = False

    # Trava de segurança: Apenas quem digitou +work pode clicar nos botões
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "❌ **Ei!** Estás a tentar roubar o trabalho de outra pessoa?",
                ephemeral=True,
            )
            return False
        return True

    async def processar_escolha(self, interaction: discord.Interaction, escolha: str):
        if escolha == self.categoria_correta:
            self.venceu = True
            await interaction.response.edit_message(
                content=f"✅ **Excelente!** Separou o lixo corretamente no contentor de **{escolha}**.",
                view=None,
            )
        else:
            await interaction.response.edit_message(
                content=f"❌ **Desastre Ecológico!**Jogou o lixo no lugar errado. O correto era **{self.categoria_correta}**.",
                view=None,
            )
        self.stop()

    # --- OS BOTÕES (CONTENTORES) ---
    @discord.ui.button(label="Papel", style=discord.ButtonStyle.primary, emoji="🟦")
    async def btn_papel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.processar_escolha(interaction, "Papel")

    @discord.ui.button(label="Plástico", style=discord.ButtonStyle.danger, emoji="🟥")
    async def btn_plastico(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.processar_escolha(interaction, "Plástico")

    @discord.ui.button(label="Vidro", style=discord.ButtonStyle.success, emoji="🟩")
    async def btn_vidro(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.processar_escolha(interaction, "Vidro")

    @discord.ui.button(
        label="Orgânico", style=discord.ButtonStyle.secondary, emoji="🟫"
    )
    async def btn_organico(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.processar_escolha(interaction, "Orgânico")

    # Se o tempo acabar antes de ele clicar
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(
                content="⏰ **Tempo Esgotado!** Se fosse mais rapido separando o lixo.",
                view=self,
            )
        except:
            pass


# --- A FUNÇÃO PRINCIPAL QUE O WORK.PY VAI CHAMAR ---
async def jogar_separar_lixo(ctx) -> bool:
    itens = {
        "🍌 Casca de Banana": "Orgânico",
        "📰 Jornal de Ontem": "Papel",
        "🍾 Garrafa de Sumos": "Vidro",
        "🥤 Copo Descartável": "Plástico",
        "📦 Caixa de Encomenda": "Papel",
        "🍎 Resto de Maçã": "Orgânico",
        "🫙 Pote de Geleia": "Vidro",
    }

    item_sorteado, categoria = random.choice(list(itens.items()))

    view = SepararLixoView(ctx, categoria)
    view.message = await ctx.send(
        f"🚛 **Trabalho Rápido!** Onde jogar este lixo?\n\n👉 **{item_sorteado}**",
        view=view,
    )

    # Pausa a execução do código até o usuário clicar ou o tempo acabar
    await view.wait()

    return view.venceu
