import os
import logging
from dotenv import load_dotenv

# Importação dos Clients e do Orquestrador
from Brain.Providers.LLMChainOrchestrator import LLMChainOrchestrator
from Brain.Providers.Clients.GeminiProvider import GeminiDriver
from Brain.Providers.Clients.GroqProvider import GroqDriver
from Brain.Providers.Clients.OllamaProvider import OllamaDriver

# --- Configuração Segura de Logs ---
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
    Fábrica inteligente da SamBot.
    Centraliza a criação de instâncias isoladas ou cadeias (combos) de IA.
    """

    _instance = None

    def __init__(self):
        self.log = logger_instance
        self.gemini_driver = GeminiDriver(self.log)
        self.groq_driver = GroqDriver(self.log)
        self.ollama_driver = OllamaDriver(self.log)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_chain(self, name: str, provider_types: list) -> LLMChainOrchestrator:
        """
        Gera uma cadeia customizada baseada em uma lista de strings.
        Ex: factory.create_chain("MinhaCadeia", ["gemini", "groq"])
        """
        selected_providers = []

        for p_type in provider_types:
            p_type_lower = p_type.lower()
            if p_type_lower == "gemini":
                selected_providers.append(self.gemini_driver)
            elif p_type_lower == "groq":
                selected_providers.append(self.groq_driver)
            elif p_type_lower == "ollama":
                selected_providers.append(self.ollama_driver)

        return LLMChainOrchestrator(
            name=name, providers=selected_providers, log_instance=self.log
        )

    def get_default_principal_chain(self) -> LLMChainOrchestrator:
        """Retorna a cadeia padrão (Camada 1 -> 1.5 -> 2 -> 3) da SamBot."""
        return LLMChainOrchestrator(
            name="Principal",
            providers=[self.gemini_driver, self.groq_driver, self.ollama_driver],
            log_instance=self.log,
        )

    def get_default_auxiliary_chain(self) -> LLMChainOrchestrator:
        """Retorna uma cadeia mais barata/rápida para tarefas secundárias (ignora o Gemini)."""
        return LLMChainOrchestrator(
            name="Auxiliar",
            providers=[self.groq_driver, self.ollama_driver],
            log_instance=self.log,
        )


llm_factory = LLMFactory.get_instance()
