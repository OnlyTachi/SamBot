import os
from typing import List, Optional
from Brain.Providers.BaseLLM import BaseLLMProvider

try:
    from openai import AsyncOpenAI

    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False


class MistralDriver(BaseLLMProvider):

    def __init__(self, log_instance, generation_config: Optional[dict] = None):
        self.log = log_instance
        self.api_key = os.getenv("MISTRAL_API_KEY")
        self.model_name = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        self.base_url = "https://api.mistral.ai/v1"
        self.temperature = 0.7
        if generation_config and "temperature" in generation_config:
            self.temperature = generation_config["temperature"]

    async def initialize(self) -> bool:
        """Testa existência de credenciais da Mistral AI."""
        if not MISTRAL_AVAILABLE:
            self.log.warning(
                "  Biblioteca 'openai' não encontrada. Camada Mistral AI offline."
            )
            return False
        if not self.api_key:
            self.log.warning(
                "  Nenhuma chave MISTRAL_API_KEY encontrada no .env. Mistral desativado."
            )
            return False

        self.log.info(
            f"  [Mistral AI] Configurado com sucesso usando o modelo: {self.model_name}"
        )
        return True

    async def generate(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """Gera resposta com o motor da Mistral AI."""
        if not MISTRAL_AVAILABLE or not self.api_key:
            return None

        text_only_prompt = prompt_parts
        if isinstance(prompt_parts, list):
            text_only_prompt = " ".join(
                [p if isinstance(p, str) else "[Imagem omitida]" for p in prompt_parts]
            )

        try:
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

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
                f"  [Mistral AI] Falha na execução com o modelo {self.model_name}: {e}"
            )
        return None

    async def get_embedding(self, text: str) -> List[float]:
        """Gera embeddings utilizando o endpoint mistral-embed se necessário."""
        if not MISTRAL_AVAILABLE or not self.api_key:
            return []

        try:
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            res = await client.embeddings.create(
                model="mistral-embed",
                input=text,
            )
            return res.data[0].embedding
        except Exception as e:
            self.log.warning(
                f"  [Mistral AI] Falha ao gerar embedding com Mistral: {e}"
            )
            return []
