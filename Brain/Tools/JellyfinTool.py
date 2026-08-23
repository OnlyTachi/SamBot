import os
import logging
import unicodedata
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

    def _remover_acentos(self, texto: str) -> str:
        """Remove acentuação para casamento elástico de títulos."""
        nfkd = unicodedata.normalize("NFKD", texto)
        return (
            "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()
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
        """Busca todo o catálogo da API e salva em JSON no DataManager."""
        if not self.is_configured:
            return False

        self.logger.info("Sincronizando catálogo do Jellyfin para o cache local...")
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
                sinopse = item.get("Overview", "Sem sinopse.")[:120] + "..."
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

        data_manager.save_knowledge(self.cache_key, catalog)
        self.logger.info("Catálogo do Jellyfin salvo no Banco De Dados com sucesso!")
        return True

    async def search_content(self, query: str) -> str:
        """Pesquisa no catálogo usando correspondência estrita e flexível."""
        if not self.is_configured:
            return "Serviço Jellyfin não configurado."

        catalog = data_manager.get_knowledge(self.cache_key)
        if not catalog:
            await self.sync_catalog()
            catalog = data_manager.get_knowledge(self.cache_key)
            if not catalog:
                return "Não foi possível acessar o catálogo do Jellyfin no momento."

        query_normalizada = self._remover_acentos(query)

        # Filtra preposições soltas e palavras com menos de 3 caracteres
        termos_busca = [t for t in query_normalizada.split() if len(t) >= 3]
        if not termos_busca:
            termos_busca = [query_normalizada]

        resultados_filmes = []
        resultados_series = []

        # 1. Busca em Séries (Prioridade para termos de temporadas/séries)
        for serie_nome, temporadas in catalog.get("series", {}).items():
            serie_norm = self._remover_acentos(serie_nome)
            # Match da frase inteira OU de termos relevantes do nome da série
            if query_normalizada in serie_norm or any(
                termo in serie_norm for termo in termos_busca
            ):
                detalhes_temps = [
                    f"{temp} ({qtd} eps)" for temp, qtd in temporadas.items()
                ]
                resumo_serie = f"📺 **{serie_nome}**\n  *Estrutura:* " + ", ".join(
                    detalhes_temps
                )
                resultados_series.append(resumo_serie)

        # 2. Busca em Filmes
        for filme in catalog.get("filmes", []):
            titulo_norm = self._remover_acentos(filme["titulo"])
            if query_normalizada in titulo_norm or any(
                termo in titulo_norm for termo in termos_busca
            ):
                resultados_filmes.append(
                    f"🎬 **{filme['titulo']}**\n  *Sinopse:* {filme['sinopse']}"
                )

        resultados_finais = resultados_series + resultados_filmes

        if not resultados_finais:
            return f"Nenhum título correspondente a '{query}' foi encontrado no catálogo do servidor."

        report = f"**Resultados encontrados no Jellyfin:**\n\n"
        for res in resultados_finais[:5]:
            report += f"{res}\n\n"
        return report.strip()
