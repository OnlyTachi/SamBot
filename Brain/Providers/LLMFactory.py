import os
import logging
import asyncio
from dotenv import load_dotenv

# 1. IMPORTAÇÕES SEGURAS (Tratamento de falta de libs)
try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from ollama import AsyncClient

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# --- Configuração de Logs ---
try:
    from Core.Logger import SamLogger as Logger

    logger_instance = Logger.get_logger("LLMFactory")
except ImportError:

    class Logger:
        def __init__(self):
            self.logger = logging.getLogger("SamBot.LLM")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)

        def info(self, msg):
            self.logger.info(msg)

        def error(self, msg):
            self.logger.error(msg)

        def critical(self, msg):
            self.logger.critical(msg)

        def warning(self, msg):
            self.logger.warning(msg)

    logger_instance = Logger()

load_dotenv()


class LLMFactory:
    """
    Factory inteligente do SamBot.
    - Importações dinâmicas (sobrevive sem Ollama ou Gemini instalados).
    - Inicialização não-bloqueante (lazy loading).
    - Failover de Embeddings (Nuvem -> Local).
    """

    _instance = None

    def __init__(self):
        self.log = logger_instance

        # --- Configurações Gemini ---
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
        self.embed_model_cloud = (
            "text-embedding-004"  # Modelo de vetor gratuito do Google
        )
        self.keys = self._carregar_chaves()
        self.current_key_index = 0
        self.active_model = None

        # --- Configurações Ollama ---
        self.remote_url = os.getenv("OLLAMA_REMOTE_URL")
        self.remote_model = os.getenv("MODEL_SMART_REMOTE")
        self.local_url = os.getenv(
            "OLLAMA_LOCAL_URL", "http://host.docker.internal:11434"
        )
        self.local_model = os.getenv("MODEL_FAST_LOCAL", "qwen2.5:1.5b")
        self.embed_model_local = os.getenv("MODEL_EMBED_LOCAL", "nomic-embed-text")

        # --- Configurações de Segurança e Geração ---
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        self.generation_config = {
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

        # 2. FLAG DE IGNIÇÃO
        self.is_ready = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _carregar_chaves(self):
        keys = []
        k_default = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if k_default:
            keys.append(k_default.strip())

        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if not key:
                break
            key_stripped = key.strip()
            if key_stripped not in keys:
                keys.append(key_stripped)
            i += 1
        return keys

    async def setup_providers(self):
        """Inicializa e testa as conexões de forma assíncrona, sem travar o bot."""
        if self.is_ready:
            return

        if not GEMINI_AVAILABLE:
            self.log.warning(
                "⚠️ Biblioteca google-generativeai não encontrada. Gemini offline."
            )
        elif not self.keys:
            self.log.error("❌ Nenhuma chave API do Gemini encontrada no .env!")
        else:
            await self._inicializar_melhor_chave_async()

        if not OLLAMA_AVAILABLE:
            self.log.warning(
                "⚠️ Biblioteca ollama não encontrada. Fallbacks locais offline."
            )

        self.is_ready = True

    async def _inicializar_melhor_chave_async(self):
        self.log.info(
            f"🔑 {len(self.keys)} chaves detectadas. Iniciando diagnóstico..."
        )
        for index, key in enumerate(self.keys):
            if await self._testar_chave_async(key, index + 1):
                genai.configure(api_key=key)
                self.active_model = self._criar_modelo()
                self.current_key_index = index
                self.log.info(f"✨ SamBot conectado usando a Chave {index + 1}.")
                return

        self.log.critical(
            "⛔ Todas as chaves falharam nos testes. IA Gemini em modo OFFLINE."
        )

    async def _testar_chave_async(self, key, index):
        """Valida a chave sem travar a thread principal."""
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(self.model_name)
            await model.generate_content_async(
                "ping", generation_config={"max_output_tokens": 1}
            )
            return True
        except Exception as e:
            err = str(e)
            if "429" in err:
                self.log.warning(f"⚠️ Chave {index} com Rate Limit (429).")
            else:
                self.log.warning(f"⚠️ Chave {index} falhou: {err[:50]}...")
            return False

    def _criar_modelo(self, system_instruction=None):
        if not GEMINI_AVAILABLE:
            return None
        return genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=self.safety_settings,
            generation_config=self.generation_config,
            system_instruction=system_instruction,
        )

    def get_model(self):
        return self.active_model

    async def check_health(self):
        if not self.is_ready:
            await self.setup_providers()
        return self.active_model is not None or OLLAMA_AVAILABLE

    def _get_next_key(self):
        if not self.keys:
            return None
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    async def _generate_gemini(self, system_instruction, prompt_parts) -> str:
        if not GEMINI_AVAILABLE or not self.keys:
            return None
        attempts = len(self.keys)

        for _ in range(attempts):
            key = self._get_next_key()
            try:
                genai.configure(api_key=key)
                model = self._criar_modelo(system_instruction=system_instruction)
                response = await model.generate_content_async(prompt_parts)
                self.active_model = model
                return response.text
            except google_exceptions.ResourceExhausted:
                self.log.warning("🔄 Chave esgotada (429). Tentando próxima...")
                continue
            except Exception as e:
                self.log.error(f"⚠️ Erro no Gemini: {e}")
                continue
        return None

    async def generate_response(self, prompt_parts, system_instruction=None) -> str:
        """Cascata Principal mantida, mas agora 100% segura."""
        # Se alguém chamou a geração antes do bot estar pronto, ele inicia sozinho (Lazy Loading)
        if not self.is_ready:
            await self.setup_providers()

        # 1. TENTATIVA GEMINI
        res = await self._generate_gemini(system_instruction, prompt_parts)
        if res:
            return res

        text_only_prompt = prompt_parts
        if isinstance(prompt_parts, list):
            text_only_prompt = " ".join(
                [p if isinstance(p, str) else "[Imagem]" for p in prompt_parts]
            )

        if not OLLAMA_AVAILABLE:
            return "🤯 *Meus sistemas falharam e o motor de emergência local não está instalado neste ambiente.*"

        # 2. TENTATIVA OLLAMA REMOTO
        if self.remote_url:
            try:
                client = AsyncClient(host=self.remote_url)
                messages = []
                if system_instruction:
                    messages.append(
                        {"role": "system", "content": str(system_instruction)}
                    )
                messages.append({"role": "user", "content": text_only_prompt})
                response = await client.chat(model=self.remote_model, messages=messages)
                return f"[☁️] {response['message']['content']}"
            except Exception as e:
                self.log.warning(f"⚠️ Falha Ollama Remoto: {e}")

        # 3. TENTATIVA OLLAMA LOCAL
        try:
            client = AsyncClient(host=self.local_url)
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": str(system_instruction)})
            messages.append({"role": "user", "content": text_only_prompt})
            response = await client.chat(model=self.local_model, messages=messages)
            return f"[📟] {response['message']['content']}"
        except Exception:
            return "🤯 *Meus sistemas de pensamento estão offline.*"

    async def generate_summary(self, text: str) -> str:
        """Helper para resumos rápidos no ciclo noturno."""
        return await self.generate_response(
            text,
            system_instruction="Você é um assistente técnico. Resuma o texto a seguir de forma extremamente concisa.",
        )

    async def get_embedding(self, text: str) -> list:
        """3. FAILOVER NA MEMÓRIA: Tenta Gemini primeiro, depois Ollama."""
        if not self.is_ready:
            await self.setup_providers()

        # Tentativa 1: Nuvem (Gemini)
        if GEMINI_AVAILABLE and self.keys:
            try:
                key = self.keys[self.current_key_index]
                genai.configure(api_key=key)
                # Executa a geração de vetor em thread separada para não travar
                result = await asyncio.to_thread(
                    genai.embed_content,
                    model=f"models/{self.embed_model_cloud}",
                    content=text,
                    task_type="retrieval_document",
                )
                return result["embedding"]
            except Exception as e:
                self.log.warning(
                    f"⚠️ Nuvem falhou ao gravar memória: {e}. Tentando HD local..."
                )

        # Tentativa 2: Local (Ollama)
        if OLLAMA_AVAILABLE:
            try:
                client = AsyncClient(host=self.local_url)
                res = await client.embeddings(model=self.embed_model_local, prompt=text)
                return res["embedding"]
            except Exception as e:
                self.log.error(f"❌ Erro crítico ao gravar memória local: {e}")

        return []


# Instância Singleton global
llm_factory = LLMFactory.get_instance()
