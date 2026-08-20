import asyncio
import os
import json
import httpx
import logging
import urllib.parse
import time
import uuid
import re
import html as html_module
from selectolax.parser import HTMLParser
from Brain.Core.NetworkManager import NetworkManager
from Brain.Memory.DataManager.Connections import data_manager


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

    def _limpar_preco(self, preco_raw) -> float:
        """Garante que o preço seja formatado como float para ordenação no Meilisearch."""
        if isinstance(preco_raw, (int, float)):
            return float(preco_raw)
        try:
            # Converte "R$ 1.500,99" -> 1500.99
            limpo = re.sub(r"[^\d,]", "", str(preco_raw)).replace(",", ".")
            return float(limpo)
        except Exception:
            return 0.0

    def _formatar_relatorio(self, ofertas: list, termo: str, origem: str) -> str:
        """Gera o texto final formatado para a leitura do LLM."""
        report = f"  **Relatório de Compras para: {termo}** *(Fonte: {origem})*\n\n"
        for off in ofertas:
            report += f"- {off['titulo']} | **R$ {off['preco']:.2f}** ({off['loja']})\n  Link: {off['link']}\n"
        return report

    async def _buscar_pelando(self, termo: str) -> list:
        """Faz o scraping do Pelando e retorna lista de objetos estruturados."""
        encoded_termo = urllib.parse.quote(termo)
        url = f"https://www.pelando.com.br/busca/{encoded_termo}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.pelando.com.br",
            "Referer": "https://www.pelando.com.br/",
            "Upgrade-Insecure-Requests": "1",
        }

        ofertas = []
        client = NetworkManager.get_httpx_client()
        try:
            response = await client.get(url, headers=headers, timeout=8.0)
            if response.status_code != 200:
                self.logger.warning(f"Pelando retornou status {response.status_code}")
                return ofertas

            parser = HTMLParser(response.text)
            island_tag = parser.css_first(
                "astro-island[component-export='SearchFeedContent']"
            )
            if not island_tag:
                return ofertas

            raw_props_json = html_module.unescape(
                island_tag.attributes.get("props", "")
            )
            props = json.loads(raw_props_json)
            clean_props = self._unwrap_astro_json(props)

            deals_list = clean_props.get("initialData", {}).get("deals", [])
            deals_list = deals_list[0].get("deals", []) if deals_list else []

            agora = int(time.time())
            for deal in deals_list[:3]:
                loja_nome = deal.get("store", {}).get("name", "Pelando")
                slug = deal.get("slug", "")

                ofertas.append(
                    {
                        "id": f"pel_{deal.get('id', uuid.uuid4().hex[:8])}",
                        "titulo": deal.get("title", "Oferta sem título"),
                        "preco": self._limpar_preco(deal.get("price", 0)),
                        "loja": loja_nome,
                        "link": f"https://www.pelando.com.br/d/{slug}",
                        "coletado_em": agora,
                        "expira_em": agora + 259200,  # +3 dias de validade no cache
                        "ativo": True,
                    }
                )
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no Pelando: {e}")

        return ofertas

    async def _buscar_mercadolivre(self, termo: str) -> list:
        """Busca produtos oficiais via API do Mercado Livre e retorna objetos estruturados."""
        params = {"q": termo, "limit": 3, "condition": "new"}
        ofertas = []
        client = NetworkManager.get_httpx_client()
        try:
            response = await client.get(self.ml_api_url, params=params, timeout=5.0)
            if response.status_code != 200:
                return ofertas

            results = response.json().get("results", [])
            agora = int(time.time())

            for item in results:
                ofertas.append(
                    {
                        "id": f"ml_{item.get('id', uuid.uuid4().hex[:8])}",
                        "titulo": item.get("title", ""),
                        "preco": self._limpar_preco(item.get("price", 0)),
                        "loja": "Mercado Livre",
                        "link": item.get("permalink", ""),
                        "coletado_em": agora,
                        "expira_em": agora + 86400,  # +24 horas (Preços mudam rápido)
                        "ativo": True,
                    }
                )
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no ML: {e}")

        return ofertas

    async def _buscar_serpapi(self, termo: str) -> list:
        """Agrega preços do Google Shopping via SerpApi e retorna objetos estruturados."""
        ofertas = []
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        if not self.serpapi_key:
            return ofertas

        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_shopping",
            "q": termo,
            "hl": "pt",
            "gl": "br",
            "api_key": self.serpapi_key,
            "num": 3,
        }
        client = NetworkManager.get_httpx_client()
        try:
            response = await client.get(url, params=params, timeout=8.0)
            if response.status_code != 200:
                return ofertas

            results = response.json().get("shopping_results", [])
            agora = int(time.time())

            for item in results[:3]:
                ofertas.append(
                    {
                        "id": f"serp_{uuid.uuid4().hex[:8]}",
                        "titulo": item.get("title", ""),
                        "preco": self._limpar_preco(item.get("price", "0")),
                        "loja": item.get("source", "Google Shopping"),
                        "link": item.get("link", ""),
                        "coletado_em": agora,
                        "expira_em": agora + 86400,
                        "ativo": True,
                    }
                )
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no SerpApi: {e}")

        return ofertas

    async def search(self, termo: str) -> str:
        """
        Orquestrador: Tenta o cache primeiro. Se falhar, dispara buscas simultaneamente,
        salva no DataManager (Meilisearch) e compila o relatório.
        """
        self.logger.info(f"Buscando produtos para: {termo}")

        ofertas_cacheadas = await data_manager.search_cached_offers(termo)
        if ofertas_cacheadas:
            self.logger.info("[Cache HIT] Ofertas encontradas no Meilisearch.")
            return self._formatar_relatorio(ofertas_cacheadas, termo, "Cache Rápido")

        self.logger.info("[Cache MISS] Iniciando scraping simultâneo nas lojas...")
        ofertas_novas = []

        # Dispara todas as buscas ao mesmo tempo usando asyncio.gather
        resultados = await asyncio.gather(
            self._buscar_pelando(termo),
            self._buscar_mercadolivre(termo),
            self._buscar_serpapi(termo),
            return_exceptions=True,  # Garante que uma falha não derrube as outras buscas
        )

        pelando_res, ml_res, serpapi_res = resultados

        if isinstance(pelando_res, list) and pelando_res:
            ofertas_novas.extend(pelando_res)

        if isinstance(ml_res, list) and ml_res:
            ofertas_novas.extend(ml_res)

        if isinstance(serpapi_res, list) and serpapi_res:
            ofertas_novas.extend(serpapi_res)

        if not ofertas_novas:
            return "Não encontrei boas ofertas ou produtos disponíveis para este termo no momento."

        await data_manager.save_offers(ofertas_novas)
        return self._formatar_relatorio(ofertas_novas, termo, "Scraping Ao Vivo")
