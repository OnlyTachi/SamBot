import asyncio
import logging
import os
import re
import time
import urllib.parse
import httpx
from rapidfuzz import fuzz
from selectolax.parser import HTMLParser
from Brain.Core.NetworkManager import NetworkManager
from Brain.Memory.DataManager.Connections import data_manager
from Core.ConfigLoader import AppConfig


class CupomFinder:

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Shopping.CupomFinder")
        self.pelando_url = "https://www.pelando.com.br/cupons-de-descontos"
        self.promobit_url = "https://api.promobit.com.br/coupon"
        self.serpapi_key = os.getenv("SERPAPI_KEY")

        # Parâmetros operacionais e limites
        self.scrape_timeout: float = float(AppConfig.get("PELANDO_TIMEOUT", "8.0"))
        self.top_coupons_limit: int = int(AppConfig.get("PELANDO_COUPON_LIMIT", "5"))
        self.cache_ttl_seconds: int = 86400  # 24 horas

    def _extrair_loja_alvo(self, texto: str) -> str:
        texto_limpo = texto.lower()
        nlp_config = data_manager.get_knowledge("nlp_shopping") or {}
        store_aliases = nlp_config.get("store_aliases", {})

        # 1. Busca Exata
        for slug_oficial, variacoes in store_aliases.items():
            for alias in variacoes:
                if re.search(rf"\b{re.escape(alias)}\b", texto_limpo):
                    return slug_oficial

        # 2. Busca Fuzzy (Erro de digitação)
        palavras = texto_limpo.split()
        for palavra in palavras:
            if len(palavra) >= 3:
                for slug_oficial, variacoes in store_aliases.items():
                    for alias in variacoes:
                        if fuzz.ratio(palavra, alias) >= 82:
                            return slug_oficial

        # 3. Fallback
        texto_limpo = re.sub(r"[^\w\s-]", "", texto_limpo)
        return re.sub(r"[\s_]+", "-", texto_limpo.strip())

    def _limpar_codigo(self, texto_codigo: str) -> str:
        """Limpa sujeiras do texto como 'Copiar', espaços extras ou quebras de linha."""
        if not texto_codigo:
            return "LINK ATIVADO"
        codigo_limpo = re.sub(r"\s+", " ", texto_codigo).strip()
        codigo_limpo = re.sub(r"\s*Copiar\s*", "", codigo_limpo, flags=re.IGNORECASE)
        return codigo_limpo if codigo_limpo else "LINK ATIVADO"

    def _formatar_relatorio(self, cupons: list, loja: str, origem: str) -> str:
        report = (
            f"🎟️ **Cupons Encontrados para {loja.title()}** *(Fonte: {origem})*:\n\n"
        )
        for cupom in cupons:
            report += f"- **{cupom['titulo']}**\n"
            report += f"  Código: `{cupom['codigo']}`\n"
            if cupom.get("link"):
                report += f"    [Pegar Cupom]({cupom['link']})\n"
            report += "\n"
        return report.strip()

    async def _buscar_promobit(self, slug_loja: str) -> list:
        """Busca cupons na API JSON nativa do Promobit via query e store_slug."""
        cupons_extraidos = []
        client = NetworkManager.get_httpx_client()
        params = {"query": slug_loja, "limit": 12}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Origin": "https://www.promobit.com.br",
            "Referer": "https://www.promobit.com.br/",
        }

        try:
            resp = await client.get(
                self.promobit_url, headers=headers, params=params, timeout=5.0
            )
            if resp.status_code != 200:
                resp = await client.get(
                    f"{self.promobit_url}?limit=12", headers=headers, timeout=5.0
                )

            if resp.status_code == 200:
                data = resp.json()
                itens = data.get("data", data) if isinstance(data, dict) else data

                if isinstance(itens, list):
                    for item in itens:
                        loja_slug_api = str(item.get("store_slug", "")).lower()
                        loja_nome_api = str(item.get("store_name", "")).lower()

                        # Valida se o cupom pertence à loja desejada
                        if slug_loja in loja_slug_api or slug_loja in loja_nome_api:
                            codigo = item.get("coupon_code") or "LINK ATIVADO"
                            titulo = (
                                item.get("coupon_title")
                                or item.get("coupon_discount_value")
                                or "Desconto Especial"
                            )
                            url_sufixo = item.get("coupon_url", "")
                            link = (
                                f"https://www.promobit.com.br{url_sufixo}"
                                if url_sufixo
                                else f"https://www.promobit.com.br/cupons/loja/{slug_loja}"
                            )

                            cupons_extraidos.append(
                                {
                                    "titulo": titulo,
                                    "codigo": self._limpar_codigo(codigo),
                                    "link": link,
                                }
                            )
                            if len(cupons_extraidos) >= self.top_coupons_limit:
                                break
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no Promobit: {e}")

        return cupons_extraidos

    async def _buscar_pelando(self, slug_loja: str, loja: str) -> list:
        """Busca cupons via Scraping HTML no Pelando."""
        cupons_extraidos = []
        url = f"{self.pelando_url}/{slug_loja}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        client = NetworkManager.get_httpx_client()

        try:
            response = await client.get(
                url, headers=headers, timeout=self.scrape_timeout
            )
            if response.status_code == 404:
                url_busca = f"https://www.pelando.com.br/busca/{urllib.parse.quote('cupom ' + loja)}"
                response = await client.get(
                    url_busca, headers=headers, timeout=self.scrape_timeout
                )

            if response.status_code == 200:
                parser = HTMLParser(response.text)
                articles = parser.css("article")
                for card in articles[: self.top_coupons_limit]:
                    titulo_el = card.css_first("h2, h3, a[title]")
                    codigo_el = card.css_first(
                        "[class*='coupon'], [class*='code'], button"
                    )
                    link_el = card.css_first("a[href*='/c/'], a[href*='/d/'], a[title]")

                    if titulo_el:
                        titulo = titulo_el.text().strip()
                        raw_codigo = codigo_el.text().strip() if codigo_el else ""
                        codigo = self._limpar_codigo(raw_codigo)
                        href = link_el.attributes.get("href", "") if link_el else ""
                        link_final = (
                            f"https://www.pelando.com.br{href}"
                            if href.startswith("/")
                            else url
                        )

                        cupons_extraidos.append(
                            {"titulo": titulo, "codigo": codigo, "link": link_final}
                        )
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no Pelando: {e}")

        return cupons_extraidos

    async def _buscar_serpapi(self, loja: str) -> list:
        """Busca cupons genéricos no Google via SerpApi como último recurso."""
        cupons_extraidos = []
        if not self.serpapi_key:
            return cupons_extraidos

        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google",
            "q": f"cupom de desconto {loja}",
            "hl": "pt",
            "gl": "br",
            "api_key": self.serpapi_key,
            "num": 3,
        }
        client = NetworkManager.get_httpx_client()

        try:
            response = await client.get(url, params=params, timeout=self.scrape_timeout)
            if response.status_code == 200:
                results = response.json().get("organic_results", [])
                for item in results[:3]:
                    cupons_extraidos.append(
                        {
                            "titulo": item.get("title", ""),
                            "codigo": "LINK ATIVADO",  # Snippets do Google raramente expõem o código explícito
                            "link": item.get("link", ""),
                        }
                    )
        except Exception as e:
            self.logger.warning(f"Falha ao buscar no SerpApi: {e}")

        return cupons_extraidos

    async def buscar_cupons(self, query: str) -> str:
        slug_loja = self._extrair_loja_alvo(query)
        self.logger.info(
            f"Loja identificada: '{slug_loja}' (Query original: '{query}')"
        )

        termo_busca = f"cupom {slug_loja}"
        loja = slug_loja.replace("-", " ").title()

        # 1. TENTA NO CACHE LOCAL (MEILISEARCH)
        cupons_cacheados = await data_manager.search_cached_offers(
            termo_busca, loja=slug_loja
        )
        if cupons_cacheados:
            self.logger.info("[Cache HIT] Cupons encontrados no Meilisearch.")
            cupons_formatados = [
                {
                    "titulo": c["titulo"],
                    "codigo": c.get("codigo", "LINK ATIVADO"),
                    "link": c["link"],
                }
                for c in cupons_cacheados
            ]
            return self._formatar_relatorio(cupons_formatados, loja, "Cache Rápido")

        self.logger.info(f"[Cache MISS] Iniciando cascata de cupons para: {loja}...")

        # 2. TENTA NA API DO PROMOBIT (Nativa e Rápida)
        cupons_extraidos = await self._buscar_promobit(slug_loja)
        origem = "Promobit API"

        # 3. TENTA PELANDO (Fallback 1)
        if not cupons_extraidos:
            self.logger.info("Promobit retornou vazio. Tentando raspagem no Pelando...")
            cupons_extraidos = await self._buscar_pelando(slug_loja, loja)
            origem = "Pelando"

        # 4. TENTA SERPAPI GOOGLE (Fallback 2)
        if not cupons_extraidos:
            self.logger.info(
                "Pelando retornou vazio. Tentando Google Search via SerpApi..."
            )
            cupons_extraidos = await self._buscar_serpapi(loja)
            origem = "Google Search"

        if not cupons_extraidos:
            return f"Nenhum cupom ativo encontrado no momento para a loja **{loja}**."

        # 5. SALVA NO CACHE E RETORNA
        agora = int(time.time())
        documentos_cache = []
        for idx, cupom in enumerate(cupons_extraidos):
            documentos_cache.append(
                {
                    "id": f"cup_{slug_loja}_{agora}_{idx}",
                    "titulo": f"cupom {slug_loja} - {cupom['titulo']}",
                    "codigo": cupom["codigo"],
                    "preco": 0.0,
                    "loja": slug_loja,
                    "link": cupom["link"],
                    "coletado_em": agora,
                    "expira_em": agora + self.cache_ttl_seconds,
                    "ativo": True,
                }
            )

        await data_manager.save_offers(documentos_cache)
        return self._formatar_relatorio(cupons_extraidos, loja, origem)
