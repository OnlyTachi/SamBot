import os
import logging
from dotenv import load_dotenv

# Importação dos Clients e do Orquestrador
from Brain.Providers.Clients.GeminiProvider import GeminiDriver
from Brain.Providers.Clients.GroqProvider import GroqDriver
from Brain.Providers.Clients.OllamaProvider import OllamaDriver
from Brain.Providers.Clients.DeepSeekProvider import DeepSeekDriver
from Brain.Providers.Clients.OpenRouterProvider import OpenRouterDriver
from Brain.Providers.Clients.MistralProvider import MistralDriver
from Brain.Providers.LLMChainOrchestrator import LLMChainOrchestrator

# --- Configuração Segura de Logs ---
try:
    from Core.Logger import SamLogger as Logger

    logger_instance = Logger.get_logger("LLMFactory")
except ImportError:
    import logging

    logger_instance = logging.getLogger("SamBot.LLM")

load_dotenv()


class LLMFactory:
    def __init__(self):
        self.log = logger_instance
        self.available_drivers = {
            "gemini": GeminiDriver(self.log),
            "groq": GroqDriver(self.log),
            "ollama": OllamaDriver(self.log),
            "deepseek": DeepSeekDriver(self.log),
            "openrouter": OpenRouterDriver(self.log),
            "mistral": MistralDriver(self.log),
        }

    def _get_active_providers_from_env(self) -> list:
        raw_order = os.getenv("LLM_CHAIN_ORDER", "gemini,groq,ollama")
        provider_names = [p.strip().lower() for p in raw_order.split(",") if p.strip()]

        ordered_providers = []
        for name in provider_names:
            driver = self.available_drivers.get(name)
            if driver:
                ordered_providers.append(driver)

        return ordered_providers

    def get_default_principal_chain(self) -> LLMChainOrchestrator:
        providers = self._get_active_providers_from_env()
        return LLMChainOrchestrator(
            name="Principal", providers=providers, log_instance=self.log
        )


llm_factory = LLMFactory()
