# Services/API/services/database_service.py
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

from Brain.Memory.DataManager.Connections import data_manager
from Brain.Memory.LongTerm.VectorStore import vector_store

logger = logging.getLogger("SamBot.Services.Database")


class DatabaseService:
    # --- MÓDULO SQLITE ---
    @staticmethod
    def list_sqlite_tables() -> List[Dict[str, Any]]:
        """Lista todas as tabelas e a contagem de registos no SQLite."""
        if not hasattr(data_manager, "db") or not data_manager.db:
            raise HTTPException(
                status_code=500, detail="Ligação com SQLite indisponível."
            )

        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        rows = data_manager.db.execute_query(query, fetchall=True)
        tables_summary = []

        if rows:
            for (table_name,) in rows:
                count_row = data_manager.db.execute_query(
                    f"SELECT COUNT(*) FROM {table_name}", fetchone=True
                )
                count = count_row[0] if count_row else 0
                tables_summary.append(
                    {"table_name": table_name, "total_records": count}
                )

        return tables_summary

    @staticmethod
    def get_table_data(
        table_name: str, page: int = 1, limit: int = 25, search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recupera registos paginados de tabelas autorizadas com suporte a pesquisa."""
        valid_tables = ["users", "knowledge", "config", "prompts"]
        if table_name not in valid_tables:
            raise HTTPException(
                status_code=400, detail="Tabela inexistente ou não autorizada."
            )

        primary_keys = {
            "users": "user_id",
            "knowledge": "key",
            "config": "key",
            "prompts": "name",
        }
        pk = primary_keys[table_name]
        offset = (page - 1) * limit

        if search:
            query = f"SELECT * FROM {table_name} WHERE {pk} LIKE ? LIMIT ? OFFSET ?"
            rows = data_manager.db.execute_query(
                query, (f"%{search}%", limit, offset), fetchall=True
            )
            count_query = f"SELECT COUNT(*) FROM {table_name} WHERE {pk} LIKE ?"
            total_rows = data_manager.db.execute_query(
                count_query, (f"%{search}%",), fetchone=True
            )[0]
        else:
            query = f"SELECT * FROM {table_name} LIMIT ? OFFSET ?"
            rows = data_manager.db.execute_query(query, (limit, offset), fetchall=True)
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            total_rows = data_manager.db.execute_query(count_query, fetchone=True)[0]

        formatted_data = []
        if rows:
            for r in rows:
                record_id, content = r[0], r[1]
                try:
                    parsed_content = (
                        json.loads(content) if isinstance(content, str) else content
                    )
                except Exception:
                    parsed_content = content
                formatted_data.append({"id": record_id, "data": parsed_content})

        return {
            "table": table_name,
            "page": page,
            "limit": limit,
            "total_records": total_rows,
            "total_pages": (total_rows + limit - 1) // limit,
            "rows": formatted_data,
        }

    # --- MÓDULO MEILISEARCH ---

    @staticmethod
    async def get_meilisearch_stats() -> Dict[str, Any]:
        """Obtém o estado e a contagem de documentos indexados no Meilisearch."""
        if not hasattr(data_manager, "meili_db") or not data_manager.meili_db:
            raise HTTPException(status_code=503, detail="Módulo Meilisearch offline.")

        index_info = await data_manager.meili_db.execute_request(
            "GET", "/indexes/ofertas"
        )
        stats = await data_manager.meili_db.execute_request(
            "GET", "/indexes/ofertas/stats"
        )
        return {
            "status": "online" if index_info else "offline",
            "index": index_info,
            "stats": stats or {},
        }

    @staticmethod
    async def search_meili_ofertas(query: str = "", limit: int = 20) -> Dict[str, Any]:
        """Executa consultas de texto completo sobre o catálogo de promoções."""
        if not hasattr(data_manager, "meili_db") or not data_manager.meili_db:
            raise HTTPException(status_code=503, detail="Módulo Meilisearch offline.")

        payload = {"q": query, "limit": limit, "sort": ["preco:asc"]}
        response = await data_manager.meili_db.execute_request(
            "POST", "/indexes/ofertas/search", payload
        )
        if not response or "hits" not in response:
            return {"total_hits": 0, "hits": []}

        return {
            "total_hits": len(response["hits"]),
            "hits": response["hits"],
            "processing_time_ms": response.get("processingTimeMs", 0),
        }

    # --- MÓDULO CHROMADB ---

    @staticmethod
    def list_chroma_collections() -> Dict[str, Any]:
        """Lista coleções ativas e total de vetores guardados no ChromaDB."""
        if not vector_store or not vector_store.client:
            raise HTTPException(
                status_code=503, detail="ChromaDB não inicializado ou offline."
            )

        collections_data = []
        for name, col in vector_store.collections.items():
            try:
                count = col.count()
            except Exception:
                count = 0
            collections_data.append({"name": name, "vector_count": count})

        return {
            "status": "online",
            "mode": vector_store.embedding_fn.working_mode,
            "collections": collections_data,
        }

    @staticmethod
    def get_chroma_documents(collection_name: str, limit: int = 20) -> Dict[str, Any]:
        """Devolve os documentos, metadados e IDs de uma coleção vetorial."""
        if not vector_store or not vector_store.client:
            raise HTTPException(status_code=503, detail="ChromaDB offline.")

        col = vector_store.collections.get(collection_name)
        if not col:
            raise HTTPException(
                status_code=404, detail="Coleção vetorial não encontrada."
            )

        try:
            data = col.get(limit=limit, include=["documents", "metadatas"])
            formatted_docs = []
            if data and "ids" in data:
                for idx, doc_id in enumerate(data["ids"]):
                    doc_text = data["documents"][idx] if "documents" in data else ""
                    metadata = data["metadatas"][idx] if "metadatas" in data else {}
                    formatted_docs.append(
                        {"id": doc_id, "document": doc_text, "metadata": metadata}
                    )

            return {
                "collection": collection_name,
                "total_fetched": len(formatted_docs),
                "documents": formatted_docs,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Erro ao ler documentos do Chroma: {e}"
            )

    @staticmethod
    async def test_chroma_query(
        collection_name: str, query_text: str, n_results: int = 3
    ) -> Dict[str, Any]:
        """Mede distâncias e score de similaridade para validação de thresholds vetoriais."""
        if not vector_store or not vector_store.client:
            raise HTTPException(status_code=503, detail="ChromaDB offline.")

        col = vector_store.collections.get(collection_name)
        if not col:
            raise HTTPException(
                status_code=404, detail="Coleção vetorial não encontrada."
            )

        try:
            embedding = await vector_store.embedding_fn.get_single_embedding(query_text)
            res = col.query(
                query_embeddings=[embedding],
                n_results=min(n_results, max(1, col.count())),
                include=["documents", "metadatas", "distances"],
            )
            results = []
            if res and "ids" in res and res["ids"]:
                for i in range(len(res["ids"][0])):
                    distance = res["distances"][0][i]
                    score = round(1.0 - distance, 4)
                    results.append(
                        {
                            "id": res["ids"][0][i],
                            "document": res["documents"][0][i],
                            "metadata": res["metadatas"][0][i],
                            "distance": distance,
                            "similarity_score": score,
                        }
                    )

            return {
                "query": query_text,
                "collection": collection_name,
                "results": results,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Erro ao executar procura vetorial: {e}"
            )
