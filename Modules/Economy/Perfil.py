# Modules/Economy/Perfil.py
import io
import logging
from pathlib import Path
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from Brain.Memory.DataManager.Connections import data_manager


class Perfil(commands.Cog):
    """Cog de Perfil Visual: Exibe o status do utilizador num Card gerado por imagem."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Perfil")
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.font_path_bold = (
            self.base_dir / "Data" / "Assets" / "MinecraftBold-nMK1.otf"
        )
        self.font_path_reg = (
            self.base_dir / "Data" / "Assets" / "MinecraftRegular-Bmg3.otf"
        )

    def _get_font(self, size: int, bold: bool = False):
        path = self.font_path_bold if bold else self.font_path_reg
        try:
            return ImageFont.truetype(str(path), size)
        except (IOError, OSError):
            return ImageFont.load_default()

    @commands.hybrid_command(
        name="perfil",
        aliases=["profile", "status"],
        description="Vê o teu card de perfil personalizado.",
    )
    async def perfil(self, ctx: commands.Context, membro: discord.Member = None):
        target = membro or ctx.author
        user_id = str(target.id)
        await ctx.defer()

        # 1. Recuperação de Dados
        carteira = data_manager.get_user_data(user_id, "carteira", 0)
        banco = data_manager.get_user_data(user_id, "banco", 0)
        xp = data_manager.get_user_data(user_id, "xp", 0)
        bio = data_manager.get_user_data(
            user_id, "bio", "Usa +setbio para mudares esta frase!"
        )
        emblemas = data_manager.get_user_data(user_id, "emblemas", ["Novato"])
        nivel = (xp // 1000) + 1
        xp_atual = xp % 1000
        percentagem_xp = max(0.0, min(1.0, xp_atual / 1000.0))

        bg_ativo = data_manager.get_user_data(user_id, "background_ativo", "padrao.png")
        caminho_bg = self.base_dir / "Data" / "Assets" / "Backgrounds" / bg_ativo

        # 2. Configuração do Canvas Base e Overlay Escuro
        card_size = (900, 450)
        if caminho_bg.exists():
            try:
                base_img = Image.open(caminho_bg).convert("RGBA").resize(card_size)
            except Exception:
                base_img = Image.new("RGBA", card_size, (26, 26, 26, 255))
        else:
            base_img = Image.new("RGBA", card_size, (26, 26, 26, 255))

        # Overlay escuro semi-transparente (alpha 140)
        overlay = Image.new("RGBA", card_size, (0, 0, 0, 140))
        base_img = Image.alpha_composite(base_img, overlay)
        draw = ImageDraw.Draw(base_img)

        # 3. Avatar Redondo
        try:
            avatar_bytes = await target.display_avatar.replace(
                size=256, format="png"
            ).read()
            avatar_raw = (
                Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((180, 180))
            )

            mask = Image.new("L", (180, 180), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 180, 180), fill=255)
            avatar_raw.putalpha(mask)

            base_img.paste(avatar_raw, (40, 45), avatar_raw)
        except Exception as e:
            self.logger.error(f"Erro ao carregar avatar no perfil: {e}")

        # 4. Tipografia e Textos Principais
        f_nome = self._get_font(38, bold=True)
        f_nivel = self._get_font(22, bold=True)
        f_bio = self._get_font(18, bold=False)
        f_label = self._get_font(16, bold=True)
        f_stats = self._get_font(24, bold=True)

        draw.text((250, 45), target.display_name, font=f_nome, fill=(255, 255, 255))
        draw.text((250, 95), f"NÍVEL {nivel}", font=f_nivel, fill=(0, 255, 128))

        bio_formatada = bio[:90] + "..." if len(bio) > 90 else bio
        draw.text((250, 135), bio_formatada, font=f_bio, fill=(200, 200, 200))

        # 5. Seção de Economia (Caixas Informativas)
        # Bolso
        draw.rounded_rectangle((250, 185, 530, 265), radius=10, fill=(35, 35, 35, 220))
        draw.text((265, 195), "NO BOLSO", font=f_label, fill=(160, 160, 160))
        draw.text((265, 225), f"${carteira:,}", font=f_stats, fill=(255, 255, 255))

        # Banco
        draw.rounded_rectangle((560, 185, 840, 265), radius=10, fill=(35, 35, 35, 220))
        draw.text((575, 195), "NO BANCO", font=f_label, fill=(160, 160, 160))
        draw.text((575, 225), f"${banco:,}", font=f_stats, fill=(255, 255, 255))

        # 6. Emblemas
        emblemas_texto = " | ".join(emblemas)
        draw.text((250, 290), f"★ {emblemas_texto}", font=f_label, fill=(255, 215, 0))

        # 7. Barra de XP
        draw.text(
            (40, 350),
            f"PROGRESSO: {xp_atual}/1000 XP",
            font=f_label,
            fill=(170, 170, 170),
        )

        bar_x, bar_y, bar_w, bar_h = 40, 380, 820, 26
        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
            radius=12,
            fill=(45, 45, 45, 255),
        )

        fill_w = int(bar_w * percentagem_xp)
        if fill_w > 15:
            draw.rounded_rectangle(
                (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h),
                radius=12,
                fill=(88, 101, 242, 255),
            )

        # Saída em buffer
        buffer = io.BytesIO()
        base_img.save(buffer, format="PNG")
        buffer.seek(0)

        file = discord.File(fp=buffer, filename=f"perfil_{user_id}.png")
        await ctx.send(file=file)

    @commands.hybrid_command(
        name="setbio", description="Altera a tua frase de biografia no perfil."
    )
    async def setbio(self, ctx: commands.Context, *, nova_bio: str):
        if len(nova_bio) > 100:
            return await ctx.send(
                "⚠️ A biografia é muito longa! Tenta resumir em 100 caracteres."
            )
        data_manager.set_user_data(str(ctx.author.id), "bio", nova_bio)
        await ctx.send(
            "✅ Biografia atualizada! Digita `+perfil` para veres o teu novo card."
        )


async def setup(bot):
    await bot.add_cog(Perfil(bot))
