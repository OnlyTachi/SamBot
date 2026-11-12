# Services/API/Routes/FilesRoutes.py
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from Services.API.Security import verify_bot_token
from Services.API.Services.FileService import FileService

router = APIRouter(prefix="/api/v1/files", tags=["Files & Configuration Editor"])


class FileSaveRequest(BaseModel):
    file_path: str
    content: str
    action: str = "hot_reload"


@router.get("/tree", dependencies=[Depends(verify_bot_token)])
async def get_editable_files_tree():
    return FileService.get_editable_files_tree()


@router.get("/read", dependencies=[Depends(verify_bot_token)])
async def read_file_content(
    path: str = Query(..., description="Caminho relativo do ficheiro")
):
    return FileService.read_file(path)


@router.post("/save", dependencies=[Depends(verify_bot_token)])
async def save_file_content(payload: FileSaveRequest):
    return await FileService.save_and_sync(
        file_path=payload.file_path,
        content=payload.content,
        action=payload.action,
    )
