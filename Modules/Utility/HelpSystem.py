import discord
from discord.ext import commands
import logging

# --- INTERFACE DE UI (O MENU DROPDOWN) ---


class HelpDropdown(discord.ui.Select):
    def __init__(self, categorias):
        self.categorias = categorias
        options = [
            discord.SelectOption(
                label="Início",
                description="Voltar para a página principal",
                emoji="🏠",
                value="home",
            )
        ]

        # Ordena as categorias para o menu ficar organizado
        for key in sorted(categorias.keys()):
            info = categorias[key]
            # Só exibe se a categoria tiver comandos visíveis
            if not info["comandos"]:
                continue

            options.append(
                discord.SelectOption(
                    label=info["exibir_nome"],
                    description=info["desc"],
                    emoji=info["emoji"],
                    value=key,
                )
            )

        super().__init__(
            placeholder="Selecione um módulo para explorar...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        cat_key = self.values[0]

        if cat_key == "home":
            await interaction.response.edit_message(
                embed=self.view.main_embed, view=self.view
            )
            return

        info = self.categorias[cat_key]

        embed = discord.Embed(
            title=f"{info['emoji']} Categoria: {info['exibir_nome']}",
            description=f"*{info['desc']}*\n\n",
            color=discord.Color.blurple(),
        )

        texto_comandos = ""
        comandos_ordenados = sorted(info["comandos"], key=lambda c: c.name)

        for cmd in comandos_ordenados:
            doc = cmd.short_doc or "Nenhuma descrição disponível."
            texto_comandos += f"**`+{cmd.name}`** — {doc}\n"

        if len(texto_comandos) > 4000:
            texto_comandos = texto_comandos[:4000] + "\n... (Muitos comandos)"

        embed.description += texto_comandos
        embed.set_footer(
            text=f"Total: {len(info['comandos'])} comandos nesta categoria."
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, categorias, main_embed):
        super().__init__(timeout=120)
        self.main_embed = main_embed
        self.add_item(HelpDropdown(categorias))


# --- COG PRINCIPAL ---


class HelpSystem(commands.Cog):
    """Substitui o sistema de ajuda nativo por um menu dinâmico e inteligente."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Help")

        self.config_pastas = {
            "Economy": {
                "nome": "Economia & RPG",
                "desc": "Trabalho, banco, loja e investimentos.",
                "emoji": "💰",
            },
            "Admin": {
                "nome": "Administração",
                "desc": "Moderação, AutoMod e Auditoria.",
                "emoji": "🛡️",
            },
            "Audio": {
                "nome": "Música",
                "desc": "Playlists e controlo de áudio.",
                "emoji": "🎶",
            },
            "Fun": {
                "nome": "Diversão",
                "desc": "Interações sociais e jogos.",
                "emoji": "🎲",
            },
            "Utility": {
                "nome": "Utilitários",
                "desc": "Informações e ferramentas do sistema.",
                "emoji": "🛠️",
            },
            "Developer": {
                "nome": "Desenvolvedor",
                "desc": "Ferramentas restritas de infraestrutura.",
                "emoji": "💻",
            },
        }

        # Remove o comando de ajuda padrão do Discord.py
        self._original_help = bot.help_command
        bot.help_command = None

    def cog_unload(self):
        self.bot.help_command = self._original_help

    @commands.hybrid_command(
        name="help",
        aliases=["ajuda"],
        description="Abre a central de ajuda interativa.",
    )
    async def help_cmd(self, ctx: commands.Context):
        # 1. Estrutura para agrupar comandos
        categorias = {}

        for cmd in self.bot.commands:
            # Ignora comandos escondidos
            if cmd.hidden:
                continue

            if (
                cmd.cog
                and cmd.cog.qualified_name == "Developer"
                and not await self.bot.is_owner(ctx.author)
            ):
                continue

            modulo_path = cmd.cog.__module__ if cmd.cog else ""
            partes = modulo_path.split(".")

            if len(partes) > 1 and partes[0] == "Modules":
                folder_name = partes[1]
            else:
                folder_name = "Utility"

            if folder_name not in categorias:
                conf = self.config_pastas.get(folder_name, {})
                categorias[folder_name] = {
                    "exibir_nome": conf.get("nome", folder_name),
                    "desc": conf.get("desc", f"Comandos do módulo {folder_name}"),
                    "emoji": conf.get("emoji", "📁"),
                    "comandos": [],
                }

            categorias[folder_name]["comandos"].append(cmd)

        embed = discord.Embed(
            title="📚 Central de Ajuda - SamBot",
            description=(
                "Bem-vindo! Seleciona uma categoria no menu abaixo para ver os comandos.\n\n"
                "💡 **Dica:** Também pode conversar comigo naturalmente no chat!"
            ),
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        for folder, info in categorias.items():
            if info["comandos"] and folder != "Developer":
                embed.add_field(
                    name=f"{info['emoji']} {info['exibir_nome']}",
                    value=f"`{len(info['comandos'])} comandos`",
                    inline=True,
                )

        view = HelpView(categorias, embed)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(HelpSystem(bot))
