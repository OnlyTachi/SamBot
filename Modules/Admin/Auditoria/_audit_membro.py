import discord
from datetime import datetime, timezone


class MembroAuditHandler:

    async def _buscar_autor(
        self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int
    ):
        """
        O Detetive: Vasculha os registos de auditoria para encontrar
        quem alterou os cargos ou o nickname do utilizador.
        """
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if entry.target.id == target_id:
                    return entry.user
        except discord.Forbidden:
            pass
        return None

    async def on_update(
        self, before: discord.Member, after: discord.Member
    ) -> discord.Embed | None:
        embed = discord.Embed(timestamp=datetime.now(timezone.utc))
        enviar = False
        autor_id = "`Desconhecido`"

        # 1. MUDANÇA DE ALCUNHA (NICKNAME)
        if before.nick != after.nick:
            # Procura no registo quem fez a alteração
            autor = await self._buscar_autor(
                after.guild, discord.AuditLogAction.member_update, after.id
            )

            # Se o autor for o próprio bot ou não for encontrado, assume que o utilizador mudou sozinho
            quem_mudou = autor.mention if autor else after.mention
            if autor:
                autor_id = f"`{autor.id}`"
            else:
                autor_id = f"`{after.id}` (Ele Próprio)"

            antes = before.nick if before.nick else before.name
            depois = after.nick if after.nick else after.name

            embed.description = (
                f"**Alcunha de {after.mention} modificada**\nAlterado por: {quem_mudou}"
            )
            embed.color = discord.Color.light_grey()

            avatar_url = after.display_avatar.url if after.display_avatar else None
            embed.set_author(
                name=f"{after.name} (Atualização de Perfil)", icon_url=avatar_url
            )

            embed.add_field(name="Alcunha Antiga", value=f"`{antes}`", inline=False)
            embed.add_field(name="Alcunha Nova", value=f"`{depois}`", inline=False)
            enviar = True

        # 2. MUDANÇA DE CARGOS (ROLES)
        elif before.roles != after.roles:
            autor = await self._buscar_autor(
                after.guild, discord.AuditLogAction.member_role_update, after.id
            )
            quem_mudou = autor.mention if autor else "Moderador Desconhecido"
            if autor:
                autor_id = f"`{autor.id}`"

            # A Matemática de Conjuntos: Descobre o que foi adicionado e o que foi removido
            cargos_adicionados = [
                role for role in after.roles if role not in before.roles
            ]
            cargos_removidos = [
                role for role in before.roles if role not in after.roles
            ]

            embed.description = f"**Cargos de {after.mention} atualizados**\nModificado por: {quem_mudou}"
            embed.color = discord.Color.purple()

            avatar_url = after.display_avatar.url if after.display_avatar else None
            embed.set_author(
                name=f"{after.name} (Atualização de Cargos)", icon_url=avatar_url
            )

            # Adiciona apenas os campos necessários
            if cargos_adicionados:
                txt_add = " ".join([r.mention for r in cargos_adicionados])
                embed.add_field(name="✅ Adicionados", value=txt_add, inline=False)
            if cargos_removidos:
                txt_rem = " ".join([r.mention for r in cargos_removidos])
                embed.add_field(name="❌ Removidos", value=txt_rem, inline=False)

            enviar = True

        # Se não for nem cargos nem nickname, o bot ignora e não envia log
        if not enviar:
            return None

        # 3. RODAPÉ TÉCNICO
        embed.add_field(name="ID do Utilizador", value=f"`{after.id}`", inline=True)
        embed.add_field(name="ID do Responsável", value=autor_id, inline=True)

        server_icon = after.guild.icon.url if after.guild.icon else None
        embed.set_footer(text="SamBot", icon_url=server_icon)

        return embed
