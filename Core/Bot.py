import asyncio
import difflib
import math
import os
import random
import traceback
from pathlib import Path

import discord
from discord.ext import commands, tasks

from Brain.Memory.DataManager.Connections import data_manager
from Core.ConfigLoader import AppConfig
from Core.Logger import Logger
from Modules.Admin.Mods._appeals import AppealStartView

# from Services.ServiceManager import ServiceManager

try:
    from Brain.Core.NetworkManager import NetworkManager
except ImportError:
    NetworkManager = None

try:
    from Brain.Providers.LLMFactory import llm_factory
except ImportError:
    llm_factory = None


class SamBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.presences = True

        # self.services: ServiceManager = None
        self.version = AppConfig.get("bot.version", "3.1.0")
        self.bot_name = AppConfig.get("bot.name", "SamBot")
        self.start_time = discord.utils.utcnow()

        owner_id = AppConfig.get("bot.owner_id") or os.getenv("OWNER_ID")
        self._owner_id_manual = int(owner_id) if owner_id else None

        self.is_music_playing = False
        self.stats = {"messages_read": 0, "commands_used": 0, "voice_time_minutes": 0}
        self.stats_file = "logs/bot_stats.json"

        self.debug_mode = AppConfig.debug_mode
        self.log = Logger()
        self.agent = None

        self.log.info(f"🤖 Inicializando {self.bot_name} Core v{self.version}...")
        if self.debug_mode:
            self.log.debug("Modo de depuração ativado no sistema.")

        self.run_pre_flight_checks()

        super().__init__(
            command_prefix=AppConfig.get("BOT_PREFIX", AppConfig.prefix),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_id=self._owner_id_manual,
        )

    def run_pre_flight_checks(self):
        """Executa checagens básicas locais antes de abrir conexão com o Gateway."""
        self.log.info("📋 Executando verificações pré-conexão...")

        provedores = []
        if os.getenv("GEMINI_API_KEY_1") or AppConfig.gemini_keys:
            provedores.append(
                f"Gemini ({AppConfig.get('GEMINI_MODEL_NAME', 'gemini-2.5-flash')})"
            )
        if os.getenv("GROQ_API_KEY"):
            provedores.append(
                f"Groq ({AppConfig.get('GROQ_MODEL', 'llama-3.1-8b-instant')})"
            )
        if os.getenv("OPENROUTER_API_KEY"):
            provedores.append(
                f"OpenRouter ({AppConfig.get('OPENROUTER_MODEL', 'llama-3.1-8b-instant')})"
            )
        if os.getenv("DEEPSEEK_API_KEY"):
            provedores.append(
                f"DeepSeek ({AppConfig.get('DEEPSEEK_MODEL', 'llama-3.1-8b-instant')})"
            )
        if os.getenv("OLLAMA_REMOTE_URL"):
            provedores.append(
                f"Ollama Remoto ({AppConfig.get('MODEL_SMART_REMOTE', 'phi3.5:latest')})"
            )
        if os.getenv("OLLAMA_LOCAL_URL"):
            provedores.append(
                f"Ollama Local ({AppConfig.get('MODEL_FAST_LOCAL', 'qwen2.5:1.5b')})"
            )

        ia_env_info = (
            f"{len(provedores)} provedor(es) detectado(s)"
            if provedores
            else "Nenhuma chave de IA detectada"
        )
        db_status = "Conectado" if data_manager else "Não detectado"
        music_mode = AppConfig.get("MUSIC_SOURCE_MODE", "ONLINE").upper()

        self.log.info(f"   - Base de Dados: {db_status}")
        self.log.info(f"   - Configuração IA (.env/YAML): {ia_env_info}")
        self.log.info(f"   - Fonte de Música: {music_mode}")

    async def setup_hook(self):
        self.log.info("🔌 Iniciando Main Loop e carregando módulos...")
        await self.carregar_cogs()

        self.agent = self.get_cog("CerebroIA")
        if self.agent:
            self.log.info(
                f"🧠 Cérebro vinculado. Status: {getattr(self.agent, 'status', 'Pronto')}"
            )
        else:
            self.log.warning(
                "⚠️ O módulo Brain/Agent.py não foi carregado. O bot operará sem IA."
            )

        # Sincronização condicional de comandos
        sync_on_startup = AppConfig.get("SYNC_COMMANDS_ON_STARTUP", True)
        test_guild_id = os.getenv("TEST_GUILD_ID")

        if sync_on_startup:
            self.log.info("Sincronizando árvore de comandos...")
            try:
                if self.debug_mode and test_guild_id:
                    guild_obj = discord.Object(id=int(test_guild_id))
                    self.tree.copy_global_to(guild=guild_obj)
                    synced = await self.tree.sync(guild=guild_obj)
                    self.log.info(
                        f"{len(synced)} comandos sincronizados na guilda de teste ({test_guild_id})."
                    )
                else:
                    synced = await self.tree.sync()
                    self.log.info(f"{len(synced)} comandos globais sincronizados.")
            except discord.HTTPException as e:
                self.log.error(
                    f"❌ Erro de API ao sincronizar comandos: {e.status} - {e.text}"
                )
            except Exception as e:
                self.log.error(f"❌ Falha inesperada na sincronização: {e}")
        else:
            self.log.info("⏩ Sincronização automática de slash commands ignorada.")

        # self.services = ServiceManager(self)
        # await self.services.start_all()
        self.log.info("✅ Setup concluído.")

    async def carregar_cogs(self):
        self.log.info("📥 Carregando extensões (Cogs)...")
        pastas_raizes = [Path("Modules"), Path("Brain"), Path("Services")]
        ignorar_pastas = {
            "Tools",
            "Memory",
            "Providers",
            "Core",
            "Data",
            "__pycache__",
            "Lavalink",
        }
        ignorar_arquivos = {"__init__.py", "LLMFactory.py", "Bot.py", "Logger.py"}

        total_carregados = 0
        total_erros = 0

        for pasta_raiz in pastas_raizes:
            if not pasta_raiz.exists():
                self.log.warning(
                    f"⚠️ Diretório de módulos não encontrado: {pasta_raiz}"
                )
                continue

            for arquivo in pasta_raiz.rglob("*.py"):
                if any(parte in ignorar_pastas for parte in arquivo.parts):
                    continue
                if arquivo.name in ignorar_arquivos or arquivo.name.startswith("_"):
                    continue

                nome_extensao = ".".join(arquivo.with_suffix("").parts)

                try:
                    await self.load_extension(nome_extensao)
                    self.log.info(f"🔹 Módulo carregado: {nome_extensao}")
                    total_carregados += 1
                except commands.NoEntryPointError:
                    if self.debug_mode:
                        self.log.debug(f"⚪ Ignorado (sem setup()): {nome_extensao}")
                except commands.ExtensionFailed as e:
                    total_erros += 1
                    self.log.error(
                        f"❌ Erro de execução no setup de {nome_extensao}: {e.original}"
                    )
                    if self.debug_mode:
                        traceback.print_exception(
                            type(e.original), e.original, e.original.__traceback__
                        )
                except commands.ExtensionNotFound:
                    total_erros += 1
                    self.log.error(f"❌ Extensão não encontrada: {nome_extensao}")
                except Exception as e:
                    total_erros += 1
                    self.log.error(
                        f"❌ Falha genérica ao carregar {nome_extensao}: {e}"
                    )

        self.log.info(
            f"🏁 Cogs finalizados: {total_carregados} carregados com sucesso | {total_erros} falhas."
        )

    async def run_diagnostics(self):
        """Executa o diagnóstico completo com a conexão ativa no Discord."""
        self.log.info("📊 Diagnóstico pós-conexão (Sistemas Online)...")
        lat = self.latency
        latency_msg = (
            f"{int(lat * 1000)}ms" if lat and not math.isnan(lat) else "Desconhecida"
        )

        modelos_configurados = []
        if os.getenv("GEMINI_API_KEY_1") or AppConfig.gemini_keys:
            modelos_configurados.append(
                ("Gemini", AppConfig.get("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
            )
        if os.getenv("GROQ_API_KEY"):
            modelos_configurados.append(
                ("Groq", AppConfig.get("GROQ_MODEL", "llama-3.1-8b-instant"))
            )
        if os.getenv("OPENROUTER_API_KEY"):
            modelos_configurados.append(
                (
                    "OpenRouter",
                    AppConfig.get("OPENROUTER_MODEL", "llama-3.1-8b-instant"),
                )
            )
        if os.getenv("DEEPSEEK_API_KEY"):
            modelos_configurados.append(
                ("DeepSeek", AppConfig.get("DEEPSEEK_MODEL", "llama-3.1-8b-instant"))
            )
        if os.getenv("OLLAMA_REMOTE_URL"):
            modelos_configurados.append(
                ("Ollama Remoto", AppConfig.get("MODEL_SMART_REMOTE", "phi3.5:latest"))
            )
        if os.getenv("OLLAMA_LOCAL_URL"):
            modelos_configurados.append(
                ("Ollama Local", AppConfig.get("MODEL_FAST_LOCAL", "qwen2.5:1.5b"))
            )

        ia_status = "DESATIVADA"
        if self.agent:
            modelo_ativo = None
            if llm_factory and getattr(llm_factory, "active_model", None):
                modelo_ativo = getattr(
                    llm_factory.active_model,
                    "model_name",
                    getattr(
                        llm_factory.active_model, "model", str(llm_factory.active_model)
                    ),
                )

            if modelo_ativo:
                secundarios = len(modelos_configurados) - 1
                txt_sec = f" (+{secundarios} secundários)" if secundarios > 0 else ""
                ia_status = f"ONLINE -> {modelo_ativo}{txt_sec}"
            elif modelos_configurados:
                primario_prov, primario_mod = modelos_configurados[0]
                secundarios = len(modelos_configurados) - 1
                txt_sec = f" (+{secundarios} secundários)" if secundarios > 0 else ""
                ia_status = f"ONLINE -> {primario_prov} ({primario_mod}){txt_sec}"
            else:
                ia_status = "ONLINE"
        else:
            ia_status = "CÉREBRO NÃO ENCONTRADO"

        checks = {
            "Discord API": f"v{discord.__version__}",
            "Latência WS": latency_msg,
            "Inteligência (IA)": ia_status,
            "Base de Dados": "Conectado" if data_manager else "Erro",
        }

        for check, status in checks.items():
            self.log.info(f"   - {check}: {status}")

        return True

    async def on_ready(self):
        self.log.info(f"🚀 Logado como: {self.user} (ID: {self.user.id})")
        self.log.info(f"🌐 Servidores ativos: {len(self.guilds)}")

        self.add_view(AppealStartView(self, 0, 0, "BAN"))
        await self.run_diagnostics()

        if not self.status_loop.is_running():
            self.status_loop.start()

        if not self.save_stats_loop.is_running():
            self.save_stats_loop.start()

        activity = discord.Activity(
            type=discord.ActivityType.listening, name="inicializando sistemas..."
        )
        await self.change_presence(status=discord.Status.dnd, activity=activity)

    @tasks.loop(minutes=1)
    async def save_stats_loop(self):
        active_vcs = len(self.voice_clients)
        self.stats["voice_time_minutes"] += active_vcs
        uptime = discord.utils.utcnow() - self.start_time
        data_to_save = {
            "uptime": str(uptime).split(".")[0],
            "messages_read": self.stats["messages_read"],
            "commands_used": self.stats["commands_used"],
            "voice_time_minutes": self.stats["voice_time_minutes"],
            "servers": len(self.guilds),
            "users": sum(g.member_count for g in self.guilds if g.member_count),
        }

        def _write_file():
            import json

            os.makedirs("logs", exist_ok=True)
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4)

        try:
            await asyncio.to_thread(_write_file)
        except Exception as e:
            self.log.debug(f"Falha momentânea ao salvar estatísticas: {e}")

    @tasks.loop(minutes=30)
    async def status_loop(self):
        if self.is_music_playing:
            return
        try:
            atividades_data = (
                data_manager.get_knowledge("atividades") if data_manager else {}
            )
            frases_arquivo = []
            if atividades_data and isinstance(atividades_data, dict):
                for categoria, lista in atividades_data.items():
                    if isinstance(lista, list):
                        frases_arquivo.extend(lista)

            padrao = ["música | Mencione-me!", "evoluindo...", "ajudando pessoas"]
            opcoes = frases_arquivo if frases_arquivo else padrao
            escolha = random.choice(opcoes)
            nova_atividade = discord.Activity(
                type=discord.ActivityType.listening, name=escolha
            )
            await self.change_presence(
                status=discord.Status.dnd, activity=nova_atividade
            )
            self.log.info(f"  Status atualizado com sucesso: Ouvindo '{escolha}'")
        except Exception as e:
            self.log.error(f"  Erro crítico ao atualizar status no terminal: {e}")

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.wait_until_ready()
        self.log.info("  Loop de status de atividades iniciado.")

    async def on_message(self, message):
        if message.author.bot:
            return
        self.stats["messages_read"] += 1
        await self.process_commands(message)

    async def on_command_completion(self, ctx):
        self.stats["commands_used"] += 1

    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, "on_error"):
            return
        if isinstance(error, commands.CommandNotFound):
            invoked = ctx.invoked_with
            all_cmds = [cmd.name for cmd in self.commands]
            for cmd in self.commands:
                all_cmds.extend(cmd.aliases)
            matches = difflib.get_close_matches(invoked, all_cmds, n=1, cutoff=0.6)
            if matches:
                await ctx.reply(
                    f"Não encontrei `{ctx.prefix}{invoked}`. Você quis dizer `{ctx.prefix}{matches[0]}`? Boboca!",
                    delete_after=15,
                )
            return
        if isinstance(error, commands.MissingPermissions):
            return await ctx.reply(
                "⚠️ Você não tem permissão para usar este comando.", delete_after=10
            )
        if isinstance(error, commands.MissingRequiredArgument):
            cmd = ctx.command
            prefixo = ctx.prefix
            modulo_path = cmd.cog.__module__ if cmd.cog else ""
            partes = modulo_path.split(".")
            folder_name = (
                partes[1] if len(partes) > 1 and partes[0] == "Modules" else "Utility"
            )
            categorias_nomes = {
                "Admin": "Administração",
                "Fun": "Diversão",
                "Utility": "Utilitários",
                "Developer": "Desenvolvedor",
                "Streamer": "Streamer",
            }
            categoria = categorias_nomes.get(folder_name, "Geral")
            descricao = (
                cmd.description
                or cmd.help
                or "Nenhuma descrição detalhada fornecida para este comando."
            )
            lista_sinonimos = [f"{prefixo}{alias}" for alias in cmd.aliases]
            lista_sinonimos.append(f"/{cmd.qualified_name}")
            txt_sinonimos = ", ".join(lista_sinonimos)
            embed = discord.Embed(
                title="❓ Como usar este comando?",
                description=f"**{prefixo}{cmd.qualified_name}**\n{descricao}\n\n👉 **Uso Correto:**\n`{prefixo}{cmd.qualified_name} {cmd.signature}`",
                color=0x9146FF,
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="📌 Sinônimos", value=f"```\n{txt_sinonimos}\n```", inline=False
            )
            embed.set_footer(
                text=f"{ctx.author.name} • {categoria}",
                icon_url=ctx.author.display_avatar.url,
            )
            return await ctx.reply(embed=embed, delete_after=60)

        self.log.error(f"Erro no comando '{ctx.command}': {error}")
        if self.debug_mode:
            traceback.print_exception(type(error), error, error.__traceback__)

    async def close(self):
        """Executado ao desligar o bot (Ctrl+C ou encerramento gracioso)."""
        # if self.services:
        # await self.services.stop_all()

        if NetworkManager:
            await NetworkManager.close_all()

        await super().close()
