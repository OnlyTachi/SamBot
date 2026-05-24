import chromadb
import os
import uuid
import time
import logging
from ._embeddings import SmartEmbeddingFunction

logger = logging.getLogger("SamBot.VectorStore")


class VectorStore:
    def __init__(self):
        self.db_path = os.path.join("Data", "Persistence", "VectorDB")
        os.makedirs(self.db_path, exist_ok=True)

        self.embedding_fn = SmartEmbeddingFunction()

        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collections = {
                "fatos_usuario": self.client.get_or_create_collection(
                    name="fatos_usuario", metadata={"hnsw:space": "cosine"}
                ),
                "resumos_diarios": self.client.get_or_create_collection(
                    name="resumos_diarios", metadata={"hnsw:space": "cosine"}
                ),
            }
            logger.info(
                f"✅ VectorStore pronta. Modo: {self.embedding_fn.working_mode}"
            )
        except Exception as e:
            logger.error(f"❌ Falha ao iniciar ChromaDB: {e}")
            self.client = None

    async def add_memory(
        self, collection_name: str, text: str, metadata: dict = None, doc_id: str = None
    ):
        if not self.client or not text:
            return

        try:
            col = self.collections.get(collection_name)
            if not col:
                return

            embedding = await self.embedding_fn.get_single_embedding(text)
            id_final = (
                doc_id
                if doc_id
                else f"mem_{int(time.time()*1000)}_{uuid.uuid4().hex[:4]}"
            )

            col.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata or {"timestamp": str(time.time())}],
                ids=[id_final],
            )
            logger.debug(
                f"💾 Memória salva em {collection_name} ({self.embedding_fn.working_mode})"
            )
        except Exception as e:
            logger.error(f"❌ Erro ao salvar memória: {e}")

    async def query_relevant(
        self, collection_name: str, query: str, n_results: int = 2
    ) -> list:
        if not self.client or not query:
            return []

        try:
            col = self.collections.get(collection_name)
            if not col or col.count() == 0:
                return []

            embedding = await self.embedding_fn.get_single_embedding(query)
            res = col.query(
                query_embeddings=[embedding], n_results=min(n_results, col.count())
            )

            if res and "documents" in res and res["documents"]:
                return res["documents"][0]
            return []
        except Exception as e:
            logger.error(f"❌ Erro na busca vetorial: {e}")
            return []


vector_store = VectorStore()
