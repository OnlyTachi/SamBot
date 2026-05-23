import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone
from Brain.Memory.DataManager import data_manager


class Avisos(commands.Cog):
    """Módulo responsável pelo Mural Público de Punições (Mural da Vergonha/Perdão)."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Avisos")

    @commands.hybrid_command(
        name="configavisos",
        description="[Admin] Define o canal onde as punições serão anunciadas.",
    )
    @commands.has_permissions(manage_guild=True)
    async def configavisos(self, ctx: commands.Context, canal: discord.TextChannel):
        configs = data_manager.get_knowledge("guild_configs") or {}
        guild_id = str(ctx.guild.id)
        if guild_id not in configs:
            configs[guild_id] = {}

        configs[guild_id]["avisos_channel"] = canal.id
        data_manager.save_knowledge("guild_configs", configs)

        await ctx.send(
            f"✅ Mural de Avisos configurado com sucesso para o canal {canal.mention}.",
            ephemeral=True,
        )

    async def enviar_aviso(
        self,
        guild: discord.Guild,
        tipo: str,
        infrator: discord.User | discord.Member,
        moderador: discord.User | discord.Member,
        motivo: str,
    ):
        """
        Gera um Embed profissional e envia para o canal de avisos do servidor (se configurado).
        """
        configs = data_manager.get_knowledge("guild_configs") or {}
        canal_id = configs.get(str(guild.id), {}).get("avisos_channel")

        if not canal_id:
            return  # Servidor não configurou o canal de avisos ainda

        canal = guild.get_channel(canal_id)
        if not canal:
            return

        embed = discord.Embed(timestamp=datetime.now(timezone.utc))

        # --- ESTILIZAÇÃO DINÂMICA PREMIUM ---
        if tipo == "BAN":
            embed.title, embed.color = "🔨 Membro Banido", discord.Color.dark_red()
        elif tipo == "KICK":
            embed.title, embed.color = "👢 Membro Expulso", discord.Color.orange()
        elif tipo == "MUTE":
            embed.title, embed.color = "🔇 Membro Silenciado", discord.Color.yellow()
        elif tipo == "UNBAN":
            embed.title, embed.color = "🕊️ Desbanimento (Unban)", discord.Color.green()
        elif tipo == "UNMUTE":
            embed.title, embed.color = (
                "🔊 Silenciamento Removido",
                discord.Color.green(),
            )
        elif tipo == "AVISO":
            embed.title, embed.color = "⚠️ Advertência Oficial", discord.Color.gold()
        elif tipo == "APELO ACEITO":
            embed.title, embed.color = (
                "📜 Apelo Aceito (Punição Revogada)",
                discord.Color.teal(),
            )
            embed.description = (
                f"O apelo de **{infrator.mention}** foi analisado e **aprovado**."
            )
        elif tipo == "AUTOMOD":
            embed.title, embed.color = (
                "🛡️ Intervenção do AutoMod",
                discord.Color.purple(),
            )
        else:
            embed.title, embed.color = (
                "📝 Atualização de Moderação",
                discord.Color.light_grey(),
            )

        # Adiciona a descrição padrão para punições normais
        if tipo != "APELO ACEITO":
            embed.description = (
                f"O utilizador **{infrator.mention}** sofreu uma sanção."
            )

        # Caixa de motivo em formato de código para destaque
        embed.add_field(
            name="Motivo / Justificativa", value=f"```\n{motivo}\n```", inline=False
        )

        # Coloca a foto do punido no canto superior direito
        avatar_infrator = (
            infrator.display_avatar.url if infrator.display_avatar else None
        )
        embed.set_thumbnail(url=avatar_infrator)

        # O Moderador que aplicou a ação fica na barra superior
        avatar_mod = moderador.display_avatar.url if moderador.display_avatar else None
        embed.set_author(
            name=f"Moderador: {moderador.display_name}", icon_url=avatar_mod
        )

        # Rodapé
        embed.set_footer(text=f"ID do Alvo: {infrator.id} • SamBot")

        try:
            await canal.send(embed=embed)
        except discord.Forbidden:
            self.logger.warning(
                f"Sem permissão para enviar avisos no canal {canal.name}."
            )


async def setup(bot):
    await bot.add_cog(Avisos(bot))
