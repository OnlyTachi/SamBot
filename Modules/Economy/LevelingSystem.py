# Modules/Economy/LevelingSystem.py
import logging
import os
import random
import re
import time
from io import BytesIO

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from Brain.Memory.DataManager.Connections import data_manager


class LevelingSystem(commands.Cog):
    """Módulo completo de Níveis por Experiência, Perfil Visual e Leaderboard em Imagem."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Leveling")
        self.user_cache = {}

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

    def _get_font(self, path: str, size: int):
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            return ImageFont.load_default()

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

        xp_total_user = users_data["global"][user_id]["xp"]
        data_manager.set_user_data(user_id, "xp", xp_total_user)
        data_manager.save_knowledge("users", users_data)

        xp_novo_local = users_data[guild_id][user_id]["xp"]
        nivel_antigo = xp_antigo_local // 1000
        nivel_novo = xp_novo_local // 1000

        if nivel_novo > nivel_antigo:
            await message.channel.send(
                f"🎉 Parabéns {message.author.mention}! Chegou ao **Nível {nivel_novo}**!",
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
                    except discord.Forbidden:
                        pass

    # ==========================================
    # CARTÃO VISUAL (PROFILE CARD)
    # ==========================================
    @commands.hybrid_command(
        name="level", aliases=["xp"], description="Gera o teu cartão de perfil visual."
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
            bg = Image.open(self.bg_padrao).convert("RGBA").resize((800, 250))
        except (FileNotFoundError, OSError):
            bg = Image.new("RGBA", (800, 250), (30, 33, 36, 255))

        draw = ImageDraw.Draw(bg)
        font_title = self._get_font(self.font_bold, 36)
        font_text = self._get_font(self.font_reg, 26)
        font_small = self._get_font(self.font_reg, 20)

        try:
            avatar_bytes = await membro.display_avatar.replace(
                size=256, format="png"
            ).read()
            avatar = (
                Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((160, 160))
            )
            mask = Image.new("L", (160, 160), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, 160, 160), fill=255)
            avatar.putalpha(mask)
            bg.paste(avatar, (40, 45), avatar)
        except Exception as e:
            self.logger.warning(f"Erro ao carregar avatar no level: {e}")

        draw.text((230, 40), str(membro.name), font=font_title, fill=(255, 255, 255))
        draw.text(
            (230, 95),
            f"Rank: #{colocacao}   |   Nível: {nivel_atual}",
            font=font_text,
            fill=(210, 210, 210),
        )

        xp_texto = f"{xp_progresso} / 1000 XP"
        bbox = draw.textbbox((0, 0), xp_texto, font=font_small)
        text_w = bbox[2] - bbox[0]
        draw.text((750 - text_w, 140), xp_texto, font=font_small, fill=(210, 210, 210))

        bar_x, bar_y, bar_w, bar_h = 230, 175, 520, 28
        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
            radius=14,
            fill=(40, 40, 40, 200),
        )

        fill_w = int(bar_w * percentual)
        if fill_w > 20:
            draw.rounded_rectangle(
                (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h),
                radius=14,
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
        description="Gera uma imagem do Top 5 de Níveis!",
    )
    async def rank(self, ctx: commands.Context, tipo: str = "local"):
        await ctx.defer()

        users_data = data_manager.get_knowledge("users") or {}
        is_global = tipo.lower() == "global"
        fonte_dados = (
            users_data.get("global", {})
            if is_global
            else users_data.get(str(ctx.guild.id), {})
        )

        if not fonte_dados:
            return await ctx.send(
                "❌ Ninguém tem dados de XP salvos nesta categoria ainda!"
            )

        tabela = [
            (u_id, d.get("xp", 0))
            for u_id, d in fonte_dados.items()
            if d.get("xp", 0) > 0
        ]
        tabela.sort(key=lambda x: x[1], reverse=True)
        top_5 = tabela[:5]

        if not top_5:
            return await ctx.send("Ninguém tem XP suficiente para aparecer no ranking.")

        # Criando o Canvas em Pillow puro
        bg = Image.new("RGBA", (900, 650), (20, 20, 20, 255))
        draw = ImageDraw.Draw(bg)

        font_titulo = self._get_font(self.font_bold, 34)
        font_texto = self._get_font(self.font_bold, 22)
        font_pequena = self._get_font(self.font_reg, 18)

        titulo_txt = (
            "🏆 LEADERBOARD - TOP 5 GLOBAL"
            if is_global
            else "🏆 LEADERBOARD - TOP 5 LOCAL"
        )
        bbox_t = draw.textbbox((0, 0), titulo_txt, font=font_titulo)
        t_w = bbox_t[2] - bbox_t[0]
        draw.text(
            ((900 - t_w) // 2, 35), titulo_txt, font=font_titulo, fill=(255, 215, 0)
        )

        y_offset = 110
        for i, (u_id, xp) in enumerate(top_5):
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

            # Renderiza Avatar
            try:
                av_bytes = (
                    await self.bot.session.get(str(url_foto))
                    if hasattr(self.bot, "session")
                    else None
                )
                if not av_bytes:
                    user_target = self.bot.get_user(int(u_id))
                    if user_target:
                        av_raw = await user_target.display_avatar.replace(
                            size=128, format="png"
                        ).read()
                    else:
                        av_raw = await self.bot.user.display_avatar.replace(
                            size=128, format="png"
                        ).read()
                avatar_img = (
                    Image.open(BytesIO(av_raw)).convert("RGBA").resize((70, 70))
                )

                mask = Image.new("L", (70, 70), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 70, 70), fill=255)
                avatar_img.putalpha(mask)
                bg.paste(avatar_img, (40, y_offset), avatar_img)
            except Exception as e:
                self.logger.warning(f"Falha ao processar avatar de {u_id}: {e}")

            medalhas = ["🥇", "🥈", "🥉", "#4", "#5"]
            medalha = medalhas[i] if i < len(medalhas) else f"#{i+1}"
            nivel = (xp // 1000) + 1

            # Card de linha
            draw.text(
                (130, y_offset + 8),
                f"{medalha} {nome}",
                font=font_texto,
                fill=(255, 255, 255),
            )
            xp_fmt = f"{xp:,}".replace(",", ".")
            draw.text(
                (680, y_offset + 12),
                f"LVL {nivel} | {xp_fmt} XP",
                font=font_pequena,
                fill=(0, 255, 128),
            )

            # Barra
            xp_no_nivel = xp % 1000
            porcentagem = xp_no_nivel / 1000.0
            bar_w = 720

            draw.rounded_rectangle(
                (130, y_offset + 46, 130 + bar_w, y_offset + 58),
                radius=6,
                fill=(45, 45, 45, 255),
            )
            fill_sub = int(bar_w * porcentagem)
            if fill_sub > 10:
                draw.rounded_rectangle(
                    (130, y_offset + 46, 130 + fill_sub, y_offset + 58),
                    radius=6,
                    fill=(0, 255, 128, 255),
                )

            y_offset += 100

        buffer = BytesIO()
        bg.save(buffer, format="PNG")
        buffer.seek(0)
        arquivo_imagem = discord.File(fp=buffer, filename="rank.png")
        await ctx.send(file=arquivo_imagem)


async def setup(bot):
    await bot.add_cog(LevelingSystem(bot))
