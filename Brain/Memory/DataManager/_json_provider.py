# Brain/Memory/DataManager/_json_provider.py

import json
import logging
import threading
from pathlib import Path
from typing import Any


class JsonIO:
    """
    Motor de I/O isolado. Lida exclusivamente com leitura, escrita e travas de thread.
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Archive.IO")
        self._lock = threading.Lock()

    def read(self, path: Path, default_type: Any = dict) -> Any:
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

    def save(self, path: Path, data: Any):
        with self._lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Falha crítica ao salvar {path.name}: {e}")
