import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("SamBot.Seeder")


class DatabaseSeeder:
    """Varre as pastas de 'Data' (Knowledge, Prompts, Persistence) no boot

    e sincroniza com o SQLite apenas se houver alterações nos arquivos.
    """

    def __init__(self, db_connection, base_data_dir: Path):
        self.db = db_connection
        self.base_dir = base_data_dir

    def _calcular_hash(self, conteudo: str) -> str:
        return hashlib.md5(conteudo.encode("utf-8")).hexdigest()

    def sync_all(self):
        """Executa a checagem e sincronização completa no boot."""
        logger.info("Verificando consistência dos arquivos de Data com o SQLite...")
        alteracoes = 0

        alteracoes += self._sync_knowledge()
        alteracoes += self._sync_prompts()
        alteracoes += self._sync_identity()

        if alteracoes > 0:
            logger.info(
                f"Sincronização concluída! {alteracoes} registros foram atualizados no"
                " banco."
            )
        else:
            logger.info(
                "Banco de dados 100% sincronizado com os arquivos locais. Nenhuma"
                " alteração necessária."
            )

    def _sync_knowledge(self) -> int:
        """Sincroniza Data/Knowledge/*.json -> Tabela knowledge"""
        folder = self.base_dir / "Knowledge"
        if not folder.exists():
            return 0

        updates = 0
        for file_path in folder.glob("*.json"):
            key = file_path.stem  # Nome do arquivo sem a extensão .json
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_text = f.read().strip()
                    if not file_text:
                        continue

                file_data = json.loads(file_text)
                # Formata normalizado para evitar divergência de espaçamento
                canonical_file_json = json.dumps(file_data, ensure_ascii=False)

                row = self.db.execute_query(
                    "SELECT data FROM knowledge WHERE key = ?", (key,), fetchone=True
                )

                db_json = row[0] if row and row[0] else ""

                # Compara se o conteúdo no banco é diferente do arquivo
                if not row or self._calcular_hash(
                    canonical_file_json
                ) != self._calcular_hash(db_json):
                    self.db.execute_query(
                        "INSERT INTO knowledge (key, data) VALUES (?, ?) ON"
                        " CONFLICT(key) DO UPDATE SET data = excluded.data",
                        (key, canonical_file_json),
                    )
                    logger.info(
                        f" [Auto-Sync] Knowledge '{key}' atualizado no SQLite a partir de"
                        " {file_path.name}"
                    )
                    updates += 1
            except Exception as e:
                logger.error(f"Erro ao sincronizar knowledge {file_path.name}: {e}")

        return updates

    def _sync_prompts(self) -> int:
        """Sincroniza Data/Prompts/*.txt -> Tabela prompts"""
        folder = self.base_dir / "Prompts"
        if not folder.exists():
            return 0

        updates = 0
        for file_path in folder.glob("*.txt"):
            persona_name = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                row = self.db.execute_query(
                    "SELECT content FROM prompts WHERE name = ?",
                    (persona_name,),
                    fetchone=True,
                )

                db_content = row[0] if row and row[0] else ""

                if not row or self._calcular_hash(content) != self._calcular_hash(
                    db_content
                ):
                    self.db.execute_query(
                        "INSERT INTO prompts (name, content) VALUES (?, ?) ON"
                        " CONFLICT(name) DO UPDATE SET content = excluded.content",
                        (persona_name, content),
                    )
                    logger.info(
                        f" [Auto-Sync] Prompt '{persona_name}' atualizado no SQLite."
                    )
                    updates += 1
            except Exception as e:
                logger.error(f"Erro ao sincronizar prompt {file_path.name}: {e}")

        return updates

    def _sync_identity(self) -> int:
        """Sincroniza Data/Persistence/identity.json -> Tabela config (key='identity')"""
        file_path = self.base_dir / "Persistence" / "identity.json"
        if not file_path.exists():
            return 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_text = f.read().strip()
                if not file_text:
                    return 0

            file_data = json.loads(file_text)
            canonical_json = json.dumps(file_data, ensure_ascii=False)

            row = self.db.execute_query(
                "SELECT data FROM config WHERE key = ?", ("identity",), fetchone=True
            )
            db_json = row[0] if row and row[0] else ""

            if not row or self._calcular_hash(canonical_json) != self._calcular_hash(
                db_json
            ):
                self.db.execute_query(
                    "INSERT INTO config (key, data) VALUES (?, ?) ON CONFLICT(key) DO"
                    " UPDATE SET data = excluded.data",
                    ("identity", canonical_json),
                )
                logger.info(
                    " [Auto-Sync] Config 'identity' atualizada no SQLite a partir de"
                    " identity.json"
                )
                return 1
        except Exception as e:
            logger.error(f"Erro ao sincronizar identity.json: {e}")

        return 0
