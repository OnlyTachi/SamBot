# Brain/Tools/Games/IGDB.py
import os
import time
import logging
from Brain.Core.NetworkManager import NetworkManager
from Brain.Memory.DataManager.Connections import data_manager


class IGDBService:
    """
    Serviço de busca de informações de jogos via API IGDB (Twitch).
    Gerencia automaticamente a geração e persistência do token OAuth2 no SQLite.
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.IGDB")
        self.client_id = os.getenv("IGDB_CLIENT_ID") or os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("IGDB_CLIENT_SECRET") or os.getenv(
            "TWITCH_CLIENT_SECRET"
        )
        self.base_url = "https://api.igdb.com/v4"

        self.access_token = None
        self.token_expires = 0
        self.cache_key = "igdb_token"

        self.is_configured = bool(self.client_id and self.client_secret)
        if not self.is_configured:
            self.logger.warning(
                "  IGDB não configurado. Verifique TWITCH_CLIENT_ID e SECRET no .env."
            )

    def _load_token_from_db(self) -> bool:
        """Carrega o token salvo no SQLite via DataManager."""
        try:
            data = data_manager.get_knowledge(self.cache_key) or {}
            expires_at = data.get("expires_at", 0)
            if expires_at > time.time() + 60:
                self.access_token = data.get("access_token")
                self.token_expires = expires_at
                return True
        except Exception as e:
            self.logger.error(f"Erro ao ler token do banco de dados: {e}")
        return False

    def _save_token_to_db(self, token: str, expires_in: int):
        """Salva o token e a expiração no SQLite via DataManager."""
        try:
            expires_at = time.time() + expires_in
            data = {"access_token": token, "expires_at": expires_at}
            data_manager.save_knowledge(self.cache_key, data)
            self.access_token = token
            self.token_expires = expires_at
        except Exception as e:
            self.logger.error(f"Erro ao salvar token no banco de dados: {e}")

    async def _authenticate(self):
        """Gera um novo token via OAuth2 da Twitch se necessário."""
        if not self.is_configured:
            return None
        if self.access_token and time.time() < self.token_expires:
            return self.access_token

        if self._load_token_from_db():
            return self.access_token

        self.logger.info("  Solicitando novo token de acesso IGDB...")
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        session = NetworkManager.get_aio_session()

        try:
            async with session.post(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    token = data["access_token"]
                    self._save_token_to_db(token, data["expires_in"])
                    return token
                else:
                    self.logger.error(
                        f"Falha na autenticação Twitch: Status {resp.status}"
                    )
        except Exception as e:
            self.logger.error(f"Erro crítico na conexão com Twitch OAuth: {e}")

        return None

    async def get_game_info(self, game_name: str) -> str:
        """Busca informações de um jogo e retorna formatado para a IA."""
        if not self.is_configured:
            return "IGDB_NOT_CONFIGURED"

        token = await self._authenticate()
        if not token:
            return "Erro ao autenticar no serviço de games."

        headers = {"Client-ID": self.client_id, "Authorization": f"Bearer {token}"}

        body = (
            f'search "{game_name}"; '
            f"fields name, summary, rating, platforms.name, first_release_date; "
            f"limit 1;"
        )
        session = NetworkManager.get_aio_session()

        try:
            async with session.post(
                f"{self.base_url}/games", headers=headers, data=body
            ) as resp:
                if resp.status == 401:
                    self.access_token = None
                    return await self.get_game_info(game_name)
                if resp.status == 200:
                    data = await resp.json()
                    if not data:
                        return f"Não encontrei informações sobre o jogo '{game_name}' no banco de dados."

                    game = data[0]
                    rating = int(game.get("rating", 0))
                    platforms = ", ".join(
                        [p["name"] for p in game.get("platforms", [])]
                    )

                    info = (
                        f"  Jogo: {game.get('name')}\n"
                        f"  Avaliação: {rating}/100\n"
                        f"  Plataformas: {platforms if platforms else 'Não listadas'}\n"
                        f"  Resumo: {game.get('summary', 'Sem resumo disponível.')[:500]}..."
                    )
                    return info
        except Exception as e:
            self.logger.error(f"Erro ao buscar jogo no IGDB: {e}")
            return "Ocorreu um erro ao consultar o banco de dados de jogos."

        return None
