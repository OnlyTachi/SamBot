import discord
from discord.ext import commands
import logging
import datetime
import time

from ._utils import checar_hierarquia, disparar_aviso
from ._appeals import notificar_infrator
from Brain.Memory.DataManager import data_manager


class ModPunicoes(commands.Cog):
    """Comandos para aplicação inteligente e escalonada de punições."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.ModPunicoes")

    # ==========================================
    # SISTEMA DE ADVERTÊNCIAS E ESCALONAMENTO
    # ==========================================

    @commands.hybrid_command(
        name="warn",
        aliases=["avisar", "advertir"],
        description="[Admin] Dá uma advertência e escala punições automaticamente.",
    )
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context, membro: discord.Member, *, motivo: str):
        if not await checar_hierarquia(ctx, membro, self.bot):
            return
        await ctx.defer(ephemeral=True)

        # Carrega o banco de dados de avisos
        guild_id = str(ctx.guild.id)
        user_id = str(membro.id)
        configs = data_manager.get_knowledge("guild_configs") or {}

        if guild_id not in configs:
            configs[guild_id] = {}
        if "warns" not in configs[guild_id]:
            configs[guild_id]["warns"] = {}
        if user_id not in configs[guild_id]["warns"]:
            configs[guild_id]["warns"][user_id] = []

        # Adiciona o novo aviso
        novo_aviso = {
            "mod_id": ctx.author.id,
            "motivo": motivo,
            "data": int(time.time()),
        }
        configs[guild_id]["warns"][user_id].append(novo_aviso)
        data_manager.save_knowledge("guild_configs", configs)

        total_avisos = len(configs[guild_id]["warns"][user_id])

        embed = discord.Embed(title="⚠️ Membro Advertido", color=discord.Color.yellow())
        embed.description = f"**{membro.display_name}** recebeu seu aviso **#{total_avisos}**.\n**Motivo:** {motivo}"
        await ctx.send(embed=embed)
        await disparar_aviso(ctx, self.bot, "AVISO", membro, motivo)

        # --- LÓGICA DE ESCALONAMENTO (PUNIÇÃO AUTOMÁTICA) ---
        try:
            if total_avisos == 3:
                # 3 Avisos = Mute de 1 hora automático
                tempo = discord.utils.utcnow() + datetime.timedelta(hours=1)
                await membro.timeout(tempo, reason="AutoMod: Atingiu 3 Advertências.")
                await notificar_infrator(
                    membro,
                    ctx.guild,
                    ctx.author,
                    "MUTE",
                    "Acúmulo de 3 advertências.",
                    self.bot,
                )
                await ctx.channel.send(
                    f"🔇 **{membro.mention} foi silenciado por 1 hora** por atingir 3 advertências."
                )

            elif total_avisos >= 5:
                # 5 Avisos = Ban Automático
                await notificar_infrator(
                    membro,
                    ctx.guild,
                    ctx.author,
                    "BAN",
                    "Acúmulo de 5 advertências.",
                    self.bot,
                )
                await membro.ban(reason="AutoMod: Atingiu 5 Advertências.")
                await ctx.channel.send(
                    f"🔨 **{membro.mention} foi banido permanentemente** por atingir o limite máximo de 5 advertências."
                )
            else:
                # Se não bateu a cota grave, manda só um aviso simples na DM
                try:
                    await membro.send(
                        f"⚠️ Você recebeu uma advertência em **{ctx.guild.name}**.\nAcúmulo atual: {total_avisos}/5\nMotivo: {motivo}"
                    )
                except:
                    pass
        except Exception as e:
            self.logger.error(f"Erro no escalonamento automático de warn: {e}")

    @commands.hybrid_command(
        name="warns",
        aliases=["avisos", "warnlist"],
        description="[Admin] Lista as advertências de um membro.",
    )
    @commands.has_permissions(manage_messages=True)
    async def warns(self, ctx: commands.Context, membro: discord.Member):
        configs = data_manager.get_knowledge("guild_configs") or {}
        avisos = (
            configs.get(str(ctx.guild.id), {}).get("warns", {}).get(str(membro.id), [])
        )

        if not avisos:
            return await ctx.send(
                f"✅ O membro **{membro.display_name}** tem uma ficha limpa! (0 Avisos)",
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"Ficha Criminal: {membro.name}", color=discord.Color.orange()
        )
        for idx, aviso in enumerate(avisos, 1):
            data_str = f"<t:{aviso['data']}:d>"
            embed.add_field(
                name=f"Aviso #{idx} ({data_str})",
                value=f"**Motivo:** {aviso['motivo']}\n**Moderador:** <@{aviso['mod_id']}>",
                inline=False,
            )

        embed.set_footer(text=f"Total acumulado: {len(avisos)}")
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="unwarn",
        aliases=["delwarn", "perdoar"],
        description="[Admin] Remove uma ou todas as advertências de um membro.",
    )
    @commands.has_permissions(manage_messages=True)
    async def unwarn(
        self, ctx: commands.Context, membro: discord.Member, numero_aviso: int
    ):
        configs = data_manager.get_knowledge("guild_configs") or {}
        guild_id, user_id = str(ctx.guild.id), str(membro.id)

        if (
            guild_id not in configs
            or "warns" not in configs[guild_id]
            or user_id not in configs[guild_id]["warns"]
        ):
            return await ctx.send(
                f"❌ O membro não possui advertências registradas.", ephemeral=True
            )

        avisos = configs[guild_id]["warns"][user_id]

        if numero_aviso == 0:
            # Opção Secreta: Digitar 0 apaga TODOS os avisos do usuário
            configs[guild_id]["warns"][user_id] = []
            data_manager.save_knowledge("guild_configs", configs)
            return await ctx.send(
                f"✅ **Ficha Limpa!** Todos os avisos de {membro.mention} foram perdoados.",
                ephemeral=True,
            )

        # O usuário digita 1, mas para a lista do python (array), é o index 0. Subtraímos 1.
        index = numero_aviso - 1
        if index < 0 or index >= len(avisos):
            return await ctx.send(
                f"❌ Aviso `#{numero_aviso}` não existe. Verifique com `/warns`.",
                ephemeral=True,
            )

        removido = avisos.pop(index)
        data_manager.save_knowledge("guild_configs", configs)

        await ctx.send(
            f"✅ O aviso **#{numero_aviso}** (\"{removido['motivo']}\") de {membro.mention} foi removido com sucesso.",
            ephemeral=True,
        )

    # ==========================================
    # PUNIÇÕES COMUNS COM INTEGRAÇÃO DE APELOS
    # ==========================================

    @commands.hybrid_command(
        name="ban", description="[Admin] Bane um membro do servidor."
    )
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        *,
        motivo: str = "Violação das regras.",
    ):
        if not await checar_hierarquia(ctx, membro, self.bot):
            return
        await ctx.defer(ephemeral=True)

        try:
            # O notificar_infrator envia a mensagem e o Botão de Apelo na DM ANTES de banir.
            await notificar_infrator(
                membro, ctx.guild, ctx.author, "BAN", motivo, self.bot
            )
            await membro.ban(reason=f"Banido por {ctx.author} - Motivo: {motivo}")

            embed = discord.Embed(
                title="🔨 Membro Banido",
                description=f"**{membro.display_name}** foi banido.\n**Motivo:** {motivo}",
                color=discord.Color.dark_red(),
            )
            await ctx.send(embed=embed)
            await disparar_aviso(ctx, self.bot, "BAN", membro, motivo)
        except Exception as e:
            await ctx.send(f"❌ Erro ao tentar banir: `{e}`")

    @commands.hybrid_command(
        name="unban", description="[Admin] Desbane um membro usando o ID."
    )
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: commands.Context,
        user_id: str,
        *,
        motivo: str = "Apelo aceito / Erro na punição.",
    ):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(
                user, reason=f"Desbanido por {ctx.author} - Motivo: {motivo}"
            )

            configs = data_manager.get_knowledge("guild_configs") or {}
            if "appeals" in configs.get(str(ctx.guild.id), {}):
                configs[str(ctx.guild.id)]["appeals"].pop(str(user_id), None)
                data_manager.save_knowledge("guild_configs", configs)

            embed = discord.Embed(
                title="🕊️ Membro Desbanido",
                description=f"**{user.name}** foi desbanido.\n**Motivo:** {motivo}",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed, ephemeral=True)
            await disparar_aviso(ctx, self.bot, "UNBAN", user, motivo)

        except discord.NotFound:
            # Captura especificamente o erro de usuário não encontrado nos bans (Unknown Ban)
            await ctx.send(
                f"❌ O usuário com ID `{user_id}` não está banido neste servidor.",
                ephemeral=True,
            )
        except Exception as e:
            # Fallback de segurança para a mensagem "Unknown Ban"
            if "10026" in str(e) or "Unknown Ban" in str(e):
                await ctx.send(
                    f"❌ O usuário com ID `{user_id}` não está banido neste servidor.",
                    ephemeral=True,
                )
            else:
                await ctx.send(
                    f"❌ Erro inesperado ao tentar desbanir: `{e}`", ephemeral=True
                )

    @commands.hybrid_command(
        name="kick", description="[Admin] Expulsa um membro do servidor."
    )
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        *,
        motivo: str = "Violação das regras.",
    ):
        if not await checar_hierarquia(ctx, membro, self.bot):
            return
        try:
            await notificar_infrator(
                membro, ctx.guild, ctx.author, "KICK", motivo, self.bot
            )
            await membro.kick(reason=f"Expulso por {ctx.author} - Motivo: {motivo}")

            embed = discord.Embed(
                title="👢 Membro Expulso",
                description=f"**{membro.display_name}** foi expulso.\n**Motivo:** {motivo}",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed, ephemeral=True)
            await disparar_aviso(ctx, self.bot, "KICK", membro, motivo)
        except Exception as e:
            await ctx.send(f"❌ Erro ao expulsar: `{e}`")

    @commands.hybrid_command(
        name="mute", aliases=["timeout"], description="[Admin] Silencia um membro."
    )
    @commands.has_permissions(moderate_members=True)
    async def mute(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        minutos: int,
        *,
        motivo: str = "Comportamento inadequado.",
    ):
        if not await checar_hierarquia(ctx, membro, self.bot):
            return
        if minutos <= 0 or minutos > 40320:
            return await ctx.send("❌ O tempo deve ser entre 1 minuto e 28 dias.")
        try:
            await notificar_infrator(
                membro,
                ctx.guild,
                ctx.author,
                "MUTE",
                f"{motivo} ({minutos} min)",
                self.bot,
            )
            tempo = discord.utils.utcnow() + datetime.timedelta(minutes=minutos)
            await membro.timeout(tempo, reason=f"Mutado por {ctx.author} - {motivo}")

            embed = discord.Embed(
                title="🔇 Membro Silenciado",
                description=f"**{membro.display_name}** foi silenciado por {minutos} min.\n**Motivo:** {motivo}",
                color=discord.Color.yellow(),
            )
            await ctx.send(embed=embed, ephemeral=True)
            await disparar_aviso(
                ctx, self.bot, "MUTE", membro, f"{motivo} ({minutos} min)"
            )
        except Exception as e:
            await ctx.send(f"❌ Erro ao silenciar: `{e}`")

    @commands.hybrid_command(
        name="unmute", description="[Admin] Remove o silenciamento de um membro."
    )
    @commands.has_permissions(moderate_members=True)
    async def unmute(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        *,
        motivo: str = "Punição revogada.",
    ):
        if not await checar_hierarquia(ctx, membro, self.bot):
            return
        try:
            await membro.timeout(
                None, reason=f"Desmutado por {ctx.author} - Motivo: {motivo}"
            )
            embed = discord.Embed(
                title="🔊 Membro Desmutado",
                description=f"O silenciamento de **{membro.display_name}** foi removido.\n**Motivo:** {motivo}",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed, ephemeral=True)
            await disparar_aviso(ctx, self.bot, "UNMUTE", membro, motivo)
        except Exception as e:
            await ctx.send(f"❌ Erro ao desmutar: `{e}`")


async def setup(bot):
    await bot.add_cog(ModPunicoes(bot))
