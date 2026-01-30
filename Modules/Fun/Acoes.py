import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
from collections import defaultdict

class Social(commands.Cog):
    def __init__(self, bot):
        """Comandos de interações sociais"""
        self.bot = bot
        self.base_url = "https://nekos.best/api/v2"
        self.counters = defaultdict(int)
        self.emoji = "🫂"

        # Configurações de texto resgatadas do Legacy
        self.actions_config = {
            "hug": {"emoji": "🤗", "verb": "deu um abraço apertado em", "self": "esta se abraçando a si próprio... precisa de um abraço real?"},
            "kiss": {"emoji": "💋", "verb": "beijou", "self": "tentou beijar-se no espelho..."},
            "slap": {"emoji": "👋", "verb": "deu um tapa em", "self": "deu um tapa em si mesmo para acordar!"},
            "pat": {"emoji": "💆", "verb": "fez carinho em", "self": "fez carinho na própria cabeça. Tudo vai ficar bem."},
            "cuddle": {"emoji": "🛋️", "verb": "fez conchinha com", "self": "enrolou-se nas cobertas sozinho."},
            "poke": {"emoji": "👉", "verb": "cutucou", "self": "está a cutucar-se... porquê?"},
            "feed": {"emoji": "🍕", "verb": "alimentou", "self": "esta comendo sozinho."},
            "yeet": {"emoji": "🚀", "verb": "arremessou", "self": "lançou-se para o espaço!"},
            "punch": {"emoji": "👊", "verb": "deu um soco em", "self": "esta lutando contra o próprio reflexo."},
            "shoot": {"emoji": "🔫", "verb": "atirou em", "self": "está a jogar roleta russa?"},
            "highfive": {"emoji": "🙌", "verb": "bateu as mãos com", "self": "tentou bater as mãos consigo próprio... triste."}
        }

    async def get_gif(self, category: str) -> str:
        """Busca um GIF aleatório da API nekos.best com fallback."""
        url = f"{self.base_url}/{category}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['results'][0]['url']
                    return "https://media.giphy.com/media/Lp51TPltqpSMM/giphy.gif"
            except:
                return "https://media.giphy.com/media/Lp51TPltqpSMM/giphy.gif"

    async def execute_interaction(self, source, author, target, action_key, can_return=True):
        config = self.actions_config.get(action_key)
        if not config: return

        # --- LÓGICA DE INTERAÇÃO COM O BOT (Resgatada do Legacy) ---
        if target.id == self.bot.user.id:
            if action_key == "kiss":
                reject_key = (author.id, 'kiss_rejected')
                if self.counters[reject_key] == 0:
                    self.counters[reject_key] += 1
                    return await self.execute_interaction(source, self.bot.user, author, "pat", False)
                else:
                    self.counters[reject_key] = 0
                    return await self.execute_interaction(source, self.bot.user, author, "yeet", False) 

            # Defesa contra agressão
            if action_key in ["slap", "punch", "shoot"]:
                gif_url = await self.get_gif("smug")
                embed = discord.Embed(description=f"😏 **{author.name}**, tentou me acertar? Sou rápida demais para ti!", color=discord.Color.orange())
                embed.set_image(url=gif_url)
                if isinstance(source, discord.Interaction): return await source.response.send_message(embed=embed)
                return await source.send(embed=embed)

        # --- PROCESSAMENTO NORMAL ---
        final_action = action_key
        # Auto-interação
        if target.id == author.id:
            description = f"{config['emoji']} **{author.name}** {config['self']}"
        else:
            description = f"{config['emoji']} **{author.name}** {config['verb']} **{target.name}**!"

        gif_url = await self.get_gif(final_action)
        embed = discord.Embed(description=description, color=discord.Color.random())
        embed.set_image(url=gif_url)
        
        # Sistema de contagem para o footer (Legacy style)
        inter_key = (author.id, target.id, action_key)
        self.counters[inter_key] += 1
        embed.set_footer(text=f"Via nekos.best • Interação #{self.counters[inter_key]}")

        # --- BOTÃO DE RETRIBUIR ---
        view = None
        if can_return and target.id != author.id and not target.bot:
            view = discord.ui.View(timeout=60)
            btn = discord.ui.Button(label="Retribuir", style=discord.ButtonStyle.secondary, emoji="↩️")

            async def callback(interaction: discord.Interaction):
                if interaction.user.id != target.id:
                    return await interaction.response.send_message("Não pode retribuir algo que não foi para voce!", ephemeral=True)
                btn.disabled = True
                await interaction.response.edit_message(view=view)
                await self.execute_interaction(interaction, target, author, action_key, False)

            btn.callback = callback
            view.add_item(btn)

        if isinstance(source, discord.Interaction):
            if not source.response.is_done(): await source.response.send_message(embed=embed, view=view)
            else: await source.followup.send(embed=embed, view=view)
        else:
            await source.send(embed=embed, view=view)

    # --- COMANDOS ---

    @commands.hybrid_command(name="hug", aliases=["abraçar"], description="Dê um abraço em alguém.")
    async def hug(self, ctx, user: discord.Member):
        """Dê um abraço em alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "hug")

    @commands.hybrid_command(name="kiss", aliases=["beijar"], description="Dê um beijo em alguém.")
    async def kiss(self, ctx, user: discord.Member):
        """Dê um beijo em alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "kiss")

    @commands.hybrid_command(name="slap", aliases=["tapa"], description="Dê um tapa em alguém.")
    async def slap(self, ctx, user: discord.Member):
        """Dê um tapa em alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "slap")

    @commands.hybrid_command(name="pat", aliases=["carinho"], description="Faça carinho em alguém.")
    async def pat(self, ctx, user: discord.Member):
        """Faça carinho em alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "pat")

    @commands.hybrid_command(name="yeet", description="Arremesse alguém para longe!")
    async def yeet(self, ctx, user: discord.Member):
        """Arremesse alguém para longe!"""
        await self.execute_interaction(ctx, ctx.author, user, "yeet")

    @commands.hybrid_command(name="cuddle", aliases=["conchinha"], description="Fique de conchinha com alguém.")
    async def cuddle(self, ctx, user: discord.Member):
        """Fique de conchinha com alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "cuddle")

    @commands.hybrid_command(name="poke", description="Cutuque alguém.")
    async def poke(self, ctx, user: discord.Member):
        """Cutuque alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "poke")

    @commands.hybrid_command(name="feed", description="Dê comida a alguém.")
    async def feed(self, ctx, user: discord.Member):
        """Dê comida a alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "feed")

    @commands.hybrid_command(name="punch", description="Dê um soco em alguém.")
    async def punch(self, ctx, user: discord.Member):
        """Dê um soco em alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "punch")

    @commands.hybrid_command(name="shoot", description="Atire em alguém.")
    async def shoot(self, ctx, user: discord.Member):
        """Atire em alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "shoot")

    @commands.hybrid_command(name="highfive", description="Dê um high-five em alguém.")
    async def highfive(self, ctx, user: discord.Member):
        """Dê um high-five em alguém."""
        await self.execute_interaction(ctx, ctx.author, user, "highfive")

    @commands.hybrid_command(name="dance", description="Comece a dançar!")
    async def dance(self, ctx):
        """Comece a dançar!"""
        gif_url = await self.get_gif("dance")
        embed = discord.Embed(description=f"💃 **{ctx.author.name}** começou a dançar!", color=discord.Color.purple())
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    # nao me questione o porquê deste comando existir
    @commands.hybrid_command(name="chutar", description="Chute o bot para ver o que acontece.")
    async def chutar(self, ctx):
        """Chute o bot para ver o que acontece."""
        await self.execute_interaction(ctx, ctx.author, self.bot.user, "yeet")

async def setup(bot):
    await bot.add_cog(Social(bot))