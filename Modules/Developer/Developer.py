import discord
from discord.ext import commands
import logging
import asyncio
import uuid

# Imports dos módulos internos
from Brain.Providers.LLMFactory import LLMFactory
from Brain.Memory.VectorStore import vector_store
from Brain.Memory.NightCycle import NightCycle


class Developer(commands.Cog):
    """
    Cog de Desenvolvedor: Ferramentas de diagnóstico de infraestrutura de IA.
    Acesso restrito ao dono do bot.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Developer")
        self.factory = LLMFactory.get_instance()
        self.emoji = "💻"

    @commands.command(name="infra", aliases=["status_llm"])
    @commands.is_owner()
    async def check_infrastructure(self, ctx):
        """Exibe a configuração atual de Alta Disponibilidade (Remote/Local)."""
        embed = discord.Embed(
            title="🔧 Infraestrutura de IA", color=discord.Color.dark_grey()
        )

        embed.add_field(
            name="🖥️ Remote (Nuvem/API)",
            value=f"Modelo: `{self.factory.model_name}`\nEmbed: `{self.factory.embed_model_cloud}`",
            inline=False,
        )
        embed.add_field(
            name="💻 Local (Ollama/CPU)",
            value=f"URL: `{self.factory.local_url}`\nFast: `{self.factory.local_model}`\nEmbed: `{self.factory.embed_model_local}`",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(name="llmtest")
    @commands.is_owner()
    async def test_generation(
        self, ctx, *, prompt: str = "Responda curto: Você está online?"
    ):
        """Testa a geração de texto (Prioridade: Gemini > Remote > Local)."""
        msg = await ctx.send("🔄 **Testando pipeline de IA...**")
        try:
            start_time = asyncio.get_event_loop().time()
            response = await self.factory.generate_response(
                prompt, "Responda de forma técnica e curta."
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
        """Testa Embedding (Gemini Cloud + Nomic Local) e ChromaDB."""
        msg = await ctx.send("💾 **Testando VectorStore (Failover Ativo)...**")
        try:
            test_id = f"test_{str(uuid.uuid4())[:8]}"

            await vector_store.add_memory(
                collection_name="fatos_usuario",
                text=text,
                metadata={"type": "debug", "author": ctx.author.name},
                doc_id=test_id,
            )

            await msg.edit(content="💾 **Dados guardados.** Tentando recuperar...")
            await asyncio.sleep(1.5)

            # CORREÇÃO: Adicionado o await
            retrieved = await vector_store.query_relevant(
                "fatos_usuario", "O que o admin esta fazendo?", n_results=1
            )

            if retrieved:
                embed = discord.Embed(
                    title="✅ Sucesso na Memória", color=discord.Color.teal()
                )
                embed.add_field(name="Input", value=text, inline=False)
                embed.add_field(name="Recuperado", value=retrieved, inline=False)
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
        msg = await ctx.send("🌙 **Forçando Ciclo Noturno...**")
        fake_logs = [
            "User: O meu jogo favorito é Elden Ring.",
            "User: Gostava que a SamBot tivesse comandos de música.",
            "User: Faz aniversario no dia 12 de Maio.",
        ]
        try:
            worker = NightCycle()
            await worker.run_maintenance(fake_logs)
            await msg.edit(
                content="✅ **Ciclo Noturno Executado!**\nVerifique os logs no terminal para ver o resumo extraído."
            )
        except Exception as e:
            await msg.edit(content=f"❌ **Erro no Ciclo:** {str(e)}")


async def setup(bot):
    await bot.add_cog(Developer(bot))
