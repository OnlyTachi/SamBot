import os
from typing import List, Optional
from Brain.Providers.BaseLLM import BaseLLMProvider

try:
    from ollama import AsyncClient

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class OllamaDriver(BaseLLMProvider):
    """
    Driver específico para o Ollama.
    Suporta tanto servidores remotos quanto instâncias locais (como Docker),
    além de geração de embeddings locais para failover.
    """

    def __init__(self, log_instance):
        self.log = log_instance

        # Configurações do Ollama Remoto
        self.remote_url = os.getenv("OLLAMA_REMOTE_URL")
        self.remote_model = os.getenv("MODEL_SMART_REMOTE")

        # Configurações do Ollama Local
        self.local_url = os.getenv(
            "OLLAMA_LOCAL_URL", "http://host.docker.internal:11434"
        )
        self.local_model = os.getenv("MODEL_FAST_LOCAL", "qwen2.5:1.5b")

        # Configuração de Embedding Local
        self.embed_model_local = os.getenv("MODEL_EMBED_LOCAL", "nomic-embed-text")

    async def initialize(self) -> bool:
        """
        Verifica se a biblioteca está disponível e valida o acesso aos serviços configurados.
        Como o Ollama local/remoto pode oscilar, o driver reporta o status de cada um.
        """
        if not OLLAMA_AVAILABLE:
            self.log.warning(
                "⚠️ Biblioteca 'ollama' não encontrada. Fallbacks locais offline."
            )
            return False

        # Verifica o que está configurado
        if not self.remote_url and not self.local_url:
            self.log.error(
                "❌ Nenhuma URL (local ou remota) do Ollama foi definida no .env!"
            )
            return False

        if self.remote_url:
            self.log.info(
                f"📟 [Ollama] Configurado para usar Remoto: {self.remote_url} ({self.remote_model})"
            )

        self.log.info(
            f"📟 [Ollama] Configurado para usar Local: {self.local_url} ({self.local_model})"
        )
        return True

    async def generate(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """
        Gera a resposta usando o Ollama.
        Tenta primeiro o Ollama Remoto (se configurado) e faz failover automático para o Ollama Local.
        """
        if not OLLAMA_AVAILABLE:
            return None

        # Normaliza o prompt para texto puro (removendo formatos complexos ou imagens se houver)
        text_only_prompt = prompt_parts
        if isinstance(prompt_parts, list):
            text_only_prompt = " ".join(
                [p if isinstance(p, str) else "[Imagem omitida]" for p in prompt_parts]
            )

        # 1. TENTATIVA: OLLAMA REMOTO
        if self.remote_url and self.remote_model:
            try:
                client = AsyncClient(host=self.remote_url)
                messages = []
                if system_instruction:
                    messages.append(
                        {"role": "system", "content": str(system_instruction)}
                    )
                messages.append({"role": "user", "content": text_only_prompt})

                response = await client.chat(model=self.remote_model, messages=messages)
                return f"{response['message']['content']}"
            except Exception as e:
                self.log.warning(
                    f"⚠️ [Ollama] Falha ao conectar ao Ollama Remoto: {e}. Tentando Local..."
                )

        # 2. TENTATIVA: OLLAMA LOCAL
        try:
            client = AsyncClient(host=self.local_url)
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": str(system_instruction)})
            messages.append({"role": "user", "content": text_only_prompt})

            response = await client.chat(model=self.local_model, messages=messages)
            return f"{response['message']['content']}"
        except Exception as e:
            self.log.error(f"❌ [Ollama] Falha crítica no Ollama Local: {e}")

        return None

    async def get_embedding(self, text: str) -> List[float]:
        """
        Gera embeddings locais (geralmente usado como failover quando a nuvem do Gemini falha).
        """
        if not OLLAMA_AVAILABLE:
            return []

        try:
            client = AsyncClient(host=self.local_url)
            res = await client.embeddings(model=self.embed_model_local, prompt=text)
            return res["embedding"]
        except Exception as e:
            self.log.error(
                f"❌ [Ollama] Erro crítico ao gravar memória local (Embedding): {e}"
            )
            return []
