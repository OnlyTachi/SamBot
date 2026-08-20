import os
import sys
import yaml
import logging
from typing import Any
from dotenv import load_dotenv


class Configuration:
    """Carregador unificado de configurações (YAML) e segredos (.env)."""

    def __init__(self, yaml_path: str = "config.yaml"):
        load_dotenv()

        self.logger = logging.getLogger("SamBot.Config")

        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        if not self.DISCORD_TOKEN:
            self.logger.critical("❌ FATAL: DISCORD_TOKEN não encontrado no .env!")
            sys.exit(1)

        self._load_yaml(yaml_path)

    def _load_yaml(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.yaml_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self.logger.warning(
                f"⚠️ Arquivo {path} não encontrado! Usando configurações vazias/padrão."
            )
            self.yaml_data = {}

        # 4. Extração Tipada das Configurações do YAML
        self.bot = self.yaml_data.get("bot", {})
        self.debug_mode = bool(self.bot.get("debug_mode", False))
        self.prefix = str(self.bot.get("prefix", "-"))
        self.owner_id = (
            int(self.bot.get("owner_id", 0)) if self.bot.get("owner_id") else None
        )

        self.llm = self.yaml_data.get("llm", {})
        self.music = self.yaml_data.get("music", {})
        self.telegram = self.yaml_data.get("telegram", {})

    def get(self, key: str, default: Any = None) -> Any:
        key_lower = key.lower()
        if hasattr(self, key_lower):
            return getattr(self, key_lower)

        if "." in key and isinstance(self.yaml_data, dict):
            parts = key.split(".")
            val = self.yaml_data
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
            val = self.yaml_data
            for p in path:
                if isinstance(val, dict) and p in val:
                    val = val[p]
                else:
                    val = None
                    break
            if val is not None:
                return ",".join(val) if isinstance(val, list) else val

        if isinstance(self.yaml_data, dict) and key in self.yaml_data:
            return self.yaml_data[key]

        env_val = os.getenv(key)
        if env_val is not None:
            return env_val

        return default

    def get_secret(self, key: str, default: Any = None) -> Any:
        """Busca segredos sensíveis diretamente do ambiente (.env)."""
        return os.getenv(key, default)

    @property
    def gemini_keys(self) -> list:
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


# Singleton para exportar e usar no resto da aplicação
AppConfig = Configuration()
