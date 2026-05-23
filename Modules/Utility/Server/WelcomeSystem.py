import discord
from discord.ext import commands
import asyncio
from typing import Optional

from Brain.Memory.DataManager import data_manager

# ==========================================
# VIEWS DE CONFIGURAÇÃO (PRIMEIRA VEZ E EDIÇÃO)
# ==========================================


class WelcomeTestView(discord.ui.View):
    """View para a Primeira Configuração (Botões Pronto / Editar / Cancelar)"""

    def __init__(self, cog, ctx, guild_id):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.guild_id = guild_id
        self.message = None

    @discord.ui.button(label="Pronto ✅", style=discord.ButtonStyle.success)
    async def btn_ready(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "❌ Apenas quem executou o comando pode interagir.", ephemeral=True
            )

        self.cog.configs[self.guild_id]["setup_done"] = True
        self.cog._save_configs()
        await interaction.response.edit_message(
            content="🎉 **Configuração inicial finalizada com sucesso!**", view=None
        )
        self.stop()

    @discord.ui.button(label="Editar ✏️", style=discord.ButtonStyle.primary)
    async def btn_edit(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "❌ Apenas quem executou o comando pode interagir.", ephemeral=True
            )

        # Transição para a tela de edição
        view = WelcomeEditView(self.cog, self.ctx, self.guild_id)
        embeds = self.cog.get_preview_embeds(
            self.ctx.guild, self.cog.configs[self.guild_id]
        )
        await interaction.response.edit_message(
            content="⚙️ **Modo de Edição**\nSelecione no menu abaixo o que deseja alterar.",
            embeds=embeds,
            view=view,
        )
        view.message = self.message
        self.stop()

    @discord.ui.button(label="Cancelar ❌", style=discord.ButtonStyle.danger)
    async def btn_cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "❌ Apenas quem executou o comando pode interagir.", ephemeral=True
            )

        await interaction.response.edit_message(
            content="❌ **Configuração cancelada.**", view=None, embeds=[]
        )
        self.stop()


class WelcomeEditView(discord.ui.View):
    """View para o Painel de Edição (Opções Isoladas via Select Menu)"""

    def __init__(self, cog, ctx, guild_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.guild_id = guild_id
        self.message = None

    @discord.ui.select(
        placeholder="Escolha o que deseja editar...",
        options=[
            discord.SelectOption(
                label="Canal de Boas-vindas", value="welcome_channel", emoji="💬"
            ),
            discord.SelectOption(
                label="Canal de Adeus", value="goodbye_channel", emoji="👋"
            ),
            discord.SelectOption(
                label="Imagem/GIF no Fundo", value="image_url", emoji="🖼️"
            ),
            discord.SelectOption(
                label="Canal de Regras", value="rules_channel", emoji="👮"
            ),
            discord.SelectOption(
                label="Canal de Suporte", value="help_channel", emoji="🛠️"
            ),
            discord.SelectOption(
                label="Ativar/Desativar DM",
                description="Manda msg simples no privado",
                value="dm_welcome",
                emoji="✉️",
            ),
        ],
    )
    async def select_callback(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "❌ Apenas quem executou pode interagir.", ephemeral=True
            )

        val = select.values[0]

        # Se for o toggle da DM, altera direto
        if val == "dm_welcome":
            atual = self.cog.configs[self.guild_id].get("dm_welcome", False)
            self.cog.configs[self.guild_id]["dm_welcome"] = not atual
            self.cog._save_configs()
            embeds = self.cog.get_preview_embeds(
                self.ctx.guild, self.cog.configs[self.guild_id]
            )
            await interaction.response.edit_message(embeds=embeds, view=self)
            return

        # Para as outras opções, pede para enviar no chat
        nome_amigavel = [opt.label for opt in select.options if opt.value == val][0]
        await interaction.response.send_message(
            f"✏️ | Envie no chat o novo valor para **{nome_amigavel}** agora (Marque o canal com `#` ou envie o link da imagem). Tem 60s:",
            ephemeral=True,
        )

        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel

        try:
            msg = await self.cog.bot.wait_for("message", check=check, timeout=60.0)

            # Processa e salva o input
            if val in [
                "welcome_channel",
                "goodbye_channel",
                "rules_channel",
                "help_channel",
            ]:
                if msg.channel_mentions:
                    self.cog.configs[self.guild_id][val] = msg.channel_mentions[0].id
                else:
                    return await interaction.followup.send(
                        "❌ Você não mencionou nenhum canal (Ex: `#geral`). Edição cancelada.",
                        ephemeral=True,
                    )
            elif val == "image_url":
                if msg.content.startswith("http://") or msg.content.startswith(
                    "https://"
                ):
                    self.cog.configs[self.guild_id][val] = msg.content.strip()
                else:
                    self.cog.configs[self.guild_id][
                        val
                    ] = None  # Zera a imagem se mandar algo inválido
                    await interaction.followup.send(
                        "⚠️ Link inválido. A imagem foi removida.", ephemeral=True
                    )

            self.cog._save_configs()

            # Tenta apagar a mensagem do usuário pra deixar o chat limpo
            try:
                await msg.delete()
            except discord.Forbidden:
                pass

            # Atualiza o Embed Principal
            embeds = self.cog.get_preview_embeds(
                self.ctx.guild, self.cog.configs[self.guild_id]
            )
            if self.message:
                await self.message.edit(embeds=embeds, view=self)

            await interaction.followup.send(
                "✅ Valor atualizado com sucesso!", ephemeral=True
            )

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "⏱️ Tempo esgotado para o envio do valor. Tente novamente.",
                ephemeral=True,
            )

    @discord.ui.button(label="Concluir Edição 💾", style=discord.ButtonStyle.success)
    async def btn_save(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "❌ Apenas quem executou pode interagir.", ephemeral=True
            )

        self.cog.configs[self.guild_id]["setup_done"] = True
        self.cog._save_configs()
        await interaction.response.edit_message(
            content="✅ **Configurações salvas! Sistema pronto.**", view=None
        )
        self.stop()


