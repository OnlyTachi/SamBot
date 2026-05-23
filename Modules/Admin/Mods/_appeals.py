import discord
import time
from Brain.Memory.DataManager import data_manager


class AppealActionView(discord.ui.View):
    """View que aparece NA DM DO MODERADOR para ele decidir o destino do infrator."""

    def __init__(self, bot, guild_id: int, user_id: int, tipo: str, mod_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = str(guild_id)
        self.user_id = str(user_id)
        self.tipo = tipo
        self.mod_id = str(mod_id)

    async def _update_appeal_status(self, status: str):
        configs = data_manager.get_knowledge("guild_configs") or {}
        if self.guild_id not in configs:
            configs[self.guild_id] = {}
        if "appeals" not in configs[self.guild_id]:
            configs[self.guild_id]["appeals"] = {}
        configs[self.guild_id]["appeals"][self.user_id] = status
        data_manager.save_knowledge("guild_configs", configs)

    async def _avisar_infrator(self, mensagem: str, cor: discord.Color):
        try:
            user = await self.bot.fetch_user(int(self.user_id))
            embed = discord.Embed(
                title="Atualização do seu Apelo", description=mensagem, color=cor
            )
            await user.send(embed=embed)
        except:
            pass  # Se a DM estiver fechada, não há o que fazer

    @discord.ui.button(
        label="Aceitar Apelo", style=discord.ButtonStyle.success, emoji="✅"
    )
    async def btn_aceitar(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        guild = self.bot.get_guild(int(self.guild_id))
        user = await self.bot.fetch_user(int(self.user_id))

        try:
            if self.tipo == "BAN":
                await guild.unban(user, reason="Apelo aceito pelo moderador.")
            elif self.tipo == "MUTE":
                membro = guild.get_member(int(self.user_id))
                if membro:
                    await membro.timeout(None, reason="Apelo aceito.")

            # Limpa o status de apelo para ele poder usar no futuro se for punido de novo
            await self._update_appeal_status("livre")
            await self._avisar_infrator(
                f"Seu apelo foi **ACEITO** no servidor {guild.name}. Sua punição foi revogada!",
                discord.Color.green(),
            )

            avisos_cog = self.bot.get_cog("Avisos")
            if avisos_cog:
                # Dispara a notícia linda no canal público!
                await avisos_cog.enviar_aviso(
                    guild,
                    "APELO ACEITO",
                    user,
                    interaction.user,
                    "A punição anterior foi revogada pelo sistema de apelos.",
                )

            await interaction.response.edit_message(
                content="✅ **Apelo Aceito.** O usuário teve a punição revogada.",
                view=None,
                embed=interaction.message.embeds[0],
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao remover punição: {e}", ephemeral=True
            )

    @discord.ui.button(
        label="Negar (Voltar amanhã)", style=discord.ButtonStyle.secondary, emoji="🕒"
    )
    async def btn_negar(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        amanha = time.time() + 86400  # 24 horas
        await self._update_appeal_status(str(amanha))

        guild = self.bot.get_guild(int(self.guild_id))
        await self._avisar_infrator(
            f"Seu apelo foi **NEGADO** no servidor {guild.name}. Você poderá tentar novamente em 24 horas.",
            discord.Color.orange(),
        )
        await interaction.response.edit_message(
            content="🕒 **Apelo Negado.** O usuário está de castigo por 24h para tentar apelar de novo.",
            view=None,
            embed=interaction.message.embeds[0],
        )

    @discord.ui.button(
        label="Negar Permanentemente", style=discord.ButtonStyle.danger, emoji="🚫"
    )
    async def btn_permanente(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._update_appeal_status("permanente")

        guild = self.bot.get_guild(int(self.guild_id))
        await self._avisar_infrator(
            f"Seu apelo foi **NEGADO PERMANENTEMENTE** no servidor {guild.name}. A decisão é final e você não poderá enviar novos apelos.",
            discord.Color.red(),
        )
        await interaction.response.edit_message(
            content="🚫 **Apelo Negado Permanentemente.** O usuário foi bloqueado do sistema de apelos.",
            view=None,
            embed=interaction.message.embeds[0],
        )


class AppealModal(discord.ui.Modal, title="Fazer um Apelo"):
    motivo = discord.ui.TextInput(
        label="Por que sua punição deve ser revogada?",
        style=discord.TextStyle.paragraph,
        placeholder="Escreva sua justificativa de forma respeitosa...",
        min_length=10,
        max_length=500,
        required=True,
    )

    def __init__(self, bot, guild_id: int, mod_id: int, tipo: str):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.mod_id = mod_id
        self.tipo = tipo

    async def on_submit(self, interaction: discord.Interaction):
        try:
            moderador = await self.bot.fetch_user(self.mod_id)
            guild = self.bot.get_guild(self.guild_id)

            embed = discord.Embed(
                title=f"📩 Novo Apelo Recebido ({self.tipo})",
                description=f"O usuário **{interaction.user.name}** (`{interaction.user.id}`) que você puniu enviou um apelo.",
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="Servidor",
                value=guild.name if guild else "Desconhecido",
                inline=False,
            )
            embed.add_field(
                name="Justificativa do Infrator",
                value=f"```\n{self.motivo.value}\n```",
                inline=False,
            )
            embed.set_footer(text="Escolha uma das ações abaixo.")

            view = AppealActionView(
                self.bot, self.guild_id, interaction.user.id, self.tipo, self.mod_id
            )
            await moderador.send(embed=embed, view=view)

            await interaction.response.send_message(
                "✅ Seu apelo foi enviado ao moderador responsável! Aguarde o resultado na sua DM.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                "❌ Não foi possível enviar o apelo. Talvez a DM do moderador esteja fechada.",
                ephemeral=True,
            )


class AppealStartView(discord.ui.View):
    """View que vai na DM do infrator quando ele é punido (Persistente)."""

    def __init__(self, bot, guild_id: int, mod_id: int, tipo: str):
        # timeout=None é obrigatório para views persistentes
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
        self.mod_id = mod_id
        self.tipo = tipo

    @discord.ui.button(
        label="📩 Fazer Apelo",
        style=discord.ButtonStyle.primary,
        custom_id="SamBot_start_appeal_btn",
    )
    async def btn_apelo(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        configs = data_manager.get_knowledge("guild_configs") or {}

        g_id = str(self.guild_id)

        status = (
            configs.get(g_id, {})
            .get("appeals", {})
            .get(str(interaction.user.id), "livre")
        )

        if status == "permanente":
            return await interaction.response.send_message(
                "🚫 O seu direito de apelo neste servidor foi revogado permanentemente.",
                ephemeral=True,
            )

        if status != "livre":
            try:
                cooldown_time = float(status)
                if time.time() < cooldown_time:
                    faltam = int((cooldown_time - time.time()) / 3600)
                    return await interaction.response.send_message(
                        f"🕒 O seu último apelo foi negado. Tente novamente daqui a {faltam} horas.",
                        ephemeral=True,
                    )
            except:
                pass

        # Abre o modal passando as informações
        await interaction.response.send_modal(
            AppealModal(self.bot, int(self.guild_id), int(self.mod_id), self.tipo)
        )


async def notificar_infrator(membro, guild, mod, tipo, motivo, bot):
    """Função auxiliar para enviar a punição e o botão de apelo para o infrator."""
    try:
        icon = "🔨" if tipo == "BAN" else "🔇" if tipo == "MUTE" else "👢"
        embed = discord.Embed(
            title=f"{icon} Você recebeu uma punição em {guild.name}",
            description=f"**Tipo:** {tipo}\n**Motivo:** {motivo}",
            color=discord.Color.red(),
        )
        embed.set_footer(
            text="Você pode tentar revogar essa punição usando o botão abaixo."
        )
        view = AppealStartView(bot, guild.id, mod.id, tipo)
        await membro.send(embed=embed, view=view)
    except:
        pass  # DM do infrator fechada
