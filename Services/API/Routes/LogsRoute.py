# Services/API/Routes/LogsRoute.py
import asyncio
import os
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect

from Services.API.Security import get_expected_token, verify_bot_token
from Services.API.Services.LogsService import LogService

router = APIRouter(prefix="/api/v1/logs", tags=["Logs & Streaming"])


@router.get("/tail", dependencies=[Depends(verify_bot_token)])
async def get_logs_tail(
    log_type: str = Query("general", pattern="^(general|errors)$"),
    lines: int = Query(100, ge=10, le=1000),
):
    return LogService.get_logs_tail(log_type, lines)


@router.websocket("/ws")
async def websocket_logs_stream(
    websocket: WebSocket,
    log_type: str = "general",
    token: Optional[str] = None,
):
    token_esperado = get_expected_token()
    if not token_esperado or token != token_esperado:
        await websocket.close(code=1008, reason="Token de autenticação inválido")
        return

    target_file = LogService.get_log_file_path(log_type)
    await websocket.accept()

    initial_history = LogService.tail_file(target_file, 20)
    for line in initial_history:
        await websocket.send_json({"type": "history", "message": line})

    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
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
                    await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json(
                {"type": "error", "message": f"Erro no stream: {str(e)}"}
            )
            await websocket.close(code=1011)
        except Exception:
            pass


@router.get("/stats", dependencies=[Depends(verify_bot_token)])
async def get_system_metrics(request: Request, userId: Optional[str] = None):
    return LogService.get_system_metrics(request.app.state.bot, userId)
