import os
from typing import List, Optional
from Brain.Providers.BaseLLM import BaseLLMProvider
from Core.ConfigLoader import AppConfig

try:
    from openai import AsyncOpenAI

    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False


class DeepSeekDriver(BaseLLMProvider):

    def __init__(self, log_instance, generation_config: Optional[dict] = None):
        self.log = log_instance
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.model_name = AppConfig.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.base_url = AppConfig.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.temperature = 0.7
        if generation_config and "temperature" in generation_config:
            self.temperature = generation_config["temperature"]

    async def initialize(self) -> bool:
        """Verifica se a biblioteca 'openai' está disponível e se a chave foi configurada."""
        if not DEEPSEEK_AVAILABLE:
            self.log.debug(
                "  Biblioteca 'openai' não encontrada. Camada DeepSeek offline."
            )
            return False
        if not self.api_key:
            self.log.debug(
                "  Nenhuma chave API da DeepSeek encontrada no .env. Camada DeepSeek desativada."
            )
            return False
        self.log.info(
            f"  [DeepSeek] Configurado com sucesso usando o modelo: {self.model_name}"
        )
        return True

    async def generate(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """Gera resposta utilizando a API da DeepSeek."""
        if not DEEPSEEK_AVAILABLE or not self.api_key:
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
                f"  [DeepSeek] Falha na execução do modelo {self.model_name}: {e}"
            )
        return None

    async def get_embedding(self, text: str) -> List[float]:
        """A DeepSeek atualmente foca em raciocínio/chat. Retorna lista vazia."""
        return []
