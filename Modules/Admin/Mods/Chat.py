import discord
from discord.ext import commands
import logging


class ModChat(commands.Cog):
    """Comandos para gestão e controle de tráfego nos canais."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.ModChat")

    @commands.hybrid_command(
        name="clear",
        aliases=["limpar", "purge"],
        description="[Admin] Apaga mensagens de um canal.",
    )
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, quantidade: int):
        if quantidade <= 0 or quantidade > 100:
            return await ctx.send(
                "❌ Você só pode apagar entre 1 e 100 mensagens por vez.",
                ephemeral=True,
            )

        await ctx.defer(ephemeral=True)
        try:
            apagadas = await ctx.channel.purge(limit=quantidade + 1)
            await ctx.send(
                f"🧹 **{len(apagadas) - 1}** mensagens foram apagadas com sucesso!",
                ephemeral=True,
            )
        except Exception as e:
            await ctx.send(f"❌ Erro ao apagar mensagens: `{e}`", ephemeral=True)

    @commands.hybrid_command(
        name="lock",
        aliases=["trancar"],
        description="[Admin] Impede membros de enviar mensagens neste canal.",
    )
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context):
        cargo_padrao = ctx.guild.default_role
        await ctx.channel.set_permissions(cargo_padrao, send_messages=False)

        embed = discord.Embed(
            title="🔒 Canal Bloqueado",
            description="Este canal foi trancado pela moderação. Apenas administradores podem enviar mensagens no momento.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="unlock",
        aliases=["destrancar"],
        description="[Admin] Libera o canal novamente para os membros.",
    )
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context):
        cargo_padrao = ctx.guild.default_role
        await ctx.channel.set_permissions(cargo_padrao, send_messages=None)

        embed = discord.Embed(
            title="🔓 Canal Desbloqueado",
            description="O canal foi liberado! Vocês já podem voltar a conversar normalmente.",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ModChat(bot))
