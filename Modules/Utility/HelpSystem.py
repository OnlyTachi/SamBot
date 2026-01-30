import discord
from discord.ext import commands
from typing import Optional, List

class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, mapping: dict):
        options = [
            discord.SelectOption(
                label="Início", 
                description="Página principal da ajuda", 
                emoji="🏠"
            )
        ]
        
        # Filtra cogs com comandos e cria opções
        for cog, cmds in mapping.items():
            if not cog or not cmds:
                continue
            name = cog.qualified_name
            emoji = getattr(cog, "emoji", "📁") # Tenta pegar emoji do cog se existir
            options.append(discord.SelectOption(label=name, description=f"Comandos de {name}", emoji=emoji))

        super().__init__(placeholder="Escolha uma categoria...", min_values=1, max_values=1, options=options)
        self.bot = bot
        self.mapping = mapping

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Início":
            embed = self.view.create_main_embed()
            await interaction.response.edit_message(embed=embed, view=self.view)
            return

        cog = self.bot.get_cog(self.values[0])
        cmds = self.mapping.get(cog)
        
        embed = discord.Embed(
            title=f"Categoria: {cog.qualified_name}",
            description=cog.description or "Sem descrição detalhada.",
            color=discord.Color.blue()
        )
        
        for cmd in cmds:
            name = f"+{cmd.name}"
            params = f" `{cmd.signature}`" if cmd.signature else ""
            desc = cmd.short_doc or "Sem descrição."
            embed.add_field(name=f"{name}{params}", value=desc, inline=False)

        embed.set_footer(text=f"Use +help <comando> para detalhes específicos.")
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, mapping: dict):
        super().__init__(timeout=60)
        self.bot = bot
        self.mapping = mapping
        self.add_item(HelpSelect(bot, mapping))

    def create_main_embed(self):
        embed = discord.Embed(
            title="📚 Central de Ajuda - SamBot",
            description=(
                "Olá! Eu sou a **SamBot**. Abaixo podes ver as categorias de comandos disponíveis.\n\n"
                "🔹 **Como usar:** Seleciona uma categoria no menu abaixo para ver os comandos."
            ),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        return embed

class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Mostra este menu de ajuda.',
            'aliases': ['ajuda', 'h']
        })

    def get_command_signature(self, command):
        return f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"

    async def send_bot_help(self, mapping):
        dest = self.get_destination()
        view = HelpView(self.context.bot, mapping)
        embed = view.create_main_embed()
        await dest.send(embed=embed, view=view)

    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Comando: +{command.name}", color=discord.Color.green())
        embed.add_field(name="Descrição", value=command.help or "Sem descrição.", inline=False)
        
        if command.aliases:
            embed.add_field(name="Atalhos", value=", ".join(command.aliases), inline=True)
            
        embed.add_field(name="Uso", value=f"`{self.get_command_signature(command)}`", inline=False)
        
        dest = self.get_destination()
        await dest.send(embed=embed)

    async def send_error_message(self, error):
        embed = discord.Embed(title="❌ Erro", description=error, color=discord.Color.red())
        await self.get_destination().send(embed=embed)

async def setup(bot):
    bot.help_command = CustomHelpCommand()