import discord
from discord.ext import commands
import logging
import asyncio
import uuid

# Imports dos módulos internos
# CORREÇÃO 1: Importa a fábrica e a instância diretamente
from Brain.Providers.LLMFactory import llm_factory, llm_factory
from Brain.Memory.LongTerm.VectorStore import vector_store
from Brain.Core.NightCycle import NightCycle


class Developer(commands.Cog):
    """
    Cog de Desenvolvedor: Ferramentas de diagnóstico de infraestrutura de IA.
    Acesso restrito ao dono do bot.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.Developer")
        self.factory = llm_factory
        self.chain = self.factory.get_default_principal_chain()
        self.emoji = "💻"

    @commands.command(name="infra", aliases=["status_llm"])
    @commands.is_owner()
    async def check_infrastructure(self, ctx):
        """Exibe a configuração atual de Alta Disponibilidade (Remote/Local)."""
        embed = discord.Embed(
            title="🔧 Infraestrutura de IA", color=discord.Color.dark_grey()
        )

        drivers = [
            f"`{driver.__class__.__name__}`"
            for driver in self.factory.available_drivers.values()
        ]
        drivers_str = ", ".join(drivers) if drivers else "Nenhum carregado"

        embed.add_field(
            name="🤖 Drivers Disponíveis",
            value=drivers_str,
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(name="llmtest")
    @commands.is_owner()
    async def test_generation(
        self, ctx, *, prompt: str = "Responda curto: Você está online?"
    ):
        """Testa a geração de texto via cadeia orquestrada."""
        msg = await ctx.send("🔄 **Testando pipeline de IA...**")
        try:
            start_time = asyncio.get_event_loop().time()
            response = await self.chain.generate_response(
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
        """Testa Embedding e ChromaDB."""
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

    @commands.command(name="reload_db", aliases=["atualizar", "syncdb"])
    @commands.is_owner()
    async def reload_knowledge_database(self, ctx):
        """Lê os arquivos JSON da pasta Knowledge, grava no SQLite e limpa os caches."""
        msg = await ctx.send(
            "🔄 **Iniciando sincronização dos JSONs com o banco de dados...**"
        )

        try:
            import json
            from pathlib import Path
            from Brain.Memory.DataManager.Connections import data_manager

            knowledge_dir = Path("Data/Knowledge")
            arquivos_atualizados = []

            if knowledge_dir.exists():
                for json_file in knowledge_dir.glob("*.json"):
                    key_name = json_file.stem
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    data_manager.save_knowledge(key_name, data)
                    arquivos_atualizados.append(f"`{key_name}`")

            data_manager.reload_all()

            if hasattr(self.bot, "pipeline") and hasattr(self.bot.pipeline, "router"):
                await self.bot.pipeline.router.sincronizar_base_rotas(force=True)

            embed = discord.Embed(
                title="✅ Banco de Dados Sincronizado!",
                description="Os arquivos JSON foram lidos e gravados com sucesso no SQLite.",
                color=discord.Color.green(),
            )

            detalhes = (
                ", ".join(arquivos_atualizados)
                if arquivos_atualizados
                else "Nenhum JSON encontrado."
            )
            embed.add_field(
                name="📂 Registros Atualizados", value=detalhes, inline=False
            )
            embed.add_field(
                name="🧠 Cache de Memória",
                value="RAM limpa & VectorStore sincronizada.",
                inline=False,
            )

            await msg.edit(content=None, embed=embed)

        except Exception as e:
            self.logger.error(f"Erro ao sincronizar banco de dados: {e}", exc_info=True)
            await msg.edit(
                content=f"❌ **Falha ao atualizar o banco de dados:** `{str(e)}`"
            )


async def setup(bot):
    await bot.add_cog(Developer(bot))
