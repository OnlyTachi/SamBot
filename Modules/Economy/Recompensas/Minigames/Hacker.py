import discord
import random
import string
import asyncio
import io
from pathlib import Path

# Biblioteca de processamento de imagens
from PIL import Image, ImageDraw, ImageFont


async def jogar_hacker(ctx) -> bool:
    """
    Minigame de digitação rápida simulando quebra de criptografia.
    Gera uma imagem com um hash aleatório usando uma fonte customizada.
    """
    codigo = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    img = Image.new("RGB", (320, 120), color=(15, 15, 15))
    draw = ImageDraw.Draw(img)

    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    caminho_fonte = base_dir / "Data" / "Assets" / "MinecraftRegular-Bmg3.otf"

    try:
        fonte = ImageFont.truetype(str(caminho_fonte), 50)
    except IOError:
        # Fallback seguro caso o caminho da fonte falhe
        fonte = ImageFont.load_default()

    draw.text((40, 30), codigo, fill=(0, 255, 0), font=fonte)

    for _ in range(8):
        y = random.randint(0, 120)
        draw.line([(0, y), (320, y)], fill=(0, 100, 0), width=2)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    arquivo_img = discord.File(buffer, filename="firewall_hash.png")

    msg = await ctx.send(
        "💻 **INVASÃO EM ANDAMENTO...**\n"
        "O firewall exige uma chave de autenticação. Digite o código exibido na imagem abaixo no chat em **15 segundos**!",
        file=arquivo_img,
    )

    def check(m):
        # A mensagem precisa ser do mesmo usuário, no mesmo canal
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        resposta = await ctx.bot.wait_for("message", timeout=15.0, check=check)

        if resposta.content.upper() == codigo:
            await ctx.send(
                "✅ **Acesso Concedido!** Você quebrou a criptografia a tempo e extraiu os dados bancários."
            )
            return True
        else:
            await ctx.send(
                f"❌ **Acesso Negado!** O hash correto era `{codigo}`. A sua conexão foi bloqueada pelo sistema de segurança."
            )
            return False

    except asyncio.TimeoutError:
        await ctx.send(
            "⏰ **Tempo Esgotado!** O administrador da rede rastreou o seu IP. Fuga imediata!"
        )
        return False
