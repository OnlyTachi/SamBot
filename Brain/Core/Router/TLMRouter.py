import logging
from typing import List, Dict, Any
from Brain.Memory.DataManager import data_manager

try:
    from semantic_router import Route, RouteLayer
    from semantic_router.encoders import HuggingFaceEncoder

    SEMANTIC_ROUTER_AVAILABLE = True
except ImportError:
    SEMANTIC_ROUTER_AVAILABLE = False
    logging.warning(
        "Bibliotecas 'semantic-router' ou 'sentence-transformers' não encontradas."
    )


class TLMRouter:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.SemanticRouter")
        self.route_layer = None
        self.encoder = None

        if SEMANTIC_ROUTER_AVAILABLE:
            self.logger.info(
                "Carregando micro-modelo de embeddings (all-MiniLM-L6-v2)..."
            )
            try:
                self.encoder = HuggingFaceEncoder(
                    name="sentence-transformers/all-MiniLM-L6-v2"
                )
                self.recarregar_gatilhos()
            except Exception as e:
                self.logger.error(f"Erro ao inicializar o encoder HuggingFace: {e}")

    def recarregar_gatilhos(self):
        """Carrega os gatilhos do DataManager e constrói o índice vetorial de rotas."""
        if not self.encoder:
            return

        self.logger.info("Construindo camada vetorial do Semantic Router...")

        triggers_dict = data_manager.get_knowledge("router_triggers") or {}
        routes = []

        for tool_name, utterances in triggers_dict.items():
            if utterances and isinstance(utterances, list):
                route = Route(name=tool_name, utterances=utterances)
                routes.append(route)

        if routes:
            try:
                self.route_layer = RouteLayer(encoder=self.encoder, routes=routes)
                self.logger.info(
                    f"  SemanticRouter ativo! {len(routes)} rotas de ferramentas indexadas."
                )
            except Exception as e:
                self.logger.error(f"Erro ao compilar o RouteLayer: {e}")
        else:
            self.logger.warning(
                "Nenhum gatilho válido foi encontrado em 'router_triggers.json'."
            )

    def _extrair_args(self, content: str, tool: str) -> str:
        """
        Heurística de Slot Filling: Extrai os argumentos limpando os gatilhos da mensagem.
        Ordenamos por tamanho para evitar substituir partes de palavras incorretamente.
        """
        triggers = data_manager.get_knowledge("router_triggers").get(tool, [])[cite:2]
        content_lower = content.lower()

        # Ordena os gatilhos do maior para o menor para limpeza mais precisa
        triggers_ordenados = sorted(triggers, key=len, reverse=True)

        for g in triggers_ordenados:
            if g.lower() in content_lower:
                content_lower = content_lower.replace(g.lower(), "", 1).strip()

        return content_lower

    async def executar(
        self, content: str, ferramentas_ativas: list
    ) -> List[Dict[str, str]]:
        """Ponto de entrada assíncrono consumido pelo Pipeline."""
        if not self.route_layer or not content.strip():
            return []

        try:
            decision = self.route_layer(content)

            if decision.name and decision.name in ferramentas_ativas:
                self.logger.info(f"[SemanticRouter] Rota cravada: '{decision.name}'")

                args = self._extrair_args(content, decision.name)

                self.logger.info(f"[SemanticRouter] Argumentos isolados: '{args}'")
                return [{"tool": decision.name, "args": args}]

        except Exception as e:
            self.logger.error(f"Erro no roteamento semântico: {e}")

        return []
