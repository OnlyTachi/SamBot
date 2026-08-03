import logging
from typing import Dict, Any, Tuple, List
from Brain.Memory.DataManager import data_manager

try:
    import spacy
    from rapidfuzz import process, fuzz

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("Bibliotecas 'spacy' ou 'rapidfuzz' ausentes no IntentClassifier.")


class IntentClassifier:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Router.IntentClassifier")
        self.data_manager = data_manager

        self.tool_triggers: Dict[str, List[str]] = {}
        self.carregar_gatilhos()

        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("pt_core_news_sm", disable=["ner", "parser"])
            except OSError:
                self.logger.warning("Modelo 'pt_core_news_sm' não encontrado no spacy.")
                self.nlp = None
        else:
            self.nlp = None

    def carregar_gatilhos(self):
        """Busca o JSON do DataManager e atualiza o dicionário em memória."""
        try:
            triggers = self.data_manager.get_knowledge("router_triggers")
            if isinstance(triggers, dict) and triggers:
                self.tool_triggers = triggers
                self.logger.info(
                    f"Gatilhos do Roteador carregados com sucesso ({len(self.tool_triggers)} ferramentas mapeadas)."
                )
            else:
                self.logger.warning(
                    "Nenhum gatilho encontrado em 'router_triggers.json'. Usando dicionário vazio."
                )
                self.tool_triggers = {}
        except Exception as e:
            self.logger.error(f"Erro ao carregar gatilhos do DataManager: {e}")
            self.tool_triggers = {}

    def _normalize(self, text: str) -> str:
        if not self.nlp:
            return text.lower().strip()
        doc = self.nlp(text.lower().strip())
        tokens = [
            token.lemma_ for token in doc if not token.is_punct and not token.is_space
        ]
        return " ".join(tokens)

    def classify_fast(self, content: str) -> Tuple[str, float]:
        """Classificação Nível 1: Retorna a ferramenta provável e o score de confiança."""
        # Se os gatilhos estiverem vazios, recarrega
        if not self.tool_triggers:
            self.carregar_gatilhos()

        normalized = self._normalize(content)
        best_tool = None
        highest_score = 0

        if SPACY_AVAILABLE and self.nlp:
            for tool, triggers in self.tool_triggers.items():
                if not triggers:
                    continue
                match = process.extractOne(
                    normalized, triggers, scorer=fuzz.token_set_ratio
                )
                if match:
                    _, score, _ = match
                    if score > highest_score:
                        highest_score = score
                        best_tool = tool

        return best_tool, highest_score
