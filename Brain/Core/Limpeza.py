# Brain/Core/Limpeza.py
import re
import logging
from typing import Optional, Dict, Any

try:
    import spacy
    from rapidfuzz import process, fuzz

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning(
        "⚠️ Bibliotecas 'spacy' ou 'rapidfuzz' ausentes. O NLP rodará em modo degradado."
    )


class LimpezaManager:
    """
    Gestor de Intenções Híbrido.
    Inclui: Remoção de emojis, correção de gírias e o Motor NLP (spaCy + RapidFuzz).
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Limpeza")

        self.slang_map = {
            r"\bvc\b": "voce",
            r"\bvcs\b": "voces",
            r"\bpra\b": "para",
            r"\bpro\b": "para o",
            r"\bt[aá]\b": "esta",
            r"\bt[oô]\b": "estou",
            r"\beq\b": "e que",
            r"\bobg\b": "obrigado",
            r"\bq\b": "que",
            r"\bn\b": "nao",
        }

        self.emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
        self.duplicate_pattern = re.compile(r"(\b\w+\b|(?!!)\W)\s+\1", re.IGNORECASE)

        # Inicializa o motor NLP local
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("pt_core_news_sm", disable=["ner", "parser"])
            except OSError:
                self.logger.warning(
                    "Modelo 'pt_core_news_sm' não encontrado. Use: python -m spacy download pt_core_news_sm"
                )
                self.nlp = None
        else:
            self.nlp = None

    def _remove_emojis(self, text: str) -> str:
        return self.emoji_pattern.sub(r"", text)

    def _fix_slang(self, text: str) -> str:
        for pattern, replacement in self.slang_map.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _remove_duplicates(self, text: str) -> str:
        last_text = ""
        while last_text != text:
            last_text = text
            text = self.duplicate_pattern.sub(r"\1", text)
        return text

    def _normalize_with_spacy(self, text: str) -> str:
        """Usa o spaCy para extrair lemas, ignorando pontuações."""
        if not text:
            return ""

        # Limpeza básica (emoji, duplicatas, gírias) antes do spaCy
        text = self._remove_emojis(text)
        text = self._remove_duplicates(text)
        text = self._fix_slang(text)
        text = text.lower().strip()

        if not self.nlp:
            return text  # Fallback se o spaCy não carregar

        doc = self.nlp(text)
        tokens_limpos = [
            token.lemma_ for token in doc if not token.is_punct and not token.is_space
        ]
        return " ".join(tokens_limpos)

    def identify_intent_hybrid(
        self, content: str, intents_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Camada 0: Mapeia intenções com casamento elástico e lematização."""
        normalized = self._normalize_with_spacy(content)
        mejor_intencao = "conversa"
        maior_score = 0
        termo_extraido = None

        if SPACY_AVAILABLE and self.nlp:
            for intent, data in intents_config.items():
                triggers = data.get("triggers", [])
                if not triggers:
                    continue

                match = process.extractOne(
                    normalized, triggers, scorer=fuzz.token_set_ratio
                )
                if match:
                    gatilho_encontrado, score, _ = match

                    if score > 85 and score > maior_score:
                        maior_score = score
                        mejor_intencao = intent
                        termo_extraido = normalized.replace(
                            gatilho_encontrado, ""
                        ).strip()
        return {
            "intent": mejor_intencao,
            "query": termo_extraido,
            "score_confianca": maior_score,
            "normalized": normalized,
            "original": content,
        }

    def identify(self, content: str) -> Dict[str, Any]:
        return self.identify_intent_hybrid(content, {})
