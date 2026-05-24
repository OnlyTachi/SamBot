# Brain/Core/Pipeline.py
import discord
import re
import random
import logging
import json
import traceback
import asyncio
from datetime import datetime
import time

# Ferramentas e Subdomínios
from Brain.Providers.LLMFactory import LLMFactory
from Brain.Memory.DataManager import data_manager
from Brain.Memory.LongTerm.VectorStore import vector_store
from Brain.Memory.LongTerm._learning import AprendizadoAtivo
from Brain.Memory.ShortTerm.Context import HistoricoManager
from Brain.Memory.ShortTerm._expressions import ExpressoesManager
from Brain.Memory.SelfKnowledge.Identity import AutoConhecimentoManager
from Brain.Core.Limpeza import LimpezaManager

logger = logging.getLogger("SamBot.Pipeline")

# 1. Carregamento Modular de Ferramentas
TOOL_CLASSES = {}


def tentar_importar_tool(nome, modulo, classe):
    try:
        mod = __import__(modulo, fromlist=[classe])
        TOOL_CLASSES[nome] = getattr(mod, classe)
    except ImportError:
        logger.warning(f"⚠️ Tool desativada ou não encontrada: {nome}")


tentar_importar_tool("weather", "Brain.Tools.WeatherTool", "WeatherTool")
tentar_importar_tool("game_search", "Brain.Tools.Games.GameTool", "GameTool")
tentar_importar_tool("web_search", "Brain.Tools.BuscaTools", "BuscaTool")
tentar_importar_tool(
    "image_search", "Brain.Tools.Images.SearchImages", "ImageSearchTool"
)
tentar_importar_tool("vision", "Brain.Tools.Images.VisionTool", "VisionTool")
tentar_importar_tool("music_recommend", "Brain.Tools.MusicRecTool", "MusicRecTool")

TOOLS_AVAILABLE = len(TOOL_CLASSES) > 0


class CognitionPipeline:
    """
    Motor Central de Cognição da SamBot.
    Orquestra Memória RAG, Ferramentas, Identidade e a Geração de Texto.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger

        self.llm_factory = LLMFactory() if LLMFactory else None
        self.vector_store = vector_store
        self.data_manager = data_manager

        # Instanciar Subdomínios
        self.aprendizado = AprendizadoAtivo(self.llm_factory, self.vector_store)
        self.historico = HistoricoManager()
        self.expressoes = ExpressoesManager()
        self.auto_conhecimento = AutoConhecimentoManager
        self.limpeza = LimpezaManager()

        self.identity = self.data_manager.get_identity()

        # Ferramentas
        self.tools = {}
        self.vision_tool = None
        self._inicializar_ferramentas()

        self.logger.info(
            f"🧠 Pipeline Cognitivo Pronto. Entidade: {self.identity.get('name')}"
        )

    def _inicializar_ferramentas(self):
        if not TOOLS_AVAILABLE:
            return
        for key, cls in TOOL_CLASSES.items():
            if key == "vision":
                try:
                    self.vision_tool = cls()
                except Exception as e:
                    self.logger.error(f"❌ Erro VisionTool: {e}")
                continue
            try:
                try:
                    self.tools[key] = cls(self.bot)
                except:
                    self.tools[key] = cls()
            except Exception as e:
                self.logger.error(f"❌ Erro na ferramenta {key}: {e}")

    def _carregar_prompt(self, persona_name: str) -> str:
        persona_key = persona_name if persona_name else "padrao"
        return self.data_manager.get_prompt(persona_key)

    async def _consultar_memoria_longa(self, query: str) -> str:
        if not query or not self.vector_store:
            return ""
        try:
            resultados = await self.vector_store.query_relevant("fatos_usuario", query)
            if not resultados:
                return ""
            texto_memoria = (
                "\n".join([f"- {m}" for m in resultados])
                if isinstance(resultados, list)
                else str(resultados)
            )
            return f"\n[MEMÓRIA DE LONGO PRAZO RELEVANTE]:\n{texto_memoria}\n"
        except Exception as e:
            self.logger.warning(f"⚠️ Aviso RAG: {e}")
            return ""

    async def _rotear_ferramentas(self, content: str) -> str:
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

        ferramentas_disponiveis = "', '".join(self.tools.keys())
        router_instruction = (
            "Responda APENAS JSON (Lista de Objetos).\n"
            f"Ferramentas: {ferramentas_disponiveis}.\n"
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
            return ""

    async def _processar_anexos(self, message: discord.Message):
        if self.vision_tool and self.vision_tool.is_image_message(message):
            try:
                return await self.vision_tool.process_attachments(message.attachments)
            except Exception as e:
                self.logger.error(f"❌ Erro VisionTool: {e}")

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

    async def _enviar_resposta(self, message: discord.Message, texto: str):
        if not texto:
            return
        LIMIT = 1900
        while len(texto) > LIMIT:
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

    async def processar_cognicao(
        self, message: discord.Message, clean_text: str, persona_name: str = None
    ):
        start = time.time()
        if not self.llm_factory:
            return

        try:
            user_id = str(message.author.id)
            user_name = message.author.display_name

            # 1. Autoconhecimento
            if hasattr(
                self.auto_conhecimento, "is_self_inquiry"
            ) and self.auto_conhecimento.is_self_inquiry(clean_text):
                prompt_id = (
                    self.auto_conhecimento.get_identity_prompt()
                    if hasattr(self.auto_conhecimento, "get_identity_prompt")
                    else "Diga quem você é."
                )
                resp = await self.llm_factory.generate_response(clean_text, prompt_id)
                return await self._enviar_resposta(message, resp)

            # 2. Pipeline de Dados
            anexos = await self._processar_anexos(message)
            fato_novo = await self.aprendizado.aprender_fatos(message, clean_text)
            rag = await self._consultar_memoria_longa(clean_text)
            tools = await self._rotear_ferramentas(clean_text)

            # Histórico
            hist_str = ""
            if hasattr(self.historico, "get_context"):
                hist_data = self.historico.get_context(user_id)
            else:
                hist_data = await self.historico.get_formatted_history(
                    message, self.bot.user
                )
            hist_str = (
                "\n".join(hist_data) if isinstance(hist_data, list) else str(hist_data)
            )

            # 3. Prompt Final
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

            parts = [f"{user_name}: {clean_text}"] if clean_text else []
            if anexos:
                parts.extend(anexos)
                if not clean_text:
                    parts.append("Analise estas imagens.")

            resposta = await self.llm_factory.generate_response(
                prompt_parts=parts, system_instruction=full_sys
            )

            # 4. Expressões e Reações
            if self.expressoes and not any(
                e in resposta for e in ["😀", "💜", "✨", "🎮"]
            ):
                reacao = self.expressoes.get_reaction(clean_text)
                if reacao:
                    resposta += f" {reacao}"

            self.logger.info(f"🗣️ Resposta gerada em {time.time()-start:.2f}s")

            if hasattr(self.historico, "add_message"):
                log_in = clean_text + (" [Anexo]" if anexos else "")
                self.historico.add_message(user_id, "user", log_in)
                self.historico.add_message(user_id, "model", resposta)

            await self._enviar_resposta(message, resposta)

        except Exception:
            self.logger.error(traceback.format_exc())
            await message.reply("🤯 *Meus neurônios entraram em curto! Pode repetir?*")
