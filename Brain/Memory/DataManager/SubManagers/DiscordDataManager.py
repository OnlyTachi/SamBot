import json
import logging
from typing import Dict, Any
from ..Connections.SQLiteConnection import DatabaseConnection
from .._cache import DataCache


class DiscordDataManager:
    """Responsável exclusivo pela interface com os usuários, preferências e Discord."""

    def __init__(self, db: DatabaseConnection, cache: DataCache):
        self.db = db
        self.cache = cache
        self.logger = logging.getLogger("SamBot.DiscordData")

    def get_user_data(self, user_id: str, key: str, default_value: Any = None) -> Any:
        row = self.db.execute_query(
            "SELECT data FROM users WHERE user_id = ?", (str(user_id),), fetchone=True
        )
        if not row or not row[0]:
            return default_value
        return json.loads(row[0]).get(key, default_value)

    def set_user_data(self, user_id: str, key: str, value: Any):
        str_uid = str(user_id)
        row = self.db.execute_query(
            "SELECT data FROM users WHERE user_id = ?", (str_uid,), fetchone=True
        )
        user_data = json.loads(row[0]) if row and row[0] else {}

        user_data[key] = value
        self.db.execute_query(
            "INSERT INTO users (user_id, data) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET data = excluded.data",
            (str_uid, json.dumps(user_data, ensure_ascii=False)),
        )

    def load_active_channels(self) -> Dict:
        cached = self.cache.get("channels")
        if cached:
            return cached

        row = self.db.execute_query(
            "SELECT data FROM config WHERE key = ?", ("channels",), fetchone=True
        )
        data = json.loads(row[0]) if row and row[0] else {}
        self.cache.set("channels", data)
        return data

    def save_active_channels(self, data: Dict):
        if not isinstance(data, dict):
            return
        self.cache.set("channels", data)
        self.db.execute_query(
            "INSERT INTO config (key, data) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET data = excluded.data",
            ("channels", json.dumps(data, ensure_ascii=False)),
        )

    def increment_contribution(self, user_id: str, field: str, amount: int = 1):
        """métricas estatísticas do usuário"""
        if not user_id:
            return

        contributions = self.get_user_data(user_id, "contributions", default_value={})

        current_val = contributions.get(field, 0)
        contributions[field] = current_val + amount

        self.set_user_data(user_id, "contributions", contributions)
