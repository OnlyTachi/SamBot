import discord
from discord.ext import commands
from discord import app_commands
import colorsys
import io
from PIL import Image


class CorInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="corinfo",
        description="Mostra detalhes e paletas sobre uma cor (Hex ou RGB)!",
    )
    @app_commands.describe(cor="Digite em Hex (ex: #592da1) ou RGB (ex: 89, 45, 161)")
    async def corinfo(self, ctx: commands.Context, *, cor: str):
        cor_limpa = cor.replace(" ", "")

        try:
            if "," in cor_limpa:
                r, g, b = map(int, cor_limpa.split(","))
            else:
                cor_limpa = cor_limpa.lstrip("#")
                if len(cor_limpa) == 3:
                    cor_limpa = "".join([c * 2 for c in cor_limpa])
                r, g, b = tuple(int(cor_limpa[i : i + 2], 16) for i in (0, 2, 4))

            if any(val < 0 or val > 255 for val in (r, g, b)):
                raise ValueError

        except ValueError:
            return await ctx.send(
                "❌ Formato inválido! Use Hex (`#592da1`) ou RGB (`89, 45, 161`).",
                ephemeral=True,
            )

        hex_principal = f"#{r:02x}{g:02x}{b:02x}".lower()
        decimal_val = (255 << 24) | (r << 16) | (g << 8) | b
        if decimal_val >= 2**31:
            decimal_val -= 2**32

        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        hsb_texto = f"{int(h*360)}°, {int(s*100)}%, {int(v*100)}%"

        def hsv_to_hex(hue, sat, val):
            hue = hue % 1.0
            nr, ng, nb = colorsys.hsv_to_rgb(hue, sat, max(0, min(1, val)))
            return f"#{int(nr*255):02x}{int(ng*255):02x}{int(nb*255):02x}".lower()

        triadica_1 = hsv_to_hex(h + 120 / 360, s, v)
        triadica_2 = hsv_to_hex(h + 240 / 360, s, v)
        analoga_1 = hsv_to_hex(h + 30 / 360, s, v)
        analoga_2 = hsv_to_hex(h - 30 / 360, s, v)
        complementar = hsv_to_hex(h + 180 / 360, s, v)

        tons_escuros = [hsv_to_hex(h, s, v - (i * 0.15)) for i in range(1, 7)]
        tons_claros = [
            hsv_to_hex(h, s - (i * 0.15), v + (i * 0.15)) for i in range(1, 7)
        ]

        embed = discord.Embed(
            title="Informações da Cor", color=discord.Color.from_rgb(r, g, b)
        )
        embed.add_field(name="RGB", value=f"`{r}, {g}, {b}`", inline=True)
        embed.add_field(name="Hexadecimal", value=f"`{hex_principal}`", inline=True)
        embed.add_field(name="Decimal", value=f"`{decimal_val}`", inline=True)
        embed.add_field(name="HSB", value=f"`{hsb_texto}`", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(
            name="Tons Escuros",
            value=", ".join(f"`{t}`" for t in tons_escuros),
            inline=False,
        )
        embed.add_field(
            name="Tons Claros",
            value=", ".join(f"`{t}`" for t in tons_claros),
            inline=False,
        )
        embed.add_field(
            name="Triádica", value=f"`{triadica_1}`, `{triadica_2}`", inline=True
        )
        embed.add_field(
            name="Análogas", value=f"`{analoga_1}`, `{analoga_2}`", inline=True
        )
        embed.add_field(name="Complementárias", value=f"`{complementar}`", inline=True)

        imagem_cor = Image.new("RGB", (500, 150), (r, g, b))
        buffer = io.BytesIO()
        imagem_cor.save(buffer, format="PNG")
        buffer.seek(0)
        arquivo_discord = discord.File(fp=buffer, filename="paleta.png")
        embed.set_image(url="attachment://paleta.png")

        await ctx.send(embed=embed, file=arquivo_discord)


async def setup(bot):
    await bot.add_cog(CorInfo(bot))
