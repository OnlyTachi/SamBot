from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import json
import yaml
from pathlib import Path

from Services.API.Security import verify_bot_token
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Memory.DataManager.DatabaseSeeder import DatabaseSeeder

router = APIRouter(prefix="/api/v1/files", tags=["Files & Configuration Editor"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Whitelist de diretórios e extensões permitidas para evitar vazamento do sistema de arquivos
ALLOWED_EXTENSIONS = {".json", ".txt", ".yaml", ".yml", ".env"}
ALLOWED_DIRECTORIES = [
    BASE_DIR / "Data" / "Prompts",
    BASE_DIR / "Data" / "Knowledge",
    BASE_DIR / "Data" / "Persistence",
    BASE_DIR,  # Permite config.yaml, application.yml na raiz
]

# --- MODELOS PYDANTIC ---


class FileSaveRequest(BaseModel):
    file_path: str  # Caminho relativo a partir da raiz (ex: "Data/Prompts/padrao.txt")
    content: str
    action: str = "hot_reload"  # "hot_reload", "save_only", "reindex_routes"


# --- UTILITÁRIO DE SEGURANÇA (PATH TRAVERSAL PROTECTION) ---


def resolve_safe_path(relative_path: str) -> Path:
    """Valida se o caminho requisitado pertence estritamente aos diretórios autorizados."""
    clean_path = relative_path.lstrip("/\\")
    target_path = (BASE_DIR / clean_path).resolve()

    # Checa se o arquivo reside dentro de algum dos diretórios permitidos
    is_safe = any(
        target_path == allowed or allowed in target_path.parents
        for allowed in ALLOWED_DIRECTORIES
    )

    if not is_safe or target_path.suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: Caminho de arquivo ou extensão não autorizada.",
        )

    return target_path


# ==========================================
# 1. LISTAGEM DE ARQUIVOS GERENCIÁVEIS
# ==========================================


@router.get("/tree", dependencies=[Depends(verify_bot_token)])
async def get_editable_files_tree():
    """Retorna uma lista categorizada de todos os arquivos que podem ser editados na dashboard."""
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

    # 3. Bases de Conhecimento (JSON)
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


# ==========================================
# 2. LEITURA DE ARQUIVO
# ==========================================


@router.get("/read", dependencies=[Depends(verify_bot_token)])
async def read_file_content(
    path: str = Query(..., description="Caminho relativo do arquivo")
):
    """Lê e retorna o conteúdo em texto puro do arquivo solicitado."""
    target_path = resolve_safe_path(path)

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "path": path,
            "filename": target_path.name,
            "extension": target_path.suffix,
            "content": content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo: {str(e)}")


# ==========================================
# 3. SALVAMENTO E SINCRONIZAÇÃO A QUENTE
# ==========================================


@router.post("/save", dependencies=[Depends(verify_bot_token)])
async def save_file_content(payload: FileSaveRequest):
    """
    Grava o novo conteúdo no disco e executa as rotinas de sincronização
    no SQLite e ChromaDB com base no tipo de arquivo.
    """
    target_path = resolve_safe_path(payload.file_path)

    # 1. Validação de Sintaxe antes de salvar no disco (Evita quebrar o JSON/YAML do bot)
    if target_path.suffix == ".json":
        try:
            json.loads(payload.content)
        except json.JSONDecodeError as err:
            raise HTTPException(
                status_code=400,
                detail=f"Sintaxe JSON inválida: {err.msg} (Linha {err.lineno})",
            )

    elif target_path.suffix in [".yaml", ".yml"]:
        try:
            yaml.safe_load(payload.content)
        except yaml.YAMLError as err:
            raise HTTPException(
                status_code=400, detail=f"Sintaxe YAML inválida: {str(err)}"
            )

    # 2. Escrita no disco
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(payload.content)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao gravar no disco: {str(e)}"
        )

    # 3. Execução das Ações de Sincronização / Hot-Reload
    sync_logs = []

    if payload.action in ["hot_reload", "reindex_routes"]:
        # Limpa os caches em RAM do DataManager
        data_manager.reload_all()
        sync_logs.append("Cache em memória (RAM) limpo.")

        # Sincroniza arquivos -> SQLite via Seeder
        try:
            seeder = DatabaseSeeder(data_manager.db, data_manager.base_dir)
            seeder.sync_all()
            sync_logs.append("Tabelas do SQLite sincronizadas via DatabaseSeeder.")
        except Exception as e:
            sync_logs.append(f"Aviso no Seeder: {e}")

        # Se o arquivo for router_triggers.json ou se a ação explícita for reindex_routes
        if (
            target_path.name == "router_triggers.json"
            or payload.action == "reindex_routes"
        ):
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
        "action_taken": payload.action,
        "sync_details": sync_logs,
    }
