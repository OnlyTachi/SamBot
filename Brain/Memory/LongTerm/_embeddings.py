import os
import asyncio
import requests
import logging
import time
from chromadb.api.types import EmbeddingFunction
import google.generativeai as genai
from dotenv import load_dotenv

from Brain.Memory.DataManager import data_manager

load_dotenv()

logger = logging.getLogger("SamBot.Embeddings")

try:
    from Brain.Providers.LLMFactory import llm_factory
except ImportError:
    llm_factory = None
    logger.error(
        "❌ LLMFactory não encontrada. O sistema de chaves Gemini será limitado."
    )


class SmartEmbeddingFunction(EmbeddingFunction):
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

        self.working_mode = "IDLE"
        self.state_key = "embedding_state"

        self._load_preference()

    def _load_preference(self):
        """Carrega o último modelo que funcionou. Validade: 7 dias."""
        state = data_manager.get_knowledge(self.state_key) or {}
        self.pref_provider = state.get("provider")
        self.pref_model = state.get("model")
        self.pref_key_index = state.get("key_index", 0)

        timestamp = state.get("timestamp", 0)
        # 604800 segundos = 7 dias
        if time.time() - timestamp > 604800:
            self.pref_provider = None

    def _save_preference(self, provider: str, model: str, key_index: int):
        """Guarda o modelo vitorioso no DataManager para acesso rápido futuro."""
        state = {
            "provider": provider,
            "model": model,
            "key_index": key_index,
            "timestamp": time.time(),
        }
        data_manager.save_knowledge(self.state_key, state)
        self.pref_provider = provider
        self.pref_model = model
        self.pref_key_index = key_index
        logger.info(
            f"💾 Preferência de Embedding guardada: {provider} -> {model} (Válido por 7 dias)"
        )

    async def _try_local(self, text):
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

    async def _try_cloud_specific(self, text, model_name, key_index):
        if not self.keys or key_index >= len(self.keys):
            return None
        try:
            genai.configure(api_key=self.keys[key_index])
            result = await asyncio.to_thread(
                genai.embed_content,
                model=model_name,
                content=text,
                task_type="retrieval_document",
            )
            self.working_mode = f"CLOUD ({model_name})"
            return result["embedding"]
        except Exception:
            return None

    async def _search_working_cloud(self, text):
        """Busca profunda em cascata (Lenta, mas só roda se não houver preferência válida)."""
        if not self.keys:
            return None

        for model_name in self.cloud_models:
            for idx in range(len(self.keys)):
                try:
                    genai.configure(api_key=self.keys[idx])
                    result = await asyncio.to_thread(
                        genai.embed_content,
                        model=model_name,
                        content=text,
                        task_type="retrieval_document",
                    )
                    self.working_mode = f"CLOUD ({model_name})"
                    # Encontrou um que funciona! Salva para os próximos 7 dias.
                    self._save_preference("cloud", model_name, idx)
                    return result["embedding"]
                except Exception as e:
                    err_msg = str(e)
                    if "404" in err_msg and "models/" in err_msg:
                        logger.warning(
                            f"⚠️ Modelo {model_name} indisponível globalmente. Pulando..."
                        )
                        break  # Não tenta outras chaves se o modelo em si foi descontinuado

                    logger.warning(
                        f"⚠️ Falha chave {idx} no {model_name}. Testando próxima..."
                    )
                    await asyncio.sleep(0.5)
        return None

    async def get_single_embedding(self, text):
        if self.pref_provider == "local":
            emb = await self._try_local(text)
            if emb:
                return emb
            self.pref_provider = None  # Se falhou, descarta a preferência

        elif self.pref_provider == "cloud" and self.pref_model:
            emb = await self._try_cloud_specific(
                text, self.pref_model, self.pref_key_index
            )
            if emb:
                return emb
            self.pref_provider = (
                None  # Se falhou, descarta a preferência e busca do zero
            )

        emb = await self._try_local(text)
        if emb:
            self._save_preference("local", self.model_local, 0)
            return emb

        emb = await self._search_working_cloud(text)
        if emb:
            return emb

        self.working_mode = "ERROR"
        return [0.0] * 768

    def __call__(self, input):
        if isinstance(input, str):
            return [asyncio.run(self.get_single_embedding(input))]
        return [asyncio.run(self.get_single_embedding(t)) for t in input]
