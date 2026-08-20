import os
import logging
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Core.NetworkManager import NetworkManager
from Core.ConfigLoader import AppConfig


class JellyfinTool:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.JellyfinTool")
        self.base_url = AppConfig.get("JELLYFIN_URL", "").rstrip("/")
        self.api_key = os.getenv("JELLYFIN_API_KEY")
        self.headers = {"X-Emby-Token": self.api_key, "Accept": "application/json"}
        self.is_configured = bool(self.base_url and self.api_key)
        self.cache_key = "jellyfin_catalog"

        if not self.is_configured:
            self.logger.warning(
                "JellyfinTool não configurado. Verifique JELLYFIN_URL e JELLYFIN_API_KEY no .env."
            )

    async def _fetch(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        session = NetworkManager.get_aio_session()
        try:
            async with session.get(
                url, headers=self.headers, params=params, timeout=15
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                self.logger.error(f"Erro na API do Jellyfin: Status {resp.status}")
        except Exception as e:
            self.logger.error(f"Falha de conexão com o Jellyfin: {e}")
        return {}

    async def sync_catalog(self):
        """Busca todo o catálogo da API e salva um mapa estruturado em JSON no DataManager."""
        if not self.is_configured:
            return False

        self.logger.info(" Sincronizando catálogo para o cache local...")
        catalog = {"filmes": [], "series": {}}

        params_movies = {
            "IncludeItemTypes": "Movie",
            "Recursive": "true",
            "Fields": "ProductionYear,Overview",
        }
        data_movies = await self._fetch("/Items", params=params_movies)

        if data_movies:
            for item in data_movies.get("Items", []):
                nome = item.get("Name", "Desconhecido")
                ano = item.get("ProductionYear", "")
                sinopse = item.get("Overview", "Sem sinopse.")[:100] + "..."
                titulo_final = f"{nome} ({ano})" if ano else nome
                catalog["filmes"].append({"titulo": titulo_final, "sinopse": sinopse})

        params_episodes = {
            "IncludeItemTypes": "Episode",
            "Recursive": "true",
            "Fields": "SeriesName,SeasonName",
        }
        data_episodes = await self._fetch("/Items", params=params_episodes)

        if data_episodes:
            for ep in data_episodes.get("Items", []):
                serie = ep.get("SeriesName")
                if not serie:
                    continue

                temporada = ep.get("SeasonName", "Especiais")

                if serie not in catalog["series"]:
                    catalog["series"][serie] = {}

                if temporada not in catalog["series"][serie]:
                    catalog["series"][serie][temporada] = 0

                catalog["series"][serie][temporada] += 1

        # 3. Salvar no Banco de Dados JSON (Data/Knowledge/jellyfin_catalog.json)
        data_manager.save_knowledge(self.cache_key, catalog)
        self.logger.info(" Cache atualizado e salvo com sucesso!")
        return True

    async def search_content(self, query: str) -> str:
        """Pesquisa instantânea usando o JSON local salvo no DataManager."""
        if not self.is_configured:
            return "Serviço Jellyfin não configurado."

        catalog = data_manager.get_knowledge(self.cache_key)

        if not catalog:
            self.logger.info("Cache não encontrado. Gerando no primeiro uso...")
            await self.sync_catalog()
            catalog = data_manager.get_knowledge(self.cache_key)
            if not catalog:
                return "Não foi possível acessar o catálogo do Jellyfin no momento."

        query_clean = (
            query.lower()
            .replace("filme", "")
            .replace("série", "")
            .replace("serie", "")
            .strip()
        )
        resultados = []

        # Busca em Filmes
        for filme in catalog.get("filmes", []):
            titulo = filme["titulo"].lower()
            if query_clean in titulo:
                resultados.append(
                    f"🎬 **{filme['titulo']}**\n  *Sinopse:* {filme['sinopse']}"
                )

        # Busca em Séries
        for serie_nome, temporadas in catalog.get("series", {}).items():
            if query_clean in serie_nome.lower():
                detalhes_temps = [
                    f"{temp} ({qtd} eps)" for temp, qtd in temporadas.items()
                ]
                resumo_serie = f"📺 **{serie_nome}**\n  *Estrutura:* " + ", ".join(
                    detalhes_temps
                )
                resultados.append(resumo_serie)

        if not resultados:
            return f"Não encontrei '{query}' salvo no servidor."

        report = f"🍿 **Resultados no servidor para '{query}':**\n\n"
        # Limita a 5 resultados para não estourar os tokens da Sam (pode aumentar caso use modelo maior)
        for res in resultados[:5]:
            report += f"{res}\n\n"

        return report.strip()
