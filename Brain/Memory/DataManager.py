import json
import os
import glob
import logging
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dotenv import load_dotenv

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


# --- 2. MOTOR ANTIGO (AGORA CHAMADO JSON PROVIDER) ---
class JsonProvider(DatabaseProvider):
    """
    Gestor Unificado de Dados em JSON.
    Antigo NeuralArchive, agora implementando a interface DatabaseProvider.
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Archive")
        self._lock = threading.Lock()

        self.base_dir = Path(__file__).resolve().parent
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

        self._cache = {
            "identity": None,
            "prompts": {},
            "nlp": None,
            "expressions": None,
            "channels": None,
        }

    # --- NÚCLEO DE I/O (ENTRADA E SAÍDA) ---
    def _io_read_json(self, path: Path, default_type: Any = dict) -> Any:
        if not path.exists():
            return default_type()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if default_type is dict and not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Erro ao ler JSON em {path.name}: {e}")
            return default_type()

    def _io_save_json(self, path: Path, data: Any):
        with self._lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Falha crítica ao salvar {path.name}: {e}")

    # --- IDENTIDADE E CONFIGURAÇÃO ---
    def get_identity(self) -> Dict:
        if self._cache["identity"]:
            return self._cache["identity"]
        path = self.folders["config"] / "identity.json"
        data = self._io_read_json(path)
        if not data:
            data = {"name": "SamBot", "version": "3.0", "status": "online"}
        self._cache["identity"] = data
        return data

    def get_prompt(self, persona: str = "padrao") -> str:
        filename = f"{persona.replace('.txt', '')}.txt"
        if filename in self._cache["prompts"]:
            return self._cache["prompts"][filename]
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
            self._cache["prompts"][filename] = content
            return content
        except Exception as e:
            self.logger.error(f"Erro ao carregar ficheiro de prompt: {e}")
            return "Erro interno ao carregar personalidade."

    def list_available_personalities(self) -> List[str]:
        files = self.folders["prompts"].glob("*.txt")
        return [f.stem for f in files]

    # --- CONHECIMENTO E NLP ---
    def get_knowledge(self, key: str) -> Any:
        if key == "nlp_data" and self._cache["nlp"]:
            return self._cache["nlp"]
        if key == "expressoes_data" and self._cache["expressions"]:
            return self._cache["expressions"]

        path = self.folders["knowledge"] / f"{key.replace('.json', '')}.json"
        data = self._io_read_json(path)

        if "nlp" in key:
            self._cache["nlp"] = data
        if "expressoes" in key:
            self._cache["expressions"] = data
        return data

    def save_knowledge(self, key: str, data: Any):
        path = self.folders["knowledge"] / f"{key.replace('.json', '')}.json"
        self._io_save_json(path, data)
        if "nlp" in key:
            self._cache["nlp"] = data
        if "expressoes" in key:
            self._cache["expressions"] = data

    def get_expressions(self) -> Dict:
        return self.get_knowledge("expressoes_data")

    # --- NOVO: SISTEMA DINÂMICO DE USUÁRIOS (XP, MOEDAS, ETC) ---
    def get_user_data(self, user_id: str, key: str, default_value: Any = None) -> Any:
        """Busca qualquer dado do usuário no arquivo central users.json"""
        path = self.folders["users"] / "users.json"
        data = self._io_read_json(path)
        user_str = str(user_id)

        if user_str not in data:
            return default_value
        return data[user_str].get(key, default_value)

    def set_user_data(self, user_id: str, key: str, value: Any):
        """Salva qualquer dado do usuário no arquivo central users.json"""
        path = self.folders["users"] / "users.json"
        data = self._io_read_json(path)
        user_str = str(user_id)

        if user_str not in data:
            data[user_str] = {}

        data[user_str][key] = value
        self._io_save_json(path, data)

    # --- LEGADO (Mantido para não quebrar o NightCycle agora) ---
    def save_music_preference(self, user_id, genre_or_artist):
        # Agora ele usa o sistema novo por baixo dos panos!
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
        if self._cache["channels"]:
            return self._cache["channels"]
        path = self.folders["config"] / "channels.json"
        if not path.exists():
            path = self.folders["persistence"] / "channels.json"
        data = self._io_read_json(path, default_type=dict)
        self._cache["channels"] = data
        return data

    def save_active_channels(self, data: Dict):
        if not isinstance(data, dict):
            return
        path = self.folders["config"] / "channels.json"
        self._cache["channels"] = data
        self._io_save_json(path, data)

    def reload_all(self):
        self._cache = {
            "identity": None,
            "prompts": {},
            "nlp": None,
            "expressions": None,
            "channels": None,
        }
        self.logger.info("♻️ DataManager: Cache limpo com sucesso.")


db_type = os.getenv("DB_TYPE", "json")

if db_type == "json":
    data_manager = JsonProvider()
else:
    # Se no futuro houver SqliteProvider, ele entra aqui.
    data_manager = JsonProvider()
