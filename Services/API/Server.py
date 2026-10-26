# Services/API/Server.py
import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Set, Callable, Awaitable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import wavelink

from Core.ConfigLoader import AppConfig
from Modules.Audio.Lavalink._maestro import maestro

# Importações de Serviços de Negócio
from Services.API.Services.AudioService import AudioService

# Importações de Rotas
from Services.API.Routes.NotificationRoute import router as notification_router
from Services.API.Routes.ControlRoute import router as control_router
from Services.API.Routes.DatabasesRoute import router as db_router
from Services.API.Routes.FilesRoutes import router as files_router
from Services.API.Routes.LogsRoute import router as logs_router
from Services.API.Routes.DownloadRoute import router as download_router
from Services.API.Routes.AuthRoute import router as auth_discord_router

logger = logging.getLogger("SamBot.APIServer")


class GuildConnectionManager:
    """Gere ligações WebSocket segmentadas por Servidor (Guild ID)."""

    def __init__(self):
        self.active_rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.global_sockets: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.global_sockets.add(websocket)

    def bind_guild(self, websocket: WebSocket, guild_id: str):
        if not guild_id:
            return
        self.unbind(websocket)
        self.active_rooms[str(guild_id)].add(websocket)
        logger.info(f"WebSocket associado à guilda: {guild_id}")

    def unbind(self, websocket: WebSocket):
        for room in self.active_rooms.values():
            room.discard(websocket)

    def disconnect(self, websocket: WebSocket):
        self.global_sockets.discard(websocket)
        self.unbind(websocket)

    async def broadcast_to_guild(self, guild_id: str, message: dict):
        """Envia mensagem apenas para os navegadores a ouvir esta guilda."""
        target_sockets = list(self.active_rooms.get(str(guild_id), set()))
        if not target_sockets:
            return
        payload = json.dumps(message)
        for ws in target_sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                self.disconnect(ws)


