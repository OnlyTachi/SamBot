import aiohttp
import httpx


class NetworkManager:
    """
    Singleton para gerenciar sessões HTTP globais do bot.
    Reaproveita conexões para ativar o Keep-Alive e reduzir latência (Connection Pooling).
    """

    _aio_session = None
    _httpx_client = None

    @classmethod
    def get_aio_session(cls) -> aiohttp.ClientSession:
        if cls._aio_session is None or cls._aio_session.closed:
            # Configura um connector otimizado para lidar com múltiplas requisições simultâneas
            connector = aiohttp.TCPConnector(limit=100, keepalive_timeout=60)
            cls._aio_session = aiohttp.ClientSession(connector=connector)
        return cls._aio_session

    @classmethod
    def get_httpx_client(cls) -> httpx.AsyncClient:
        if cls._httpx_client is None or cls._httpx_client.is_closed:
            cls._httpx_client = httpx.AsyncClient(follow_redirects=True, timeout=10.0)
        return cls._httpx_client

    @classmethod
    async def close_all(cls):
        """Deve ser chamado no desligamento (shutdown) do bot."""
        if cls._aio_session and not cls._aio_session.closed:
            await cls._aio_session.close()
        if cls._httpx_client and not cls._httpx_client.is_closed:
            await cls._httpx_client.aclose()
