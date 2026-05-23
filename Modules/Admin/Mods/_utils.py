import discord


async def checar_hierarquia(ctx, membro: discord.Member, bot) -> bool:
    """Verifica se o bot e o autor têm permissão hierárquica para punir o membro."""
    if membro.id == ctx.author.id:
        await ctx.send("❌ Você não pode punir a si mesmo!", ephemeral=True)
        return False
    if membro.id == bot.user.id:
        await ctx.send("❌ Eu não vou me punir!", ephemeral=True)
        return False
    if ctx.author.top_role <= membro.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send(
            "❌ Você não pode punir alguém com um cargo igual ou superior ao seu.",
            ephemeral=True,
        )
        return False
    if ctx.guild.me.top_role <= membro.top_role:
        await ctx.send(
            "❌ Eu não tenho permissão para punir este membro (o cargo dele é maior que o meu).",
            ephemeral=True,
        )
        return False
    return True


async def disparar_aviso(ctx, bot, tipo: str, membro: discord.Member, motivo: str):
    """Busca o módulo de Avisos e aciona a função de anúncio público."""
    avisos_cog = bot.get_cog("Avisos")
    if avisos_cog:
        await avisos_cog.enviar_aviso(ctx.guild, tipo, membro, ctx.author, motivo)
