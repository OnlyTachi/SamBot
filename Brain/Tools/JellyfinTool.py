# Brain/Tools/JellyfinTool.py
import aiohttp
import os
import random
import logging


class JellyfinTool:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.JellyfinTool")
        self.base_url = os.getenv("JELLYFIN_URL", "").rstrip("/")
        self.api_key = os.getenv("JELLYFIN_API_KEY")
        self.headers = {"X-Emby-Token": self.api_key, "Accept": "application/json"}
        self.is_configured = bool(self.base_url and self.api_key)

        if not self.is_configured:
            self.logger.warning(
                "JellyfinTool não configurado. Verifique JELLYFIN_URL e JELLYFIN_API_KEY no .env."
            )

    async def _fetch(self, endpoint: str, params: dict = None) -> list:
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=self.headers, params=params, timeout=10
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    self.logger.error(f"Erro na API do Jellyfin: Status {resp.status}")
        except Exception as e:
            self.logger.error(f"Falha de conexão com o Jellyfin: {e}")
        return []

    async def search_content(self, query: str) -> str:
        """Busca filmes ou séries correspondentes ao termo digitado pelo usuário com busca elástica."""
        if not self.is_configured:
            return "Serviço Jellyfin não configurado."

        query_clean = (
            query.lower()
            .replace("filme", "")
            .replace("série", "")
            .replace("serie", "")
            .strip()
        )

        params = {
            "IncludeItemTypes": "Movie,Series",
            "Recursive": "true",
            "Fields": "Overview,ProductionYear",  # Puxa o ano junto
        }

        data = await self._fetch("/Items", params=params)
        items = data.get("Items", []) if isinstance(data, dict) else []

        if not items:
            return f"Não encontrei nenhum filme ou série no catálogo do Jellyfin."

        resultados_filtrados = []
        for item in items:
            name_lower = item.get("Name", "").lower()
            original_title_lower = item.get(
                "OriginalTitle", ""
            ).lower()  # Garante busca se o nome estiver em inglês

            if query_clean in name_lower or name_lower in query_clean:
                resultados_filtrados.append(item)
            elif len(query_clean) >= 3 and (
                query_clean[:-1] in name_lower or name_lower in query_clean[:-1]
            ):
                resultados_filtrados.append(item)

        if not resultados_filtrados:
            return (
                f"Não encontrei nenhum filme ou série com o nome '{query}' no Jellyfin."
            )

        report = f"  **Resultados encontrados no Jellyfin para: {query}**\n"
        for item in resultados_filtrados[:3]:  # Limita aos 3 primeiros resultados
            tipo = "Filme" if item.get("Type") == "Movie" else "Série"
            ano = (
                f" ({item.get('ProductionYear')})" if item.get("ProductionYear") else ""
            )
            sinopse = item.get("Overview", "Sem sinopse disponível.")
            if len(sinopse) > 200:
                sinopse = sinopse[:200] + "..."
            report += (
                f"- **{item.get('Name')}{ano}** [{tipo}]\n  *Sinopse:* {sinopse}\n"
            )

        return report

    async def recommend_trends(self, args: str = "") -> str:
        """Recomenda itens aleatórios ou recentemente adicionados."""
        if not self.is_configured:
            return "Serviço Jellyfin não configurado."

        params = {
            "IncludeItemTypes": "Movie,Series",
            "Recursive": "true",
            "SortBy": "DateCreated",
            "SortOrder": "Descending",
            "Limit": "20",
        }

        data = await self._fetch("/Items", params=params)
        items = data.get("Items", []) if isinstance(data, dict) else []

        if not items:
            return "Não há conteúdo disponível no momento para recomendar."

        sampled = random.sample(items, min(3, len(items)))

        report = "🎬 **Sugestões de Conteúdo no Jellyfin:**\nAqui estão algumas novidades do servidor que você pode gostar:\n"
        for item in sampled:
            tipo = "Filme" if item.get("Type") == "Movie" else "Série"
            ano = (
                f" ({item.get('ProductionYear')})" if item.get("ProductionYear") else ""
            )
            report += f"- 🍿 **{item.get('Name')}{ano}** ({tipo})\n"
        return report
