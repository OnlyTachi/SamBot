import re
import unicodedata
from typing import Optional, Dict, Any
# vassoura mágica para limpeza e normalização de comandos de usuário.. talvez útil para chatbots e assistentes virtuais.
class LimpezaManager:
    """
    Gestor de Intenções.
    Inclui: Remoção de emojis, correção de gírias, deduplicação de comandos
    e normalização linguística profunda.
    """

    def __init__(self):
        # Dicionário de correções rápidas (Gírias/Erros comuns)
        self.slang_map = {
            r'\bvc\b': 'voce',
            r'\bvcs\b': 'voces',
            r'\bpra\b': 'para',
            r'\bpro\b': 'para o',
            r'\bt[aá]\b': 'esta',
            r'\bt[oô]\b': 'estou',
            r'\beq\b': 'e que',
            r'\bobg\b': 'obrigado',
            r'\bq\b': 'que',
            r'\bn\b': 'nao'
        }

        # Configuração de Intenções
        self._intents_config = {
            "clima": [
                r'clima\s+(?:em|no|na)?\s*(.+)',
                r'tempo\s+(?:em|no|na)?\s*(.+)',
                r'previsao\s+(?:do\s+tempo)?\s*(?:para)?\s*(.+)',
                r'vai\s+chover\s+(?:em|no|na)?\s*(.+)'
            ],
            "jogos": [
                r'quanto\s+custa\s+(.+)',
                r'preco\s+(?:do|de)?\s*(.+)',
                r'vale\s+a\s+pena\s+comprar\s+(.+)',
                r'informacoes\s+sobre\s+o\s+jogo\s+(.+)'
            ],
            "busca": [
                r'quem\s+e\s+(.+)',
                r'o\s+que\s+e\s+(.+)',
                r'pesquise\s+(?:sobre)?\s*(.+)',
                r'google\s+(.+)'
            ]
        }

        # Compilação de padrões
        self.patterns = {
            intent: [re.compile(p, re.IGNORECASE) for p in regex_list]
            for intent, regex_list in self._intents_config.items()
        }
        
        # Regex para Emojis e Símbolos Especiais (Unicode range)
        self.emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
        # Regex para repetições de palavras ou símbolos (ex: !! ou "ola ola")
        self.duplicate_pattern = re.compile(r'(\b\w+\b|(?!!)\W)\s+\1', re.IGNORECASE)

    def _remove_emojis(self, text: str) -> str:
        """Remove ícones e emojis da string."""
        return self.emoji_pattern.sub(r'', text)

    def _fix_slang(self, text: str) -> str:
        """Corrige gírias e abreviações comuns."""
        for pattern, replacement in self.slang_map.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _remove_duplicates(self, text: str) -> str:
        """Remove comandos ou palavras duplicadas acidentalmente (ex: !bot !bot)."""
        # Aplica a limpeza de duplicatas consecutivas
        last_text = ""
        while last_text != text:
            last_text = text
            text = self.duplicate_pattern.sub(r'\1', text)
        return text

    def _normalize_text(self, text: str) -> str:
        """Processo completo de higienização e normalização."""
        if not text: return ""
        
        # 1. Remover Emojis
        text = self._remove_emojis(text)
        
        # 2. Remover duplicatas (ex: "!!", "clima clima")
        text = self._remove_duplicates(text)
        
        # 3. Corrigir gírias (vc -> voce)
        text = self._fix_slang(text)
        
        # 4. Normalização Unicode (remover acentos)
        text = "".join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        
        return text.lower().strip()

    def _clean_query(self, query: str) -> str:
        """Limpeza final do termo extraído."""
        return query.strip("?.! ,")

    def identify(self, content: str) -> Dict[str, Any]:
        """Identifica a intenção após limpeza profunda."""
        normalized = self._normalize_text(content)
        
        for intent, regex_list in self.patterns.items():
            for pattern in regex_list:
                match = pattern.search(normalized)
                if match:
                    extracted = self._clean_query(match.group(1))
                    
                    if intent == "busca" and len(extracted) < 3:
                        continue
                        
                    return {
                        "intent": intent,
                        "query": extracted,
                        "normalized": normalized,
                        "original": content
                    }

        return {"intent": "conversa", "query": None, "normalized": normalized, "original": content}

# --- Teste da Inteligência ---
if __name__ == "__main__":
    manager = LimpezaManager()
    testes = [
        "!! clima em Lisboa ☀️☀️",
        "vc sabe o preco pro Elden Ring??",
        "pesquise sobre sobre o que e o que e IA",
        "pra onde vai o tempo em em Lisboa"
    ]

    for t in testes:
        res = manager.identify(t)
        print(f"Original: {t}")
        print(f"Limpado:  {res['normalized']}")
        print(f"Intenção: {res['intent']} | Termo: {res['query']}")
        print("-" * 30)