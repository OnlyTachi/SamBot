import discord
from discord.ext import commands
import logging
import io
from pathlib import Path
from easy_pil import Editor, Canvas, Font, load_image_async

from Brain.Memory.DataManager import data_manager


class Perfil(commands.Cog):
    """
    Cog de Perfil Visual: Exibe o status do utilizador num Card gerado por imagem.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Perfil")

    @commands.hybrid_command(
        name="perfil",
        aliases=["profile", "status"],
        description="Vê o teu card de perfil personalizado.",
    )
    async def perfil(self, ctx: commands.Context, membro: discord.Member = None):
        target = membro or ctx.author
        user_id = str(target.id)

        # O ctx.defer() é obrigatório aqui para evitar timeout enquanto a imagem é gerada
        await ctx.defer()

        # 1. Recuperação de Dados
        carteira = data_manager.get_user_data(user_id, "carteira", 0)
        banco = data_manager.get_user_data(user_id, "banco", 0)
        xp = data_manager.get_user_data(user_id, "xp", 0)
        bio = data_manager.get_user_data(
            user_id, "bio", "Usa +setbio para mudares esta frase!"
        )
        emblemas = data_manager.get_user_data(user_id, "emblemas", ["🔰 Novato"])

        nivel = (xp // 1000) + 1
        xp_atual = xp % 1000
        percentagem_xp = (xp_atual / 1000) * 100

        # BUSCA O FUNDO ATIVO
        bg_ativo = data_manager.get_user_data(user_id, "background_ativo", "padrao.png")

        # 2. Configuração do Fundo (Imagem vs Canvas)
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        caminho_bg = base_dir / "Data" / "Assets" / "Backgrounds" / bg_ativo

        if caminho_bg.exists():
            background = Editor(str(caminho_bg)).resize((900, 450))
        else:
            # Fallback caso o arquivo suma
            background = Editor(Canvas((900, 450), color="#1A1A1A"))

        # Adiciona uma camada escura semi-transparente para o texto não sumir no fundo
        overlay = Canvas((900, 450), color=(0, 0, 0, 140))  # 140 é a opacidade (0-255)
        background.paste(Editor(overlay), (0, 0))

        # Carregamento de Fontes
        try:
            f_nome = Font.poppins(variant="bold", size=45)
            f_bio = Font.poppins(variant="italic", size=22)
            f_stats = Font.poppins(variant="regular", size=25)
            f_label = Font.poppins(variant="bold", size=18)
        except:
            f_nome = f_bio = f_stats = f_label = Font.default()

        # 3. Avatar Redondo
        avatar_url = target.display_avatar.url
        try:
            avatar_img = await load_image_async(str(avatar_url))
            avatar = Editor(avatar_img).resize((200, 200)).circle_image()
            background.paste(avatar, (40, 40))
        except Exception as e:
            self.logger.error(f"Erro ao carregar avatar no perfil: {e}")

        # 4. Textos Principais
        # Nome e Nível
        background.text((270, 50), target.display_name, font=f_nome, color="white")
        background.text((270, 105), f"NÍVEL {nivel}", font=f_stats, color="#00FF00")

        # Biografia (com quebra de linha manual simples se for muito longa)
        bio_formatada = bio[:100] + "..." if len(bio) > 100 else bio
        background.text((270, 160), bio_formatada, font=f_bio, color="#CCCCCC")

        # 5. Seção de Economia (Caixas Informativas)
        # Retângulo para o Bolso
        background.rectangle(
            (270, 230), width=280, height=80, fill="#252525", radius=10
        )
        background.text((285, 240), "NO BOLSO", font=f_label, color="#AAAAAA")
        background.text((285, 270), f"🪙 {carteira:,}", font=f_stats, color="white")

        # Retângulo para o Banco
        background.rectangle(
            (570, 230), width=280, height=80, fill="#252525", radius=10
        )
        background.text((585, 240), "NO BANCO", font=f_label, color="#AAAAAA")
        background.text((585, 270), f"🪙 {banco:,}", font=f_stats, color="white")

        # 6. Barra de XP no Fundo
        background.text(
            (40, 360),
            f"PROGRESSO DO NÍVEL: {xp_atual}/1000 XP",
            font=f_label,
            color="#AAAAAA",
        )
        background.bar(
            (40, 390),
            max_width=820,
            height=25,
            percentage=100,
            fill="#333333",
            radius=10,
        )
        background.bar(
            (40, 390),
            max_width=820,
            height=25,
            percentage=percentagem_xp,
            fill="#00FF00",
            radius=10,
        )

        # 7. Emblemas (Lista horizontal simples)
        emblemas_texto = " | ".join(emblemas)
        background.text(
            (270, 325), f"🏅 {emblemas_texto}", font=f_label, color="#FFD700"
        )

        # Envio da Imagem
        file = discord.File(fp=background.image_bytes, filename=f"perfil_{user_id}.png")
        await ctx.send(file=file)

    @commands.hybrid_command(
        name="setbio", description="Altera a tua frase de biografia no perfil."
    )
    async def setbio(self, ctx: commands.Context, *, nova_bio: str):
        if len(nova_bio) > 100:
            return await ctx.send(
                "❌ A biografia é muito longa! Tenta resumir em 100 caracteres."
            )

        data_manager.set_user_data(str(ctx.author.id), "bio", nova_bio)
        await ctx.send(
            "✅ Biografia atualizada! Digita `+perfil` para veres o teu novo card."
        )


async def setup(bot):
    await bot.add_cog(Perfil(bot))
