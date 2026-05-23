import discord
from discord.ext import commands
import logging
from Brain.Memory.DataManager import data_manager


class LevelAdmin(commands.Cog):
    """Módulo de Administração do Sistema de Níveis e XP."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.LevelAdmin")

    def _get_config(self, guild_id: str):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if guild_id not in configs:
            configs[guild_id] = {}
        if "leveling" not in configs[guild_id]:
            configs[guild_id]["leveling"] = {
                "rewards": {},  # "nivel": cargo_id
                "no_xp_channels": [],  # [canal_id, canal_id]
                "role_boosts": {},  # "cargo_id": 1.5 (Multiplicador)
            }
        return configs, configs[guild_id]["leveling"]

    # ==========================================
    # PAINEL GERAL
    # ==========================================
    @commands.hybrid_command(
        name="levelpainel",
        description="[Admin] Vê todas as configurações de XP do servidor.",
    )
    @commands.has_permissions(manage_guild=True)
    async def levelpainel(self, ctx: commands.Context):
        configs, level_config = self._get_config(str(ctx.guild.id))

        embed = discord.Embed(
            title="⚙️ Painel de Configuração de Níveis", color=discord.Color.blurple()
        )

        # 1. Cargos de Recompensa
        recompensas = level_config.get("rewards", {})
        if recompensas:
            txt_recompensas = "\n".join(
                [
                    f"**Nível {lvl}:** <@&{role_id}>"
                    for lvl, role_id in sorted(
                        recompensas.items(), key=lambda x: int(x[0])
                    )
                ]
            )
        else:
            txt_recompensas = "Nenhuma recompensa configurada."
        embed.add_field(
            name="🎁 Recompensas por Nível", value=txt_recompensas, inline=False
        )

        # 2. Multiplicadores de XP (Boosts)
        boosts = level_config.get("role_boosts", {})
        if boosts:
            txt_boosts = "\n".join(
                [f"<@&{role_id}>: **{mult}x XP**" for role_id, mult in boosts.items()]
            )
        else:
            txt_boosts = "Nenhum cargo tem bônus de XP."
        embed.add_field(name="🚀 Boosts de XP (Cargos)", value=txt_boosts, inline=False)

        # 3. Canais sem XP
        canais = level_config.get("no_xp_channels", [])
        if canais:
            txt_canais = " ".join([f"<#{c_id}>" for c_id in canais])
        else:
            txt_canais = "Todos os canais dão XP."
        embed.add_field(
            name="🔇 Canais Bloqueados (Sem XP)", value=txt_canais, inline=False
        )

        embed.set_footer(
            text="Use os comandos /levelrecompensa, /levelboost e /levelcanal para alterar."
        )
        await ctx.send(embed=embed)

    # ==========================================
    # RECOMPENSAS (Add / Edit / Remove)
    # ==========================================
    @commands.hybrid_command(
        name="levelrecompensa",
        description="[Admin] Adiciona ou remove um cargo de recompensa por nível.",
    )
    @commands.has_permissions(manage_roles=True)
    async def levelrecompensa(
        self, ctx: commands.Context, nivel: int, cargo: discord.Role = None
    ):
        configs, level_config = self._get_config(str(ctx.guild.id))

        if cargo is None:
            # Se não enviar o cargo, o bot assume que é para DELETAR a recompensa
            if str(nivel) in level_config["rewards"]:
                del level_config["rewards"][str(nivel)]
                data_manager.save_knowledge("guild_configs", configs)
                return await ctx.send(
                    f"✅ Recompensa do **Nível {nivel}** removida com sucesso.",
                    ephemeral=True,
                )
            else:
                return await ctx.send(
                    f"❌ O Nível {nivel} não possui recompensa configurada.",
                    ephemeral=True,
                )

        # Adiciona ou Atualiza (Edit) a recompensa
        level_config["rewards"][str(nivel)] = cargo.id
        data_manager.save_knowledge("guild_configs", configs)
        await ctx.send(
            f"✅ **Nível {nivel}** agora recompensa os membros com o cargo {cargo.mention}.",
            ephemeral=True,
        )

    # ==========================================
    # MULTIPLICADORES / BOOSTS (Add / Edit / Remove)
    # ==========================================
    @commands.hybrid_command(
        name="levelboost",
        description="[Admin] Dá um multiplicador de XP para um cargo (Ex: 1.5 ou 2.0).",
    )
    @commands.has_permissions(manage_guild=True)
    async def levelboost(
        self, ctx: commands.Context, cargo: discord.Role, multiplicador: float
    ):
        configs, level_config = self._get_config(str(ctx.guild.id))

        if multiplicador <= 1.0:
            # Se o multiplicador for 1.0 ou menor, nós deletamos o boost
            if str(cargo.id) in level_config["role_boosts"]:
                del level_config["role_boosts"][str(cargo.id)]
                data_manager.save_knowledge("guild_configs", configs)
                return await ctx.send(
                    f"✅ Boost do cargo {cargo.mention} foi removido.", ephemeral=True
                )
            return await ctx.send(
                "❌ Multiplicadores devem ser maiores que 1.0.", ephemeral=True
            )

        # Limita a 5x para evitar quebrar o sistema
        if multiplicador > 5.0:
            multiplicador = 5.0

        level_config["role_boosts"][str(cargo.id)] = multiplicador
        data_manager.save_knowledge("guild_configs", configs)
        await ctx.send(
            f"✅ Membros com o cargo {cargo.mention} agora ganharão **{multiplicador}x mais XP**!",
            ephemeral=True,
        )

    # ==========================================
    # CANAIS BLOQUEADOS (Add / Remove)
    # ==========================================
    @commands.hybrid_command(
        name="levelcanal",
        description="[Admin] Bloqueia ou desbloqueia o ganho de XP num canal de texto.",
    )
    @commands.has_permissions(manage_channels=True)
    async def levelcanal(self, ctx: commands.Context, canal: discord.TextChannel):
        configs, level_config = self._get_config(str(ctx.guild.id))

        if canal.id in level_config["no_xp_channels"]:
            level_config["no_xp_channels"].remove(canal.id)
            data_manager.save_knowledge("guild_configs", configs)
            await ctx.send(
                f"✅ O canal {canal.mention} foi **desbloqueado** e voltou a dar XP.",
                ephemeral=True,
            )
        else:
            level_config["no_xp_channels"].append(canal.id)
            data_manager.save_knowledge("guild_configs", configs)
            await ctx.send(
                f"🔇 O canal {canal.mention} foi **bloqueado**. Ninguém ganhará XP lá.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(LevelAdmin(bot))
