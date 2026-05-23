import re
import discord


class InviteHandler:
    def __init__(self):
        # Expressão regular otimizada para capturar qualquer variação de convite do Discord.
        self.invite_regex = re.compile(
            r"(?:https?://)?(?:www\.)?(?:discord\.gg/|discord(?:app)?\.com/invite/)([a-zA-Z0-9-]+)",
            re.IGNORECASE,
        )

    async def analisar(self, message: discord.Message, config: dict) -> str | None:
        """
        Analisa a mensagem em busca de convites.
        Ignora se o canal, membro ou cargo estiver na whitelist.
        """
        canais_permitidos = config.get("invite_whitelist_channels", [])
        cargos_permitidos = config.get("invite_whitelist_roles", [])
        membros_permitidos = config.get("invite_whitelist_members", [])

        # Checa se o canal está liberado (Ex: chat de divulgação)
        if message.channel.id in canais_permitidos:
            return None

        # Checa se o membro específico está liberado
        if message.author.id in membros_permitidos:
            return None

        if isinstance(message.author, discord.Member):
            user_role_ids = [role.id for role in message.author.roles]
            # Usa 'any' para ver se pelo menos um cargo do usuário está na lista de permitidos
            if any(role_id in cargos_permitidos for role_id in user_role_ids):
                return None

        content = message.content.lower()
        matches = self.invite_regex.findall(content)

        if matches:
            return "Envio não autorizado de convite do Discord. Boboca!"

        return None
