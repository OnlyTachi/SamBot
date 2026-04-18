import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import os
import uuid

# Imports dos módulos internos
from Brain.Providers.LLMFactory import LLMFactory
from Brain.Memory.VectorStore import vector_store
from Brain.Memory.NightCycle import NightCycle


class Admin(commands.Cog):
    """
    Cog de Administração: Contém ferramentas de moderação e diagnóstico de infraestrutura de IA.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Admin")
        self.factory = LLMFactory.get_instance()
        self.emoji = "🔧"

    # --- Funções Auxiliares ---
    async def log_action(self, ctx, action, target, reason):
        self.logger.info(
            f"{ctx.author} executou {action} em {target}. Motivo: {reason}"
        )

    # --- Comandos de Moderação (Públicos para Staff) ---

    @commands.hybrid_command(name="clear", description="Limpa mensagens do chat.")
    @app_commands.describe(quantidade="Número de mensagens para apagar (1-100)")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, quantidade: int):
        """Apaga um número especificado de mensagens no canal atual."""
        if quantidade < 1 or quantidade > 100:
            return await ctx.send(
                "❌ Por favor, escolha um número entre 1 e 100.", ephemeral=True
            )
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=quantidade)
        await ctx.send(
            f"🧹 **{len(deleted)}** mensagens limpas por {ctx.author.mention}.",
            delete_after=5,
        )

    @commands.hybrid_command(name="kick", description="Expulsa um membro do servidor.")
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        *,
        motivo: str = "Sem motivo definido",
    ):
        """Expulsa um membro do servidor com um motivo opcional."""
        if (
            membro.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.send(
                "❌ Não podes expulsar alguém com cargo superior ao teu."
            )
        await membro.kick(reason=f"Mod: {ctx.author} | Motivo: {motivo}")
        await ctx.send(f"👢 **{membro.name}** foi expulso. Motivo: {motivo}")

    @commands.hybrid_command(name="ban", description="Bane um membro do servidor.")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        *,
        motivo: str = "Sem motivo definido",
    ):
        """Bane um membro do servidor com um motivo opcional."""
        if (
            membro.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.send(
                "❌ Não podes banir alguém com cargo superior ao teu."
            )
        await membro.ban(reason=f"Mod: {ctx.author} | Motivo: {motivo}")
        await ctx.send(f"🔨 **{membro.name}** foi banido permanentemente.")

    # --- Comandos de Infraestrutura (Apenas Dono) ---
    # era pra eu ter separado em outro cog mas ja foi.. proximo update, eu acho

    @commands.command(name="infra", aliases=["status_llm"])
    @commands.is_owner()
    async def check_infrastructure(self, ctx):
        """Exibe a configuração atual de Alta Disponibilidade (Remote/Local)."""
        embed = discord.Embed(
            title="🔧 Infraestrutura de IA", color=discord.Color.blue()
        )

        embed.add_field(
            name="🖥️ Remote (Tailscale/GPU)",
            value=f"URL: `{self.factory.remote_url}`\nSmart: `{self.factory.remote_model_smart}`\nEmbed: `{self.factory.remote_model_embed}`",
            inline=False,
        )
        embed.add_field(
            name="💻 Local (Notebook/CPU)",
            value=f"URL: `{self.factory.local_url}`\nFast: `{self.factory.local_model_fast}`\nEmbed: `{self.factory.local_model_embed}`",
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.command(name="llmtest")
    @commands.is_owner()
    async def test_generation(
        self, ctx, *, prompt: str = "Responde curto: Esta online?"
    ):
        """Testa a geração de texto (Prioridade: Gemini > Remote > Local)."""
        msg = await ctx.send("🔄 **A testar pipeline de IA...**")

        try:
            start_time = asyncio.get_event_loop().time()
            # O generate_response já trata a cascata completa
            response = await self.factory.generate_response(
                prompt, "Responde de forma técnica e curta."
            )
            elapsed = round(asyncio.get_event_loop().time() - start_time, 2)

            embed = discord.Embed(
                title="🧠 Resultado do Teste LLM",
                description=response,
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"Tempo de resposta: {elapsed}s")
            await msg.edit(content="✅ **Teste Concluído!**", embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ **Falha na Geração:** {str(e)}")

    @commands.command(name="memtest")
    @commands.is_owner()
    async def test_memory_system(self, ctx, *, text: str = "Teste de banco vetorial."):
        """Testa Embedding (Nomic) + ChromaDB."""
        msg = await ctx.send("💾 **A testando VectorStore (Nomic Failover)...**")

        try:
            test_id = f"test_{str(uuid.uuid4())[:8]}"
            # 1. Escrita
            vector_store.add_memory(
                collection_name="fatos_usuario",
                text=text,
                metadata={"type": "debug", "author": ctx.author.name},
                doc_id=test_id,
            )

            await msg.edit(content="💾 **Dados guardados.** Tentando recuperar...")
            await asyncio.sleep(1.5)

            # 2. Leitura
            retrieved = vector_store.query_relevant(
                "fatos_usuario", "O que o admin esta fazendo?", n_results=1
            )

            if retrieved:
                embed = discord.Embed(
                    title="✅ Sucesso na Memória", color=discord.Color.teal()
                )
                embed.add_field(name="Input", value=text, inline=False)
                embed.add_field(name="Recuperado", value=retrieved[0], inline=False)
                await msg.edit(content=None, embed=embed)
            else:
                await msg.edit(
                    content="⚠️ **Aviso:** Guardado com sucesso, mas a busca semântica falhou."
                )
        except Exception as e:
            await msg.edit(content=f"❌ **Erro no VectorStore:** {str(e)}")

    @commands.command(name="forcenight")
    @commands.is_owner()
    async def force_night_cycle(self, ctx):
        """Simula e executa o Ciclo Noturno imediatamente."""
        msg = await ctx.send("🌙 **A forçar Ciclo Noturno...**")

        fake_logs = [
            "User: O meu jogo favorito é Elden Ring.",
            "User: Gostava que a SamBot tivesse comandos de música.",
            "User: Faz aniversario no dia 12 de Maio.",
        ]

        try:
            worker = NightCycle()
            await worker.run_maintenance(fake_logs)
            await msg.edit(
                content="✅ **Ciclo Noturno Executado!**\nVerifica os logs para ver o resumo do Phi-3.5/Qwen."
            )
        except Exception as e:
            await msg.edit(content=f"❌ **Erro no Ciclo:** {str(e)}")


async def setup(bot):
    await bot.add_cog(Admin(bot))
