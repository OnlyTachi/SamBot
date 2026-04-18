# algum dia no futuro, talvez eu suporte múltiplos provedores LLM
# por enquanto, apenas Gemini com fallback para Ollama local/remoto
import os
import logging
import asyncio
import google.generativeai as genai
from ollama import AsyncClient
from google.api_core import exceptions as google_exceptions
from dotenv import load_dotenv

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
    Factory que gerencia a inteligência do SamBot.
    Implementa cascata de provedores: Gemini -> Ollama Remote -> Ollama Local.
    Suporta múltiplas chaves Gemini com rotação automática e diagnóstico inicial.
    Agora com suporte nativo a visão (multimodal) e instruções de sistema.
    """

    _instance = None

    def __init__(self):
        self.log = logger_instance

        # --- Configurações Gemini ---
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
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
        self.embed_model = os.getenv("MODEL_EMBED_LOCAL", "nomic-embed-text")

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

        if not self.keys:
            self.log.error("❌ Nenhuma chave API do Gemini encontrada no .env!")
        else:
            self._inicializar_melhor_chave()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _carregar_chaves(self):
        """Carrega chaves sequenciais (GEMINI_API_KEY_1...) ou a chave única padrão."""
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

    def _inicializar_melhor_chave(self):
        """Testa as chaves detectadas e configura o modelo com a primeira funcional."""
        self.log.info(
            f"🔑 {len(self.keys)} chaves detectadas. Iniciando diagnóstico..."
        )

        for index, key in enumerate(self.keys):
            if self._testar_chave(key, index + 1):
                genai.configure(api_key=key)
                self.active_model = self._criar_modelo()
                self.current_key_index = index
                self.log.info(f"✨ SamBot está conectado usando a Chave {index + 1}.")
                return

        self.log.critical(
            "⛔ Todas as chaves falharam nos testes. IA Gemini em modo OFFLINE."
        )

    def _testar_chave(self, key, index):
        """Valida a chave realizando uma chamada mínima de 1 token (Síncrono)."""
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(self.model_name)
            model.generate_content("ping", generation_config={"max_output_tokens": 1})
            return True
        except Exception as e:
            err = str(e)
            if "429" in err:
                self.log.warning(f"⚠️ Chave {index} está com Rate Limit (429).")
            else:
                self.log.warning(
                    f"⚠️ Chave {index} inválida ou erro de conexão: {err[:50]}..."
                )
            return False

    def _criar_modelo(self, system_instruction=None):
        """Instancia o modelo com configurações de segurança e instrução de sistema opcional."""
        return genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=self.safety_settings,
            generation_config=self.generation_config,
            system_instruction=system_instruction,
        )

    def get_model(self):
        """Retorna a instância ativa do GenerativeModel."""
        return self.active_model

    async def check_health(self=None):
        """Verifica se o subsistema de IA está saudável."""
        instance = self if isinstance(self, LLMFactory) else llm_factory
        if not instance or not instance.keys:
            return False

        if instance.active_model:
            return True

        for key in instance.keys:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(instance.model_name)
                await asyncio.to_thread(
                    model.generate_content,
                    "ping",
                    generation_config={"max_output_tokens": 1},
                )
                return True
            except Exception:
                continue
        return False

    def _get_next_key(self):
        """Rotaciona o índice para a próxima chave disponível."""
        if not self.keys:
            return None
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key

    async def _generate_gemini(self, system_instruction, prompt_parts) -> str:
        """Tenta gerar via Gemini com suporte multimodal e rotação de chaves."""
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
                self.log.warning(
                    f"🔄 Chave esgotada (429). Tentando próxima rotação..."
                )
                continue
            except Exception as e:
                self.log.error(f"⚠️ Erro no Gemini: {e}")
                continue
        return None

    async def generate_response(self, prompt_parts, system_instruction=None) -> str:
        """
        Cascata Principal: Gemini -> Ollama Remoto -> Ollama Local.

        Args:
            prompt_parts: String ou Lista [texto, imagem_dict, ...]
            system_instruction: Instrução de sistema (identidade do bot)
        """

        # 1. TENTATIVA GEMINI (Suporta Multimodal)
        res = await self._generate_gemini(system_instruction, prompt_parts)
        if res:
            return res

        # Fallbacks (Ollama geralmente não suporta as mesmas estruturas de imagem do SDK Google de forma direta)
        # Se for uma lista (multimodal), tentamos extrair apenas o texto para os fallbacks básicos
        text_only_prompt = prompt_parts
        if isinstance(prompt_parts, list):
            text_only_prompt = " ".join(
                [p if isinstance(p, str) else "[Imagem]" for p in prompt_parts]
            )

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

        # 3. TENTATIVA OLLAMA LOCAL (Fallback CPU)
        try:
            client = AsyncClient(host=self.local_url)
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": str(system_instruction)})
            messages.append({"role": "user", "content": text_only_prompt})

            response = await client.chat(model=self.local_model, messages=messages)
            return f"[📟] {response['message']['content']}"
        except Exception:
            return "🤯 *Meus sistemas de pensamento estão offline. Verifique minha conexão ou chaves de API.*"

    async def get_embedding(self, text: str) -> list:
        """Gera vetores para memória de longo prazo (ChromaDB)."""
        try:
            client = AsyncClient(host=self.local_url)
            res = await client.embeddings(model=self.embed_model, prompt=text)
            return res["embedding"]
        except Exception as e:
            self.log.error(f"❌ Erro ao gerar embedding: {e}")
            return []

    async def generate_summary(self, text: str) -> str:
        """Helper para resumos rápidos."""
        return await self.generate_response(
            text,
            system_instruction="Você é um assistente técnico. Resuma o texto a seguir de forma extremamente concisa.",
        )


# Instância Singleton global
llm_factory = LLMFactory.get_instance()

# Alias para compatibilidade
LLMFactory.get_provider = lambda self: llm_factory
