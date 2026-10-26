# Services/API/services/file_service.py
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from fastapi import HTTPException
import yaml

from Brain.Memory.DataManager.Connections import data_manager
from Brain.Memory.DataManager.DatabaseSeeder import DatabaseSeeder

logger = logging.getLogger("SamBot.Services.Files")

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ALLOWED_EXTENSIONS = {".json", ".txt", ".yaml", ".yml", ".env"}
ALLOWED_DIRECTORIES = [
    BASE_DIR / "Data" / "Prompts",
    BASE_DIR / "Data" / "Knowledge",
    BASE_DIR / "Data" / "Persistence",
    BASE_DIR,
]


class FileService:
    @staticmethod
    def resolve_safe_path(relative_path: str) -> Path:
        """Garante que o caminho reside estritamente nas pastas autorizadas (Anti Path Traversal)."""
        clean_path = relative_path.lstrip("/\\")
        target_path = (BASE_DIR / clean_path).resolve()

        is_safe = any(
            target_path == allowed or allowed in target_path.parents
            for allowed in ALLOWED_DIRECTORIES
        )
        if not is_safe or target_path.suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=403,
                detail="Acesso negado: Caminho de ficheiro ou extensão não autorizada.",
            )
        return target_path

    @staticmethod
    def get_editable_files_tree() -> Dict[str, List[Dict[str, Any]]]:
        """Mapeia os ficheiros de configuração, persona e dados do sistema."""
        files_tree = {"configs": [], "prompts": [], "knowledge": [], "persistence": []}

        # 1. Configs da raiz
        for f in ["config.yaml", "config.example.yaml", ".env", "application.yml"]:
            p = BASE_DIR / f
            if p.exists():
                files_tree["configs"].append(
                    {"name": f, "path": f, "size_bytes": p.stat().st_size}
                )

        # 2. Prompts de Persona
        prompts_dir = BASE_DIR / "Data" / "Prompts"
        if prompts_dir.exists():
            for p in prompts_dir.glob("*.txt"):
                rel_path = str(p.relative_to(BASE_DIR)).replace("\\", "/")
                files_tree["prompts"].append(
                    {"name": p.name, "path": rel_path, "size_bytes": p.stat().st_size}
                )

        # 3. Bases de Conhecimento
        knowledge_dir = BASE_DIR / "Data" / "Knowledge"
        if knowledge_dir.exists():
            for k in knowledge_dir.glob("*.json"):
                rel_path = str(k.relative_to(BASE_DIR)).replace("\\", "/")
                files_tree["knowledge"].append(
                    {"name": k.name, "path": rel_path, "size_bytes": k.stat().st_size}
                )

        # 4. JSONs de Persistência direta
        identity_file = BASE_DIR / "Data" / "Persistence" / "identity.json"
        if identity_file.exists():
            rel_path = str(identity_file.relative_to(BASE_DIR)).replace("\\", "/")
            files_tree["persistence"].append(
                {
                    "name": "identity.json",
                    "path": rel_path,
                    "size_bytes": identity_file.stat().st_size,
                }
            )

        return files_tree

    @classmethod
    def read_file(cls, relative_path: str) -> Dict[str, Any]:
        """Lê e devolve o conteúdo em texto do ficheiro indicado."""
        target_path = cls.resolve_safe_path(relative_path)
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Ficheiro não encontrado.")

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "path": relative_path,
                "filename": target_path.name,
                "extension": target_path.suffix,
                "content": content,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Erro ao ler ficheiro: {str(e)}"
            )

    @classmethod
    async def save_and_sync(
        cls, file_path: str, content: str, action: str = "hot_reload"
    ) -> Dict[str, Any]:
        """Valida a integridade formal, grava as alterações e executa reindexação a quente."""
        target_path = cls.resolve_safe_path(file_path)

        # 1. Validação de Sintaxe pré-gravação
        if target_path.suffix == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError as err:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sintaxe JSON inválida: {err.msg} (Linha {err.lineno})",
                )
        elif target_path.suffix in [".yaml", ".yml"]:
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as err:
                raise HTTPException(
                    status_code=400, detail=f"Sintaxe YAML inválida: {str(err)}"
                )

        # 2. Escrita no disco
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Erro ao gravar no disco: {str(e)}"
            )

        # 3. Execução das rotinas de sincronização e Hot-Reload
        sync_logs = []
        if action in ["hot_reload", "reindex_routes"]:
            data_manager.reload_all()
            sync_logs.append("Cache em memória (RAM) limpo.")

            try:
                seeder = DatabaseSeeder(data_manager.db, data_manager.base_dir)
                seeder.sync_all()
                sync_logs.append("Tabelas do SQLite sincronizadas via DatabaseSeeder.")
            except Exception as e:
                sync_logs.append(f"Aviso no Seeder: {e}")

            if target_path.name == "router_triggers.json" or action == "reindex_routes":
                try:
                    from Brain.Core.Router.TLMRouter import TLMRouter

                    router_inst = TLMRouter()
                    await router_inst.sincronizar_base_rotas(force=True)
                    sync_logs.append(
                        "Gatilhos de rotas reindexados com sucesso no ChromaDB."
                    )
                except Exception as e:
                    sync_logs.append(f"Falha ao reindexar rotas no ChromaDB: {e}")

        return {
            "status": "saved",
            "file": target_path.name,
            "action_taken": action,
            "sync_details": sync_logs,
        }
