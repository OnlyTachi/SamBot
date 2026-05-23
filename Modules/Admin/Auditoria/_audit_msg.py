import discord
from datetime import datetime


class MsgAuditHandler:
    async def on_delete(self, message: discord.Message) -> discord.Embed:
        # Cor vermelha vibrante para exclusões
        embed = discord.Embed(color=discord.Color.brand_red(), timestamp=datetime.now())

        # O "set_author" cria aquele topo elegante com a foto redondinha do usuário
        avatar_url = (
            message.author.display_avatar.url if message.author.display_avatar else None
        )
        embed.set_author(
            name=f"{message.author.name} - Mensagem Deletada", icon_url=avatar_url
        )

        # Canal onde ocorreu
        embed.description = f"**Canal:** {message.channel.mention}"

        # Conteúdo da mensagem com o prefixo '>>>' para virar um bloco de citação no Discord
        conteudo = (
            message.content[:4000]
            if message.content
            else "*Mensagem sem texto (apenas mídia/embed)*"
        )
        embed.add_field(name="Conteúdo", value=f">>> {conteudo}", inline=False)

        # O CAÇADOR DE ARQUIVOS (Se tiver imagem ou anexo apagado)
        if message.attachments:
            anexos = "\n".join(
                [f"📎 [{a.filename}]({a.url})" for a in message.attachments]
            )
            embed.add_field(name="Arquivos Anexados", value=anexos, inline=False)

            # Tenta pegar a primeira imagem e colocar um "print" dela no log
            primeiro_anexo = message.attachments[0]
            if primeiro_anexo.content_type and primeiro_anexo.content_type.startswith(
                "image/"
            ):
                embed.set_image(url=primeiro_anexo.proxy_url)

        # O "set_footer" coloca o texto miudinho no final do card com os IDs (vital para staffs)
        embed.set_footer(
            text=f"ID do Usuário: {message.author.id} • ID da Mensagem: {message.id}"
        )

        return embed

    async def on_edit(
        self, before: discord.Message, after: discord.Message
    ) -> discord.Embed:
        # Cor Dourada/Amarela para edições
        embed = discord.Embed(color=discord.Color.gold(), timestamp=datetime.now())

        avatar_url = (
            before.author.display_avatar.url if before.author.display_avatar else None
        )
        embed.set_author(
            name=f"{before.author.name} - Mensagem Editada", icon_url=avatar_url
        )

        # Adiciona um link rápido para o moderador pular direto para a mensagem
        embed.description = f"**Canal:** {before.channel.mention} | [Ir para a mensagem]({after.jump_url})"

        # Uso de blocos de código (```texto```) para facilitar a leitura da edição
        antes = before.content[:1000] or "*Vazio*"
        depois = after.content[:1000] or "*Vazio*"

        embed.add_field(name="Antiga", value=f"```\n{antes}\n```", inline=False)
        embed.add_field(name="Nova", value=f"```\n{depois}\n```", inline=False)

        embed.set_footer(
            text=f"ID do Usuário: {before.author.id} • ID da Mensagem: {before.id}"
        )

        return embed
