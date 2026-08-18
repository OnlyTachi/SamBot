import logging
from pathlib import Path
from typing import Dict, List, Any

# Importacoes dos módulos especializados
from .Connections.SQLiteConnection import DatabaseConnection
from ._cache import DataCache
from .SubManagers.BrainDataManager import BrainDataManager
from .SubManagers.DiscordDataManager import DiscordDataManager
from .Connections.MeiliConnection import MeiliConnection
from .SubManagers.ShoppingDataManager import ShoppingDataManager


class DataManagerFacade:
    """Orquestrador Principal"""

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Archive")
        self.cache = DataCache()

        base_dir = Path(__file__).resolve().parent.parent.parent.parent / "Data"
        db_path = base_dir / "Persistence" / "database.db"
        self.db = DatabaseConnection(db_path)

        # Compatibilidade Comandos Legados
        self.folders = {
            "persistence": base_dir / "Persistence",
            "users": base_dir / "Persistence",
            "knowledge": base_dir / "Knowledge",
            "config": base_dir / "Config",
        }
        for folder in self.folders.values():
            folder.mkdir(parents=True, exist_ok=True)

        self.meili_db = MeiliConnection()

        self.brain = BrainDataManager(self.db, self.cache)
        self.discord = DiscordDataManager(self.db, self.cache)
        self.shopping = ShoppingDataManager(self.meili_db, self.db, self.cache)

    # --- ROTEAMENTO SHOPPING (Meilisearch) ---
    async def search_cached_offers(self, query: str) -> list:
        return await self.shopping.search_cached_offers(query)

    async def save_offers(self, offers: list):
        await self.shopping.save_offers(offers)

    async def purge_expired_offers(self):
        await self.shopping.purge_expired_offers()

    def parse_and_process_telegram_offer(self, text: str, msg_id: int) -> dict | None:
        if not self.cache.get("nlp_shopping"):
            nlp_data = self.brain.get_knowledge("nlp_shopping")
            self.cache.set("nlp_shopping", nlp_data)
        return self.shopping.parse_telegram_offer(text, msg_id)

    # --- ROTEAMENTO BRAIN (Cognição e Config) ---
    def get_identity(self) -> Dict:
        return self.brain.get_identity()

    def get_prompt(self, persona: str = "padrao") -> str:
        return self.brain.get_prompt(persona)

    def get_knowledge(self, key: str) -> Any:
        return self.brain.get_knowledge(key)

    def save_knowledge(self, key: str, data: Any):
        self.brain.save_knowledge(key, data)

    def get_expressions(self) -> Dict:
        return self.brain.get_knowledge("expressoes_data")

    def get_router_triggers(self) -> Dict[str, List[str]]:
        return self.brain.get_knowledge("router_triggers") or {}

    # --- ROTEAMENTO DISCORD (Usuários e Integrações) ---
    def get_user_data(self, user_id: str, key: str, default_value: Any = None) -> Any:
        return self.discord.get_user_data(user_id, key, default_value)

    def set_user_data(self, user_id: str, key: str, value: Any):
        self.discord.set_user_data(user_id, key, value)

    def load_active_channels(self) -> Dict:
        return self.discord.load_active_channels()

    def save_active_channels(self, data: Dict):
        self.discord.save_active_channels(data)

    def save_music_preference(self, user_id, genre_or_artist):
        current_likes = self.discord.get_user_data(user_id, "music_likes", [])
        if genre_or_artist not in current_likes:
            current_likes.append(genre_or_artist)
            self.discord.set_user_data(user_id, "music_likes", current_likes)

    def get_user_music_context(self, user_id):
        prefs = self.discord.get_user_data(user_id, "music_likes", [])
        if prefs:
            return f"O utilizador gosta de: {', '.join(prefs)}."
        return ""

    # --- UTILITÁRIOS ---
    def reload_all(self):
        self.cache.reset()
        self.logger.info("  DataManager: Cache limpo com sucesso.")


data_manager = DataManagerFacade()
