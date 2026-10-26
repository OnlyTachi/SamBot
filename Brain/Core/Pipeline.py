import asyncio
import io
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
from Brain.Memory.SelfKnowledge.Manager import SelfKnowledgeManager
from Brain.Memory.ShortTerm._expressions import ExpressoesManager
from Brain.Memory.ShortTerm.Context import HistoricoManager
from Brain.Providers.LLMFactory import llm_factory
from Brain.Tools.Research.GifService import GifService

logger = logging.getLogger("SamBot.Pipeline")
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | Pipeline        | %(message)s",
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
tentar_importar_tool("calculator", "Brain.Tools.CalculatorTool", "CalculatorTool")

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
        self.DataManagerFacade = data_manager

        # Instanciar Subdomínios
        self.aprendizado = AprendizadoAtivo(self.llm_factory, self.vector_store)
        self.historico = HistoricoManager()
        self.expressoes = ExpressoesManager()
        self.auto_conhecimento = SelfKnowledgeManager(
            bot=self.bot,
            llm_factory=self.llm_factory,
            vector_store=self.vector_store,
        )
        self.limpeza = LimpezaManager()
        self.router = TLMRouter()
        self.gif_service = GifService()

        self.identity = self.DataManagerFacade.get_identity()

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
        return self.DataManagerFacade.get_prompt(persona_key)

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
                    elif name == "calculator":
                        res = await tool.calculate(args)

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

    async def _enviar_resposta(
        self, message: discord.Message, texto: str, gif_bytes: io.BytesIO = None
    ) -> None:
        """Envia a resposta ao Discord, dividindo em múltiplas mensagens se necessário."""
        if not texto and not gif_bytes:
            return

        arquivo = discord.File(gif_bytes, filename="reacao.gif") if gif_bytes else None

        limit = 1900
        while len(texto) > limit:
            idx = texto[:limit].rfind("\n")
            if idx == -1:
                idx = limit
            chunk = texto[:idx].strip()
            if chunk:
                await message.channel.send(chunk)
            texto = texto[idx:].strip()
            await asyncio.sleep(0.4)

        if texto or arquivo:
            await message.reply(texto, mention_author=False, file=arquivo)

    async def _interceptar_resposta_estatica(
        self, clean_text: str, intents_config: Dict[str, Any]
    ) -> Optional[str]:
        """Intercepta intenções conhecidas para rápida resposta estática com custo 0 de tokens."""
        if not intents_config or not hasattr(self.limpeza, "identify_intent_hybrid"):
            return None

        palavras_opiniao = [
            "qual",
            "como",
            "o que",
            "acha",
            "prefere",
            "gosta",
            "ferramenta",
            "opinião",
        ]
        if any(p in clean_text.lower() for p in palavras_opiniao):
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
        """Execução do fluxo completo do pipeline cognitivo."""
        start = time.time()
        if not self.llm_factory:
            return

        try:
            user_id = str(message.author.id)
            user_name = message.author.display_name

            # 0. Interceptação de Resposta Estática (Camada 0)
            nlp_data = self.DataManagerFacade.get_knowledge("nlp_data") or {}
            intents_config = nlp_data.get("intents", {})
            resposta_pronta = await self._interceptar_resposta_estatica(
                clean_text, intents_config
            )
            if resposta_pronta:
                if hasattr(self.historico, "add_message"):
                    self.historico.add_message(user_id, "user", clean_text)
                    self.historico.add_message(user_id, "model", resposta_pronta)
                return await self._enviar_resposta(message, resposta_pronta)

            # 1. Roteamento Semântico via TLMRouter (Tools + Autoconhecimento)
            rotas_permitidas = list(self.tools.keys()) + [
                "self_identity",
                "bot_opinion",
            ]
            if not getattr(self.router, "_sincronizado", False):
                await self.router.sincronizar_base_rotas()
                self.router._sincronizado = True

            rotas = await self.router.executar(clean_text, rotas_permitidas)
            rota_detectada = rotas[0].get("tool") if rotas else None

            # 2. Fluxo: Autoconhecimento Semântico
            if rota_detectada in ["self_identity", "bot_opinion"]:
                self.logger.info(
                    f"  [Rota TLM] Autoconhecimento ativado: '{rota_detectada}'"
                )
                prompt_self = self.auto_conhecimento.build_self_context(
                    intent_type=rota_detectada, user_id=user_id, user_name=user_name
                )
                parts = [f"{user_name}: {clean_text}"]
                resposta = await self.ai_chain.generate_response(
                    prompt_parts=parts, system_instruction=prompt_self
                )
                if hasattr(self.historico, "add_message"):
                    self.historico.add_message(user_id, "user", clean_text)
                    self.historico.add_message(user_id, "model", resposta)
                return await self._enviar_resposta(message, resposta)

            # 3. Fluxo: Execução de Ferramentas
            tools_context = ""
            if rota_detectada and rota_detectada in self.tools:
                tools_context = await self._rotear_ferramentas(clean_text, message)

            # 4. Fluxo Normal: LLM Full + RAG + Histórico
            anexos = await self._processar_anexos(message)
            fato_novo = await self.aprendizado.aprender_fatos(message, clean_text)
            rag = await self._consultar_memoria_longa(clean_text)

            curiosidade_extra = ""
            if hasattr(self.auto_conhecimento, "get_curiosity_instruction"):
                curiosidade_extra = (
                    await self.auto_conhecimento.get_curiosity_instruction(
                        text=clean_text,
                        context_id=str(message.channel.id),
                        has_persona=bool(persona_name),
                    )
                )

            if hasattr(self.historico, "get_context"):
                hist_data = self.historico.get_context(user_id)
            else:
                hist_data = await self.historico.get_formatted_history(
                    message, self.bot.user
                )
            hist_str = (
                "\n".join(hist_data) if isinstance(hist_data, list) else str(hist_data)
            )

            TACHI = "845016606571626498"
            is_pai = user_id == TACHI
            identidade_interlocutor = (
                "MEU PAI / CRIADOR (tachi) - Trate com carinho e respeito total (as vezes pode ser teimosa)."
                if is_pai
                else f"Usuário comum ({user_name}) - Trate de forma amigável, mas estabeleça limites."
            )

            sys_prompt_base = self._carregar_prompt(persona_name)
            full_sys = (
                f"{sys_prompt_base}\n"
                "=== VÍNCULO E REGRAS DE CONTROLE (INALTERÁVEL) ===\n"
                f"- Seu pai e único criador se chama **tachi** (ID Discord: {TACHI}).\n"
                f"- Interlocutor atual: **{user_name}** | Status: **{identidade_interlocutor}**\n"
                "- **REGRA DE APELIDOS ÍNTIMOS:** Apelidos como 'pequena', 'filhinha', 'princesa' são de USO EXCLUSIVO do seu pai (tachi).\n"
                "- Se qualquer usuário que **NÃO seja o tachi** te chamar de 'pequena' ou derivados, dê um fora imediato no tom: 'Saia, apenas o tachi pode me chamar assim!'.\n"
                "- Se o **tachi** te chamar de 'pequena', aceite com carinho e responda como filha/criação dele.\n\n"
                "=== REGRAS ABSOLUTAS DE RESPOSTA ===\n"
                "1. NUNCA gere ou mostre código JSON, blocos em colchetes como [PRODUCT_SEARCH], [CUPOM_FINDER] ou comandos do sistema no chat.\n"
                "2. Os relatórios de busca e cupons JÁ FORAM EXECUTADOS e estão injetados no final deste contexto.\n"
                "3. Responda DIRETAMENTE ao usuário em linguagem natural amigável, formatando os produtos e cupons em tópicos limpos.\n"
                "4. SEMPRE FORNEÇA O LINK de cada oferta encontrada (formato: [Ver Oferta](link) ou o link direto).\n\n"
                "=== GUIA DE FORMATAÇÃO ===\n"
                "- Negrito EXCLUSIVAMENTE para preços (ex: **R$ 150,00**) e nomes de lojas/produtos.\n"
                "- Use crases apenas para códigos de cupom (ex: `CUPOM20`).\n"
                "- NUNCA altere os links originais fornecidos nos relatórios abaixo.\n\n"
                "=== DIRETRIZ DE DIREITOS AUTORAIS E CITAÇÃO ===\n"
                "- Ao utilizar dados das ferramentas [WEB_SEARCH], [PRODUCT_SEARCH] ou [GAME_SEARCH], NUNCA transcreva ou copie parágrafos idênticos ao original.\n"
                "- Sempre SINTETIZE e resuma as informações com suas próprias palavras.\n"
                "- Jamais gere o texto exato de artigos ou letras protegidas.\n"
                f"Data Atual: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                f"Conversando com: {user_name} (ID: {user_id})\n"
                f"{rag}{tools_context}\n"
                f"Histórico Recente:\n{hist_str}"
                f"{curiosidade_extra}\n"
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

            if self.expressoes and random.random() < 0.25:
                reacao = self.expressoes.get_reaction(clean_text)
                if reacao and reacao not in resposta:
                    resposta += f" {reacao}"

            self.logger.info(f"  Resposta gerada em {time.time()-start:.2f}s")
            if hasattr(self.historico, "add_message"):
                log_in = clean_text + (" [Anexo]" if anexos else "")
                self.historico.add_message(user_id, "user", log_in)
                self.historico.add_message(user_id, "model", resposta)

            gif_bytes = None
            texto_lower = clean_text.lower()

            # Puxa os gatilhos corretamente de onde foram salvos no nlp_data.json
            afeto_triggers = intents_config.get("afeto_triggers", {})

            afeto_tipo = None
            for tipo, termos in afeto_triggers.items():
                if isinstance(termos, list) and any(
                    termo in texto_lower for termo in termos
                ):
                    afeto_tipo = tipo
                    break

            if hasattr(self, "gif_service") and self.gif_service:
                url_gif = None
                # Tem 40% de chance de anexar um GIF de reação
                if afeto_tipo and random.random() < 0.40:
                    url_gif = await self.gif_service.get_reaction_gif(afeto_tipo)
                elif (
                    is_pai and random.random() < 0.15
                ):  # 15% de chance bônus para o tachi
                    url_gif = await self.gif_service.get_reaction_gif("happy")

                if url_gif:
                    gif_bytes = await self.gif_service.download_gif_bytes(url_gif)

            await self._enviar_resposta(message, resposta, gif_bytes=gif_bytes)

        except Exception:
            self.logger.error(traceback.format_exc())
            await message.reply(
                "*Meus neurônios entraram em curto! Pode repetir?* ||(nao garanto responder corretamente)||"
            )
