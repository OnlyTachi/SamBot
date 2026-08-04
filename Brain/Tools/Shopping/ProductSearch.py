import os
import json
import httpx
import logging
import urllib.parse
import html as html_module
from selectolax.parser import HTMLParser


class ProductSearchTool:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Shopping.ProductSearch")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.ml_api_url = "https://api.mercadolibre.com/sites/MLB/search"

    @staticmethod
    def _unwrap_astro_json(item):
        """Desembala a estrutura de arrays do Astro: [0, valor] -> valor"""
        if isinstance(item, list):
            if len(item) == 2 and item[0] in (0, 1):
                return ProductSearchTool._unwrap_astro_json(item[1])
            return [ProductSearchTool._unwrap_astro_json(x) for x in item]
        elif isinstance(item, dict):
            return {k: ProductSearchTool._unwrap_astro_json(v) for k, v in item.items()}
        return item

    async def _buscar_pelando(self, termo: str) -> str:
        """Faz o scraping do Pelando usando a lógica Astro + Selectolax."""
        encoded_termo = urllib.parse.quote(termo)
        url = f"https://www.pelando.com.br/busca/{encoded_termo}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.pelando.com.br",
            "Referer": "https://www.pelando.com.br/",
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers, timeout=8.0)
                if response.status_code != 200:
                    self.logger.warning(
                        f"Pelando retornou status {response.status_code}"
                    )
                    return ""

                parser = HTMLParser(response.text)
                island_tag = parser.css_first(
                    "astro-island[component-export='SearchFeedContent']"
                )
                if not island_tag:
                    return ""

                raw_props_json = html_module.unescape(
                    island_tag.attributes.get("props", "")
                )
                props = json.loads(raw_props_json)
                clean_props = self._unwrap_astro_json(props)
                initial_data = clean_props.get("initialData", {})
                deals_wrapper = initial_data.get("deals", [])
                deals_list = deals_wrapper[0].get("deals", []) if deals_wrapper else []

                if not deals_list:
                    return ""

                report = "**🏷️ Ofertas da Comunidade (Pelando):**\n"
                for deal in deals_list[:3]:
                    loja = deal.get("store", {}).get("name", "Desconhecida")
                    preco = deal.get("price", 0)
                    titulo = deal.get("title", "")
                    link = f"https://www.pelando.com.br/d/{deal.get('slug')}"
                    temperatura = deal.get("temperature", 0)
                    report += f"- {titulo} | **R$ {preco}** ({loja}) [🔥 {temperatura}°]\n  Link: {link}\n"

                return report + "\n"
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no Pelando: {e}")
            return ""

    async def _buscar_mercadolivre(self, termo: str) -> str:
        """Busca produtos oficiais via API do Mercado Livre."""
        params = {"q": termo, "limit": 3, "condition": "new"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.ml_api_url, params=params, timeout=5.0)
                if response.status_code != 200:
                    return ""

                data = response.json()
                results = data.get("results", [])

                if not results:
                    return ""

                report = "**📦 Resultados no Mercado Livre:**\n"
                for item in results:
                    titulo = item.get("title")
                    preco = item.get("price")
                    link = item.get("permalink")
                    frete = (
                        "🚚 Frete Grátis"
                        if item.get("shipping", {}).get("free_shipping")
                        else "📦 Frete Pago"
                    )

                    report += (
                        f"- {titulo} | **R$ {preco:.2f}** ({frete})\n  Link: {link}\n"
                    )

                return report + "\n"
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no ML: {e}")
            return ""

    async def _buscar_serpapi(self, termo: str) -> str:
        """Agrega preços do Google Shopping via SerpApi."""
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        if not self.serpapi_key:
            return ""

        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_shopping",
            "q": termo,
            "hl": "pt",
            "gl": "br",
            "api_key": self.serpapi_key,
            "num": 3,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=8.0)
                if response.status_code != 200:
                    return ""

                data = response.json()
                results = data.get("shopping_results", [])

                if not results:
                    return ""

                report = "**🛍️ Comparativo Google Shopping:**\n"
                for item in results[:3]:
                    titulo = item.get("title")
                    preco = item.get("price")
                    loja = item.get("source")
                    link = item.get("link")

                    report += (
                        f"- {titulo[:60]}... | **{preco}** ({loja})\n  Link: {link}\n"
                    )

                return report + "\n"
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no SerpApi: {e}")
            return ""

    async def search(self, termo: str) -> str:
        """
        Orquestrador: Dispara as buscas simultaneamente e compila o relatório.
        """
        self.logger.info(f"Buscando produtos para: {termo}")

        relatorio = f"🛒 **Relatório de Compras para: {termo}**\n\n"

        # O Pelando costuma ser a melhor fonte de desconto real, executamos primeiro
        pelando_res = await self._buscar_pelando(termo)
        if pelando_res:
            relatorio += pelando_res

        # O ML garante disponibilidade padrão
        ml_res = await self._buscar_mercadolivre(termo)
        if ml_res:
            relatorio += ml_res

        # SerpApi engloba Amazon, Kabum, Magalu (se configurado)
        serpapi_res = await self._buscar_serpapi(termo)
        if serpapi_res:
            relatorio += serpapi_res

        if relatorio.strip() == f"🛒 **Relatório de Compras para: {termo}**":
            return "Não encontrei boas ofertas ou produtos disponíveis para este termo no momento."

        return relatorio
