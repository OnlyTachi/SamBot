import discord
from discord.ext import commands
import logging
import datetime


class Moderacao(commands.Cog):
    """
    Cog de Moderação: Comandos manuais para controle de usuários e chat.
    Integra-se automaticamente com o módulo de Avisos para anúncios públicos.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Moderacao")

    async def _checar_hierarquia(self, ctx, membro: discord.Member) -> bool:
        """Verifica se o bot e o autor têm permissão hierárquica para punir o membro."""
        if membro.id == ctx.author.id:
            await ctx.send("❌ Você não pode punir a si mesmo!", ephemeral=True)
            return False
        if membro.id == self.bot.user.id:
            await ctx.send("❌ Eu não vou me punir!", ephemeral=True)
            return False
        if (
            ctx.author.top_role <= membro.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            await ctx.send(
                "❌ Você não pode punir alguém com um cargo igual ou superior ao seu.",
                ephemeral=True,
            )
            return False
        if ctx.guild.me.top_role <= membro.top_role:
            await ctx.send(
                "❌ Eu não tenho permissão para punir este membro (o cargo dele é maior que o meu).",
                ephemeral=True,
            )
            return False
        return True

    async def _disparar_aviso(
        self, ctx, tipo: str, membro: discord.Member, motivo: str
    ):
        """Busca o módulo de Avisos e aciona a função de anúncio público."""
        avisos_cog = self.bot.get_cog("Avisos")
        if avisos_cog:
            await avisos_cog.enviar_aviso(ctx.guild, tipo, membro, ctx.author, motivo)

    # --- COMANDO DE BANIR ---
    @commands.hybrid_command(
        name="ban", description="[Admin] Bane um membro do servidor."
    )
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        *,
        motivo: str = "Violação das regras do servidor.",
    ):
        if not await self._checar_hierarquia(ctx, membro):
            return

        try:
            # Tenta avisar o usuário na DM antes de banir
            try:
                await membro.send(
                    f"🔨 Você foi **banido** do servidor **{ctx.guild.name}**.\n**Motivo:** {motivo}"
                )
            except:
                pass  # Ignora se a DM estiver fechada

            await membro.ban(reason=f"Banido por {ctx.author} - Motivo: {motivo}")

            embed = discord.Embed(
                title="🔨 Membro Banido", color=discord.Color.dark_red()
            )
            embed.description = f"**{membro.display_name}** foi banido com sucesso.\n**Motivo:** {motivo}"
            await ctx.send(embed=embed, ephemeral=True)

            # Aciona o canal público de punições
            await self._disparar_aviso(ctx, "BAN", membro, motivo)

        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro ao tentar banir o membro: `{e}`")
            self.logger.error(f"Erro no comando ban: {e}")

    # --- COMANDO DE DESBANIR (UNBAN) ---
    @commands.hybrid_command(
        name="unban",
        aliases=["desbanir"],
        description="[Admin] Desbane um membro do servidor usando o ID.",
    )
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: commands.Context,
        user_id: str,
        *,
        motivo: str = "Apelo aceito / Erro na punição.",
    ):
        try:
            uid = int(user_id)
            user = await self.bot.fetch_user(uid)

            await ctx.guild.unban(
                user, reason=f"Desbanido por {ctx.author} - Motivo: {motivo}"
            )

            embed = discord.Embed(
                title="🕊️ Membro Desbanido", color=discord.Color.green()
            )
            embed.description = f"**{user.name}** (`{user.id}`) foi desbanido com sucesso.\n**Motivo:** {motivo}"
            await ctx.send(embed=embed, ephemeral=True)

            # Opcional: Aciona o canal de avisos (Você precisaria adicionar a cor do UNBAN lá no Avisos.py)
            await self._disparar_aviso(ctx, "UNBAN", user, motivo)

        except ValueError:
            await ctx.send(
                "❌ Erro: Você deve fornecer o ID numérico do usuário.", ephemeral=True
            )
        except discord.NotFound:
            await ctx.send(
                "❌ Erro: Usuário não encontrado nos registros do Discord ou não está banido.",
                ephemeral=True,
            )
        except Exception as e:
            await ctx.send(
                f"❌ Ocorreu um erro ao tentar desbanir o usuário: `{e}`",
                ephemeral=True,
            )

    # --- COMANDO DE EXPULSAR (KICK) ---
    @commands.hybrid_command(
        name="kick", description="[Admin] Expulsa um membro do servidor."
    )
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        *,
        motivo: str = "Violação das regras do servidor.",
    ):
        if not await self._checar_hierarquia(ctx, membro):
            return

        try:
            try:
                await membro.send(
                    f"👢 Você foi **expulso** do servidor **{ctx.guild.name}**.\n**Motivo:** {motivo}"
                )
            except:
                pass

            await membro.kick(reason=f"Expulso por {ctx.author} - Motivo: {motivo}")

            embed = discord.Embed(
                title="👢 Membro Expulso", color=discord.Color.orange()
            )
            embed.description = f"**{membro.display_name}** foi expulso com sucesso.\n**Motivo:** {motivo}"
            await ctx.send(embed=embed, ephemeral=True)

            await self._disparar_aviso(ctx, "KICK", membro, motivo)

        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro ao tentar expulsar o membro: `{e}`")

    # --- COMANDO DE SILENCIAR (MUTE / TIMEOUT) ---
    @commands.hybrid_command(
        name="mute",
        aliases=["timeout", "silenciar"],
        description="[Admin] Silencia um membro temporariamente.",
    )
    @commands.has_permissions(moderate_members=True)
    async def mute(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        minutos: int,
        *,
        motivo: str = "Comportamento inadequado.",
    ):
        if not await self._checar_hierarquia(ctx, membro):
            return

        if minutos <= 0 or minutos > 40320:  # Limite do Discord é 28 dias
            return await ctx.send(
                "❌ O tempo de mute deve ser entre 1 minuto e 28 dias (40320 minutos)."
            )

        try:
            tempo = discord.utils.utcnow() + datetime.timedelta(minutes=minutos)
            await membro.timeout(
                tempo, reason=f"Mutado por {ctx.author} - Motivo: {motivo}"
            )

            embed = discord.Embed(
                title="🔇 Membro Silenciado", color=discord.Color.yellow()
            )
            embed.description = f"**{membro.display_name}** foi silenciado por **{minutos} minutos**.\n**Motivo:** {motivo}"
            await ctx.send(embed=embed, ephemeral=True)

            await self._disparar_aviso(
                ctx, "MUTE", membro, f"{motivo} ({minutos} minutos)"
            )

        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro ao tentar silenciar o membro: `{e}`")

    # --- COMANDO DE DESMUTAR (UNMUTE) ---
    @commands.hybrid_command(
        name="unmute",
        aliases=["desmutar", "removetimeout"],
        description="[Admin] Remove o silenciamento (timeout) de um membro.",
    )
    @commands.has_permissions(moderate_members=True)
    async def unmute(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        *,
        motivo: str = "Punição revogada / Tempo perdoado.",
    ):
        # Usa a sua própria função de segurança para evitar que moderadores desmutem superiores
        if not await self._checar_hierarquia(ctx, membro):
            return

        try:
            # Remover o timeout no Discord.py exige apenas passar "None" como tempo
            await membro.timeout(
                None, reason=f"Desmutado por {ctx.author} - Motivo: {motivo}"
            )

            embed = discord.Embed(
                title="🔊 Membro Desmutado", color=discord.Color.green()
            )
            embed.description = f"O silenciamento de **{membro.display_name}** foi removido com sucesso.\n**Motivo:** {motivo}"
            await ctx.send(embed=embed, ephemeral=True)

            # Aciona o canal de avisos públicos
            await self._disparar_aviso(ctx, "UNMUTE", membro, motivo)

        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro ao tentar desmutar o membro: `{e}`")

    # --- COMANDO DE ADVERTÊNCIA (WARN) ---
    @commands.hybrid_command(
        name="warn",
        aliases=["avisar", "advertir"],
        description="[Admin] Dá uma advertência formal a um membro.",
    )
    @commands.has_permissions(manage_messages=True)  # Permissão mais leve que ban/kick
    async def warn(self, ctx: commands.Context, membro: discord.Member, *, motivo: str):
        if not await self._checar_hierarquia(ctx, membro):
            return

        try:
            # Tenta avisar na DM
            try:
                await membro.send(
                    f"⚠️ Você recebeu uma **advertência** no servidor **{ctx.guild.name}**.\n**Motivo:** {motivo}"
                )
            except:
                pass

            embed = discord.Embed(
                title="⚠️ Membro Advertido", color=discord.Color.yellow()
            )
            embed.description = f"**{membro.display_name}** foi advertido com sucesso.\n**Motivo:** {motivo}"
            await ctx.send(embed=embed, ephemeral=True)

            # O seu módulo de avisos já tem a cor e suporte para "AVISO" prontos!
            await self._disparar_aviso(ctx, "AVISO", membro, motivo)

        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro ao tentar advertir o membro: `{e}`")

    # --- COMANDO DE LIMPAR CHAT (CLEAR / PURGE) ---
    @commands.hybrid_command(
        name="clear",
        aliases=["limpar", "purge"],
        description="[Admin] Apaga mensagens de um canal.",
    )
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, quantidade: int):
        if quantidade <= 0 or quantidade > 100:
            return await ctx.send(
                "❌ Você só pode apagar entre 1 e 100 mensagens por vez.",
                ephemeral=True,
            )

        # O ctx.defer é importante caso apagar muitas mensagens demore
        await ctx.defer(ephemeral=True)

        try:
            # +1 para apagar também a mensagem que o moderador usou para chamar o comando
            apagadas = await ctx.channel.purge(limit=quantidade + 1)
            await ctx.send(
                f"🧹 **{len(apagadas) - 1}** mensagens foram apagadas com sucesso!",
                ephemeral=True,
            )
        except Exception as e:
            await ctx.send(f"❌ Erro ao apagar mensagens: `{e}`", ephemeral=True)

    # --- COMANDOS DE BLOQUEIO DE CANAL (LOCK/UNLOCK) ---
    @commands.hybrid_command(
        name="lock",
        aliases=["trancar"],
        description="[Admin] Impede temporariamente que os membros enviem mensagens neste canal.",
    )
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context):
        cargo_padrao = ctx.guild.default_role

        # Altera a permissão do canal atual para o cargo @everyone
        await ctx.channel.set_permissions(cargo_padrao, send_messages=False)

        embed = discord.Embed(
            title="🔒 Canal Bloqueado",
            description="Este canal foi trancado pela moderação. Apenas administradores podem enviar mensagens no momento.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="unlock",
        aliases=["destrancar"],
        description="[Admin] Libera o canal novamente para os membros.",
    )
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context):
        cargo_padrao = ctx.guild.default_role

        # Restaura a permissão padrão (None faz com que siga a configuração global do servidor)
        await ctx.channel.set_permissions(cargo_padrao, send_messages=None)

        embed = discord.Embed(
            title="🔓 Canal Desbloqueado",
            description="O canal foi liberado! Vocês já podem voltar a conversar normalmente.",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderacao(bot))
