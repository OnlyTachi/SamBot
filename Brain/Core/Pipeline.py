import asyncio
import json
import logging
import random
import re
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import discord

# Ferramentas e Subdomínios
from Brain.Core.Router.IntentClassifier import LimpezaManager
from Brain.Core.Router.TLMRouter import TLMRouter
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Memory.LongTerm._learning import AprendizadoAtivo
from Brain.Memory.LongTerm.VectorStore import vector_store
from Brain.Memory.SelfKnowledge.Identity import AutoConhecimentoManager
from Brain.Memory.ShortTerm._expressions import ExpressoesManager
from Brain.Memory.ShortTerm.Context import HistoricoManager
from Brain.Providers.LLMFactory import llm_factory

logger = logging.getLogger("SamBot.Pipeline")
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | Pipeline | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# 1. Carregamento Modular de Ferramentas
TOOL_CLASSES: Dict[str, Any] = {}


def tentar_importar_tool(nome: str, modulo: str, classe: str) -> None:
    """Importa dinamicamente módulos de ferramentas, registrando-os no dicionário TOOL_CLASSES."""
    try:
        mod = __import__(modulo, fromlist=[classe])
        TOOL_CLASSES[nome] = getattr(mod, classe)
    except ImportError:
        logger.warning(f"⚠️ Tool desativada ou não encontrada: {nome}")


tentar_importar_tool("weather", "Brain.Tools.WeatherTool", "WeatherTool")
tentar_importar_tool("game_search", "Brain.Tools.Games.GameTool", "GameTool")
tentar_importar_tool("music_recommend", "Brain.Tools.MusicRecTool", "MusicRecTool")
tentar_importar_tool("anime", "Brain.Tools.Anime.AnimeTool", "AnimeTool")
tentar_importar_tool("jellyfin", "Brain.Tools.JellyfinTool", "JellyfinTool")
tentar_importar_tool("pokemon", "Brain.Tools.PokemonTool", "PokemonTool")
tentar_importar_tool("web_search", "Brain.Tools.Research.WebSearch", "BuscaTool")
tentar_importar_tool(
    "image_search", "Brain.Tools.Research.SearchImages", "ImageSearchTool"
)
tentar_importar_tool("vision", "Brain.Tools.Research.VisionTool", "VisionTool")
tentar_importar_tool(
    "product_search", "Brain.Tools.Shopping.ProductSearch", "ProductSearchTool"
)
tentar_importar_tool("cupom_finder", "Brain.Tools.Shopping.CupomFinder", "CupomFinder")
tentar_importar_tool(
    "shopping_list", "Brain.Tools.Shopping.ShoppingList", "ShoppingListManager"
)

TOOLS_AVAILABLE = len(TOOL_CLASSES) > 0


