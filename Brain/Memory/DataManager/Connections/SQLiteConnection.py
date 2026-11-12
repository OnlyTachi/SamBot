import sqlite3
import logging
import threading
import os
from pathlib import Path
from typing import Optional, List, Tuple, Any
from Core.ConfigLoader import AppConfig


class DatabaseConnection:
    """Gerenciador dedicado para o SQLite com parâmetros configuráveis."""

    def __init__(self, db_path: Path):
        self.db_path: Path = db_path
        self.logger: logging.Logger = logging.getLogger("SamBot.Database")
        self._lock: threading.Lock = threading.Lock()

        self.timeout = float(
            AppConfig.yaml_data.get("database", {}).get("sqlite_timeout", 30.0)
        )
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        script = """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        
        BEGIN TRANSACTION;
        CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS knowledge (key TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS prompts (name TEXT PRIMARY KEY, content TEXT);
        COMMIT;
        """
        self.execute_script(script)

    def execute_query(
        self,
        query: str,
        params: Tuple[Any, ...] = (),
        fetchone: bool = False,
        fetchall: bool = False,
    ) -> Any:
        with self._lock:
            try:
                with sqlite3.connect(
                    self.db_path, check_same_thread=False, timeout=self.timeout
                ) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    if fetchone:
                        return cursor.fetchone()
                    if fetchall:
                        return cursor.fetchall()
                    conn.commit()
                    return True
            except sqlite3.Error as e:
                self.logger.error(f"Erro no SQLite: {e} | Query: {query}")
                return None

    def execute_script(self, script: str) -> None:
        with self._lock:
            try:
                with sqlite3.connect(
                    self.db_path, check_same_thread=False, timeout=self.timeout
                ) as conn:
                    conn.executescript(script)
            except sqlite3.Error as e:
                self.logger.error(f"Erro ao executar script SQLite: {e}")
