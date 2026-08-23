# Services/API/Server.py
import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Core.ConfigLoader import AppConfig

# Importação das Rotas
from Services.API.NotificationRoute import router as notification_router

# As próximas rotas que adicionaremos:
from Services.API.Routes.ControlRoute import router as control_router
from Services.API.Routes.DatabasesRoute import router as db_router
from Services.API.Routes.FilesRoutes import router as files_router
from Services.API.Routes.LogsRoute import router as logs_router

logger = logging.getLogger("SamBot.APIServer")


class APIServer:
    def __init__(self, bot):
        self.bot = bot
        self.host = AppConfig.get("API_HOST", "0.0.0.0")
        self.port = int(AppConfig.get("API_PORT", 8080))
        self.app = FastAPI(title="SamBot Internal Agent API", version="1.0.0")

        self.app.state.bot = bot

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Registro das Rotas
        self.app.include_router(notification_router)
        self.app.include_router(control_router)
        self.app.include_router(db_router)
        self.app.include_router(files_router)
        self.app.include_router(logs_router)

        self._server = None
        self._serve_task = None

    async def start(self):
        """Inicializa o Uvicorn sem bloquear a thread principal."""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio",
        )
        self._server = uvicorn.Server(config)
        self._serve_task = asyncio.create_task(self._server.serve())
        logger.info(f"🚀 API da SamBot rodando em http://{self.host}:{self.port}")

    async def stop(self):
        """Finaliza o servidor de forma graciosa."""
        if self._server:
            self._server.should_exit = True
            if self._serve_task:
                await self._serve_task
            logger.info("🛑 Servidor da API finalizado.")
