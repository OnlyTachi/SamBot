import os
from typing import List, Optional
from Brain.Providers.BaseLLM import BaseLLMProvider
from Core.ConfigLoader import AppConfig

try:
    from openai import AsyncOpenAI

    OPENROUTER_AVAILABLE = True
except ImportError:
    OPENROUTER_AVAILABLE = False


class OpenRouterDriver(BaseLLMProvider):

    def __init__(self, log_instance, generation_config: Optional[dict] = None):
        self.log = log_instance
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model_name = os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
        )
        self.base_url = "https://openrouter.ai/api/v1"
        self.site_url = AppConfig.get(
            "OPENROUTER_SITE_URL", "https://github.com/SamBot"
        )
        self.app_name = AppConfig.get("OPENROUTER_APP_NAME", "SamBot")
        self.temperature = 0.7
        if generation_config and "temperature" in generation_config:
            self.temperature = generation_config["temperature"]

    async def initialize(self) -> bool:
        """Valida disponibilidade e credenciais do OpenRouter."""
        if not OPENROUTER_AVAILABLE:
            self.log.debug(
                "  Biblioteca 'openai' não encontrada. Camada OpenRouter offline."
            )
            return False
        if not self.api_key:
            self.log.debug(
                "  Nenhuma chave OPENROUTER_API_KEY no .env. Camada OpenRouter desativada."
            )
            return False
        self.log.info(
            f"  [OpenRouter] Configurado com sucesso para o modelo: {self.model_name}"
        )
        return True

    async def generate(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """Gera resposta através da API do OpenRouter."""
        if not OPENROUTER_AVAILABLE or not self.api_key:
            return None

        text_only_prompt = prompt_parts
        if isinstance(prompt_parts, list):
            text_only_prompt = " ".join(
                [p if isinstance(p, str) else "[Imagem omitida]" for p in prompt_parts]
            )

        try:
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name,
                },
            )

            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": str(system_instruction)})
            messages.append({"role": "user", "content": text_only_prompt})

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.log.warning(
                f"  [OpenRouter] Falha ao processar requisição no modelo {self.model_name}: {e}"
            )
        return None

    async def get_embedding(self, text: str) -> List[float]:
        """Embedding via OpenRouter (se suportado pelo modelo configurado)."""
        return []
