import discord
from datetime import datetime, timezone


class VozAuditHandler:
    async def on_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> discord.Embed | None:
        # Filtro de Ruído: Se o canal antes e depois for o mesmo, foi apenas um mute/unmute. Ignoramos.
        if before.channel == after.channel:
            return None

        embed = discord.Embed(timestamp=datetime.now(timezone.utc))
        avatar_url = member.display_avatar.url if member.display_avatar else None

        # 1. ENTROU NO CANAL DE VOZ
        if before.channel is None and after.channel is not None:
            embed.color = discord.Color.green()
            embed.description = f"**{member.mention} conectou-se a um canal de voz**"
            embed.set_author(name=f"{member.name} (Entrou na Voz)", icon_url=avatar_url)

            embed.add_field(
                name="Canal",
                value=f"{after.channel.mention} (`{after.channel.name}`)",
                inline=False,
            )

            # Rodapé Técnico
            embed.add_field(name="ID do Usuário", value=f"`{member.id}`", inline=True)
            embed.add_field(
                name="ID do Canal", value=f"`{after.channel.id}`", inline=True
            )

        # 2. SAIU DO CANAL DE VOZ
        elif before.channel is not None and after.channel is None:
            embed.color = discord.Color.red()
            embed.description = f"**{member.mention} desconectou-se do canal de voz**"
            embed.set_author(name=f"{member.name} (Saiu da Voz)", icon_url=avatar_url)

            embed.add_field(
                name="Canal",
                value=f"{before.channel.mention} (`{before.channel.name}`)",
                inline=False,
            )

            # Rodapé Técnico
            embed.add_field(name="ID do Usuário", value=f"`{member.id}`", inline=True)
            embed.add_field(
                name="ID do Canal", value=f"`{before.channel.id}`", inline=True
            )

        # 3. TROCOU DE CANAL DE VOZ
        elif before.channel is not None and after.channel is not None:
            embed.color = discord.Color.gold()
            embed.description = f"**{member.mention} trocou de canal de voz**"
            embed.set_author(
                name=f"{member.name} (Trocou de Canal)", icon_url=avatar_url
            )

            # Colocamos lado a lado para facilitar a leitura visual
            embed.add_field(name="Saiu de", value=before.channel.mention, inline=True)
            embed.add_field(name="Entrou em", value=after.channel.mention, inline=True)

            # Rodapé Técnico
            embed.add_field(name="ID do Usuário", value=f"`{member.id}`", inline=False)

        server_icon = member.guild.icon.url if member.guild.icon else None
        embed.set_footer(text="SamBot", icon_url=server_icon)

        return embed
