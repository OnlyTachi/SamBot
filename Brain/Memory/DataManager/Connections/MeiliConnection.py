import aiohttp
import os
import logging

from Brain.Core.NetworkManager import NetworkManager
from Core.ConfigLoader import AppConfig


class MeiliConnection:
    """
    Gerenciador dedicado para o Meilisearch.
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Meilisearch")
        self.host = AppConfig.get("MEILI_HOST", "http://127.0.0.1:7700")
        self.api_key = AppConfig.get("MEILI_MASTER_KEY", "sua_chave_master_aqui")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def setup_index(self):
        """Cria o índice de ofertas e configura as regras de filtro e ordenação."""
        url_index = f"{self.host}/indexes/ofertas"
        session = NetworkManager.get_aio_session()

        try:
            async with session.post(
                f"{self.host}/indexes",
                headers=self.headers,
                json={"uid": "ofertas", "primaryKey": "id"},
            ) as resp_idx:
                if resp_idx.status not in [200, 201, 202]:
                    self.logger.warning(
                        f"Aviso ao criar índice: {await resp_idx.text()}"
                    )

            # Configura atributos filtráveis e ordenáveis
            settings = {
                "filterableAttributes": ["expira_em", "ativo", "loja", "preco"],
                "sortableAttributes": ["preco", "coletado_em"],
            }
            async with session.patch(
                f"{url_index}/settings", headers=self.headers, json=settings
            ) as resp:
                if resp.status in [200, 202]:
                    self.logger.info("Índice 'ofertas' configurado com sucesso.")
                else:
                    self.logger.error(f"Erro ao configurar índice: {await resp.text()}")
        except (aiohttp.ClientError, Exception) as e:
            self.logger.error(f"Falha ao configurar índice: {e}")

    async def execute_request(self, method: str, endpoint: str, payload: dict = None):
        """Método base para chamadas REST."""
        url = f"{self.host}{endpoint}"
        session = NetworkManager.get_aio_session()

        req_kwargs = {"headers": self.headers}
        if method.upper() == "GET":
            req_kwargs["params"] = payload
        else:
            req_kwargs["json"] = payload

        try:
            async with session.request(method.upper(), url, **req_kwargs) as resp:
                if resp.status in [200, 201, 202]:
                    return await resp.json()
                return None
        except (aiohttp.ClientError, Exception) as e:
            self.logger.error(
                f"Erro na comunicação com Meilisearch ({method} {endpoint}): {e}"
            )
            return None
