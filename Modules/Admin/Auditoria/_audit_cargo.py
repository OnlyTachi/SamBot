import discord
from datetime import datetime, timezone


class CargoAuditHandler:

    async def _buscar_autor(
        self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int
    ):
        """
        O Detetive: Vasculha os últimos 5 logs de auditoria do servidor
        para descobrir quem criou ou apagou o cargo.
        """
        try:
            # Puxa os últimos 5 eventos específicos (criação ou exclusão de cargo)
            async for entry in guild.audit_logs(limit=5, action=action):
                if entry.target.id == target_id:
                    return entry.user
        except discord.Forbidden:
            # Caso o bot perca a permissão de ver o log de auditoria
            pass
        return None

    async def on_create(self, role: discord.Role) -> discord.Embed:
        # Busca quem foi o moderador responsável pela criação
        autor = await self._buscar_autor(
            role.guild, discord.AuditLogAction.role_create, role.id
        )

        embed = discord.Embed(
            description=f"**Novo cargo criado no servidor: {role.mention}**",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        if autor:
            avatar_url = autor.display_avatar.url if autor.display_avatar else None
            embed.set_author(name=f"{autor.name} (Criou um Cargo)", icon_url=avatar_url)
            autor_id = f"`{autor.id}`"
        else:
            embed.set_author(name="Moderador Desconhecido (Criou um Cargo)")
            autor_id = "`Desconhecido`"

        # Detalhes do Cargo
        embed.add_field(name="Nome do Cargo", value=f"`{role.name}`", inline=True)
        embed.add_field(name="Cor Padrão", value=f"`{str(role.color)}`", inline=True)

        # O Rodapé Técnico alinhado
        embed.add_field(name="ID do Moderador", value=autor_id, inline=True)
        embed.add_field(name="ID do Cargo", value=f"`{role.id}`", inline=True)

        server_icon = role.guild.icon.url if role.guild.icon else None
        embed.set_footer(text="SamBot", icon_url=server_icon)

        return embed

    async def on_delete(self, role: discord.Role) -> discord.Embed:
        # Busca quem foi o moderador responsável pela exclusão
        autor = await self._buscar_autor(
            role.guild, discord.AuditLogAction.role_delete, role.id
        )

        # Nota: Quando um cargo é apagado, a menção (<@&ID>) quebra.
        # Por isso usamos o nome do cargo em negrito em vez de mention.
        embed = discord.Embed(
            description=f"**Um cargo foi apagado: `{role.name}`**",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )

        if autor:
            avatar_url = autor.display_avatar.url if autor.display_avatar else None
            embed.set_author(
                name=f"{autor.name} (Apagou um Cargo)", icon_url=avatar_url
            )
            autor_id = f"`{autor.id}`"
        else:
            embed.set_author(name="Moderador Desconhecido (Apagou um Cargo)")
            autor_id = "`Desconhecido`"

        # O Rodapé Técnico alinhado
        embed.add_field(name="ID do Moderador", value=autor_id, inline=True)
        embed.add_field(name="ID do Cargo", value=f"`{role.id}`", inline=True)

        server_icon = role.guild.icon.url if role.guild.icon else None
        embed.set_footer(text="SamBot", icon_url=server_icon)

        return embed
