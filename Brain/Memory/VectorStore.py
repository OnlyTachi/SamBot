import chromadb
import os
import uuid
import time
import requests
import logging
import google.generativeai as genai
from chromadb.api.types import EmbeddingFunction

# --- Importação da Fábrica Central ---
try:
    from Brain.Providers.LLMFactory import llm_factory
except ImportError:
    llm_factory = None
    logging.error("❌ LLMFactory não encontrada. O sistema de chaves Gemini será limitado.")

# Configuração de Logger
logger = logging.getLogger("SamBot.VectorStore")

class NomicFailoverEmbedding(EmbeddingFunction):
    """
    Estratégia Híbrida de Embedding com Rotação de Chaves:
    1. Tenta Local (Ollama/Nomic) -> Timeout de 2s.
    2. Fallback para Google Gemini -> Usa Pool de chaves da LLMFactory com rotação automática.
    """
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_HOST")
        self.model_local = "nomic-embed-text"
        self.model_cloud = "models/text-embedding-004"
        
        self.keys = llm_factory.keys if llm_factory and hasattr(llm_factory, 'keys') else []
        self.current_key_index = 0
        
        if not self.keys:
            env_key = os.getenv("GEMINI_API_KEY")
            if env_key:
                self.keys = [env_key]
        
        self.working_mode = "IDLE"

    def _rotate_key(self):
        """Rotaciona para a próxima chave Gemini disponível."""
        if len(self.keys) <= 1: return
        old_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        logger.info(f"🔄 Rotação de Chave Embedding: {old_index} -> {self.current_key_index}")

    def _get_local_embedding(self, text):
        """Tenta Ollama Local com timeout de 2s."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.model_local, "prompt": text},
                timeout=2
            )
            if response.status_code == 200:
                self.working_mode = "LOCAL"
                return response.json()["embedding"]
        except:
            pass
        return None

    def _get_google_embedding(self, text):
        """Tenta Google Gemini com rotação em caso de erro (Quota/Auth)."""
        if not self.keys: return None

        tentativas = len(self.keys)
        for _ in range(tentativas):
            key = self.keys[self.current_key_index]
            try:
                genai.configure(api_key=key)
                result = genai.embed_content(
                    model=self.model_cloud,
                    content=text,
                    task_type="retrieval_document"
                )
                self.working_mode = "CLOUD"
                return result['embedding']
            except Exception as e:
                logger.warning(f"⚠️ Erro na chave Gemini {self.current_key_index}: {e}")
                self._rotate_key()
                continue
        return None

    def __call__(self, input):
        """Método obrigatório para o ChromaDB."""
        texts = [input] if isinstance(input, str) else input
        embeddings = []
        
        for text in texts:
            emb = self._get_local_embedding(text)
            
            if not emb:
                emb = self._get_google_embedding(text)
            
            if not emb:
                self.working_mode = "ERROR"
                emb = [0.0] * 768
                
            embeddings.append(emb)
        return embeddings

class VectorStore:
    """
    Gerencia Fatos e Resumos no ChromaDB. 
    Compatível com o fluxo do Agent.py.
    """
    def __init__(self):
        self.db_path = os.path.join("Data", "Persistence", "VectorDB")
        os.makedirs(self.db_path, exist_ok=True)
        
        self.embedding_fn = NomicFailoverEmbedding()
        
        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            self.collections = {
                "fatos_usuario": self.client.get_or_create_collection(
                    name="fatos_usuario",
                    embedding_function=self.embedding_fn
                ),
                "resumos_diarios": self.client.get_or_create_collection(
                    name="resumos_diarios",
                    embedding_function=self.embedding_fn
                )
            }
            
            num_keys = len(self.embedding_fn.keys)
            logger.info(f"✅ ChromaDB Híbrido pronto ({num_keys} chaves Gemini de backup).")
            
        except Exception as e:
            logger.error(f"❌ Falha crítica ao iniciar VectorStore: {e}")
            self.client = None

    def add_memory(self, collection_name: str, text: str, metadata: dict, doc_id: str = None):
        """Adiciona uma memória em uma coleção específica."""
        if not self.client: return
        try:
            col = self.collections.get(collection_name)
            if not col: return

            id_final = doc_id if doc_id else f"mem_{int(time.time()*1000)}_{uuid.uuid4().hex[:4]}"
            
            col.add(
                documents=[text],
                metadatas=[metadata or {"timestamp": str(time.time())}],
                ids=[id_final]
            )
            logger.debug(f"💾 Memória salva [{self.embedding_fn.working_mode}] -> {collection_name}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar memória: {e}")

    def query_relevant(self, collection_name: str, query: str, n_results: int = 2) -> list:
        """Busca conteúdos relevantes para o contexto."""
        if not self.client: return []
        try:
            col = self.collections.get(collection_name)
            if not col or col.count() == 0: return []

            res = col.query(
                query_texts=[query],
                n_results=min(n_results, col.count())
            )

            if res and 'documents' in res and res['documents']:
                return res['documents'][0]
            return []
        except Exception as e:
            logger.error(f"❌ Erro na busca vetorial: {e}")
            return []

# Instância Global para o sistema
vector_store = VectorStore()