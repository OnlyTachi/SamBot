# nao me questione por que o nome do arquivo é Agent.py
# apenas aceite que é assim que deve ser
# ignore os monte de comentários tambem pls
import discord
from discord.ext import commands
import re
import random
import logging
import json
import traceback
import asyncio
from datetime import datetime
import time
import os

# --- Configuração de Logging ---
logger = logging.getLogger("SamBot.Agent")

# --- Inteligência ---
try:
    from Brain.Providers.LLMFactory import llm_factory
except ImportError:
    logger.critical("❌ Provedor LLM (LLMFactory) não encontrado!")
    llm_factory = None

# --- Importação Robusta de Módulos ---
TOOLS_AVAILABLE = False
MEMORY_AVAILABLE = False

# --- Ferramentas Externas ---
try:
    from Brain.Tools.WeatherTool import WeatherTool
    from Brain.Tools.Games.GameTool import GameTool
    from Brain.Tools.BuscaTools import BuscaTool
    from Brain.Tools.Images.SearchImages import ImageSearchTool
    from Brain.Tools.MusicRecTool import MusicRecTool

    TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Algumas ferramentas não foram encontradas: {e}")

# --- Módulos de Memória e Dados ---
try:
    from Brain.Memory.VectorStore import vector_store
    from Brain.Memory.Historico import HistoricoManager
    from Brain.Memory.Expressoes import ExpressoesManager
    from Brain.Memory.AutoConhecimento import AutoConhecimentoManager
    from Brain.Memory.Limpeza import LimpezaManager
    from Brain.Memory.DataManager import data_manager

    MEMORY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Módulos de memória/dados indisponíveis: {e}")


