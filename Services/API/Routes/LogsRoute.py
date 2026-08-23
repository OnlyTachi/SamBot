from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from typing import List, Optional
import asyncio
import os
from pathlib import Path

from Services.API.Security import verify_bot_token

router = APIRouter(prefix="/api/v1/logs", tags=["Logs & Streaming"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"

LOG_FILES_MAP = {
    "general": LOGS_DIR / "sambot_general.log",
    "errors": LOGS_DIR / "sambot_errors.log",
}

# --- FUNÇÃO AUXILIAR: LER ÚLTIMAS LINHAS (TAIL) ---


def tail_file(file_path: Path, lines_count: int = 100) -> List[str]:
    """Lê eficientemente as últimas N linhas de um arquivo de texto."""
    if not file_path.exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            return [line.rstrip("\r\n") for line in all_lines[-lines_count:]]
    except Exception:
        return []


# ==========================================
# 1. CONSULTA HTTP (REST TAIL)
# ==========================================


@router.get("/tail", dependencies=[Depends(verify_bot_token)])
async def get_logs_tail(
    log_type: str = Query("general", regex="^(general|errors)$"),
    lines: int = Query(100, ge=10, le=1000),
):
    """Retorna as últimas linhas de um arquivo de log para inicialização da UI."""
    target_file = LOG_FILES_MAP.get(log_type)
    if not target_file:
        raise HTTPException(status_code=400, detail="Tipo de log inválido.")

    logs = tail_file(target_file, lines)
    return {
        "log_type": log_type,
        "file": target_file.name,
        "lines_returned": len(logs),
        "logs": logs,
    }


# ==========================================
# 2. STREAMING CONTÍNUO VIA WEBSOCKET
# ==========================================


@router.websocket("/ws")
async def websocket_logs_stream(
    websocket: WebSocket, log_type: str = "general", token: Optional[str] = None
):
    """
    Canal WebSocket bidirecional para streaming em tempo real.
    Autenticação realizada via Query Parameter (?token=SEU_TOKEN).
    """
    from Core.ConfigLoader import AppConfig
    from Brain.Memory.DataManager.Connections import data_manager

    token_esperado = AppConfig.get("API_SECRET_TOKEN") or os.getenv("API_SECRET_TOKEN")
    if not token_esperado:
        admin_secret = data_manager.get_knowledge("api_security")
        token_esperado = admin_secret.get("staff_token", "sambot_default_secret_token")

    if token != token_esperado:
        await websocket.close(code=1008, reason="Token de autenticação inválido")
        return

    target_file = LOG_FILES_MAP.get(log_type, LOG_FILES_MAP["general"])
    await websocket.accept()

    initial_history = tail_file(target_file, 20)
    for line in initial_history:
        await websocket.send_json({"type": "history", "message": line})

    try:
        # Abre o arquivo em modo leitura contínua (tail -f)
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            # Move o cursor para o final do arquivo
            f.seek(0, os.SEEK_END)

            while True:
                line = f.readline()
                if line:
                    clean_line = line.rstrip("\r\n")
                    if clean_line:
                        await websocket.send_json(
                            {"type": "log", "log_type": log_type, "message": clean_line}
                        )
                else:
                    # Aguarda novas linhas serem gravadas no disco
                    await asyncio.sleep(0.3)

    except WebSocketDisconnect:
        # Desconexão normal do cliente (fechou a aba)
        pass
    except Exception as e:
        try:
            await websocket.send_json(
                {"type": "error", "message": f"Erro no stream: {str(e)}"}
            )
            await websocket.close(code=1011)
        except Exception:
            pass
