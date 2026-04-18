import discord
from discord.ext import commands
import aiohttp
from collections import defaultdict


class SocialBase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://nekos.best/api/v2"
        self.counters = defaultdict(int)

        # O dicionário mestre de ações foi mantido aqui
        self.actions_config = {
            "hug": {
                "emoji": "🤗",
                "verb": "deu um abraço apertado em",
                "self": "esta se abraçando a si próprio... precisa de um abraço real?",
            },
            "kiss": {
                "emoji": "💋",
                "verb": "beijou",
                "self": "tentou beijar-se no espelho...",
            },
            "slap": {
                "emoji": "👋",
                "verb": "deu um tapa em",
                "self": "deu um tapa em si mesmo para acordar!",
            },
            "pat": {
                "emoji": "💆",
                "verb": "fez carinho em",
                "self": "fez carinho na própria cabeça. Tudo vai ficar bem.",
            },
            "cuddle": {
                "emoji": "🛋️",
                "verb": "fez conchinha com",
                "self": "enrolou-se nas cobertas sozinho.",
            },
            "poke": {
                "emoji": "👉",
                "verb": "cutucou",
                "self": "esta se cutucando contra si mesmo... porquê?",
            },
            "feed": {
                "emoji": "🍕",
                "verb": "alimentou",
                "self": "esta comendo sozinho.",
            },
            "yeet": {
                "emoji": "🚀",
                "verb": "arremessou",
                "self": "lançou-se para o espaço!",
            },
            "punch": {
                "emoji": "👊",
                "verb": "deu um soco em",
                "self": "esta lutando contra o próprio reflexo.",
            },
            "shoot": {
                "emoji": "🔫",
                "verb": "atirou em",
                "self": "esta jogando roleta russa?",
            },
            "highfive": {
                "emoji": "🙌",
                "verb": "bateu as mãos com",
                "self": "tentou bater as mãos consigo próprio... tragico.",
            },
            "handhold": {
                "emoji": "🤝",
                "verb": "segurou a mão de",
                "self": "entrelaçou os próprios dedos... solitário.",
            },
            "bite": {
                "emoji": "🧛",
                "verb": "deu uma mordidinha em",
                "self": "mordeu a própria língua sem querer!",
            },
        }

    async def get_gif(self, category: str) -> str:
        """Busca um GIF aleatório da API nekos.best com fallback."""
        url = f"{self.base_url}/{category}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["results"][0]["url"]
                    return "https://media.giphy.com/media/Lp51TPltqpSMM/giphy.gif"
            except:
                return "https://media.giphy.com/media/Lp51TPltqpSMM/giphy.gif"

    async def execute_interaction(
        self, source, author, target, action_key, can_return=True
    ):
        """Lógica centralizada de criação de interações resgatada do código original"""
        config = self.actions_config.get(action_key)
        if not config:
            return

        # Defesas e interações específicas do bot
        if target.id == self.bot.user.id:
            if action_key == "kiss":
                reject_key = (author.id, "kiss_rejected")
                if self.counters[reject_key] == 0:
                    self.counters[reject_key] += 1
                    return await self.execute_interaction(
                        source, self.bot.user, author, "pat", False
                    )
                else:
                    self.counters[reject_key] = 0
                    return await self.execute_interaction(
                        source, self.bot.user, author, "yeet", False
                    )

            if action_key in ["slap", "punch", "shoot"]:
                gif_url = await self.get_gif("smug")
                embed = discord.Embed(
                    description=f"😏 **{author.name}**, tentou me acertar? Sou rápida demais para ti!",
                    color=discord.Color.orange(),
                )
                embed.set_image(url=gif_url)
                if isinstance(source, discord.Interaction):
                    return await source.response.send_message(embed=embed)
                return await source.send(embed=embed)

        # Processamento Normal
        final_action = action_key
        if target.id == author.id:
            description = f"{config['emoji']} **{author.name}** {config['self']}"
        else:
            description = f"{config['emoji']} **{author.name}** {config['verb']} **{target.name}**!"

        gif_url = await self.get_gif(final_action)
        embed = discord.Embed(description=description, color=discord.Color.random())
        embed.set_image(url=gif_url)

        inter_key = (author.id, target.id, action_key)
        self.counters[inter_key] += 1
        embed.set_footer(text=f"Via nekos.best • Interação #{self.counters[inter_key]}")

        # Botão de Retribuir
        view = None
        if can_return and target.id != author.id and not target.bot:
            view = discord.ui.View(timeout=60)
            btn = discord.ui.Button(
                label="Retribuir", style=discord.ButtonStyle.secondary, emoji="↩️"
            )

            async def callback(interaction: discord.Interaction):
                if interaction.user.id != target.id:
                    return await interaction.response.send_message(
                        "Não pode retribuir algo que não foi para voce!", ephemeral=True
                    )
                btn.disabled = True
                await interaction.response.edit_message(view=view)
                await self.execute_interaction(
                    interaction, target, author, action_key, False
                )

            btn.callback = callback
            view.add_item(btn)

        if isinstance(source, discord.Interaction):
            if not source.response.is_done():
                await source.response.send_message(embed=embed, view=view)
            else:
                await source.followup.send(embed=embed, view=view)
        else:
            await source.send(embed=embed, view=view)
