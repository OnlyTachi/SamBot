# Services/API/Routes/DatabasesRoute.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from Services.API.Security import verify_bot_token
from Services.API.Services.DatabaseService import DatabaseService

router = APIRouter(prefix="/api/v1/db", tags=["Databases Viewer"])


class VectorSearchTestRequest(BaseModel):
    collection_name: str
    query_text: str
    n_results: int = 3


# 1. SQLITE
@router.get("/sqlite/tables", dependencies=[Depends(verify_bot_token)])
async def list_sqlite_tables():
    return {"tables": DatabaseService.list_sqlite_tables()}


@router.get("/sqlite/table/{table_name}", dependencies=[Depends(verify_bot_token)])
async def get_sqlite_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
):
    return DatabaseService.get_table_data(table_name, page, limit, search)


# 2. MEILISEARCH
@router.get("/meili/stats", dependencies=[Depends(verify_bot_token)])
async def get_meilisearch_stats():
    return await DatabaseService.get_meilisearch_stats()


@router.get("/meili/ofertas", dependencies=[Depends(verify_bot_token)])
async def search_meili_ofertas(
    query: str = Query("", description="Termo de pesquisa"),
    limit: int = Query(20, ge=1, le=50),
):
    return await DatabaseService.search_meili_ofertas(query, limit)


# 3. CHROMADB
@router.get("/chroma/collections", dependencies=[Depends(verify_bot_token)])
async def list_chroma_collections():
    return DatabaseService.list_chroma_collections()


@router.get(
    "/chroma/collection/{collection_name}", dependencies=[Depends(verify_bot_token)]
)
async def get_chroma_documents(
    collection_name: str, limit: int = Query(20, ge=1, le=100)
):
    return DatabaseService.get_chroma_documents(collection_name, limit)


@router.post("/chroma/query-test", dependencies=[Depends(verify_bot_token)])
async def test_chroma_query(payload: VectorSearchTestRequest):
    return await DatabaseService.test_chroma_query(
        payload.collection_name, payload.query_text, payload.n_results
    )
