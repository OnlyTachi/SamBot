import discord
from discord.ext import commands
from discord import app_commands
import re


class GerenciamentoExpressoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    grupo_expressions = app_commands.Group(
        name="expressions", description="Gerenciamento de expressões do servidor"
    )
    grupo_emoji_mod = app_commands.Group(
        name="emoji",
        description="Gerencia emojis do servidor",
        parent=grupo_expressions,
    )
    grupo_sticker_mod = app_commands.Group(
        name="sticker",
        description="Gerencia figurinhas do servidor",
        parent=grupo_expressions,
    )

    # ---------------- EMOJIS ---------------- #

    @grupo_emoji_mod.command(
        name="add", description="Adiciona um novo emoji ao servidor."
    )
    @app_commands.describe(
        nome="Nome do emoji (sem espaços)", ficheiro="A imagem ou GIF do emoji"
    )
    @app_commands.checks.has_permissions(manage_expressions=True)
    async def emoji_add(
        self, interaction: discord.Interaction, nome: str, ficheiro: discord.Attachment
    ):
        await interaction.response.defer()

        try:
            imagem_bytes = await ficheiro.read()
            novo_emoji = await interaction.guild.create_custom_emoji(
                name=nome.replace(" ", "_"),
                image=imagem_bytes,
                reason=f"Adicionado por {interaction.user}",
            )
            await interaction.followup.send(
                f"✅ O emoji {novo_emoji} (`:{novo_emoji.name}:`) foi adicionado com sucesso!"
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Ocorreu um erro ao adicionar o emoji. Verifique se o ficheiro não excede o limite de tamanho. Detalhes: `{e.text}`"
            )

    @grupo_emoji_mod.command(name="remove", description="Remove um emoji do servidor.")
    @app_commands.describe(emoji="O emoji que deseja remover")
    @app_commands.checks.has_permissions(manage_expressions=True)
    async def emoji_remove(self, interaction: discord.Interaction, emoji: str):
        match = re.search(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>", emoji)
        if not match:
            return await interaction.response.send_message(
                "❌ Forneça um emoji válido para remover.", ephemeral=True
            )

        emoji_id = int(match.group(1))
        emoji_obj = interaction.guild.get_emoji(emoji_id)

        if not emoji_obj:
            return await interaction.response.send_message(
                "❌ Não consegui encontrar este emoji no servidor.", ephemeral=True
            )

        await emoji_obj.delete(reason=f"Removido por {interaction.user}")
        await interaction.response.send_message("✅ Emoji removido com sucesso!")

    # ---------------- FIGURINHAS (STICKERS) ---------------- #

    @grupo_sticker_mod.command(
        name="add", description="Adiciona uma figurinha (sticker) ao servidor."
    )
    @app_commands.describe(
        nome="Nome da figurinha",
        ficheiro="A imagem para a figurinha",
        emoji_relacionado="Um emoji padrão associado",
    )
    @app_commands.checks.has_permissions(manage_expressions=True)
    async def sticker_add(
        self,
        interaction: discord.Interaction,
        nome: str,
        ficheiro: discord.Attachment,
        emoji_relacionado: str,
    ):
        await interaction.response.defer()

        try:
            # Converte o ficheiro enviado para um objeto utilizável na API
            file_obj = await ficheiro.to_file()
            novo_sticker = await interaction.guild.create_sticker(
                name=nome,
                description=f"Adicionado via SamBot",
                emoji=emoji_relacionado,
                file=file_obj,
                reason=f"Adicionado por {interaction.user}",
            )
            await interaction.followup.send(
                f"✅ Figurinha `{novo_sticker.name}` adicionada com sucesso!"
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Erro ao adicionar figurinha. Detalhes: `{e.text}`"
            )

    @grupo_sticker_mod.command(
        name="remove", description="Remove uma figurinha do servidor."
    )
    @app_commands.describe(nome_exato="O nome exato da figurinha para remover")
    @app_commands.checks.has_permissions(manage_expressions=True)
    async def sticker_remove(self, interaction: discord.Interaction, nome_exato: str):
        # Procura a figurinha pelo nome
        sticker_obj = discord.utils.get(interaction.guild.stickers, name=nome_exato)

        if not sticker_obj:
            return await interaction.response.send_message(
                "❌ Não encontrei nenhuma figurinha com esse nome.", ephemeral=True
            )

        await sticker_obj.delete(reason=f"Removida por {interaction.user}")
        await interaction.response.send_message(
            f"✅ Figurinha `{nome_exato}` removida com sucesso!"
        )


async def setup(bot):
    await bot.add_cog(GerenciamentoExpressoes(bot))
