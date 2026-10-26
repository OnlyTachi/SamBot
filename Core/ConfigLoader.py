import os
import sys
import yaml
import logging
from typing import Any
from dotenv import load_dotenv


class _AppConfig:
    """Carregador de configurações (YAML) e segredos (.env)."""

    yaml_data: dict = {}
    bot: dict = {}
    llm: dict = {}
    music: dict = {}
    telegram: dict = {}
    debug_mode: bool = False
    prefix: str = "-"
    owner_id: int | None = None
    DISCORD_TOKEN: str | None = None

    @classmethod
    def load(cls, yaml_path: str = "config.yaml") -> None:
        load_dotenv()
        cls.logger = logging.getLogger("SamBot.Config")
        cls.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        if not cls.DISCORD_TOKEN:
            cls.logger.critical("DISCORD_TOKEN não encontrado no .env!")
            sys.exit(1)

        cls._load_yaml(yaml_path)

    @classmethod
    def _load_yaml(cls, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                cls.yaml_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            cls.logger.warning(
                f"Arquivo {path} não encontrado! Usando configurações padrão."
            )
            cls.yaml_data = {}

        cls.bot = cls.yaml_data.get("bot", {})
        cls.debug_mode = bool(cls.bot.get("debug_mode", False))
        cls.prefix = str(cls.bot.get("prefix", "-"))
        cls.owner_id = (
            int(cls.bot.get("owner_id", 0)) if cls.bot.get("owner_id") else None
        )
        cls.llm = cls.yaml_data.get("llm", {})
        cls.music = cls.yaml_data.get("music", {})
        cls.telegram = cls.yaml_data.get("telegram", {})

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        key_lower = key.lower()
        if hasattr(cls, key_lower):
            return getattr(cls, key_lower)

        if "." in key and isinstance(cls.yaml_data, dict):
            parts = key.split(".")
            val = cls.yaml_data
            for part in parts:
                if isinstance(val, dict) and part in val:
                    val = val[part]
                else:
                    val = None
                    break
            if val is not None:
                return val

        model_mappings = {
            "GROQ_MODEL": ["llm", "models", "groq"],
            "GEMINI_MODEL_NAME": ["llm", "models", "gemini"],
            "MISTRAL_MODEL": ["llm", "models", "mistral"],
            "DEEPSEEK_MODEL": ["llm", "models", "deepseek"],
            "OPENROUTER_MODEL": ["llm", "models", "openrouter"],
            "LLM_CHAIN_ORDER": ["llm", "chain_order"],
        }
        if key in model_mappings:
            path = model_mappings[key]
            val = cls.yaml_data
            for p in path:
                if isinstance(val, dict) and p in val:
                    val = val[p]
                else:
                    val = None
                    break
            if val is not None:
                return ",".join(val) if isinstance(val, list) else val

        if isinstance(cls.yaml_data, dict) and key in cls.yaml_data:
            return cls.yaml_data[key]

        env_val = os.getenv(key)
        if env_val is not None:
            return env_val

        return default

    @classmethod
    def get_secret(cls, key: str, default: Any = None) -> Any:
        """Busca segredos diretamente do ambiente (.env)."""
        return os.getenv(key, default)

    @property
    def gemini_keys(cls) -> list:
        """Agrupa todas as chaves do Gemini automaticamente."""
        keys = []
        k_default = os.getenv("GEMINI_API_KEY")
        if k_default:
            keys.append(k_default.strip())
        i = 1
        while True:
            k = os.getenv(f"GEMINI_API_KEY_{i}")
            if not k:
                break
            k_clean = k.strip()
            if k_clean not in keys:
                keys.append(k_clean)
            i += 1
        return keys


# Carrega os dados na importação e expõe como AppConfig
_AppConfig.load()
AppConfig = _AppConfig
