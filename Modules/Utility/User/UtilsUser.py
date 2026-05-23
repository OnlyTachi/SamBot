import discord
from discord.ext import commands
from typing import Optional
import time


class UtilsUser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Verifica se o autor está AFK e aplica a tolerância de 5 segundos
        if message.author.id in self.afk_users:
            afk_data = self.afk_users[message.author.id]
            if time.time() - afk_data["time"] > 5:
                del self.afk_users[message.author.id]
                await message.channel.send(
                    f"ℹ️ | Modo AFK desativado! Bem-vindo de volta, {message.author.mention}."
                )

        # Avisa caso mencionem alguém que está AFK
        if message.mentions:
            for mentioned in message.mentions:
                if mentioned.id in self.afk_users:
                    afk_data = self.afk_users[mentioned.id]
                    timestamp = int(afk_data["time"])
                    motivo = afk_data["motivo"]

                    # Usa o timestamp relativo do Discord (<t:TIMESTAMP:R>) que mostra "há X minutos/horas"
                    if motivo:
                        await message.channel.send(
                            f"💤 | {mentioned.mention} está AFK <t:{timestamp}:R>!\n> **Motivo:** {motivo}"
                        )
                    else:
                        await message.channel.send(
                            f"💤 | {mentioned.mention} está AFK <t:{timestamp}:R>!"
                        )

    @commands.hybrid_command(
        name="afk", description="Ativa o modo AFK com ou sem um motivo específico."
    )
    async def afk(self, ctx: commands.Context, *, motivo: Optional[str] = None):
        # Salva o motivo (se houver) e o timestamp exato de quando o AFK foi ativado
        self.afk_users[ctx.author.id] = {"motivo": motivo, "time": time.time()}

        msg = (
            "💤 | Modo AFK ativado! Para a sua conveniência, o modo AFK será "
            "automaticamente desativado quando você falar algo no chat!"
        )

        if motivo:
            msg += f"\n> **Motivo:** {motivo}"

        await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(UtilsUser(bot))
