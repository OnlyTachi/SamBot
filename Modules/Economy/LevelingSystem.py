import discord
from discord.ext import commands
import logging
import time
import random
import re
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from easy_pil import Editor, Canvas, Font, load_image_async

from Brain.Memory.DataManager import data_manager


class LevelingSystem(commands.Cog):
    """Módulo completo de Níveis por Experiência, Perfil Visual e Leaderboard em Imagem."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Leveling")
        self.user_cache = {}

        # Caminhos de Assets (PIL)
        self.base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.bg_padrao = os.path.join(
            self.base_dir, "Data", "Assets", "Background", "xp.jpeg"
        )
        self.font_bold = os.path.join(
            self.base_dir, "Data", "Assets", "MinecraftBold-nMK1.otf"
        )
        self.font_reg = os.path.join(
            self.base_dir, "Data", "Assets", "MinecraftRegular-Bmg3.otf"
        )

    def remover_repeticoes(self, texto: str) -> str:
        return re.sub(r"(.)\1+", r"\1", texto)

    # ==========================================
    # MOTOR DE XP E ANTI-FARM
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        agora = time.time()

        configs = data_manager.get_knowledge("guild_configs") or {}
        level_config = configs.get(guild_id, {}).get("leveling", {})

        if message.channel.id in level_config.get("no_xp_channels", []):
            return

        content = message.content.strip()
        if len(content) <= 5:
            return

        cache = self.user_cache.get(user_id, {"last_time": 0, "last_content": ""})
        if content.lower() == cache["last_content"].lower():
            return

        tempo_simulado = len(content) / 7.0
        tempo_decorrido = agora - cache["last_time"]
        if tempo_decorrido < tempo_simulado:
            return

        conteudo_limpo = self.remover_repeticoes(content)
        if len(conteudo_limpo) <= 12:
            return

        self.user_cache[user_id] = {"last_time": agora, "last_content": content}

        min_xp = max(1, int(len(conteudo_limpo) / 7))
        max_xp = max(1, int(len(conteudo_limpo) / 4))
        xp_ganho = random.randint(min_xp, max_xp)
        if xp_ganho > 35:
            xp_ganho = 35

        boosts = level_config.get("role_boosts", {})
        maior_multiplicador = 1.0
        for role in message.author.roles:
            if str(role.id) in boosts:
                mult = boosts[str(role.id)]
                if mult > maior_multiplicador:
                    maior_multiplicador = mult

        xp_ganho = int(xp_ganho * maior_multiplicador)

        users_data = data_manager.get_knowledge("users") or {}
        if guild_id not in users_data:
            users_data[guild_id] = {}
        if user_id not in users_data[guild_id]:
            users_data[guild_id][user_id] = {"xp": 0, "mensagens": 0}
        if "global" not in users_data:
            users_data["global"] = {}
        if user_id not in users_data["global"]:
            users_data["global"][user_id] = {"xp": 0, "mensagens": 0}

        xp_antigo_local = users_data[guild_id][user_id]["xp"]
        users_data[guild_id][user_id]["xp"] += xp_ganho
        users_data[guild_id][user_id]["mensagens"] += 1
        users_data["global"][user_id]["xp"] += xp_ganho
        users_data["global"][user_id]["mensagens"] += 1
        xp_novo_local = users_data[guild_id][user_id]["xp"]

        nivel_antigo = xp_antigo_local // 1000
        nivel_novo = xp_novo_local // 1000

        if nivel_novo > nivel_antigo:
            await message.channel.send(
                f"🎉 Parabéns {message.author.mention}! Chegou o **Nível {nivel_novo}**!",
                delete_after=15.0,
            )

            recompensas = level_config.get("rewards", {})
            cargo_id = recompensas.get(str(nivel_novo))
            if cargo_id:
                cargo = message.guild.get_role(int(cargo_id))
                if cargo:
                    try:
                        await message.author.add_roles(
                            cargo, reason=f"Recompensa de Nível {nivel_novo}"
                        )
                        await message.channel.send(
                            f"🎖️ {message.author.mention} desbloqueou o cargo **{cargo.name}**!",
                            delete_after=15.0,
                        )
                    except discord.Forbidden:
                        pass

        data_manager.save_knowledge("users", users_data)

    # ==========================================
    # CARTÃO VISUAL (PROFILE CARD)
    # ==========================================
    @commands.hybrid_command(
        name="level",
        aliases=["perfil", "xp"],
        description="Gera o teu cartão de perfil visual.",
    )
    async def level(self, ctx: commands.Context, membro: discord.Member = None):
        membro = membro or ctx.author
        await ctx.defer()

        users_data = data_manager.get_knowledge("users") or {}
        guild_id, user_id = str(ctx.guild.id), str(membro.id)

        perfil_local = users_data.get(guild_id, {}).get(user_id, {"xp": 0})
        xp_total = perfil_local["xp"]

        nivel_atual = xp_total // 1000
        xp_progresso = xp_total % 1000
        percentual = xp_progresso / 1000.0

        ranking_local = sorted(
            users_data.get(guild_id, {}).items(),
            key=lambda x: x[1].get("xp", 0),
            reverse=True,
        )
        colocacao = next(
            (i for i, v in enumerate(ranking_local, 1) if v[0] == user_id),
            len(ranking_local) + 1,
        )
        if xp_total == 0:
            colocacao = "N/A"

        try:
            bg = Image.open(self.bg_padrao).convert("RGBA")
            bg = bg.resize((800, 250))
        except FileNotFoundError:
            bg = Image.new("RGBA", (800, 250), (30, 33, 36, 255))

        draw = ImageDraw.Draw(bg)

        try:
            font_title = ImageFont.truetype(self.font_bold, 42)
            font_text = ImageFont.truetype(self.font_reg, 32)
            font_small = ImageFont.truetype(self.font_reg, 24)
        except IOError:
            font_title = font_text = font_small = ImageFont.load_default()

        avatar_bytes = await membro.display_avatar.replace(
            size=256, format="png"
        ).read()
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
        avatar = avatar.resize((160, 160))

        mask = Image.new("L", (160, 160), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 160, 160), fill=255)
        avatar.putalpha(mask)

        bg.paste(avatar, (40, 45), avatar)

        draw.text((230, 40), str(membro.name), font=font_title, fill=(255, 255, 255))
        draw.text(
            (230, 100),
            f"Rank: #{colocacao}   |   Nível: {nivel_atual}",
            font=font_text,
            fill=(210, 210, 210),
        )

        xp_texto = f"{xp_progresso} / 1000 XP"
        bbox = draw.textbbox((0, 0), xp_texto, font=font_small)
        text_w = bbox[2] - bbox[0]
        draw.text((750 - text_w, 145), xp_texto, font=font_small, fill=(210, 210, 210))

        bar_x, bar_y = 230, 175
        bar_w, bar_h = 520, 30

        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
            radius=15,
            fill=(40, 40, 40, 200),
        )

        fill_w = int(bar_w * percentual)
        if fill_w > 20:
            draw.rounded_rectangle(
                (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h),
                radius=15,
                fill=(88, 101, 242, 255),
            )

        buffer = BytesIO()
        bg.save(buffer, format="PNG")
        buffer.seek(0)

        file = discord.File(buffer, filename=f"rank_{membro.name}.png")
        await ctx.send(file=file)

    # ==========================================
    # LEADERBOARD (RANKING VISUAL)
    # ==========================================
    @commands.hybrid_command(
        name="rank",
        aliases=["top", "leaderboard"],
        description="Gera uma imagem incrível com o Top 5 de Níveis!",
    )
    async def rank(self, ctx: commands.Context, tipo: str = "local"):
        """Gera o ranking visual. Aceita 'local' ou 'global'."""
        await ctx.defer()

        # Carrega dados unificados via data_manager
        users_data = data_manager.get_knowledge("users") or {}
        is_global = tipo.lower() == "global"
        fonte_dados = (
            users_data.get("global", {})
            if is_global
            else users_data.get(str(ctx.guild.id), {})
        )

        if not fonte_dados:
            return await ctx.send(
                "🕸️ Ninguém tem dados de XP salvos nesta categoria ainda!"
            )

        # Extrai os dados e ordena do maior para o menor
        tabela = []
        for u_id, dados in fonte_dados.items():
            xp = dados.get("xp", 0)
            if xp > 0:
                tabela.append((u_id, xp))

        tabela.sort(key=lambda x: x[1], reverse=True)
        top_5 = tabela[:5]

        if not top_5:
            return await ctx.send("Ninguém tem XP suficiente para aparecer no ranking.")

        # Inicia a tela de pintura usando easy_pil
        background = Editor(Canvas((900, 650), color="#141414"))

        try:
            fonte_titulo = Font.poppins(variant="bold", size=45)
            fonte_texto = Font.poppins(variant="regular", size=30)
            fonte_pequena = Font.poppins(variant="regular", size=20)
        except Exception:
            fonte_titulo = Font.default()
            fonte_texto = Font.default()
            fonte_pequena = Font.default()

        titulo_txt = (
            "🏆 LEADERBOARD - TOP 5 GLOBAL 🌍"
            if is_global
            else "🏆 LEADERBOARD - TOP 5 LOCAL 🏆"
        )
        background.text(
            (450, 40),
            titulo_txt,
            font=fonte_titulo,
            color="#FFD700",
            align="center",
        )

        y_offset = 120  # Posição Y inicial da primeira linha

        for i, (u_id, xp) in enumerate(top_5):
            # Busca de membros adaptada para local ou global
            nome = f"User {u_id}"
            url_foto = self.bot.user.display_avatar.url

            if is_global:
                membro_obj = self.bot.get_user(int(u_id))
                if membro_obj:
                    nome = membro_obj.name
                    url_foto = membro_obj.display_avatar.url
            else:
                membro = ctx.guild.get_member(int(u_id))
                if membro:
                    nome = membro.display_name
                    url_foto = membro.display_avatar.url

            # --- AVATAR REDONDO ---
            try:
                avatar_img = await load_image_async(str(url_foto))
                avatar = Editor(avatar_img).resize((80, 80)).circle_image()
                background.paste(avatar, (40, y_offset))
            except Exception as e:
                self.logger.warning(f"Falha ao baixar avatar de {u_id}: {e}")

            # --- MEDALHAS E IDENTIFICAÇÃO ---
            medalha = f"#{i+1}"
            if i == 0:
                medalha = "🥇"
            elif i == 1:
                medalha = "🥈"
            elif i == 2:
                medalha = "🥉"

            nivel = (xp // 1000) + 1

            # Nome / Exibição
            background.text(
                (150, y_offset + 10),
                f"{medalha} {nome}",
                font=fonte_texto,
                color="white",
            )

            # Nível e Valor formatados
            xp_fmt = f"{xp:,}".replace(",", ".")
            background.text(
                (860, y_offset + 10),
                f"LVL {nivel} | {xp_fmt} XP",
                font=fonte_pequena,
                color="#00FF00",
                align="right",
            )

            # --- BARRA DE PROGRESSO ---
            xp_no_nivel_atual = xp % 1000
            porcentagem = (xp_no_nivel_atual / 1000) * 100

            # Fundo cinza escuro
            background.bar(
                (150, y_offset + 55),
                max_width=710,
                height=15,
                percentage=100,
                fill="#2b2b2b",
                radius=7,
            )
            # Preenchimento Verde sobreposto
            if porcentagem > 0:
                background.bar(
                    (150, y_offset + 55),
                    max_width=710,
                    height=15,
                    percentage=porcentagem,
                    fill="#00FF00",
                    radius=7,
                )

            y_offset += 100

        arquivo_imagem = discord.File(fp=background.image_bytes, filename="rank.png")
        await ctx.send(file=arquivo_imagem)


async def setup(bot):
    await bot.add_cog(LevelingSystem(bot))
