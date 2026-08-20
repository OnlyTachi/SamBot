import json
import logging
import os
import time
from typing import Any, Dict


class SystemInspector:
    """Coleta métricas e status operacional dos subsistemas da SamBot."""

    def __init__(self, bot=None, llm_factory=None, vector_store=None):
        self.bot = bot
        self.llm_factory = llm_factory
        self.vector_store = vector_store
        self.logger = logging.getLogger("SamBot.SystemInspector")
        self.stats_file = "logs/bot_stats.json"
        self.start_time = time.time()

    def _carregar_stats_file(self) -> dict:
        """Lê o snapshot consolidado gerado pelo loop do core principal."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.debug(f"Aviso ao ler bot_stats.json: {e}")
        return {}

    def get_system_snapshot(self) -> Dict[str, Any]:
        """Gera um resumo técnico em tempo real unindo bot_stats.json e o estado dos subsistemas."""
        file_stats = self._carregar_stats_file()

        # 1. Provedores Ativos na Cadeia de IA
        provedores_online = []
        if self.llm_factory:
            try:
                chain = self.llm_factory.get_default_principal_chain()
                provedores_online = [
                    p.__class__.__name__.replace("Driver", "")
                    for p in chain.active_providers
                ]
            except Exception:
                pass

        # 2. Contagem de Memórias Vetoriais no ChromaDB
        total_vetores = 0
        if self.vector_store and getattr(self.vector_store, "collections", None):
            try:
                for col in self.vector_store.collections.values():
                    total_vetores += col.count()
            except Exception:
                pass

        # 3. Uptime (Prioriza o formatado pelo core; senão calcula local)
        uptime_str = file_stats.get("uptime")
        if not uptime_str:
            uptime_seconds = int(time.time() - self.start_time)
            h, r = divmod(uptime_seconds, 3600)
            m, s = divmod(r, 60)
            uptime_str = f"{h:02d}:{m:02d}:{s:02d}"

        # 4. Latência do Discord
        latencia_str = "N/A"
        if self.bot and hasattr(self.bot, "latency"):
            latencia_str = f"{round(self.bot.latency * 1000)}ms"

        return {
            "uptime": uptime_str,
            "mensagens_lidas": file_stats.get("messages_read", 0),
            "comandos_executados": file_stats.get("commands_used", 0),
            "tempo_voz_minutos": file_stats.get("voice_time_minutes", 0),
            "servidores": file_stats.get(
                "servers", len(self.bot.guilds) if self.bot else 1
            ),
            "usuarios_alcancados": file_stats.get("users", 0),
            "provedores_ativos": (
                provedores_online if provedores_online else ["Nenhum / Offline"]
            ),
            "driver_primario": (
                provedores_online[0] if provedores_online else "Desconhecido"
            ),
            "total_memorias_rag": total_vetores,
            "latencia_discord": latencia_str,
        }
