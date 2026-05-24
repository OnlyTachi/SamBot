# Brain/Memory/DataManager/Manager.py

import os
import logging
from pathlib import Path
from typing import Dict, List, Any
from abc import ABC, abstractmethod
from dotenv import load_dotenv

from ._json_provider import JsonIO
from ._cache import DataCache

load_dotenv()


# --- 1. O CONTRATO (INTERFACE UNIVERSAL) ---
class DatabaseProvider(ABC):
    @abstractmethod
    def get_identity(self) -> Dict:
        pass

    @abstractmethod
    def get_prompt(self, persona: str) -> str:
        pass

    @abstractmethod
    def get_knowledge(self, key: str) -> Any:
        pass

    @abstractmethod
    def save_knowledge(self, key: str, data: Any):
        pass

    @abstractmethod
    def get_user_data(self, user_id: str, key: str) -> Any:
        pass

    @abstractmethod
    def set_user_data(self, user_id: str, key: str, value: Any):
        pass


# --- 2. ORQUESTRADOR JSON ---
class JsonProvider(DatabaseProvider):
    """
    Gestor Unificado de Dados em JSON refatorado.
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Archive")

        # Módulos isolados
        self.io = JsonIO()
        self.cache = DataCache()

        # Ajuste de rota: Agora estamos dentro de Brain/Memory/DataManager
        self.base_dir = Path(__file__).resolve().parent.parent
        self.root = self.base_dir.parent.parent / "Data"

        self.folders = {
            "config": self.root / "Config",
            "prompts": self.root / "Prompts",
            "knowledge": self.root / "Knowledge",
            "persistence": self.root / "Persistence",
            "users": self.root / "Users",
        }

        for folder in self.folders.values():
            folder.mkdir(parents=True, exist_ok=True)

    # --- ATALHOS DE COMPATIBILIDADE (Para NightCycle.py) ---
    def _io_read_json(self, path: Path, default_type: Any = dict) -> Any:
        return self.io.read(path, default_type)

    def _io_save_json(self, path: Path, data: Any):
        self.io.save(path, data)

    # --- IDENTIDADE E CONFIGURAÇÃO ---
    def get_identity(self) -> Dict:
        cached = self.cache.get("identity")
        if cached:
            return cached

        path = self.folders["config"] / "identity.json"
        data = self.io.read(path)
        if not data:
            data = {"name": "SamBot", "version": "3.0", "status": "online"}

        self.cache.set("identity", data)
        return data

    def get_prompt(self, persona: str = "padrao") -> str:
        filename = f"{persona.replace('.txt', '')}.txt"
        cached = self.cache.get_prompt(filename)
        if cached:
            return cached

        path = self.folders["prompts"] / filename

        if not path.exists():
            if persona != "padrao":
                self.logger.warning(
                    f"Persona {persona} não encontrada, usando 'padrao'."
                )
                return self.get_prompt("padrao")
            return "Você é o SamBot, um assistente inteligente."

        try:
            content = path.read_text(encoding="utf-8").strip()
            self.cache.set_prompt(filename, content)
            return content
        except Exception as e:
            self.logger.error(f"Erro ao carregar ficheiro de prompt: {e}")
            return "Erro interno ao carregar personalidade."

    def list_available_personalities(self) -> List[str]:
        files = self.folders["prompts"].glob("*.txt")
        return [f.stem for f in files]

    # --- CONHECIMENTO E NLP ---
    def get_knowledge(self, key: str) -> Any:
        if key == "nlp_data" and self.cache.get("nlp"):
            return self.cache.get("nlp")
        if key == "expressoes_data" and self.cache.get("expressions"):
            return self.cache.get("expressions")

        path = self.folders["knowledge"] / f"{key.replace('.json', '')}.json"
        data = self.io.read(path)

        if "nlp" in key:
            self.cache.set("nlp", data)
        if "expressoes" in key:
            self.cache.set("expressions", data)
        return data

    def save_knowledge(self, key: str, data: Any):
        path = self.folders["knowledge"] / f"{key.replace('.json', '')}.json"
        self.io.save(path, data)
        if "nlp" in key:
            self.cache.set("nlp", data)
        if "expressoes" in key:
            self.cache.set("expressions", data)

    def get_expressions(self) -> Dict:
        return self.get_knowledge("expressoes_data")

    # --- SISTEMA DINÂMICO DE USUÁRIOS ---
    def get_user_data(self, user_id: str, key: str, default_value: Any = None) -> Any:
        path = self.folders["users"] / "users.json"
        data = self.io.read(path)
        user_str = str(user_id)

        if user_str not in data:
            return default_value
        return data[user_str].get(key, default_value)

    def set_user_data(self, user_id: str, key: str, value: Any):
        path = self.folders["users"] / "users.json"
        data = self.io.read(path)
        user_str = str(user_id)

        if user_str not in data:
            data[user_str] = {}

        data[user_str][key] = value
        self.io.save(path, data)

    # --- LEGADO ---
    def save_music_preference(self, user_id, genre_or_artist):
        current_likes = self.get_user_data(user_id, "music_likes", [])
        if genre_or_artist not in current_likes:
            current_likes.append(genre_or_artist)
            self.set_user_data(user_id, "music_likes", current_likes)
            self.logger.info(
                f"Gosto musical '{genre_or_artist}' salvo para o usuário {user_id}"
            )

    def get_user_music_context(self, user_id):
        prefs = self.get_user_data(user_id, "music_likes", [])
        if prefs:
            return f"O utilizador gosta de: {', '.join(prefs)}."
        return ""

    # --- PERSISTÊNCIA DE CANAIS ---
    def load_active_channels(self) -> Dict:
        cached = self.cache.get("channels")
        if cached:
            return cached

        path = self.folders["config"] / "channels.json"
        if not path.exists():
            path = self.folders["persistence"] / "channels.json"

        data = self.io.read(path, default_type=dict)
        self.cache.set("channels", data)
        return data

    def save_active_channels(self, data: Dict):
        if not isinstance(data, dict):
            return
        path = self.folders["config"] / "channels.json"
        self.cache.set("channels", data)
        self.io.save(path, data)

    def reload_all(self):
        self.cache.reset()
        self.logger.info("♻️ DataManager: Cache limpo com sucesso.")


db_type = os.getenv("DB_TYPE", "json")

if db_type == "json":
    data_manager = JsonProvider()
else:
    data_manager = JsonProvider()
