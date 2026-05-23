import discord
from discord.ext import commands
from discord import app_commands
import re


class EmojiInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    grupo_emoji = app_commands.Group(
        name="emoji", description="Comandos relacionados a emojis"
    )

    @grupo_emoji.command(
        name="info", description="Mostra as informações de um emoji personalizado."
    )
    @app_commands.describe(
        emoji="O emoji que deseja inspecionar (apenas emojis personalizados)"
    )
    async def info(self, interaction: discord.Interaction, emoji: str):
        match = re.match(r"<(a?):([a-zA-Z0-9\_]+):([0-9]+)>$", emoji.strip())

        if not match:
            return await interaction.response.send_message(
                "❌ Por favor, forneça um emoji personalizado válido do Discord.",
                ephemeral=True,
            )

        animado = bool(match.group(1))
        nome = match.group(2)
        emoji_id = int(match.group(3))

        extensao = "gif" if animado else "png"
        url_emoji = f"https://cdn.discordapp.com/emojis/{emoji_id}.{extensao}"

        emoji_obj = self.bot.get_emoji(emoji_id)

        embed = discord.Embed(title=f"Emoji: {nome}", color=discord.Color.blurple())
        embed.set_thumbnail(url=url_emoji)
        embed.add_field(name="ID", value=f"`{emoji_id}`", inline=True)
        embed.add_field(name="Animado?", value="Sim" if animado else "Não", inline=True)

        if emoji_obj:
            embed.add_field(
                name="Servidor de Origem",
                value=f"`{emoji_obj.guild.name}`",
                inline=False,
            )
            criado_em = discord.utils.format_dt(emoji_obj.created_at, style="F")
            embed.add_field(name="Criado em", value=criado_em, inline=False)
        else:
            embed.add_field(
                name="Download",
                value=f"[Clique aqui para baixar a imagem]({url_emoji})",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(EmojiInfo(bot))
