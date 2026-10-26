# Services/ServiceManager.py
import asyncio
import logging
from Core.ConfigLoader import AppConfig

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
        self.bot.services = self

        # 1. Chave Seletora Geral
        self.master_enabled = self._is_enabled("services.enabled", default=True)

        if not self.master_enabled:
            self.logger.info(
                "Service Switch DESATIVADO (services.enabled: false). Nenhum serviço externo será inicializado."
            )
            self.api = None
            self.telegram = None
            self.notifier = None
            return

        # 2. Seletores individuais por serviço
        api_on = self._is_enabled("services.api", default=True)
        tg_on = self._is_enabled("services.telegram", default=False)
        notifier_on = self._is_enabled("services.notifier", default=False)

        self.api = self._init_service(APIServer, "APIServer") if api_on else None
        self.telegram = (
            self._init_service(TelegramScraper, "TelegramScraper") if tg_on else None
        )
        self.notifier = (
            self._init_service(PromoNotifier, "PromoNotifier") if notifier_on else None
        )

        self.logger.info(
            f"Status dos Seletores -> API: {'ON' if self.api else 'OFF'} | "
            f"Telegram: {'ON' if self.telegram else 'OFF'} | "
            f"Notifier: {'ON' if self.notifier else 'OFF'}"
        )

    def _is_enabled(self, key: str, default: bool = False) -> bool:
        """Lê booleanos do config.yaml de forma segura (trata strings e bools)."""
        val = AppConfig.get(key, default)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes", "on")

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
        if not self.master_enabled:
            return
        self.logger.info("Iniciando serviços autônomos habilitados...")
        await self._safe_start(self.api, "APIServer")
        await self._safe_start(self.telegram, "TelegramScraper")
        await self._safe_start(self.notifier, "PromoNotifier")

    async def stop_all(self):
        if not self.master_enabled:
            return
        self.logger.info("Encerrando serviços autônomos...")
        await self._safe_stop(self.notifier, "PromoNotifier")
        await self._safe_stop(self.telegram, "TelegramScraper")
        await self._safe_stop(self.api, "APIServer")

    async def restart_all(self):
        if not self.master_enabled:
            return
        self.logger.info("Reiniciando serviços autônomos...")
        await self.stop_all()
        await asyncio.sleep(1.0)  # Pequena pausa para liberar portas/sockets
        await self.start_all()
        self.logger.info("Serviços autônomos reiniciados com sucesso.")