class CerebroIA(commands.Cog):
    """
    O coração cognitivo da SamBot.
    Gere a integração entre LLM, Memória Vetorial (RAG), Expressões e Ferramentas.
    """

    def __init__(self, bot):
        self.bot = bot

        # --- Inicialização de Gestores ---
        self.tools = {}
        if TOOLS_AVAILABLE:
            self._inicializar_ferramentas()

        if MEMORY_AVAILABLE:
            self.expressoes = ExpressoesManager()
            self.historico = HistoricoManager()
            self.autoconhecimento = AutoConhecimentoManager
            self.limpeza = LimpezaManager()
            self.data_manager = data_manager
            self.identity = (
                data_manager.get_identity()
                if hasattr(data_manager, "get_identity")
                else {"name": "SamBot"}
            )
        else:
            self.identity = {"name": "SamBot"}

        # Canais Ativos e Personas
        self.active_channels = {}
        if MEMORY_AVAILABLE:
            raw_channels = data_manager.load_active_channels()
            self.active_channels = (
                raw_channels if isinstance(raw_channels, dict) else {}
            )

        logger.info(f"🧠 Cérebro Conectado. Entidade: {self.identity.get('name')}")

    def _inicializar_ferramentas(self):
        """Inicializa ferramentas com tratamento de erro individual."""
        tool_map = {
            "weather": WeatherTool,
            "game_search": GameTool,
            "web_search": BuscaTool,
            "image_search": ImageSearchTool,
            "music_recommend": MusicRecTool,
        }
        for key, cls in tool_map.items():
            try:
                # Tenta instanciar com bot, senão puro
                try:
                    self.tools[key] = cls(self.bot)
                except:
                    self.tools[key] = cls()
            except Exception as e:
                logger.error(f"❌ Erro ao carregar ferramenta {key}: {e}")

    def _carregar_prompt(self, persona_name: str) -> str:
        """Carrega o system prompt baseado na persona ou arquivo."""
        if MEMORY_AVAILABLE:
            persona_key = persona_name if persona_name else "padrao"
            return self.data_manager.get_prompt(persona_key)

        # Fallback para arquivo local se data_manager falhar
        path = f"./Data/Prompts/{persona_name}.txt"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return "Você é a Sam, uma assistente virtual divertida e especialista em jogos e música."

    async def _consultar_memoria_longa(self, user_id: str, query: str) -> str:
        """Busca factos relevantes no ChromaDB (RAG)."""
        if not MEMORY_AVAILABLE:
            return ""
        try:
            fatos = vector_store.query_relevant(
                "fatos_usuario", f"user:{user_id} {query}", n_results=2
            )
            resumos = vector_store.query_relevant("resumos_diarios", query, n_results=1)
            memorias = fatos + resumos
            if not memorias:
                return ""
            return (
                f"\n[MEMÓRIA DE LONGO PRAZO RELEVANTE]:\n"
                + "\n".join([f"- {m}" for m in memorias])
                + "\n"
            )
        except Exception as e:
            logger.error(f"❌ Erro RAG: {e}")
            return ""

    async def _aprender_fatos(self, message: discord.Message, clean_text: str) -> str:
        """
        Identifica, valida via LLM, salva no VectorStore e retorna o fato aprendido.
        """
        if not MEMORY_AVAILABLE:
            return None

        # Gatilhos básicos para evitar chamadas excessivas à LLM
        gatilhos = [
            "meu nome",
            "eu gosto",
            "eu amo",
            "eu odeio",
            "eu moro",
            "sou ",
            "tenho ",
            "meu aniversário",
            "trabalho com",
            "minha mãe",
            "meu pai",
        ]

        if not any(g in clean_text.lower() for g in gatilhos):
            return None

        try:
            user_name = message.author.name

            system_prompt = (
                "Você é o Núcleo de Memória da SamBot. Sua função é extrair fatos PERMANENTES sobre o usuário.\n"
                "Analise a frase do usuário. Se for uma informação pessoal relevante (nome, gosto, profissão, local), extraia APENAS o fato.\n"
                "Se for uma brincadeira, sarcasmo ou irrelevante, responda 'IGNORE'.\n"
                "Exemplo: 'Eu amo pizza' -> 'Gosta de pizza'\n"
                "Exemplo: 'Sou o batman' -> 'IGNORE'"
            )

            extracao = await llm_factory.generate_response(
                system_prompt=system_prompt,
                user_prompt=f"Usuário {user_name} disse: '{clean_text}'",
            )

            if "IGNORE" in extracao.upper() or len(extracao.strip()) < 3:
                return None

            # Persistência na memória de longo prazo
            doc_id = f"fact_{message.author.id}_{int(time.time())}"
            vector_store.add_memory(
                "fatos_usuario",
                f"Fato sobre {user_name}: {extracao}",
                {
                    "user_id": str(message.author.id),
                    "timestamp": str(datetime.now()),
                    "source_text": clean_text,
                },
                doc_id,
            )

            await message.add_reaction("🧠")
            logger.info(
                f"🧠 Memória Episódica: Fato salvo para {user_name} -> {extracao}"
            )

            return extracao

        except Exception as e:
            logger.error(f"❌ Erro ao processar fato: {e}")
            return None

    async def _rotear_ferramentas(self, content: str, provider) -> str:
        """
        Decide e executa ferramentas externas via JSON Router.
        Suporta Multi-Tool Calling e Retry em caso de JSON inválido.
        """
        if not self.tools:
            return ""

        router_prompt = (
            "Analise a solicitação e responda APENAS um JSON (Lista de Objetos).\n"
            "Ferramentas disponíveis: 'weather', 'game_search', 'image_search', 'web_search', 'music_recommend'.\n"
            "Retorne uma lista vazia [] se nenhuma ferramenta for necessária.\n"
            'Exemplo Multi-Tool: [{"tool": "weather", "args": "São Paulo"}, {"tool": "game_search", "args": "Elden Ring"}]\n'
            f"Usuário: {content}"
        )

        last_error = ""

        for attempt in range(3):
            try:
                prompt_atual = router_prompt
                if attempt > 0:
                    prompt_atual += f"\n\n[ERRO ANTERIOR]: O JSON gerado era inválido ({last_error}). Corrija a sintaxe estritamente."

                decisao_raw = await provider.generate_response(
                    user_prompt=prompt_atual,
                    system_prompt="Responda APENAS JSON válido. Sem markdown, sem explicações.",
                )

                json_str = decisao_raw.replace("```json", "").replace("```", "").strip()
                if not json_str:
                    return ""

                data = json.loads(json_str)

                if isinstance(data, dict):
                    data = [data]

                if not isinstance(data, list):
                    continue

                results_accumulated = []

                for action in data:
                    tool_name = action.get("tool")
                    args = action.get("args", "")

                    if tool_name not in self.tools or tool_name == "none":
                        continue

                    logger.info(f"🛠️ Executando Tool: {tool_name} | Args: {args}")

                    try:
                        tool_obj = self.tools[tool_name]
                        res = ""

                        if tool_name == "image_search":
                            res = tool_obj.obter_imagem(str(args))
                        elif tool_name == "weather":
                            res = await tool_obj.get_weather(str(args))
                        elif tool_name == "music_recommend":
                            res = await tool_obj.recommend_music(str(args))
                        elif tool_name == "game_search":
                            res = await tool_obj.search_game(str(args))
                        else:
                            res = await tool_obj.buscar_na_cascata(str(args))

                        results_accumulated.append(
                            f"\n[RESULTADO {tool_name.upper()}]:\n{res}"
                        )
                    except Exception as e:
                        logger.error(f"❌ Erro na execução da tool {tool_name}: {e}")
                        results_accumulated.append(
                            f"\n[ERRO {tool_name.upper()}]: Falha ao executar."
                        )

                return "\n".join(results_accumulated) + "\n"

            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON Inválido na tentativa {attempt+1}: {e}")
                last_error = str(e)
                continue
            except Exception as e:
                logger.error(f"⚠️ Erro crítico no Roteador: {e}")
                break

        return ""

    def _is_command(self, message: discord.Message, prefixes) -> bool:
        """Verifica agressivamente se a mensagem parece um comando para ser ignorada."""
        content = message.content.strip()

        if isinstance(prefixes, str):
            if content.startswith(prefixes):
                return True
        elif isinstance(prefixes, list):
            if any(content.startswith(p) for p in prefixes):
                return True

        common_prefixes = ["!", "/", ".", "?", "+", "-", "$", "%", "&", "*"]
        if any(content.startswith(p) for p in common_prefixes) and len(content) > 1:
            if not content[1].isspace():
                return True

        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitora mensagens e decide quando interagir."""
        if message.author.bot or message.author.id == self.bot.user.id:
            return

        prefix = await self.bot.get_prefix(message)
        if self._is_command(message, prefix):
            return

        is_mentioned = self.bot.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_reply = (
            message.reference
            and message.reference.cached_message
            and message.reference.cached_message.author.id == self.bot.user.id
        )

        persona_ativa = self.active_channels.get(str(message.channel.id))
        chance_aleatoria = persona_ativa and random.random() < 0.05

        if is_mentioned or is_dm or is_reply or chance_aleatoria:
            async with message.channel.typing():
                clean_text = (
                    message.content.replace(f"<@{self.bot.user.id}>", "")
                    .replace(f"<@!{self.bot.user.id}>", "")
                    .strip()
                )

                if not clean_text:
                    clean_text = "Olá!"

                input_text = clean_text
                if MEMORY_AVAILABLE:
                    try:
                        clean_data = self.limpeza.identify(clean_text)
                        input_text = clean_data.get("normalized", clean_text)
                    except Exception as e:
                        logger.warning(f"⚠️ Erro na normalização de limpeza: {e}")

                await self.processar_cognicao(message, input_text, persona_ativa)

    async def processar_cognicao(
        self, message: discord.Message, clean_text: str, persona_name: str
    ):
        """Fluxo: Contexto -> RAG -> Tools -> LLM -> Resposta."""
        start_time = time.time()
        user_id = str(message.author.id)
        user_name = message.author.display_name

        try:
            provider = llm_factory.get_provider() if llm_factory else None
            if not provider:
                return

            fato_aprendido = await self._aprender_fatos(message, clean_text)

            if MEMORY_AVAILABLE and self.autoconhecimento.is_self_inquiry(clean_text):
                resp = await provider.generate_response(
                    clean_text, self.autoconhecimento.get_identity_prompt()
                )
                return await self._enviar_resposta(message, resp)

            contexto_memoria = await self._consultar_memoria_longa(user_id, clean_text)
            contexto_ferramentas = await self._rotear_ferramentas(clean_text, provider)

            historico_chat = ""
            if MEMORY_AVAILABLE:
                historico_chat = await self.historico.get_formatted_history(
                    message, self.bot.user
                )

            sys_prompt = self._carregar_prompt(persona_name)

            full_system = (
                f"{sys_prompt}\n"
                f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                f"{contexto_memoria}{contexto_ferramentas}"
                f"\nHistórico:\n{historico_chat}"
            )

            if fato_aprendido:
                full_system += (
                    f"\n[EVENTO DE SISTEMA]: Você ACABOU de aprender e salvar uma nova memória sobre o usuário: '{fato_aprendido}'. "
                    "Use essa informação AGORA para dar uma resposta calorosa e confirmar que guardou isso!"
                )

            resposta = await provider.generate_response(
                user_prompt=f"{user_name}: {clean_text}", system_prompt=full_system
            )

            if MEMORY_AVAILABLE and not any(
                e in resposta for e in ["😀", "🤔", "✨", "💜", "😊"]
            ):
                resposta += f" {self.expressoes.get_reaction(clean_text)}"

            logger.info(
                f"🗣️ Resposta para {user_name} gerada em {time.time()-start_time:.2f}s"
            )
            await self._enviar_resposta(message, resposta)

        except Exception:
            logger.error(f"🔥 Erro Cognitivo: {traceback.format_exc()}")
            await message.reply("🤯 *Tive um pequeno curto-circuito. Pode repetir?*")

    async def _enviar_resposta(self, message: discord.Message, texto: str):
        """Envia a resposta dividindo-a inteligentemente respeitando os limites do Discord."""
        if not texto:
            return

        LIMIT = 1900
        chunks = []

        while len(texto) > LIMIT:
            split_index = texto[:LIMIT].rfind("\n")
            if split_index == -1:
                split_index = texto[:LIMIT].rfind(". ")
                if split_index != -1:
                    split_index += 1
            if split_index == -1:
                split_index = texto[:LIMIT].rfind(" ")
            if split_index == -1:
                split_index = LIMIT

            chunk = texto[:split_index].strip()
            if chunk:
                chunks.append(chunk)
            texto = texto[split_index:].strip()

        if texto:
            chunks.append(texto)

        for i, chunk in enumerate(chunks):
            try:
                if i == 0:
                    await message.reply(chunk, mention_author=False)
                else:
                    await message.channel.send(chunk)
                if len(chunks) > 1:
                    await asyncio.sleep(0.5)
            except discord.HTTPException as e:
                logger.error(f"❌ Erro ao enviar chunk: {e}")


async def setup(bot):
    await bot.add_cog(CerebroIA(bot))
