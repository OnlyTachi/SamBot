import discord
from discord.ext import commands
from discord import app_commands
import urllib.parse


class QRCode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="qrcode",
        aliases=["qr", "gerarqr"],
        description="Gera um QR Code a partir de um link ou texto!",
    )
    @app_commands.describe(conteudo="O link ou texto que será codificado no QR Code")
    async def qrcode(self, ctx: commands.Context, *, conteudo: str):
        await ctx.defer()

        # Codifica o texto para ser usado com segurança em uma URL
        conteudo_url = urllib.parse.quote(conteudo.strip())

        # Define o tamanho do QR Code (300x300 pixels)
        qr_url = f"https://quickchart.io/qr?text={conteudo_url}&size=300"

        # Construção do visual do Embed
        embed = discord.Embed(
            title="🖼️ Seu QR Code foi gerado!",
            description="Aponte a câmera do seu celular para escanear o código abaixo.",
            color=0x2B2D31,
        )
        embed.set_image(url=qr_url)
        embed.set_footer(text=f"Solicitado por {ctx.author.name}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(QRCode(bot))
