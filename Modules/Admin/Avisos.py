import discord
from discord.ext import commands
import logging

from Brain.Memory.DataManager import data_manager


class Avisos(commands.Cog):
    """
    Cog de Avisos: Gerencia o canal público de punições.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Avisos")

    @commands.hybrid_command(
        name="setavisos",
        description="[Admin] Define o canal onde as punições serão anunciadas publicamente.",
    )
    @commands.has_permissions(manage_guild=True)
    async def setavisos(self, ctx: commands.Context, canal: discord.TextChannel):
        guild_id = str(ctx.guild.id)

        # Puxa as configurações usando o nosso DataManager universal
        configs = data_manager.get_knowledge("guild_configs") or {}
        if guild_id not in configs:
            configs[guild_id] = {}

        configs[guild_id]["canal_avisos_id"] = canal.id
        data_manager.save_knowledge("guild_configs", configs)

        embed = discord.Embed(
            title="📢 Canal de Avisos Configurado",
            description=f"Todas as punições públicas (bans, kicks, mutes) serão anunciadas no canal {canal.mention}.",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    async def enviar_aviso(
        self,
        guild: discord.Guild,
        tipo: str,
        membro: discord.Member,
        moderador: discord.Member,
        motivo: str,
    ):
        """
        Função interna que será chamada pelo Moderacao.py e AutoMod.py.
        Não é um comando que os usuários podem digitar.
        """
        guild_id = str(guild.id)
        configs = data_manager.get_knowledge("guild_configs") or {}
        canal_id = configs.get(guild_id, {}).get("canal_avisos_id")

        # Se o servidor não tiver configurado o canal, simplesmente não envia nada
        if not canal_id:
            return

        canal = guild.get_channel(canal_id)
        if not canal:
            return

        cores = {
            "BAN": discord.Color.dark_red(),
            "KICK": discord.Color.orange(),
            "MUTE": discord.Color.yellow(),
            "AVISO": discord.Color.blue(),
            "UNBAN": discord.Color.green(),
            "UNMUTE": discord.Color.green(),
        }

        cor = cores.get(tipo.upper(), discord.Color.red())

        embed = discord.Embed(title=f"⚖️ Punição Aplicada: {tipo.upper()}", color=cor)
        embed.add_field(
            name="👤 Infrator", value=f"{membro.mention} (`{membro.id}`)", inline=True
        )
        embed.add_field(name="👮 Moderador", value=moderador.mention, inline=True)
        embed.add_field(name="📝 Motivo", value=f"*{motivo}*", inline=False)

        # Põe a foto do infrator no canto do aviso
        embed.set_thumbnail(url=membro.display_avatar.url)

        try:
            await canal.send(embed=embed)
        except discord.Forbidden:
            self.logger.warning(
                f"Sem permissão para enviar avisos públicos no canal {canal.name}."
            )


async def setup(bot):
    await bot.add_cog(Avisos(bot))
