import json
import logging
from typing import Dict, Any
from ..Connections.SQLiteConnection import DatabaseConnection
from .._cache import DataCache


class BrainDataManager:
    """Responsável exclusivo pela camada cognitiva (prompts, identidade, NLP)."""

    def __init__(self, db: DatabaseConnection, cache: DataCache):
        self.db = db
        self.cache = cache
        self.logger = logging.getLogger("SamBot.BrainData")

    def get_identity(self) -> Dict:
        cached = self.cache.get("identity")
        if cached:
            return cached

        row = self.db.execute_query(
            "SELECT data FROM config WHERE key = ?", ("identity",), fetchone=True
        )
        data = (
            json.loads(row[0])
            if row and row[0]
            else {"name": "SamBot", "version": "3.0", "status": "online"}
        )
        self.cache.set("identity", data)
        return data

    def get_prompt(self, persona: str = "padrao") -> str:
        filename = f"{persona.replace('.txt', '')}"
        cached = self.cache.get_prompt(filename)
        if cached:
            return cached

        row = self.db.execute_query(
            "SELECT content FROM prompts WHERE name = ?", (filename,), fetchone=True
        )
        if row and row[0]:
            self.cache.set_prompt(filename, row[0])
            return row[0]

        if persona != "padrao":
            self.logger.warning(f"Persona {persona} não encontrada, usando 'padrao'.")
            return self.get_prompt("padrao")
        return "Você é o SamBot, uma assistente inteligente."

    def get_knowledge(self, key: str) -> Any:
        clean_key = key.replace(".json", "")
        if clean_key == "nlp_data" and self.cache.get("nlp"):
            return self.cache.get("nlp")
        if clean_key == "expressoes_data" and self.cache.get("expressions"):
            return self.cache.get("expressions")

        row = self.db.execute_query(
            "SELECT data FROM knowledge WHERE key = ?", (clean_key,), fetchone=True
        )
        data = json.loads(row[0]) if row and row[0] else {}

        if "nlp" in clean_key:
            self.cache.set("nlp", data)
        if "expressoes" in clean_key:
            self.cache.set("expressions", data)
        return data

    def save_knowledge(self, key: str, data: Any):
        clean_key = key.replace(".json", "")
        json_data = json.dumps(data, ensure_ascii=False)
        self.db.execute_query(
            "INSERT INTO knowledge (key, data) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET data = excluded.data",
            (clean_key, json_data),
        )
        if "nlp" in clean_key:
            self.cache.set("nlp", data)
        if "expressoes" in clean_key:
            self.cache.set("expressions", data)