class APIServer:
    def __init__(self, bot):
        self.bot = bot
        self.host = AppConfig.get("api.host")
        self.port = int(AppConfig.get("api.port"))
        self.app = FastAPI(title="SamBot Internal API", version="1.0.0")
        self.app.state.bot = bot
        self.manager = GuildConnectionManager()
        self.app.state.ws_manager = self.manager
        self.bot.ws_manager = self.manager

        allowed_origins = AppConfig.get("api.cors_origins", ["http://localhost:3000"])
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Registo das Rotas da Aplicação
        self.app.include_router(notification_router)
        self.app.include_router(control_router)
        self.app.include_router(db_router)
        self.app.include_router(files_router)
        self.app.include_router(logs_router)
        self.app.include_router(download_router)
        self.app.include_router(auth_discord_router)

        self._server = None
        self._serve_task = None

        # Despachador de Ações delegado para o AudioService
        self._action_handlers: Dict[
            str, Callable[[wavelink.Player, dict, str], Awaitable[None]]
        ] = {
            "PLAY": lambda vc, p, u: AudioService.play(
                self.bot, vc, p.get("trackId"), u, p.get("bitRate")
            ),
            "ENQUEUE": lambda vc, p, u: AudioService.enqueue(
                self.bot, vc, p.get("trackId"), u
            ),
            "PAUSE": lambda vc, p, u: AudioService.pause(self.bot, vc),
            "RESUME": lambda vc, p, u: AudioService.resume(self.bot, vc),
            "SKIP": lambda vc, p, u: AudioService.skip(vc),
            "SEEK": lambda vc, p, u: AudioService.seek(
                self.bot, vc, p.get("position", 0)
            ),
            "SET_VOLUME": lambda vc, p, u: AudioService.set_volume(
                self.bot, vc, int(p.get("volume", 80))
            ),
            "SET_LOOP": lambda vc, p, u: AudioService.set_loop(
                self.bot, vc, p.get("mode", "OFF")
            ),
            "SHUFFLE": lambda vc, p, u: AudioService.shuffle(self.bot, vc),
            "CLEAR_QUEUE": self._handle_clear_queue,
            "REMOVE_QUEUE": self._handle_remove_queue,
            "REORDER_QUEUE": self._handle_reorder_queue,
        }

        @self.app.websocket("/ws/bot")
        async def bot_websocket_endpoint(websocket: WebSocket):
            await self.manager.connect(websocket)
            logger.info("Cliente WebUI conectado ao WebSocket do Bot.")
            try:
                while True:
                    data_raw = await websocket.receive_text()
                    msg = json.loads(data_raw)
                    op = msg.get("op")

                    if op == "HANDSHAKE":
                        guild_id = msg.get("guildId")
                        if guild_id:
                            self.manager.bind_guild(websocket, str(guild_id))
                        await websocket.send_json(
                            {
                                "op": "ACK",
                                "status": "AUTHENTICATED",
                                "guildId": guild_id,
                                "version": getattr(self.bot, "version", "3.3.1-beta"),
                            }
                        )
                        if guild_id and self.bot.voice_clients:
                            for vc in self.bot.voice_clients:
                                if hasattr(vc, "guild") and str(vc.guild.id) == str(
                                    guild_id
                                ):
                                    await maestro.sync_player_state(self.bot, vc)
                                    break

                    elif op == "SUBSCRIBE_GUILD":
                        guild_id = msg.get("guildId")
                        if guild_id:
                            self.manager.bind_guild(websocket, str(guild_id))
                            await websocket.send_json(
                                {
                                    "op": "ACK",
                                    "event": "SUBSCRIBED",
                                    "guildId": guild_id,
                                }
                            )
                        for vc in self.bot.voice_clients:
                            if hasattr(vc, "guild") and str(vc.guild.id) == str(
                                guild_id
                            ):
                                await maestro.sync_player_state(self.bot, vc)
                                break

                    elif op == "COMMAND":
                        cmd_data = msg.get("data", {})
                        action = cmd_data.get("action", "").upper()
                        payload = cmd_data.get("payload", {})
                        user_id = cmd_data.get("userId")
                        guild_id = cmd_data.get("guildId")
                        logger.info(
                            f"Comando recebido via WS: {action} | Payload: {payload}"
                        )

                        target_vc = None
                        if guild_id:
                            for vc in self.bot.voice_clients:
                                if hasattr(vc, "guild") and str(vc.guild.id) == str(
                                    guild_id
                                ):
                                    target_vc = vc
                                    break
                        elif self.bot.voice_clients:
                            target_vc = self.bot.voice_clients[0]

                        # Se for PLAY e o bot não estiver na chamada, efetua conexão automática
                        if action == "PLAY" and (
                            not target_vc or not target_vc.channel
                        ):
                            user_member = None
                            if user_id and str(user_id).isdigit():
                                for g in self.bot.guilds:
                                    if guild_id and str(g.id) != str(guild_id):
                                        continue
                                    m = g.get_member(int(user_id))
                                    if m and m.voice and m.voice.channel:
                                        user_member = m
                                        break

                            if (
                                user_member
                                and user_member.voice
                                and user_member.voice.channel
                            ):
                                try:
                                    target_vc = await user_member.voice.channel.connect(
                                        cls=wavelink.Player, self_deaf=True
                                    )
                                    logger.info(
                                        f"SamBot conectou-se a '{user_member.voice.channel.name}' via PLAY."
                                    )
                                except Exception as e:
                                    logger.error(f"Erro ao conectar SamBot: {e}")
                                    await websocket.send_json(
                                        {
                                            "op": "ERROR",
                                            "message": f"Falha ao conectar no canal de voz: {e}",
                                            "traceId": msg.get("traceId"),
                                        }
                                    )
                                    continue
                            else:
                                await websocket.send_json(
                                    {
                                        "op": "ERROR",
                                        "message": "Precisa de estar num canal de voz para iniciar a música.",
                                        "traceId": msg.get("traceId"),
                                    }
                                )
                                continue

                        if not target_vc or not target_vc.channel:
                            await websocket.send_json(
                                {
                                    "op": "ERROR",
                                    "message": "Bot não está em nenhum canal de voz.",
                                    "traceId": msg.get("traceId"),
                                }
                            )
                            continue

                        # Validação Anti-Ghost DJ
                        membro_na_call = False
                        if user_id and str(user_id).isdigit():
                            guild = target_vc.guild
                            member = guild.get_member(int(user_id))
                            if not member:
                                try:
                                    member = await guild.fetch_member(int(user_id))
                                except Exception:
                                    member = None
                            if member and member.voice and member.voice.channel:
                                membro_na_call = (
                                    member.voice.channel.id == target_vc.channel.id
                                )
                            else:
                                membro_na_call = any(
                                    str(m.id) == str(user_id)
                                    for m in target_vc.channel.members
                                )

                        if not membro_na_call and user_id != "usr_guest":
                            await websocket.send_json(
                                {
                                    "op": "ERROR",
                                    "message": "Acesso negado: Precisa de estar na mesma sala de voz",
                                    "traceId": msg.get("traceId"),
                                }
                            )
                            continue

                        handler = self._action_handlers.get(action)
                        if not handler:
                            await websocket.send_json(
                                {
                                    "op": "ERROR",
                                    "message": f"Ação '{action}' não suportada",
                                    "traceId": msg.get("traceId"),
                                }
                            )
                            continue

                        try:
                            await handler(target_vc, payload, str(user_id))
                            await websocket.send_json(
                                {"op": "ACK", "traceId": msg.get("traceId")}
                            )
                        except Exception as e:
                            logger.error(f"Erro ao executar ação do player: {e}")
                            await websocket.send_json(
                                {
                                    "op": "ERROR",
                                    "message": str(e),
                                    "traceId": msg.get("traceId"),
                                }
                            )

            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
                logger.info("Cliente WebUI desconectado do WebSocket.")
            except Exception as e:
                self.manager.disconnect(websocket)
                logger.error(f"Erro no WebSocket do Bot: {e}")

    # Handlers residuais específicos de manipulação de coleção interna da fila
    async def _handle_clear_queue(
        self, vc: wavelink.Player, payload: dict, user_id: str
    ):
        vc.queue.clear()
        await maestro.sync_player_state(self.bot, vc)

    async def _handle_remove_queue(
        self, vc: wavelink.Player, payload: dict, user_id: str
    ):
        queue_id = payload.get("queueId")
        idx_target = str(payload.get("index"))
        for idx, item in enumerate(vc.queue):
            if getattr(item, "queue_id", None) == queue_id or str(idx) == idx_target:
                del vc.queue[idx]
                break
        await maestro.sync_player_state(self.bot, vc)

    async def _handle_reorder_queue(
        self, vc: wavelink.Player, payload: dict, user_id: str
    ):
        from_idx = int(payload.get("from", -1))
        to_idx = int(payload.get("to", -1))
        q_len = len(vc.queue)
        if 0 <= from_idx < q_len and 0 <= to_idx < q_len:
            q_list = list(vc.queue)
            item = q_list.pop(from_idx)
            q_list.insert(to_idx, item)
            vc.queue.clear()
            for t in q_list:
                vc.queue.put(t)
            await maestro.sync_player_state(self.bot, vc)

    async def start(self):
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio",
        )
        self._server = uvicorn.Server(config)
        self._serve_task = asyncio.create_task(self._server.serve())
        logger.info(f"API da SamBot a correr em http://{self.host}:{self.port}")

    async def stop(self):
        if self._server:
            self._server.should_exit = True
            if self._serve_task:
                await self._serve_task
            logger.info("Servidor API finalizado com sucesso.")
