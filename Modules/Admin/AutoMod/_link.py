import re
import discord
import aiohttp
import logging
from urllib.parse import urlparse


class LinkHandler:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.AutoMod")
        # Regex para capturar qualquer URL (http, https, www)
        self.url_regex = re.compile(
            r"(?:https?://|www\.)[^\s/$.?#].[^\s]*", re.IGNORECASE
        )

        # O CACHE: Guarda os links já verificados na memória RAM
        self.link_cache = {}

    async def analisar(self, message: discord.Message, config: dict) -> str | None:
        """
        Analisa a mensagem, ignora sites seguros e checa sites desconhecidos na API.
        """
        # 1. VERIFICA WHITELISTS DE CANAIS
        canais_permitidos = config.get("link_whitelist_channels", [])
        if message.channel.id in canais_permitidos:
            return None

        content = message.content.lower()
        links_encontrados = self.url_regex.findall(content)

        if not links_encontrados:
            return None

        # 2. DOMÍNIOS SUPER SEGUROS (Pula a API para economizar tempo)
        dominios_seguros = [
            "youtube.com",
            "youtu.be",
            "tenor.com",
            "giphy.com",
            "discord.com",
            "discord.media",
            "twitch.tv",
            "kick.com",
            "tiktok.com",
            "instagram.com",
            "twitter.com",
            "x.com",
        ]

        # 3. DOMÍNIOS BLOQUEADOS PELA STAFF
        blacklist_local = config.get("link_blacklist_domains", [])

        for link in links_encontrados:
            try:
                # Garante que tem protocolo para extrair o domínio certinho
                url_to_parse = link if link.startswith("http") else f"http://{link}"
                dominio = urlparse(url_to_parse).netloc.replace("www.", "")
            except Exception:
                continue

            # Se for um site super famoso, deixa passar
            if any(dominio.endswith(seguro) for seguro in dominios_seguros):
                continue

            # Se for um domínio que sua staff bloqueou manualmente
            if any(dominio.endswith(bad) for bad in blacklist_local):
                return f"Link bloqueado pela staff (`{dominio}`)."

            # 4. VERIFICAÇÃO NA API EXTERNA COM CACHE
            is_suspeito = await self.checar_api_externa(dominio)
            if is_suspeito:
                return f"Link malicioso detectado pela segurança (`{dominio}`)."

        return None

    async def checar_api_externa(self, dominio: str) -> bool:
        """
        Consulta a API gratuita Sinking Yachts para golpes de Discord.
        """
        # Se já checamos esse site antes, pega da memória RAM
        if dominio in self.link_cache:
            return self.link_cache[dominio]

        # Endpoint gratuito da Sinking Yachts
        api_url = f"https://phish.sinking.yachts/v2/check/{dominio}"
        headers = {"accept": "application/json", "X-Identity": "SamBot-Security"}

        try:
            # Colocamos um timeout de 4 segundos. Se a internet oscilar ou a API cair,
            # o bot não trava e a mensagem do usuário é enviada normalmente.
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=4.0) as resp:
                    if resp.status == 200:
                        is_bad = (
                            await resp.json()
                        )  # Retorna booleano direto (true/false)

                        # Prevenção caso a API retorne texto em vez de booleano
                        if isinstance(is_bad, str):
                            is_bad = is_bad.lower() == "true"

                        # Salva a resposta no cache
                        self.link_cache[dominio] = is_bad
                        return is_bad
                    else:
                        # Se a API sobrecarregar, deixamos passar por segurança
                        return False
        except Exception as e:
            self.logger.warning(
                f"⚠️ Erro ao consultar API de links para o domínio {dominio}. Passando direto."
            )
            return False