class CognitionPipeline:
    """
    Motor Central de Cognição da SamBot.
    Orquestra Memória RAG, Ferramentas, Identidade e a Geração de Texto.
    """

    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.logger = logger

        self.llm_factory = llm_factory
        self.ai_chain = self.llm_factory.get_default_principal_chain()
        self.vector_store = vector_store
        self.data_manager = data_manager

        # Instanciar Subdomínios
        self.aprendizado = AprendizadoAtivo(self.llm_factory, self.vector_store)
        self.historico = HistoricoManager()
        self.expressoes = ExpressoesManager()
        self.auto_conhecimento = AutoConhecimentoManager
        self.limpeza = LimpezaManager()
        self.router = TLMRouter()

        self.identity = self.data_manager.get_identity()

        # Ferramentas
        self.tools: Dict[str, Any] = {}
        self.vision_tool: Optional[Any] = None
        self._inicializar_ferramentas()

        self.logger.info(
            f"🧠 Pipeline Cognitivo Pronto. Entidade: {self.identity.get('name')}"
        )

    def _inicializar_ferramentas(self) -> None:
        """Instancia todas as ferramentas disponíveis no registro."""
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
                except Exception:
                    self.tools[key] = cls()
            except Exception as e:
                self.logger.error(f"❌ Erro na ferramenta {key}: {e}")

    def _carregar_prompt(self, persona_name: Optional[str]) -> str:
        """Carrega o prompt base correspondente à persona requisitada."""
        persona_key = persona_name if persona_name else "padrao"
        return self.data_manager.get_prompt(persona_key)

    async def _consultar_memoria_longa(self, query: str) -> str:
        """Consulta a memória vetorial de longo prazo (RAG) por contexto relevante."""
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
            self.logger.warning(f"Aviso RAG: {e}")
            return ""

    async def _rotear_ferramentas(self, content: str, message: discord.Message) -> str:
        """Roteia e executa chamadas de ferramentas dinâmicas baseadas no input do usuário."""
        if not self.tools:
            return ""

        if not getattr(self.router, "_sincronizado", False):
            await self.router.sincronizar_base_rotas()
            self.router._sincronizado = True

        ferramentas_ativas = list(self.tools.keys())
        actions = await self.router.executar(content, ferramentas_ativas)

        if not actions or not isinstance(actions, list):
            return ""

        results: List[str] = []
        prefixos_de_falha = (
            "não encontrei",
            "erro",
            "nenhum",
            "igdb_not_configured",
            "não foi possível",
        )

        for action in actions:
            name = action.get("tool")
            args = str(action.get("args", ""))

            if name in self.tools:
                self.logger.info(
                    f"  [Ferramenta] Executando: '{name}' | Argumentos: '{args}'"
                )
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
                    elif name == "anime":
                        if args.startswith("http"):
                            res = await tool.identify_anime_by_image(args)
                        else:
                            res = await tool.search_anime(args)
                    elif name == "music_recommend":
                        res = await tool.recommend_music(args)
                    elif name == "game_search":
                        res = await tool.search_game(args)
                    elif name == "jellyfin":
                        res = await tool.search_content(args)
                    elif name == "web_search":
                        res = (
                            await tool.buscar_na_cascata(args)
                            if hasattr(tool, "buscar_na_cascata")
                            else await tool.search(args)
                        )
                    elif name == "pokemon":
                        res = await tool.executar(
                            action.get("action_type", "buscar_pokemon"), args
                        )
                    elif name == "cupom_finder":
                        res = await tool.buscar_cupons(args)
                    elif name == "product_search":
                        res = await tool.search(args)
                    elif name == "shopping_list":
                        res = (
                            await tool.orcar_lista(message.author.id)
                            if "orçar" in args or "lista" in args
                            else tool.listar_itens(message.author.id)
                        )

                    if name in ["game_search", "anime"] and "web_search" in self.tools:
                        if not res or str(res).strip().lower().startswith(
                            prefixos_de_falha
                        ):
                            self.logger.warning(
                                f"  [Fallback] A ferramenta '{name}' falhou ou não encontrou dados. Acionando 'web_search' para o termo: '{args}'"
                            )
                            web_tool = self.tools["web_search"]
                            res = (
                                await web_tool.buscar_na_cascata(args)
                                if hasattr(web_tool, "buscar_na_cascata")
                                else await web_tool.search(args)
                            )
                            name = "web_search"

                    if res and not str(res).strip().lower().startswith(
                        prefixos_de_falha
                    ):
                        results.append(f"\n[{name.upper()}]: {res}")
                    else:
                        self.logger.info(
                            f"Retorno da ferramenta '{name}' ignorado por ser nulo ou erro."
                        )

                except Exception as e:
                    self.logger.error(
                        f"  Erro ao executar a ferramenta '{name}': {e}", exc_info=True
                    )

        return "".join(results) + "\n" if results else ""

    async def _processar_anexos(self, message: discord.Message) -> List[Dict[str, Any]]:
        """Processa anexos da mensagem Discord (imagens/mídia) para consumo pelo LLM/Vision."""
        if self.vision_tool and self.vision_tool.is_image_message(message):
            try:
                return await self.vision_tool.process_attachments(message.attachments)
            except Exception as e:
                self.logger.error(f"Erro VisionTool: {e}")

        parts: List[Dict[str, Any]] = []
        valid_exts = (".png", ".jpg", ".jpeg", ".webp")
        for att in message.attachments:
            if any(att.filename.lower().endswith(ext) for ext in valid_exts):
                try:
                    data = await att.read()
                    parts.append(
                        {"mime_type": att.content_type or "image/jpeg", "data": data}
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Não foi possível ler o anexo '{att.filename}' de {message.author.name}: {e}"
                    )
        return parts

    async def _enviar_resposta(self, message: discord.Message, texto: str) -> None:
        """Envia resposta ao Discord dividindo mensagens longas respeitando o limite do Discord."""
        if not texto:
            return
        limit = 1900
        while len(texto) > limit:
            idx = texto[:limit].rfind("\n")
            if idx == -1:
                idx = texto[:limit].rfind(". ")
            if idx == -1:
                idx = texto[:limit].rfind(" ")
            if idx == -1:
                idx = limit
            chunk = texto[:idx].strip()
            if chunk:
                await message.channel.send(chunk)
            texto = texto[idx:].strip()
            await asyncio.sleep(0.4)
        if texto:
            await message.reply(texto, mention_author=False)

    async def _interceptar_resposta_estatica(
        self, clean_text: str, intents_config: Dict[str, Any]
    ) -> Optional[str]:
        """Intercepta intenções conhecidas para rápida resposta estática com custo 0 de tokens."""
        if not intents_config or not hasattr(self.limpeza, "identify_intent_hybrid"):
            return None

        ferramentas_dinamicas = [
            "weather",
            "game_search",
            "music_recommend",
            "anime",
            "jellyfin",
            "pokemon",
            "web_search",
            "product_search",
            "cupom_finder",
            "shopping_list",
        ]

        resultado = self.limpeza.identify_intent_hybrid(clean_text, intents_config)
        intent = resultado.get("intent")
        score = resultado.get("score_confianca", 0)

        if intent in ferramentas_dinamicas:
            return None

        if intent in intents_config and score > 85:
            responses = intents_config[intent].get("responses", [])
            if responses:
                return random.choice(responses)

        if hasattr(self, "router"):
            rotas = await self.router.executar(clean_text, list(intents_config.keys()))
            if rotas:
                intent_semantica = rotas[0].get("tool")

                if intent_semantica in ferramentas_dinamicas:
                    return None

                if intent_semantica in intents_config:
                    responses = intents_config[intent_semantica].get("responses", [])
                    if responses:
                        return random.choice(responses)

        return None

    async def processar_cognicao(
        self,
        message: discord.Message,
        clean_text: str,
        persona_name: Optional[str] = None,
    ) -> None:
        """Execução do fluxo completo do pipeline de cognição."""
        start = time.time()
        if not self.llm_factory:
            return

        try:
            user_id = str(message.author.id)
            user_name = message.author.display_name

            # 0. Interceptação de Resposta Estática
            nlp_data = self.data_manager.get_knowledge("nlp_data") or {}
            intents_config = nlp_data.get("intents", {})

            resposta_pronta = await self._interceptar_resposta_estatica(
                clean_text, intents_config
            )

            if resposta_pronta:
                self.logger.info(
                    "⚡ [Camada 0] Mensagem interceptada estaticamente. Custo: 0 tokens."
                )

                if hasattr(self.historico, "add_message"):
                    self.historico.add_message(user_id, "user", clean_text)
                    self.historico.add_message(user_id, "model", resposta_pronta)

                return await self._enviar_resposta(message, resposta_pronta)

            # 1. Autoconhecimento
            if hasattr(
                self.auto_conhecimento, "is_self_inquiry"
            ) and self.auto_conhecimento.is_self_inquiry(clean_text):
                prompt_id = (
                    self.auto_conhecimento.get_identity_prompt()
                    if hasattr(self.auto_conhecimento, "get_identity_prompt")
                    else "Diga quem você é."
                )
                resp = await self.ai_chain.generate_response(clean_text, prompt_id)
                return await self._enviar_resposta(message, resp)

            # 2. Pipeline de Dados
            anexos = await self._processar_anexos(message)
            fato_novo = await self.aprendizado.aprender_fatos(message, clean_text)
            rag = await self._consultar_memoria_longa(clean_text)
            tools = await self._rotear_ferramentas(clean_text, message)

            # Histórico
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
                "=== REGRAS ABSOLUTAS DE RESPOSTA ===\n"
                "1. NUNCA gere ou mostre código JSON, blocos em colchetes como [PRODUCT_SEARCH], [CUPOM_FINDER] ou comandos do sistema no chat.\n"
                "2. Os relatórios de busca e cupons JÁ FORAM EXECUTADOS e estão injetados no final deste contexto.\n"
                "3. Responda DIRETAMENTE ao usuário em linguagem natural amigável, formatando os produtos e cupons em tópicos limpos.\n\n"
                "=== GUIA DE FORMATAÇÃO ===\n"
                "- Negrito EXCLUSIVAMENTE para preços (ex: **R$ 150,00**) e nomes de lojas/produtos.\n"
                "- Use crases apenas para códigos de cupom (ex: `CUPOM20`).\n"
                "- NUNCA altere os links originais fornecidos nos relatórios abaixo.\n\n"
                f"Data Atual: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                f"Conversando com: {user_name} (ID: {user_id})\n"
                f"{rag}{tools}\n"
                f"Histórico Recente:\n{hist_str}"
            )
            if fato_novo:
                full_sys += f"\n[SISTEMA]: Você acabou de aprender isto agora: '{fato_novo}'. Comente brevemente!"

            parts: List[Any] = [f"{user_name}: {clean_text}"] if clean_text else []
            if anexos:
                parts.extend(anexos)
                if not clean_text:
                    parts.append("Analise estas imagens.")

            resposta = await self.ai_chain.generate_response(
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
            await message.reply(
                "*Meus neurônios entraram em curto! Pode repetir?* ||(nao garanto responder corretamente)||"
            )
