# Services/API/Routes/DownloadRoute.py
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from Services.API.Security import verify_bot_token
from Services.API.Services.DownloadService import DownloadService

router = APIRouter(prefix="/api/download", tags=["Download Pipeline"])


class DownloadRequest(BaseModel):
    url: str
    requester: Optional[Dict[str, Any]] = None


@router.post("/tasks", dependencies=[Depends(verify_bot_token)])
async def create_download_task(
    payload: DownloadRequest, background_tasks: BackgroundTasks
):
    task_entry = await DownloadService.create_task(
        url=payload.url,
        requester=payload.requester,
    )
    # Agenda o polling assíncrono em background na infraestrutura do FastAPI
    background_tasks.add_task(DownloadService.poll_worker_status, task_entry["taskId"])

    return {"success": True, **task_entry}


@router.get("/tasks/{task_id}", dependencies=[Depends(verify_bot_token)])
async def get_task_status(task_id: str):
    return DownloadService.get_task(task_id)
