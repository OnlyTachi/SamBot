import random
from Brain.Memory.DataManager.Connections import data_manager


class ExpressoesManager:
    """Gerencia reações e expressões idiomáticas da bot."""

    def __init__(self):
        self.data = data_manager.get_expressions() or {}

    def get_reaction(self, content: str) -> str:
        """Retorna expressão apenas se houver sentimento real detectado."""
        if not self.data:
            return ""
        content_lower = content.lower()
        reaction_pool = []

        if any(
            w in content_lower
            for w in ["kkk", "haha", "lol", "engracado", "engraçado", "xd", "meme"]
        ):
            reaction_pool = self.data.get("risada", [])
        elif any(
            w in content_lower
            for w in ["triste", "chorar", "ruim", "bad", "chateado", "foda", "droga"]
        ):
            reaction_pool = self.data.get("triste", [])
        elif any(
            w in content_lower
            for w in [
                "uau",
                "nossa",
                "incrivel",
                "incrível",
                "chocado",
                "mds",
                "caramba",
            ]
        ):
            reaction_pool = self.data.get("surpresa", [])

        # Se não casou com sentimentos fortes, retorna vazio em vez de forçar "padrao"
        if reaction_pool:
            return random.choice(reaction_pool)
        return ""

    def get_emoji_reaction(self, emotion: str) -> str:
        """Puxa um emoji específico da categoria legada."""
        emojis_dict = self.data.get("emojis", {})
        pool = emojis_dict.get(emotion, emojis_dict.get("neutro", ["✨"]))
        return random.choice(pool)
