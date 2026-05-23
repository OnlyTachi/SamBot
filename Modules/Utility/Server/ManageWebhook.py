import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json


class Webhooks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Grupo principal "/webhook"
    grupo_webhook = app_commands.Group(
        name="webhook", description="Comandos para gerir Webhooks do servidor"
    )

    # Subgrupos atrelados a "/webhook"
    grupo_enviar = app_commands.Group(
        name="enviar",
        description="Envia mensagens através de um webhook",
        parent=grupo_webhook,
    )
    grupo_editar = app_commands.Group(
        name="editar",
        description="Edita mensagens enviadas por webhooks",
        parent=grupo_webhook,
    )

    # ---------------- ENVIAR ---------------- #

    @grupo_enviar.command(
        name="simples",
        description="Envia uma mensagem de texto simples através de um webhook.",
    )
    @app_commands.describe(url="A URL do Webhook", mensagem="O texto que deseja enviar")
    @app_commands.checks.has_permissions(manage_webhooks=True)
    async def enviar_simples(
        self, interaction: discord.Interaction, url: str, mensagem: str
    ):
        # Ephemeral=True impede que a URL do webhook fique visível no chat para outros utilizadores
        await interaction.response.defer(ephemeral=True)

        async with aiohttp.ClientSession() as session:
            try:
                webhook = discord.Webhook.from_url(url, session=session)
                await webhook.send(
                    content=mensagem,
                    username=interaction.user.display_name,
                    avatar_url=interaction.user.display_avatar.url,
                )
                await interaction.followup.send(
                    "✅ Mensagem simples enviada com sucesso!"
                )
            except Exception as e:
                await interaction.followup.send(f"❌ Ocorreu um erro ao enviar: `{e}`")

    @grupo_enviar.command(
        name="json",
        description="Envia uma mensagem através de uma webhook no formato JSON.",
    )
    @app_commands.describe(
        url="A URL do Webhook",
        dados_json="O código JSON da mensagem (embeds, content, etc)",
    )
    @app_commands.checks.has_permissions(manage_webhooks=True)
    async def enviar_json(
        self, interaction: discord.Interaction, url: str, dados_json: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            dados = json.loads(dados_json)
        except json.JSONDecodeError:
            return await interaction.followup.send(
                "❌ O formato JSON que forneceu é inválido. Verifique se existem erros de sintaxe."
            )

        async with aiohttp.ClientSession() as session:
            try:
                webhook = discord.Webhook.from_url(url, session=session)

                # Converte os blocos "embeds" do JSON para objetos discord.Embed nativos
                embeds = [discord.Embed.from_dict(e) for e in dados.get("embeds", [])]

                await webhook.send(
                    content=dados.get("content"),
                    embeds=embeds,
                    username=dados.get("username", interaction.bot.user.name),
                    avatar_url=dados.get(
                        "avatar_url",
                        (
                            interaction.bot.user.avatar.url
                            if interaction.bot.user.avatar
                            else None
                        ),
                    ),
                )
                await interaction.followup.send("✅ Mensagem JSON enviada com sucesso!")
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro ao enviar a mensagem JSON: `{e}`"
                )

    @grupo_enviar.command(
        name="repostar",
        description="Reposta o conteúdo de uma mensagem existente através do webhook.",
    )
    @app_commands.describe(
        url="A URL do Webhook",
        mensagem_id="O ID da mensagem (deve estar no mesmo canal)",
    )
    @app_commands.checks.has_permissions(manage_webhooks=True)
    async def enviar_repostar(
        self, interaction: discord.Interaction, url: str, mensagem_id: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            # Tenta encontrar a mensagem original no canal onde o comando foi usado
            msg = await interaction.channel.fetch_message(int(mensagem_id))
        except (discord.NotFound, ValueError):
            return await interaction.followup.send(
                "❌ Mensagem não encontrada. Certifique-se de utilizar um ID válido de uma mensagem **neste canal**."
            )

        async with aiohttp.ClientSession() as session:
            try:
                webhook = discord.Webhook.from_url(url, session=session)

                # Clona o conteúdo, os embeds, o autor e a foto
                await webhook.send(
                    content=msg.content,
                    embeds=msg.embeds,
                    username=msg.author.display_name,
                    avatar_url=msg.author.display_avatar.url,
                )
                await interaction.followup.send("✅ Mensagem repostada com sucesso!")
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro ao repostar a mensagem: `{e}`"
                )

    # ---------------- EDITAR ---------------- #

    @grupo_editar.command(
        name="json",
        description="Edita uma mensagem previamente enviada por webhook via JSON.",
    )
    @app_commands.describe(
        url="A URL do Webhook",
        mensagem_id="O ID da mensagem do webhook a ser editada",
        dados_json="O novo código JSON",
    )
    @app_commands.checks.has_permissions(manage_webhooks=True)
    async def editar_json(
        self,
        interaction: discord.Interaction,
        url: str,
        mensagem_id: str,
        dados_json: str,
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            dados = json.loads(dados_json)
        except json.JSONDecodeError:
            return await interaction.followup.send(
                "❌ O formato JSON fornecido é inválido."
            )

        async with aiohttp.ClientSession() as session:
            try:
                webhook = discord.Webhook.from_url(url, session=session)
                embeds = [discord.Embed.from_dict(e) for e in dados.get("embeds", [])]

                # Edita a mensagem alvo no webhook
                await webhook.edit_message(
                    message_id=int(mensagem_id),
                    content=dados.get("content"),
                    embeds=embeds,
                )
                await interaction.followup.send(
                    "✅ Mensagem de webhook editada com sucesso!"
                )
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao editar a mensagem: `{e}`")


async def setup(bot):
    await bot.add_cog(Webhooks(bot))
