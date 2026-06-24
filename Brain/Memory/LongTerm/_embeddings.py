import os
import time
import logging
from chromadb.api.types import EmbeddingFunction
from dotenv import load_dotenv

from Brain.Memory.DataManager import data_manager
from Brain.Providers.LLMFactory import llm_factory

load_dotenv()
logger = logging.getLogger("SamBot.Embeddings")


class SmartEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.state_key = "embedding_state"
        self.working_mode = "IDLE"

        self.ai_chain = llm_factory.get_default_principal_chain()

        self._load_preference()

    def _load_preference(self):
        """Carrega o último estado que funcionou para fins de log ou auditoria."""
        state = data_manager.get_knowledge(self.state_key) or {}
        self.pref_provider = state.get("provider")
        timestamp = state.get("timestamp", 0)

        if time.time() - timestamp > 604800:
            self.pref_provider = None

    def _save_preference(self, provider: str):
        """Salva o provedor bem-sucedido no DataManager."""
        state = {
            "provider": provider,
            "timestamp": time.time(),
        }
        data_manager.save_knowledge(self.state_key, state)
        self.pref_provider = provider
        logger.info(f"💾 [Embeddings] Estado de sucesso registrado: {provider}")

    async def get_single_embedding(self, text: str) -> list:
        """
        Solicita o vetor à cadeia principal.
        A própria cadeia tenta o Gemini primeiro e, se falhar, aciona o Ollama local.
        """
        if not text:
            return [0.0] * 768

        try:
            embedding = await self.ai_chain.get_embedding(text)

            if embedding:
                self.working_mode = "CHAIN_ACTIVE"
                return embedding

        except Exception as e:
            logger.error(f"❌ [Embeddings] Erro inesperado na cadeia de vetores: {e}")

        self.working_mode = "ERROR"
        return [0.0] * 768

    def __call__(self, input):
        """Ponto de entrada síncrono exigido pelo ChromaDB."""
        import asyncio

        if isinstance(input, str):
            return [asyncio.run(self.get_single_embedding(input))]
        return [asyncio.run(self.get_single_embedding(t)) for t in input]
