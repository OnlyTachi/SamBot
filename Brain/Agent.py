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
import io

# --- Configuração de Logging ---
logger = logging.getLogger("SamBot.Agent")

# --- Importação de Módulos e Inteligência ---
# Tentamos importar os provedores e managers com suporte a falhas parciais
TOOLS_AVAILABLE = False
MEMORY_AVAILABLE = False

try:
    from Brain.Providers.LLMFactory import LLMFactory
except ImportError:
    logger.critical("❌ Provedor LLM (LLMFactory) não encontrado!")
    LLMFactory = None

try:
    # Ferramentas
    from Brain.Tools.WeatherTool import WeatherTool
    from Brain.Tools.Games.GameTool import GameTool
    from Brain.Tools.BuscaTools import BuscaTool
    from Brain.Tools.Images.SearchImages import ImageSearchTool
    from Brain.Tools.Images.VisionTool import VisionTool
    from Brain.Tools.MusicRecTool import MusicRecTool

    TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Algumas ferramentas não foram encontradas: {e}")

try:
    # Memória e Dados
    from Brain.Memory.VectorStore import VectorStore
    from Brain.Memory.Historico import HistoricoManager
    from Brain.Memory.Expressoes import ExpressoesManager
    from Brain.Memory.AutoConhecimento import AutoConhecimento
    from Brain.Memory.Limpeza import LimpezaManager
    from Brain.Memory.DataManager import data_manager

    MEMORY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Módulos de memória/dados indisponíveis: {e}")


