# Services/API/services/download_service.py
import asyncio
import logging
import time
import uuid
from typing import Any, Dict, Optional
import httpx
from fastapi import HTTPException

from Brain.Memory.DataManager.Connections import data_manager
from Core.ConfigLoader import AppConfig

logger = logging.getLogger("SamBot.Services.Download")


class DownloadService:
    # Registo em memória partilhado das tarefas de transferência ativas
    _tasks: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_worker_url(cls) -> str:
        return AppConfig.get("yt_worker.url", "http://127.0.0.1:4000").rstrip("/")

    @classmethod
    async def ping_worker(cls) -> bool:
        """Verifica a disponibilidade do worker de download."""
        worker_url = cls.get_worker_url()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{worker_url}/ping")
                return res.status_code == 200
        except Exception:
            return False

    @classmethod
    async def poll_worker_status(cls, task_id: str):
        """Monitoriza o progresso no servidor Node.js e atualiza o estado local."""
        worker_url = cls.get_worker_url()
        async with httpx.AsyncClient() as client:
            while True:
                await asyncio.sleep(2)
                try:
                    res = await client.get(f"{worker_url}/status/{task_id}")
                    if res.status_code == 200:
                        data = res.json()
                        if task_id in cls._tasks:
                            cls._tasks[task_id]["status"] = data.get("status")
                            cls._tasks[task_id]["progress"] = data.get("progress")
                            cls._tasks[task_id]["logOutput"] = data.get("logs")
                            if data.get("track"):
                                cls._tasks[task_id]["track"] = data.get("track")

                        if data.get("status") in ["COMPLETED", "FAILED"]:
                            break
                except Exception:
                    if task_id in cls._tasks:
                        cls._tasks[task_id]["logOutput"].append(
                            "Falha de comunicação temporária com o worker..."
                        )

    @classmethod
    async def create_task(
        cls, url: str, requester: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Valida o worker, cria a tarefa, regista contribuições e envia para processamento."""
        is_alive = await cls.ping_worker()
        if not is_alive:
            raise HTTPException(
                status_code=503,
                detail="Servidor de download indisponível no momento. Tente novamente mais tarde.",
            )

        task_id = f"dl_{int(time.time())}_{str(uuid.uuid4())[:5]}"
        worker_url = cls.get_worker_url()

        # Contabilização de métricas/contribuições
        requester_id = requester.get("id") if requester else None
        if requester_id and requester_id != "usr_guest":
            try:
                data_manager.increment_contribution(
                    str(requester_id), "sharedLinksCount", 1
                )
            except Exception as e:
                logger.warning(
                    f"Erro ao registar métrica de contribuição para {requester_id}: {e}"
                )

        task_entry = {
            "taskId": task_id,
            "url": url,
            "status": "QUEUED",
            "progress": 5,
            "title": "Aguardando extração...",
            "artist": "Pipeline yt-dlp",
            "logOutput": [
                f"[{time.strftime('%H:%M:%S')}] Tarefa {task_id} registada na Sam.",
                f"[{time.strftime('%H:%M:%S')}] Handshake com worker concluído.",
            ],
            "track": None,
        }
        cls._tasks[task_id] = task_entry

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{worker_url}/download",
                    json={"url": url, "taskId": task_id},
                )
        except Exception as e:
            cls._tasks.pop(task_id, None)
            raise HTTPException(
                status_code=500, detail=f"Erro ao despachar tarefa para o worker: {e}"
            )

        return task_entry

    @classmethod
    def get_task(cls, task_id: str) -> Dict[str, Any]:
        """Obtém o estado e os logs de uma tarefa específica."""
        task = cls._tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return task
