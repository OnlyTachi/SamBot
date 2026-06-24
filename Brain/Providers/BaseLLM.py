import abc
from typing import List, Optional


class BaseLLMProvider(abc.ABC):
    """Interface abstrata obrigatória para todas as IA."""

    @abc.abstractmethod
    async def initialize(self) -> bool:
        """Testa a conectividade e chaves do provedor."""
        pass

    @abc.abstractmethod
    async def generate(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """Gera resposta de texto a partir do prompt."""
        pass

    @abc.abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Gera vetores de busca (embeddings)."""
        pass
