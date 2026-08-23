# Services/ServiceManager.py
import logging

logger = logging.getLogger("SamBot.Services")

try:
    from Services.Telegram.TelegramIngestor import TelegramScraper
except Exception as e:
    TelegramScraper = None
    logger.warning(f"Módulo TelegramScraper não pôde ser importado: {e}")

try:
    from Services.Notifications.PromoNotifier import PromoNotifier
except Exception as e:
    PromoNotifier = None
    logger.warning(f"Módulo PromoNotifier não pôde ser importado: {e}")

try:
    from Services.API.Server import APIServer
except Exception as e:
    APIServer = None
    logger.warning(f"Módulo APIServer não pôde ser importado: {e}")


class ServiceManager:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.telegram = self._init_service(TelegramScraper, "TelegramScraper")
        self.notifier = self._init_service(PromoNotifier, "PromoNotifier")
        self.api = self._init_service(APIServer, "APIServer")

    def _init_service(self, service_cls, name: str):
        if service_cls is None:
            return None
        try:
            return service_cls(self.bot)
        except Exception as e:
            self.logger.warning(f"Não foi possível instanciar {name}: {e}")
            return None

    async def _safe_start(self, service, name: str):
        if not service:
            self.logger.warning(f"Pulando inicialização do {name} (não configurado).")
            return
        try:
            await service.start()
            self.logger.info(f"{name} iniciado com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao iniciar {name}: {e}", exc_info=True)

    async def _safe_stop(self, service, name: str):
        if not service:
            return
        try:
            await service.stop()
            self.logger.info(f"{name} encerrado com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao encerrar {name}: {e}", exc_info=True)

    async def start_all(self):
        self.logger.info("Inicializando serviços autônomos...")
        await self._safe_start(self.api, "APIServer")
        await self._safe_start(self.telegram, "TelegramScraper")
        await self._safe_start(self.notifier, "PromoNotifier")

    async def stop_all(self):
        self.logger.info("Encerrando serviços autônomos...")
        await self._safe_stop(self.notifier, "PromoNotifier")
        await self._safe_stop(self.telegram, "TelegramScraper")
        await self._safe_stop(self.api, "APIServer")
