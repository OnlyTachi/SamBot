import discord
from discord.ext import commands
import logging
from easy_pil import Editor, Canvas, Font, load_image_async

from Brain.Memory.DataManager import data_manager


class Ranking(commands.Cog):
    """
    Cog de Ranking Visual: Gera um Leaderboard em imagem usando easy-pil.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Ranking")

    @commands.hybrid_command(
        name="rank",
        aliases=["top", "leaderboard"],
        description="Gera uma imagem com o Top 5 do servidor!",
    )
    async def rank(self, ctx: commands.Context, categoria: str = "xp"):
        """
        Gera o ranking visual. Atualmente otimizado para a categoria XP.
        """

        await ctx.defer()

        # 1. Carrega os dados
        users_path = data_manager.folders["users"] / "users.json"
        todos_usuarios = data_manager._io_read_json(users_path)

        if not todos_usuarios:
            return await ctx.send("🕸️ Ninguém tem dados salvos ainda!")

        # Extrai os dados e ordena do maior para o menor
        tabela = []
        for u_id, dados in todos_usuarios.items():
            xp = dados.get("xp", 0)
            if xp > 0:
                tabela.append((u_id, xp))

        tabela.sort(key=lambda x: x[1], reverse=True)
        top_5 = tabela[:5]

        if not top_5:
            return await ctx.send("Ninguém tem XP suficiente para aparecer no ranking.")

        background = Editor(Canvas((900, 650), color="#141414"))

        try:
            fonte_titulo = Font.poppins(variant="bold", size=45)
            fonte_texto = Font.poppins(variant="regular", size=30)
            fonte_pequena = Font.poppins(variant="regular", size=20)
        except Exception:
            fonte_titulo = Font.default()
            fonte_texto = Font.default()
            fonte_pequena = Font.default()

        background.text(
            (450, 40),
            "🏆 LEADERBOARD - TOP 5 XP 🏆",
            font=fonte_titulo,
            color="#FFD700",
            align="center",
        )

        y_offset = 120  # Posição Y inicial do primeiro colocado

        for i, (u_id, xp) in enumerate(top_5):
            # Tenta pegar o membro no servidor
            membro = ctx.guild.get_member(int(u_id))
            nome = membro.display_name if membro else f"User {u_id}"

            # --- AVATAR REDONDO ---
            url_foto = (
                membro.display_avatar.url
                if membro
                else self.bot.user.display_avatar.url
            )
            try:
                avatar_img = await load_image_async(str(url_foto))
                avatar = Editor(avatar_img).resize((80, 80)).circle_image()
                background.paste(avatar, (40, y_offset))
            except Exception as e:
                self.logger.warning(f"Falha ao baixar avatar de {u_id}: {e}")

            # --- TEXTOS (Nome e Posição) ---
            medalha = f"#{i+1}"
            if i == 0:
                medalha = "🥇"
            elif i == 1:
                medalha = "🥈"
            elif i == 2:
                medalha = "🥉"

            nivel = (xp // 1000) + 1

            # Escreve o Nome à esquerda
            background.text(
                (150, y_offset + 10),
                f"{medalha} {nome}",
                font=fonte_texto,
                color="white",
            )
            # Escreve Nível e XP alinhados à direita
            background.text(
                (860, y_offset + 10),
                f"LVL {nivel} | {xp:,} XP",
                font=fonte_pequena,
                color="#00FF00",
                align="right",
            )

            # --- BARRA DE PROGRESSO ---
            # Calcula a % do nível atual (ex: se tem 1500 XP, o progresso no nível 2 é de 50%)
            xp_no_nivel_atual = xp % 1000
            porcentagem = (xp_no_nivel_atual / 1000) * 100

            # Fundo da barra (Cinza escuro)
            background.bar(
                (150, y_offset + 55),
                max_width=710,
                height=15,
                percentage=100,
                fill="#2b2b2b",
                radius=7,
            )
            # Barra preenchida (Verde SamBot), sobrepondo o fundo
            if porcentagem > 0:
                background.bar(
                    (150, y_offset + 55),
                    max_width=710,
                    height=15,
                    percentage=porcentagem,
                    fill="#00FF00",
                    radius=7,
                )

            # Move o cursor Y para desenhar o próximo jogador mais para baixo
            y_offset += 100

        arquivo_imagem = discord.File(fp=background.image_bytes, filename="rank.png")
        await ctx.send(file=arquivo_imagem)


async def setup(bot):
    await bot.add_cog(Ranking(bot))