# ==========================================
# COG PRINCIPAL
# ==========================================


class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}  # Cache de convites: {guild_id: {invite_code: uses}}
        self._load_configs()

    def _load_configs(self):
        dados = data_manager.get_knowledge("guild_configs")
        self.configs = dados if isinstance(dados, dict) else {}

    def _save_configs(self):
        data_manager.save_knowledge("guild_configs", self.configs)

    def get_preview_embeds(self, guild, guild_data):
        """Gera os Embeds de Teste (Como vai ficar na prática) e de Dashboard."""

        # --- Embed 1: O Preview exato de como fica no chat ---
        preview = discord.Embed(
            title=f"Membro de Teste | Bem-vindo",
            description=f"Olá Olá, seja bem-vindo(a) ao {guild.name}!\n\nConvidado por: @Convidante *(Usos: 1)*",
            color=discord.Color.from_rgb(91, 194, 122),
        )
        if guild_data.get("image_url"):
            preview.set_image(url=guild_data.get("image_url"))

        preview.set_footer(text=f"{guild.name} • © Todos os direitos reservados.")
        preview.add_field(
            name="Sabia que...",
            value=f"Você é o **{len(guild.members)}º** membro aqui no servidor?",
            inline=True,
        )
        preview.add_field(
            name="Info do Usuário",
            value=f"@Membro de Teste\n||(ID: 0000000000)||",
            inline=True,
        )

        if guild_data.get("help_channel"):
            preview.add_field(
                name="Precisando de ajuda?",
                value=f"Tire suas dúvidas aqui <#{guild_data['help_channel']}>",
                inline=True,
            )
        if guild_data.get("rules_channel"):
            preview.add_field(
                name="Evite punições!",
                value=f"Leia as nossas <#{guild_data['rules_channel']}> para evitar futuras punições!",
                inline=True,
            )

        # --- Embed 2: Status do Dashboard de Configurações ---
        config_embed = discord.Embed(
            title="⚙️ Status das Configurações", color=discord.Color.blurple()
        )

        wc = (
            f"<#{guild_data['welcome_channel']}>"
            if guild_data.get("welcome_channel")
            else "🔴 Não definido"
        )
        gc = (
            f"<#{guild_data['goodbye_channel']}>"
            if guild_data.get("goodbye_channel")
            else "🔴 Não definido"
        )
        img = (
            f"[Link Inserido]({guild_data['image_url']})"
            if guild_data.get("image_url")
            else "🔴 Não definido"
        )
        rc = (
            f"<#{guild_data['rules_channel']}>"
            if guild_data.get("rules_channel")
            else "🔴 Não definido"
        )
        hc = (
            f"<#{guild_data['help_channel']}>"
            if guild_data.get("help_channel")
            else "🔴 Não definido"
        )
        dm = "🟢 Ativado" if guild_data.get("dm_welcome") else "🔴 Desativado"

        config_embed.description = (
            f"**Canal de Boas-Vindas:** {wc}\n"
            f"**Canal de Adeus:** {gc}\n"
            f"**Canal de Regras:** {rc}\n"
            f"**Canal de Suporte:** {hc}\n"
            f"**Boas-Vindas na DM:** {dm}\n"
            f"**Imagem de Fundo:** {img}"
        )

        return [preview, config_embed]

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invite_cache[guild.id] = {
                    invite.code: invite.uses for invite in invites
                }
            except discord.Forbidden:
                self.invite_cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if invite.guild.id not in self.invite_cache:
            self.invite_cache[invite.guild.id] = {}
        self.invite_cache[invite.guild.id][invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if invite.guild.id in self.invite_cache:
            self.invite_cache[invite.guild.id].pop(invite.code, None)

    async def _find_inviter(self, member: discord.Member):
        guild = member.guild
        if guild.id not in self.invite_cache:
            self.invite_cache[guild.id] = {}

        try:
            current_invites = await guild.invites()
        except discord.Forbidden:
            return None, 0

        inviter_found = None
        uses_found = 0
        old_invites = self.invite_cache[guild.id]

        for invite in current_invites:
            if invite.code in old_invites and invite.uses > old_invites[invite.code]:
                inviter_found = invite.inviter
                uses_found = invite.uses
                break
            elif invite.code not in old_invites and invite.uses > 0:
                inviter_found = invite.inviter
                uses_found = invite.uses
                break

        self.invite_cache[guild.id] = {
            invite.code: invite.uses for invite in current_invites
        }
        return inviter_found, uses_found

    def parse_placeholders(
        self,
        text: str,
        member: discord.Member,
        inviter: Optional[discord.Member] = None,
        inviter_uses: int = 0,
    ) -> str:
        if not text:
            return ""
        inviter_mention = inviter.mention if inviter else "Desconhecido"
        inviter_name = inviter.name if inviter else "Desconhecido"

        replacements = {
            "{user}": member.name,
            "{@user}": member.mention,
            "{user-id}": str(member.id),
            "{user-avatar-url}": (
                member.display_avatar.url if member.display_avatar else ""
            ),
            "{guild}": member.guild.name,
            "{guild-size}": str(len(member.guild.members)),
            "{inviter}": inviter_mention,
            "{inviter-name}": inviter_name,
            "{inviter-uses}": str(inviter_uses),
        }
        for key, value in replacements.items():
            text = text.replace(key, value)
        return text

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = str(member.guild.id)
        if guild_id not in self.configs or not self.configs[guild_id].get(
            "welcome_enabled", False
        ):
            return

        guild_data = self.configs[guild_id]

        # 1. Enviar mensagem na DM se configurado (Requisito 3)
        if guild_data.get("dm_welcome", False):
            try:
                dm_embed = discord.Embed(
                    title=f"Bem-vindo(a) ao {member.guild.name}!",
                    description=f"Olá {member.mention}, ficamos muito felizes em ter você aqui conosco!",
                    color=discord.Color.from_rgb(91, 194, 122),
                )
                if member.guild.icon:
                    dm_embed.set_thumbnail(url=member.guild.icon.url)

                if guild_data.get("rules_channel"):
                    dm_embed.add_field(
                        name="📚 Regras",
                        value=f"Não esqueça de ler as regras em <#{guild_data['rules_channel']}>",
                        inline=False,
                    )
                if guild_data.get("help_channel"):
                    dm_embed.add_field(
                        name="🛠️ Suporte",
                        value=f"Precisando de ajuda? Vá no canal <#{guild_data['help_channel']}>",
                        inline=False,
                    )

                dm_embed.set_footer(text=f"{member.guild.name} • Divirta-se!")
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # Ignora se o membro estiver com DM fechada

        # 2. Enviar mensagem no Chat Público (Se existir)
        channel_id = guild_data.get("welcome_channel")
        channel = member.guild.get_channel(channel_id) if channel_id else None

        if channel:
            inviter, inviter_uses = await self._find_inviter(member)
            embed = discord.Embed(
                title=self.parse_placeholders(
                    "{user} | Bem-vindo", member, inviter, inviter_uses
                ),
                description=f"Olá Olá, seja bem-vindo(a) ao {member.guild.name}!\n\nConvidado por: {inviter.mention if inviter else 'Não identificado'} *(Usos: {inviter_uses})*",
                color=discord.Color.from_rgb(91, 194, 122),
            )
            if guild_data.get("image_url"):
                embed.set_image(url=guild_data.get("image_url"))
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(
                text=f"{member.guild.name} • © Todos os direitos reservados."
            )

            embed.add_field(
                name="Sabia que...",
                value=f"Você é o **{len(member.guild.members)}º** membro aqui no servidor?",
                inline=True,
            )
            embed.add_field(
                name="Info do Usuário",
                value=f"{member.mention}\n||({member.id})||",
                inline=True,
            )

            if guild_data.get("help_channel"):
                embed.add_field(
                    name="Precisando de ajuda?",
                    value=f"Tire suas dúvidas aqui <#{guild_data['help_channel']}>",
                    inline=True,
                )
            if guild_data.get("rules_channel"):
                embed.add_field(
                    name="Evite punições!",
                    value=f"Leia as nossas <#{guild_data['rules_channel']}> para evitar futuras punições!",
                    inline=True,
                )

            await channel.send(content=member.mention, embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild_id = str(member.guild.id)
        if guild_id not in self.configs or not self.configs[guild_id].get(
            "welcome_enabled", False
        ):
            return

        guild_data = self.configs[guild_id]
        channel_id = guild_data.get("goodbye_channel")
        channel = member.guild.get_channel(channel_id) if channel_id else None

        if channel:
            embed = discord.Embed(
                title="👋 Alguém saiu do servidor...",
                description=f"**{member.name}** saiu correndo! Agora somos apenas {len(member.guild.members)} membros.",
                color=discord.Color.red(),
            )
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

    @commands.hybrid_group(
        name="welcome",
        description="Comandos de controle do sistema de Boas-vindas e Invites",
    )
    @commands.has_permissions(manage_guild=True)
    async def welcome_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "❓ Use `/welcome ligar`, `/welcome desligar` ou `/welcome editar`."
            )

    @welcome_group.command(
        name="ligar", description="Ativa o sistema de boas-vindas no servidor."
    )
    async def welcome_on(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.configs:
            self.configs[guild_id] = {}

        self.configs[guild_id]["welcome_enabled"] = True
        self._save_configs()
        await ctx.send(
            "✅ O sistema de boas-vindas e rastreador de convites foi **ativado**."
        )

    @welcome_group.command(
        name="desligar", description="Desativa o sistema de boas-vindas no servidor."
    )
    async def welcome_off(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        if guild_id in self.configs:
            self.configs[guild_id]["welcome_enabled"] = False
            self._save_configs()
        await ctx.send("🛑 O sistema de boas-vindas foi **desativado**.")

    @welcome_group.command(
        name="editar",
        description="Abre o painel de configuração e edição de Boas-Vindas.",
    )
    async def welcome_edit(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.configs:
            self.configs[guild_id] = {"welcome_enabled": True}

        # Verifica se já concluiu alguma configuração antes
        is_first_time = not self.configs[guild_id].get("setup_done", False)

        embeds = self.get_preview_embeds(ctx.guild, self.configs[guild_id])

        if is_first_time:
            view = WelcomeTestView(self, ctx, guild_id)
            msg = await ctx.send(
                "🚀 **Teste de Boas-Vindas**\nEste é o formato atual. Você deseja salvar assim ou editar algo?",
                embeds=embeds,
                view=view,
            )
            view.message = msg
        else:
            view = WelcomeEditView(self, ctx, guild_id)
            msg = await ctx.send(
                "⚙️ **Painel de Edição de Boas-Vindas**\nSelecione no menu abaixo o que deseja alterar.",
                embeds=embeds,
                view=view,
            )
            view.message = msg


async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))
