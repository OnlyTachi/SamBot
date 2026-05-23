import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import format_dt


class InfoServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🖥️"

    @commands.hybrid_group(
        name="servidor",
        aliases=["server"],
        invoke_without_command=True,
        description="Comandos informativos sobre o servidor.",
    )
    async def servidor_grupo(self, ctx: commands.Context):
        embed = discord.Embed(
            title="ℹ️ Comando: servidor",
            description="Use este grupo de comandos para obter informações visuais e detalhadas sobre o servidor atual.",
            color=0x5865F2,  # Blurple padrão do Discord
        )

        embed.add_field(
            name="🛠️ Subcomandos Disponíveis",
            value=(
                "`-servidor info` — Mostra estatísticas completas do servidor.\n"
                "`-servidor icone` — Exibe e envia o link do ícone do servidor.\n"
                "`-servidor banner` — Exibe o banner de fundo do servidor (se houver).\n"
                "`-servidor splash` — Exibe a tela de splash de convite (se houver)."
            ),
            inline=False,
        )

        embed.add_field(
            name="💡 Dica",
            value="Você também pode utilizar estes comandos como Slash Commands usando `/servidor`!",
            inline=False,
        )

        embed.set_footer(
            text=f"Solicitado por {ctx.author.display_name} • Servidor",
            icon_url=ctx.author.display_avatar.url,
        )

        await ctx.send(embed=embed)

    @servidor_grupo.command(
        name="info", description="Mostra informações detalhadas sobre o servidor."
    )
    async def servidor_info(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            return await ctx.send(
                "❌ Este comando só pode ser usado dentro de um servidor!"
            )

        embed = discord.Embed(
            title=f"🏰 {guild.name}",
            description=guild.description
            or "Sem descrição definida para este servidor.",
            color=0x5865F2,
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        # Informações Gerais
        embed.add_field(name="🆔 ID do Servidor", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👑 Dono", value=f"{guild.owner.mention}", inline=True)
        embed.add_field(
            name="📅 Criado em",
            value=format_dt(guild.created_at, style="F"),
            inline=False,
        )

        # Membros
        humanos = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        embed.add_field(
            name="👥 Membros",
            value=f"Total: `{guild.member_count}`\n👤 Humanos: `{humanos}`\n🤖 Bots: `{bots}`",
            inline=True,
        )

        # Canais e Impulsos
        embed.add_field(
            name="🛡️ Recursos",
            value=f"Cargos: `{len(guild.roles)}`\nEmojis: `{len(guild.emojis)}`\nStickers: `{len(guild.stickers)}`",
            inline=True,
        )

        embed.add_field(
            name="💎 Impulsos",
            value=f"Nível: `{guild.premium_tier}`\nBoosts: `{guild.premium_subscription_count}`",
            inline=True,
        )

        embed.set_footer(
            text=f"Solicitado por {ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=embed)

    @servidor_grupo.command(
        name="icone",
        aliases=["icon", "avatar"],
        description="Mostra o ícone do servidor.",
    )
    async def servidor_icone(self, ctx: commands.Context):
        if not ctx.guild.icon:
            return await ctx.send("❌ Este servidor não possui um ícone definido.")

        embed = discord.Embed(title=f"🖼️ Ícone de {ctx.guild.name}", color=0x5865F2)
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @servidor_grupo.command(name="banner", description="Mostra o banner do servidor.")
    async def servidor_banner(self, ctx: commands.Context):
        if not ctx.guild.banner:
            return await ctx.send("❌ Este servidor não possui um banner definido.")

        embed = discord.Embed(title=f"🖼️ Banner de {ctx.guild.name}", color=0x5865F2)
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.send(embed=embed)

    @servidor_grupo.command(
        name="splash",
        description="Mostra a tela de splash (fundo de convite) do servidor.",
    )
    async def servidor_splash(self, ctx: commands.Context):
        if not ctx.guild.splash:
            return await ctx.send(
                "❌ Este servidor não possui uma imagem de splash definida."
            )

        embed = discord.Embed(title=f"🖼️ Splash de {ctx.guild.name}", color=0x5865F2)
        embed.set_image(url=ctx.guild.splash.url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(InfoServer(bot))