class CerebroIA(commands.Cog):
    """
    O coração cognitivo da SamBot.
    Gere a integração entre LLM, Memória Vetorial (RAG), Expressões, Visão e Ferramentas.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger

        # --- Inicialização de Gestores ---
        self.llm_factory = LLMFactory() if LLMFactory else None
        self.tools = {}

        if MEMORY_AVAILABLE:
            self.vector_store = VectorStore()
            self.historico = HistoricoManager()
            self.expressoes = ExpressoesManager()
            self.auto_conhecimento = AutoConhecimento()
            self.limpeza = LimpezaManager()
            self.data_manager = data_manager
            self.identity = (
                data_manager.get_identity()
                if hasattr(data_manager, "get_identity")
                else {"name": "Sam"}
            )
        else:
            self.identity = {"name": "Sam"}

        # Canais Ativos e Personas (Persistência da versão 1)
        self.active_channels = {}
        if MEMORY_AVAILABLE and hasattr(self.data_manager, "load_active_channels"):
            raw_channels = self.data_manager.load_active_channels()
            self.active_channels = (
                raw_channels if isinstance(raw_channels, dict) else {}
            )

        # --- Inicialização de Ferramentas ---
        self._inicializar_ferramentas()

        self.logger.info(f"🧠 Cérebro Conectado. Entidade: {self.identity.get('name')}")

    def _inicializar_ferramentas(self):
        """Inicializa ferramentas com tratamento de erro individual e suporte a assinaturas variadas."""
        if not TOOLS_AVAILABLE:
            return

        tool_map = {
            "weather": WeatherTool,
            "game_search": GameTool,
            "web_search": BuscaTool,
            "image_search": ImageSearchTool,
            "music_recommend": MusicRecTool,
        }

        try:
            self.vision_tool = VisionTool()
        except:
            self.vision_tool = None

        for key, cls in tool_map.items():
            try:
                # Tenta instanciar com bot ou sem bot (suporte a ambas as versões)
                try:
                    self.tools[key] = cls(self.bot)
                except:
                    self.tools[key] = cls()
            except Exception as e:
                self.logger.error(f"❌ Erro ao carregar ferramenta {key}: {e}")

    def _carregar_prompt(self, persona_name: str) -> str:
        """Carrega o system prompt baseado na persona ou identidade padrão."""
        if MEMORY_AVAILABLE and hasattr(self.data_manager, "get_prompt"):
            persona_key = persona_name if persona_name else "padrao"
            return self.data_manager.get_prompt(persona_key)

        if MEMORY_AVAILABLE and hasattr(self.auto_conhecimento, "get_identity"):
            return self.auto_conhecimento.get_identity()

        return "Você é a Sam, uma assistente virtual divertida e especialista em jogos e música."

    async def _consultar_memoria_longa(self, query: str) -> str:
        """Busca fatos relevantes no ChromaDB (RAG)."""
        if not query or not self.vector_store:
            return ""

        try:
            # Tenta os métodos conhecidos do VectorStore
            if hasattr(self.vector_store, "query_relevant"):
                # Método novo (provavelmente só 1 arg)
                resultados = await self.vector_store.query_relevant(query)

            elif hasattr(self.vector_store, "query_relevant"):
                # CORREÇÃO: Método antigo exige (coleção, query)
                # Passamos "fatos_usuario" como coleção padrão
                resultados = await self.vector_store.query_relevant(
                    "fatos_usuario", query
                )

            else:
                return ""

            if not resultados:
                return ""

            # Se for lista de strings, junta. Se for string, usa direto.
            if isinstance(resultados, list):
                texto_memoria = "\n".join([f"- {m}" for m in resultados])
            else:
                texto_memoria = str(resultados)

            return f"\n[MEMÓRIA DE LONGO PRAZO RELEVANTE]:\n{texto_memoria}\n"

        except Exception as e:
            # Log de aviso, mas não crasha mais
            self.logger.warning(f"⚠️ Aviso RAG (Memória ignorada): {e}")
            return ""

    async def _aprender_fatos(self, message: discord.Message, clean_text: str) -> str:
        """Identifica, valida e guarda fatos sobre o utilizador."""
        if not MEMORY_AVAILABLE or not clean_text or not self.llm_factory:
            return None

        gatilhos = [
            "meu nome",
            "eu gosto",
            "eu amo",
            "eu odeio",
            "eu moro",
            "sou ",
            "tenho ",
            "trabalho com",
        ]
        if not any(g in clean_text.lower() for g in gatilhos):
            return None

        try:
            user_name = message.author.display_name
            system_prompt = (
                "Você é o Núcleo de Memória da SamBot. Extraia fatos PERMANENTES.\n"
                "Se for relevante, extraia APENAS o fato curto. Se for lixo/piada/temporário, responda 'IGNORE'.\n"
                "Ex: 'Eu amo pizza' -> 'Gosta de pizza'"
            )

            extracao = await self.llm_factory.generate_response(
                prompt_parts=[f"Usuário {user_name} disse: '{clean_text}'"],
                system_instruction=system_prompt,
            )

            if "IGNORE" in extracao.upper() or len(extracao.strip()) < 3:
                return None

            if hasattr(self.vector_store, "add_memory"):
                await self.vector_store.add_memory(
                    f"Fato sobre {user_name}: {extracao}",
                    metadata={
                        "user_id": str(message.author.id),
                        "user_name": user_name,
                        "timestamp": str(datetime.now()),
                    },
                )

            await message.add_reaction("🧠")
            return extracao
        except Exception as e:
            self.logger.error(f"❌ Erro ao aprender: {e}")
            return None

    async def _rotear_ferramentas(self, content: str) -> str:
        """Decide e executa ferramentas usando LLM se gatilhos forem detectados."""
        if not self.tools or not self.llm_factory:
            return ""

        triggers = [
            "clima",
            "tempo",
            "jogo",
            "game",
            "imagem",
            "foto",
            "pesquisa",
            "busca",
            "recomenda",
            "musica",
        ]
        if not any(t in content.lower() for t in triggers):
            return ""

        router_instruction = (
            "Responda APENAS JSON (Lista de Objetos).\n"
            "Ferramentas: 'weather', 'game_search', 'image_search', 'web_search', 'music_recommend'.\n"
            'Ex: [{"tool": "weather", "args": "Lisboa"}]'
        )

        try:
            decisao_raw = await self.llm_factory.generate_response(
                prompt_parts=[f"Usuário: {content}"],
                system_instruction=router_instruction,
            )

            json_str = decisao_raw.replace("```json", "").replace("```", "").strip()
            if not json_str or json_str == "[]" or "{" not in json_str:
                return ""

            actions = json.loads(json_str)
            if isinstance(actions, dict):
                actions = [actions]

            results = []
            for action in actions:
                name = action.get("tool")
                args = str(action.get("args", ""))
                if name in self.tools:
                    self.logger.info(f"🛠️ Executando {name}...")
                    tool = self.tools[name]
                    res = ""
                    try:
                        if name == "image_search":
                            res = (
                                await tool.search(args)
                                if hasattr(tool, "search")
                                else tool.obter_imagem(args)
                            )
                        elif name == "weather":
                            res = await tool.get_weather(args)
                        elif name == "music_recommend":
                            res = await tool.recommend_music(args)
                        elif name == "game_search":
                            res = await tool.search_game(args)
                        elif name == "web_search":
                            res = (
                                await tool.buscar_na_cascata(args)
                                if hasattr(tool, "buscar_na_cascata")
                                else await tool.search(args)
                            )

                        results.append(f"\n[{name.upper()}]: {res}")
                    except Exception as e:
                        self.logger.error(f"Erro na tool {name}: {e}")

            return "".join(results) + "\n"
        except Exception as e:
            self.logger.error(f"Erro no roteador: {e}")
            return ""

    def _is_command(self, message: discord.Message, prefixes) -> bool:
        """Verificação para não processar comandos como se fosse conversa natural."""
        content = message.content.strip()
        if not content:
            return False
        if isinstance(prefixes, (str, list)) and any(
            content.startswith(p)
            for p in (prefixes if isinstance(prefixes, list) else [prefixes])
        ):
            return True
        # Prefixos comuns de outros bots
        common = ["!", "/", ".", "?", "+", "-", "$", "%", "*"]
        return (
            any(content.startswith(p) for p in common)
            and len(content) > 1
            and not content[1].isspace()
        )

    async def _processar_anexos(self, message: discord.Message):
        """Usa VisionTool se disponível, ou fallback para leitura binária básica."""
        if self.vision_tool and self.vision_tool.is_image_message(message):
            try:
                return await self.vision_tool.process_attachments(message.attachments)
            except Exception as e:
                self.logger.error(f"❌ Erro VisionTool: {e}")

        # Fallback manual da versão 1
        parts = []
        valid_exts = (".png", ".jpg", ".jpeg", ".webp")
        for att in message.attachments:
            if any(att.filename.lower().endswith(ext) for ext in valid_exts):
                try:
                    data = await att.read()
                    parts.append(
                        {"mime_type": att.content_type or "image/jpeg", "data": data}
                    )
                except:
                    pass
        return parts

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
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

        persona = self.active_channels.get(str(message.channel.id))
        # 5% de chance de intervir se estiver num canal "ativo"
        should_reply = (
            is_mentioned or is_dm or is_reply or (persona and random.random() < 0.05)
        )

        if should_reply:
            async with message.channel.typing():
                clean_text = re.sub(r"<@!?\d+>", "", message.content).strip()
                if not clean_text and not message.attachments:
                    clean_text = "Olá!"

                input_text = clean_text
                if MEMORY_AVAILABLE and self.limpeza:
                    try:
                        # Normalização da versão 1
                        res = self.limpeza.identify(clean_text)
                        input_text = (
                            res.get("normalized", clean_text)
                            if isinstance(res, dict)
                            else clean_text
                        )
                    except:
                        pass

                await self.processar_cognicao(message, input_text, persona)

    async def processar_cognicao(
        self, message: discord.Message, clean_text: str, persona_name: str = None
    ):
        """Fluxo Cognitivo Híbrido Completo."""
        start = time.time()
        if not self.llm_factory:
            return

        try:
            user_id = str(message.author.id)
            user_name = message.author.display_name

            # 1. Autoconhecimento (Verifica se o user pergunta sobre a identidade da IA)
            if (
                MEMORY_AVAILABLE
                and hasattr(self.auto_conhecimento, "is_self_inquiry")
                and self.auto_conhecimento.is_self_inquiry(clean_text)
            ):
                prompt_id = (
                    self.auto_conhecimento.get_identity_prompt()
                    if hasattr(self.auto_conhecimento, "get_identity_prompt")
                    else "Diga quem você é."
                )
                resp = await self.llm_factory.generate_response(clean_text, prompt_id)
                return await self._enviar_resposta(message, resp)

            # 2. Pipeline de Dados
            anexos = await self._processar_anexos(message)
            fato_novo = await self._aprender_fatos(message, clean_text)
            rag = await self._consultar_memoria_longa(user_id, clean_text)
            tools = await self._rotear_ferramentas(clean_text)

            # Histórico
            hist_str = ""
            if MEMORY_AVAILABLE:
                hist_data = (
                    self.historico.get_context(user_id)
                    if hasattr(self.historico, "get_context")
                    else await self.historico.get_formatted_history(
                        message, self.bot.user
                    )
                )
                hist_str = (
                    "\n".join(hist_data)
                    if isinstance(hist_data, list)
                    else str(hist_data)
                )

            # 3. Construção do Prompt Final
            sys_prompt_base = self._carregar_prompt(persona_name)
            full_sys = (
                f"{sys_prompt_base}\n"
                f"Data Atual: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                f"Conversando com: {user_name} (ID: {user_id})\n"
                f"{rag}{tools}\n"
                f"Histórico Recente:\n{hist_str}"
            )

            if fato_novo:
                full_sys += f"\n[SISTEMA]: Você acabou de aprender isto agora: '{fato_novo}'. Comente brevemente!"

            # 4. Payload e Geração
            parts = [f"{user_name}: {clean_text}"] if clean_text else []
            if anexos:
                parts.extend(anexos)
                if not clean_text:
                    parts.append("Analise estas imagens.")

            resposta = await self.llm_factory.generate_response(
                prompt_parts=parts, system_instruction=full_sys
            )

            # 5. Personalidade (Expressões/Reações)
            if (
                MEMORY_AVAILABLE
                and self.expressoes
                and not any(e in resposta for e in ["😀", "💜", "✨", "🎮"])
            ):
                reacao = self.expressoes.get_reaction(clean_text)
                if reacao:
                    resposta += f" {reacao}"

            # 6. Pós-processamento e Envio
            self.logger.info(f"🗣️ Resposta gerada em {time.time()-start:.2f}s")

            if MEMORY_AVAILABLE and hasattr(self.historico, "add_message"):
                log_in = clean_text + (" [Anexo]" if anexos else "")
                self.historico.add_message(user_id, "user", log_in)
                self.historico.add_message(user_id, "model", resposta)

            await self._enviar_resposta(message, resposta)

        except Exception:
            self.logger.error(traceback.format_exc())
            await message.reply("🤯 *Meus neurônios entraram em curto! Pode repetir?*")

    async def _enviar_resposta(self, message: discord.Message, texto: str):
        """Envia dividindo inteligentemente por parágrafos ou frases (respeitando limite de 2k)."""
        if not texto:
            return
        LIMIT = 1900

        while len(texto) > LIMIT:
            # Tenta quebrar em linha, senão em ponto, senão em espaço
            idx = texto[:LIMIT].rfind("\n")
            if idx == -1:
                idx = texto[:LIMIT].rfind(". ")
            if idx == -1:
                idx = texto[:LIMIT].rfind(" ")
            if idx == -1:
                idx = LIMIT

            chunk = texto[:idx].strip()
            if chunk:
                await message.channel.send(chunk)
            texto = texto[idx:].strip()
            await asyncio.sleep(0.4)

        if texto:
            await message.reply(texto, mention_author=False)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Recurso da versão 1: Reagir com 🧠 para forçar aprendizado ou feedback."""
        if user.bot or str(reaction.emoji) != "🧠":
            return
        frases = [
            "Guardado! 💾💜",
            "Memória salva! ✨",
            "Anotado no meu HD! 📝",
            "Adoro saber mais sobre ti! 🥰",
        ]
        try:
            await user.send(f"**SamBot Memória:** {random.choice(frases)}")
        except:
            pass

    async def run(self, message):
        """Método de compatibilidade para chamadas manuais."""
        await self.on_message(message)


async def setup(bot):
    await bot.add_cog(CerebroIA(bot))
