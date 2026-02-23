import chromadb
import os
import uuid
import time
import requests
import logging
import asyncio
import google.generativeai as genai
from chromadb.api.types import EmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

# --- Importação da Fábrica Central ---
try:
    from Brain.Providers.LLMFactory import llm_factory
except ImportError:
    llm_factory = None
    logging.error(
        "❌ LLMFactory não encontrada. O sistema de chaves Gemini será limitado."
    )

# Configuração de Logger
logger = logging.getLogger("SamBot.VectorStore")


class SmartEmbeddingFunction(EmbeddingFunction):
    """
    Estratégia Híbrida e Inteligente de Embedding:
    1. Tenta Local (Ollama/Nomic) -> Timeout rápido.
    2. Fallback Gemini Cloud:
       - Tenta modelos em cascata: text-embedding-004 -> embedding-001.
       - Rotação de chaves automática para erros de cota (429).
       - Troca de modelo imediata para erros de disponibilidade (404).
    """

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_HOST") or os.getenv(
            "OLLAMA_LOCAL_URL", "http://localhost:11434"
        )
        self.model_local = "nomic-embed-text"

        self.cloud_models = ["models/text-embedding-004", "models/embedding-001"]

        self.keys = (
            llm_factory.keys if llm_factory and hasattr(llm_factory, "keys") else []
        )
        if not self.keys:
            k = os.getenv("GEMINI_API_KEY")
            if k:
                self.keys = [k]

        self.current_key_index = 0
        self.working_mode = "IDLE"

    def _rotate_key(self):
        if len(self.keys) <= 1:
            return
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        logger.info(f"🔄 Rotação de Chave Embedding: Índice {self.current_key_index}")

    async def _get_local_embedding(self, text):
        """Tenta gerar o vetor via Ollama local."""
        try:

            def call_ollama():
                return requests.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": self.model_local, "prompt": text},
                    timeout=2,
                )

            response = await asyncio.to_thread(call_ollama)
            if response.status_code == 200:
                self.working_mode = "LOCAL"
                return response.json()["embedding"]
        except:
            pass
        return None

    async def _get_google_embedding(self, text):
        """Tenta gerar o vetor via Google Gemini com cascata de modelos e chaves."""
        if not self.keys:
            return None

        for model_name in self.cloud_models:
            for _ in range(len(self.keys)):
                key = self.keys[self.current_key_index]
                try:
                    genai.configure(api_key=key)

                    result = await asyncio.to_thread(
                        genai.embed_content,
                        model=model_name,
                        content=text,
                        task_type="retrieval_document",
                    )

                    self.working_mode = f"CLOUD ({model_name})"
                    return result["embedding"]

                except Exception as e:
                    err_msg = str(e)

                    if "404" in err_msg and "models/" in err_msg:
                        logger.warning(
                            f"⚠️ Modelo {model_name} indisponível. Pulando para o próximo..."
                        )
                        break  # Sai do loop de chaves e vai para o próximo modelo

                    logger.warning(
                        f"⚠️ Erro no modelo {model_name} (Chave {self.current_key_index}): {err_msg[:50]}..."
                    )
                    self._rotate_key()
                    await asyncio.sleep(0.5)

        return None

    async def get_single_embedding(self, text):
        """Fluxo de decisão do embedding."""
        emb = await self._get_local_embedding(text)
        if emb:
            return emb

        emb = await self._get_google_embedding(text)
        if emb:
            return emb

        self.working_mode = "ERROR"
        return [0.0] * 768

    def __call__(self, input):
        """
        Método obrigatório para o ChromaDB.
        Nota: O ChromaDB costuma chamar isso de forma síncrona internamente.
        """
        if isinstance(input, str):
            return [asyncio.run(self.get_single_embedding(input))]
        return [asyncio.run(self.get_single_embedding(t)) for t in input]


class VectorStore:
    """
    Gerencia Fatos e Resumos no ChromaDB.
    Focado em persistência de longo prazo para o Agente.
    """

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
        """Adiciona uma memória de forma assíncrona."""
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
        """Busca conteúdos relevantes."""
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


# Instância Global
vector_store = VectorStore()
