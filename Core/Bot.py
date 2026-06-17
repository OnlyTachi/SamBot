import discord
from discord.ext import commands, tasks
import logging
import difflib
import random
import asyncio
import os
import math
import json

# Camada de Inteligência e Dados
from Brain.Memory.DataManager import data_manager
from Modules.Admin.Mods._appeals import AppealStartView

try:
    # Importa a instância já inicializada para diagnósticos
    from Brain.Providers.LLMFactory import LLMFactory, llm_factory
except ImportError:
    LLMFactory = None
    llm_factory = None

try:
    from .Logger import Logger
except ImportError:

    class Logger:
        def __init__(self):
            self.logger = logging.getLogger("SamBot.Core")
            if not self.logger.handlers:
                logging.basicConfig(level=logging.INFO)

        def info(self, msg):
            self.logger.info(msg)

        def error(self, msg):
            self.logger.error(msg)

        def critical(self, msg):
            self.logger.critical(msg)

        def warning(self, msg):
            self.logger.warning(msg)


class SamBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.presences = True

        try:
            with open("config.json", "r", encoding="utf-8") as f:
                self.config_info = json.load(f)
        except FileNotFoundError:
            self.config_info = {"version": "2.0.5", "name": "SamBot"}

        self.version = self.config_info.get("version", "2.0.5")
        self.start_time = discord.utils.utcnow()
        owner_id = os.getenv("OWNER_ID")
        self._owner_id_manual = int(owner_id) if owner_id else None
        self.is_music_playing = False

        self.stats = {"messages_read": 0, "commands_used": 0, "voice_time_minutes": 0}
        self.stats_file = "logs/bot_stats.json"

        self.log = Logger()
        self.agent = None

        self.log.info(
            f"🤖 Inicializando {self.config_info.get('name', 'SamBot')} Core v{self.version}..."
        )

        super().__init__(
            command_prefix=os.getenv("BOT_PREFIX", "-"),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_id=self._owner_id_manual,
        )

    async def setup_hook(self):
        self.log.info("🔌 Iniciando Main Loop e carregando módulos...")
        await self.carregar_cogs()

        self.agent = self.get_cog("CerebroIA")
        if self.agent:
            self.log.info(
                f"🧠 Cérebro IA (Agent) vinculado. Status: {getattr(self.agent, 'status', 'Pronto')}"
            )
        else:
            self.log.warning(
                "⚠️ O módulo Brain/Agent.py não foi carregado. O bot operará sem IA."
            )

        self.log.info("🔄 Sincronizando árvore de comandos...")
        try:
            synced = await self.tree.sync()
            self.log.info(f"✅ {len(synced)} comandos sincronizados com sucesso.")
        except Exception as e:
            self.log.error(f"❌ Falha na sincronização de comandos: {e}")

        self.log.info("✅ Setup do hook concluído.")

    async def carregar_cogs(self):
        self.log.info("📥 Carregando extensões (Cogs)...")
        pastas_raizes = [
            "./Modules",
            "./Brain",
            "./Audio",
        ]  # Incluí Audio para garantir que a refatoração carregue bem
        ignorar_pastas = [
            "Tools",
            "Memory",
            "Providers",
            "Core",
            "Data",
            "__pycache__",
            "Lavalink",
        ]
        ignorar_arquivos = ["__init__.py", "LLMFactory.py", "Bot.py", "Logger.py"]

        for pasta_raiz in pastas_raizes:
            if not os.path.exists(pasta_raiz):
                continue
            for root, dirs, files in os.walk(pasta_raiz):
                dirs[:] = [d for d in dirs if d not in ignorar_pastas]
                for file in files:
                    # Ignoramos arquivos que começam com _ (ex: _manager.py, _core.py) na nova arquitetura
                    if (
                        file.endswith(".py")
                        and file not in ignorar_arquivos
                        and not file.startswith("_")
                    ):
                        caminho_relativo = os.path.relpath(
                            os.path.join(root, file), "."
                        )
                        nome_extensao = caminho_relativo.replace(os.sep, ".").replace(
                            ".py", ""
                        )
                        try:
                            await self.load_extension(nome_extensao)
                            self.log.info(f"🔹 Módulo carregado: {nome_extensao}")
                        except commands.NoEntryPointError:
                            pass
                        except Exception as e:
                            self.log.error(f"❌ Falha ao carregar {nome_extensao}: {e}")

    async def run_diagnostics(self):
        self.log.info("🏥 Diagnóstico pós-conexão...")
        lat = self.latency
        latency_msg = (
            f"{int(lat * 1000)}ms" if lat and not math.isnan(lat) else "Desconhecida"
        )

        ia_status = "OFFLINE"
        if self.agent:
            ia_status = "ONLINE"
            if llm_factory and getattr(llm_factory, "active_model", None):
                nome_modelo = getattr(
                    llm_factory.active_model,
                    "model_name",
                    str(llm_factory.active_model),
                )
                ia_status += f" ({nome_modelo})"
            else:
                ia_status += " (Sem LLM)"
        else:
            ia_status = "CÉREBRO NÃO ENCONTRADO"

        checks = {
            "Discord API": f"v{discord.__version__}",
            "Latência WS": latency_msg,
            "Inteligência": ia_status,
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

        # Inicia o laço que envia dados para o Launcher
        if not self.save_stats_loop.is_running():
            self.save_stats_loop.start()

        activity = discord.Activity(
            type=discord.ActivityType.listening, name="inicializando sistemas..."
        )
        await self.change_presence(status=discord.Status.dnd, activity=activity)

    @tasks.loop(minutes=1)
    async def save_stats_loop(self):
        """Salva as estatísticas do bot a cada 1 minuto para o launcher conseguir ler."""
        active_vcs = len(self.voice_clients)
        self.stats["voice_time_minutes"] += active_vcs

        uptime = discord.utils.utcnow() - self.start_time

        data_to_save = {
            "uptime": str(uptime).split(".")[
                0
            ],  # Formata para não mostrar milisegundos
            "messages_read": self.stats["messages_read"],
            "commands_used": self.stats["commands_used"],
            "voice_time_minutes": self.stats["voice_time_minutes"],
            "servers": len(self.guilds),
            "users": sum(g.member_count for g in self.guilds if g.member_count),
        }

        try:
            os.makedirs("logs", exist_ok=True)
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4)
        except Exception:
            pass  # Ignora silenciosamente se o arquivo estiver em uso

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
            self.log.info(f"✅ Status atualizado com sucesso: Ouvindo '{escolha}'")

        except Exception as e:
            self.log.error(f"❌ Erro crítico ao atualizar status no terminal: {e}")

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.wait_until_ready()
        self.log.info("🕒 Loop de status de atividades iniciado.")

    async def on_message(self, message):
        if message.author.bot:
            return

        self.stats["messages_read"] += 1
        await self.process_commands(message)

    async def on_command_completion(self, ctx):
        """Evento disparado quando um comando termina com sucesso."""
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
                    f"Não encontrei `{ctx.prefix}{invoked}`. Você quis dizer `{ctx.prefix}{matches[0]}`? bobao!!",
                    delete_after=15,
                )
            return

        if isinstance(error, commands.MissingPermissions):
            return await ctx.reply(
                "⛔ Você não tem permissão para usar este comando.", delete_after=10
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
                title="📌 Como usar este comando?",
                description=f"**{prefixo}{cmd.qualified_name}**\n{descricao}\n\n🤔 **Uso Correto:**\n`{prefixo}{cmd.qualified_name} {cmd.signature}`",
                color=0x9146FF,
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="🔍 Sinônimos", value=f"```\n{txt_sinonimos}\n```", inline=False
            )
            embed.set_footer(
                text=f"{ctx.author.name} • {categoria}",
                icon_url=ctx.author.display_avatar.url,
            )

            return await ctx.reply(embed=embed, delete_after=60)

        self.log.error(f"Erro no comando '{ctx.command}': {error}")
