import discord
from discord.ext import commands
from discord import app_commands


class ConvitesInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    grupo_convite = app_commands.Group(
        name="convite", description="Gerencia e busca informações de convites"
    )

    @grupo_convite.command(
        name="info",
        description="Mostra informações detalhadas sobre um link de convite.",
    )
    @app_commands.describe(
        codigo="O link ou o código do convite (ex: discord.gg/codigo)"
    )
    async def convite_info(self, interaction: discord.Interaction, codigo: str):
        codigo = (
            codigo.replace("https://discord.gg/", "")
            .replace("discord.gg/", "")
            .split("/")[-1]
        )

        try:
            # Faz a busca do convite na API do Discord
            convite = await self.bot.fetch_invite(
                codigo, with_counts=True, with_expiration=True
            )

            embed = discord.Embed(
                title=f"🔗 Informações do Convite: {convite.code}",
                color=discord.Color.green(),
            )

            if convite.guild:
                embed.add_field(
                    name="Servidor", value=f"`{convite.guild.name}`", inline=True
                )
                embed.set_thumbnail(
                    url=convite.guild.icon.url if convite.guild.icon else None
                )

            embed.add_field(
                name="Canal Alvo", value=f"`{convite.channel.name}`", inline=True
            )

            if convite.inviter:
                embed.add_field(
                    name="Criado por", value=f"{convite.inviter.mention}", inline=True
                )

            embed.add_field(
                name="Usos",
                value=(
                    f"`{convite.uses}`"
                    if convite.uses is not None
                    else "`Desconhecido`"
                ),
                inline=True,
            )
            embed.add_field(
                name="Membros no Servidor",
                value=f"`{convite.approximate_member_count}`",
                inline=True,
            )

            await interaction.response.send_message(embed=embed)

        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Não consegui encontrar esse convite. Ele pode ser inválido ou já ter expirado.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ocorreu um erro ao buscar o convite: `{e}`", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ConvitesInfo(bot))
