import discord
from discord.ext import commands, tasks
import logging
import difflib
import random
import asyncio
import os
import math
from datetime import datetime

# Camada de Inteligência e Dados
from Brain.Memory.DataManager import data_manager
try:
    # Importa a instância já inicializada para diagnósticos
    from Brain.Providers.LLMFactory import LLMFactory, llm_factory
except ImportError:
    LLMFactory = None
    llm_factory = None

# Tenta importar o Logger customizado
try:
    from .Logger import Logger
except ImportError:
    class Logger:
        def __init__(self):
            self.logger = logging.getLogger("SamBot.Core")
            if not self.logger.handlers:
                logging.basicConfig(level=logging.INFO)
        def info(self, msg): self.logger.info(msg)
        def error(self, msg): self.logger.error(msg)
        def critical(self, msg): self.logger.critical(msg)
        def warning(self, msg): self.logger.warning(msg)

class SamBot(commands.Bot):
    def __init__(self):
        # 1. Configuração de Intents (Permissões)
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.presences = True

        # 2. Configuração de Identidade
        self.version = "2.0.5"
        self.start_time = datetime.now()
        owner_id = os.getenv("OWNER_ID")
        self._owner_id_manual = int(owner_id) if owner_id else None
        self.is_music_playing = False

        # 3. Inicialização do Logger
        self.log = Logger()
        self.agent = None 
        
        self.log.info(f"🤖 Inicializando SamBot Core v{self.version}...")

        super().__init__(
            command_prefix=os.getenv("BOT_PREFIX"),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_id=self._owner_id_manual
        )

    async def setup_hook(self):
        """Método de inicialização assíncrona do discord.py"""
        self.log.info("🔌 Iniciando Main Loop...")
        await self.carregar_cogs()
        self.agent = self.get_cog('CerebroIA')
        if self.agent:
            self.log.info(f"🧠 Cérebro IA (Agent) vinculado ao Core. Status: {self.agent.status if hasattr(self.agent, 'status') else 'Pronto'}")
        else:
            self.log.warning("⚠️ O módulo Brain/Agent.py não foi carregado. O bot está em modo 'Lobotomizado'.")    

        await self.run_diagnostics()

        self.log.info("🔄 Sincronizando árvore de comandos...")
        try:
            synced = await self.tree.sync()
            self.log.info(f"✅ {len(synced)} comandos sincronizados com sucesso.")
        except Exception as e:
            self.log.error(f"❌ Falha na sincronização de comandos: {e}")

        self.log.info("✅ Setup do hook concluído.")

    async def carregar_cogs(self):
        """Carrega recursivamente os arquivos .py nas pastas Modules e Brain, filtrando utilitários."""
        self.log.info("📥 Carregando extensões (Cogs)...")
        
        pastas_raizes = ['./Modules', './Brain']
        ignorar_pastas = ['Tools', 'Memory', 'Providers', 'Core', 'Data', '__pycache__', 'Lavalink']
        ignorar_arquivos = ['__init__.py', 'LLMFactory.py', 'Bot.py', 'Logger.py']

        for pasta_raiz in pastas_raizes:
            if not os.path.exists(pasta_raiz):
                continue
                
            for root, dirs, files in os.walk(pasta_raiz):
                dirs[:] = [d for d in dirs if d not in ignorar_pastas]
                
                for file in files:
                    if file.endswith(".py") and file not in ignorar_arquivos:
                        caminho_relativo = os.path.relpath(os.path.join(root, file), ".")
                        nome_extensao = caminho_relativo.replace(os.sep, ".").replace(".py", "")
                        
                        try:
                            await self.load_extension(nome_extensao)
                            self.log.info(f"🔹 Módulo carregado: {nome_extensao}")
                        except commands.NoEntryPointError:
                            pass
                        except Exception as e:
                            self.log.error(f"❌ Falha ao carregar {nome_extensao}: {e}")

    async def run_diagnostics(self):
        """Executa verificações de inicialização e saúde do sistema."""
        self.log.info("🏥 Iniciando diagnóstico de sistemas...")
        
        lat = self.latency
        latency_msg = f"{int(lat * 1000)}ms" if lat and not math.isnan(lat) else "WS Offline"
        ia_status = "OFFLINE"
        if self.agent:
            ia_status = "ONLINE"
            if llm_factory and llm_factory.active_model:
                nome_modelo = getattr(llm_factory.active_model, 'model_name', str(llm_factory.active_model))
                ia_status += f" ({nome_modelo})"
            else:
                ia_status += " (Sem LLM)"
        else:
            ia_status = "CÉREBRO NÃO ENCONTRADO"

        checks = {
            "Discord API": f"v{discord.__version__}",
            "Latência": latency_msg,
            "Inteligência": ia_status,
            "Base de Dados": "Conectado" if data_manager else "Erro"
        }
        
        for check, status in checks.items():
            self.log.info(f"   - {check}: {status}")
            
        return True

    async def on_ready(self):
        """Evento disparado ao estabelecer conexão."""
        self.log.info(f"🚀 Logado como: {self.user} (ID: {self.user.id})")
        self.log.info(f"🌐 Servidores ativos: {len(self.guilds)}")
        if not self.status_loop.is_running():
            self.status_loop.start()

        # Status inicial focado em música e interação
        activity = discord.Activity(type=discord.ActivityType.listening)
        await self.change_presence(status=discord.Status.dnd, activity=activity)

# talvez mover isso para outro lugar depois e arrumar os status...

    @tasks.loop(minutes=30)
    async def status_loop(self):
        """Alterna a atividade do bot usando dados do DataManager."""
        if self.is_music_playing:
            return      
        try:
            atividades_data = data_manager.get_knowledge('atividades') if data_manager else {}
            
            frases_arquivo = []
            
            if atividades_data and isinstance(atividades_data, dict):
                for categoria, lista in atividades_data.items():
                    if isinstance(lista, list):
                        frases_arquivo.extend(lista)
            
            padrao = ["música | Mencione-me!", "evoluindo...", "ajudando pessoas"]
            
            opcoes = frases_arquivo + padrao
            
            if not opcoes:
                opcoes = padrao 

            escolha = random.choice(opcoes)
            
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(type=discord.ActivityType.listening, name=escolha, status=discord.Status.dont_disturb)
            )
        except Exception as e:
            self.log.error(f"Erro ao atualizar status: {e}")

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.wait_until_ready()

    async def on_message(self, message):
        """Processa mensagens recebidas."""
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        """Gerencia erros de comandos e sugere alternativas similares."""
        if hasattr(ctx.command, 'on_error'):
            return

        if isinstance(error, commands.CommandNotFound):
            invoked = ctx.invoked_with
            all_cmds = [cmd.name for cmd in self.commands]
            for cmd in self.commands:
                all_cmds.extend(cmd.aliases)
            
            matches = difflib.get_close_matches(invoked, all_cmds, n=1, cutoff=0.6)
            if matches:
                await ctx.reply(f"Não encontrei `{ctx.prefix}{invoked}`. Você quis dizer `{ctx.prefix}{matches[0]}`? bobao!!", delete_after=15)
            return

        if isinstance(error, commands.MissingPermissions):
            return await ctx.reply("⛔ Você não tem permissão para usar este comando.", delete_after=10)

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply(f"⚠️ Uso incorreto! Tente: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", delete_after=20)

        self.log.error(f"Erro no comando '{ctx.command}': {error}")