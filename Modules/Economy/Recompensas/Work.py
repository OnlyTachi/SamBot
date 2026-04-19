import random

import discord
from discord.ext import commands
import logging
import time

from Brain.Memory.DataManager import data_manager


class JobDropdown(discord.ui.Select):
    def __init__(self, empregos_disponiveis, xp_usuario):
        options = []
        for job_id, info in empregos_disponiveis.items():
            if xp_usuario >= info.get("xp_necessario", 0):
                desc = (
                    f"Salário: 🪙 {info['salario_base']} | {info['descricao'][:40]}..."
                )
                options.append(
                    discord.SelectOption(
                        label=info["nome"], value=job_id, description=desc, emoji="💼"
                    )
                )

        super().__init__(
            placeholder="Selecione a sua nova profissão...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        job_id = self.values[0]
        user_id = str(interaction.user.id)

        data_manager.set_user_data(user_id, "emprego_atual", job_id)
        data_manager.set_user_data(user_id, "ultima_troca_emprego", time.time())

        await interaction.response.edit_message(
            content=f"🎉 Parabéns! Assinou o contrato como **{self.options[0].label}**.\nUse `+work` para começar o seu expediente!",
            view=None,
        )


class JobSelectView(discord.ui.View):
    def __init__(self, empregos, xp_usuario):
        super().__init__(timeout=60)
        self.add_item(JobDropdown(empregos, xp_usuario))


class Work(commands.Cog):
    """Cog de Trabalho e Profissões."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Work")

    @commands.hybrid_command(
        name="work",
        aliases=["trabalhar"],
        description="Trabalhe para ganhar moedas e maestria!",
    )
    async def work(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        agora = time.time()

        empregos_db = data_manager.get_knowledge("jobs") or {}
        if not empregos_db:
            return await ctx.send(
                "❌ A agência de empregos está fechada no momento (jobs.json não encontrado)."
            )

        emprego_atual = data_manager.get_user_data(user_id, "emprego_atual", None)
        xp_usuario = data_manager.get_user_data(user_id, "xp", 0)

        # Se não tem emprego, abre a agência (Menu Dropdown)
        if not emprego_atual or emprego_atual not in empregos_db:
            view = JobSelectView(empregos_db, xp_usuario)
            return await ctx.send(
                "📝 **Agência de Empregos Da Sam**\nVocê está desempregado! Escolha uma profissão abaixo de acordo com o seu nível de XP:",
                view=view,
            )

        # 3. Cooldown do Expediente (ex: 30 minutos = 1800 segundos)
        ultimo_work = data_manager.get_user_data(user_id, "ultimo_work", 0)
        cooldown_shift = 1800

        if agora - ultimo_work < cooldown_shift:
            faltam = int((cooldown_shift - (agora - ultimo_work)) / 60)
            return await ctx.send(
                f"⏳ O seu turno já acabou! Descanse por mais **{faltam} minutos** antes de trabalhar novamente."
            )

        # 4. Dados do Emprego Atual
        job_info = empregos_db[emprego_atual]
        salario_base = job_info.get("salario_base", 100)
        xp_ganho = job_info.get("xp_ganho", 10)
        minigames = job_info.get("minigames", [])

        # 5. Lógica de Minigames Dinâmica
        if minigames:
            jogo_sorteado = random.choice(minigames)
            venceu = True  # Começamos assumindo que ganha, a não ser que o jogo diga o contrário

            if jogo_sorteado == "separar_lixo":
                from .Minigames.Lixo import jogar_separar_lixo

                venceu = await jogar_separar_lixo(ctx)

            elif jogo_sorteado == "digitar_codigo":
                from .Minigames.Hacker import jogar_hacker

                venceu = await jogar_hacker(ctx)

            # Se ele perdeu o minigame, ele não recebe o pagamento!
            if not venceu:
                # Atualiza o cooldown para ele não poder tentar logo a seguir
                data_manager.set_user_data(user_id, "ultimo_work", agora)
                return await ctx.send(
                    "❌ Como falhou em sua tarefa, eu **peguei o seu pagamento** deste turno. Volta mais tarde!!"
                )

        # 6. Maestria (Proficiência)
        # Salva a maestria específica deste emprego no formato: {"lixeiro": 5, "hacker": 12}
        maestrias = data_manager.get_user_data(user_id, "maestrias", {})
        nivel_maestria = maestrias.get(emprego_atual, 0)

        # A cada nível de maestria, ganha 5% a mais de bônus!
        bonus_percentual = nivel_maestria * 0.05
        salario_final = int(salario_base + (salario_base * bonus_percentual))

        # Atualiza a maestria para o próximo turno
        maestrias[emprego_atual] = nivel_maestria + 1

        # 7. Pagamento e Salvamento de Dados
        saldo_atual = data_manager.get_user_data(user_id, "carteira", 0)
        data_manager.set_user_data(user_id, "carteira", saldo_atual + salario_final)
        data_manager.set_user_data(user_id, "xp", xp_usuario + xp_ganho)
        data_manager.set_user_data(user_id, "ultimo_work", agora)
        data_manager.set_user_data(user_id, "maestrias", maestrias)

        # 8. Relatório Final
        embed = discord.Embed(title="💼 Fim de Expediente", color=discord.Color.green())
        embed.add_field(name="Profissão", value=job_info["nome"], inline=True)
        embed.add_field(
            name="Pagamento",
            value=f"🪙 {salario_final:,} *(+{int(bonus_percentual*100)}% bônus)*",
            inline=True,
        )
        embed.add_field(
            name="Progresso",
            value=f"⭐ +{xp_ganho} XP\n📈 Maestria: Nível {nivel_maestria + 1}",
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="demissao",
        aliases=["resign"],
        description="Peça demissão do seu emprego atual.",
    )
    async def demissao(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        agora = time.time()

        emprego_atual = data_manager.get_user_data(user_id, "emprego_atual", None)
        if not emprego_atual:
            return await ctx.send(
                "❌ Tu não pode pedir demissão se não esta empregado!"
            )

        # Cooldown de 24 horas para trocar de emprego
        ultima_troca = data_manager.get_user_data(user_id, "ultima_troca_emprego", 0)
        cooldown_demissao = 86400  # 24 horas

        if agora - ultima_troca < cooldown_demissao:
            faltam_horas = int((cooldown_demissao - (agora - ultima_troca)) // 3600)
            return await ctx.send(
                f"⚠️ **Penalidade de Contrato!** Tem de esperar mais **{faltam_horas} horas** antes de pedir demissão novamente."
            )

        # Efetua a demissão
        data_manager.set_user_data(user_id, "emprego_atual", None)
        data_manager.set_user_data(
            user_id, "ultima_troca_emprego", agora
        )  # Reseta o timer

        await ctx.send(
            "📝 **Demissão Aceita!** Assinou a sua rescisão. Use `+work` quando quiser procurar um novo emprego."
        )


async def setup(bot):
    await bot.add_cog(Work(bot))
