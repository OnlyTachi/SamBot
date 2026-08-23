# Services/API/Routes/ControlRoute.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import psutil
import platform
import time
from Services.API.Security import verify_bot_token
from Brain.Memory.SelfKnowledge.SystemInspector import SystemInspector

router = APIRouter(prefix="/api/v1/control", tags=["Bot Control & Telemetry"])


class CogActionRequest(BaseModel):
    cog_name: str


# --- 1. TELEMETRIA E SAÚDE DO BOT ---


@router.get("/status", dependencies=[Depends(verify_bot_token)])
async def get_bot_status(request: Request):
    """Retorna métricas em tempo real de hardware, Discord e subsistemas."""
    bot = request.app.state.bot
    inspector = SystemInspector(bot=bot)
    snapshot = inspector.get_system_snapshot()

    # Métricas de hardware
    ram = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent()

    return {
        "status": "online" if bot.is_ready() else "connecting",
        "bot_user": {
            "name": bot.user.name if bot.user else "Offline",
            "id": str(bot.user.id) if bot.user else None,
            "avatar": bot.user.display_avatar.url if bot.user else None,
        },
        "system": {
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "cpu_usage_percent": cpu_percent,
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_percent": ram.percent,
        },
        "telemetry": snapshot,
    }


# --- 2. GERENCIAMENTO DE COGS / EXTENSÕES ---


@router.get("/cogs", dependencies=[Depends(verify_bot_token)])
async def list_cogs(request: Request):
    """Lista todos os Cogs carregados no bot."""
    bot = request.app.state.bot
    cogs_info = []

    for cog_name, cog_instance in bot.cogs.items():
        cogs_info.append(
            {
                "name": cog_name,
                "module": cog_instance.__module__,
                "commands_count": len(cog_instance.get_commands()),
                "description": (
                    cog_instance.__doc__.strip() if cog_instance.__doc__ else ""
                ),
            }
        )

    return {"loaded_cogs": cogs_info, "total": len(cogs_info)}


@router.post("/cogs/reload", dependencies=[Depends(verify_bot_token)])
async def reload_cog(payload: CogActionRequest, request: Request):
    """Recarrega um Cog específico pelo nome do seu módulo/extensão."""
    bot = request.app.state.bot
    module_target = None

    # Procura se o usuário enviou o nome da classe ou o path do módulo
    for cog_name, cog_instance in bot.cogs.items():
        if cog_name.lower() == payload.cog_name.lower():
            module_target = cog_instance.__module__
            break

    if not module_target:
        module_target = (
            payload.cog_name
        )  # Tenta usar o caminho direto (ex: Modules.Fun.Dice)

    try:
        await bot.reload_extension(module_target)
        return {
            "status": "success",
            "message": f"Módulo '{module_target}' recarregado com sucesso!",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao recarregar extensão '{module_target}': {str(e)}",
        )


@router.post("/cogs/reload-all", dependencies=[Depends(verify_bot_token)])
async def reload_all_cogs(request: Request):
    """Tenta recarregar todas as extensões registradas."""
    bot = request.app.state.bot
    results = {"success": [], "failed": []}

    loaded_modules = list(bot.extensions.keys())
    for ext in loaded_modules:
        try:
            await bot.reload_extension(ext)
            results["success"].append(ext)
        except Exception as e:
            results["failed"].append({"extension": ext, "error": str(e)})

    return {"status": "completed", "results": results}


# --- 3. KILL SWITCH (DESLIGAMENTO CONTROLADO) ---


@router.post("/kill", dependencies=[Depends(verify_bot_token)])
async def trigger_kill_switch(request: Request):
    """Desliga o bot de forma graciosa fechando as conexões."""
    bot = request.app.state.bot

    async def _shutdown():
        await asyncio.sleep(1.0)  # Aguarda responder a requisição HTTP primeiro
        await bot.close()

    asyncio.create_task(_shutdown())
    return {
        "status": "shutdown_initiated",
        "message": "Comando de desligamento recebido. A SamBot está encerrando suas tarefas.",
    }
