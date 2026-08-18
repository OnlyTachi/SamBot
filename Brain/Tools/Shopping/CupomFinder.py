import asyncio
import logging
import os
import re
import time
import urllib.parse
import httpx
from selectolax.parser import HTMLParser
from Brain.Core.NetworkManager import NetworkManager
from Brain.Memory.DataManager.Connections import data_manager
from Core.ConfigLoader import AppConfig


class CupomFinder:

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Shopping.CupomFinder")
        self.base_url = "https://www.pelando.com.br/cupons-de-descontos"

        # Parâmetros operacionais e limites
        self.scrape_timeout: float = float(AppConfig.get("PELANDO_TIMEOUT", "8.0"))
        self.top_coupons_limit: int = int(AppConfig.get("PELANDO_COUPON_LIMIT", "5"))
        self.cache_ttl_seconds: int = 86400  # 24 horas

    def _formatar_slug(self, loja: str) -> str:
        loja_limpa = loja.lower().strip()
        nlp_config = data_manager.get_knowledge("nlp_shopping") or {}
        store_aliases = nlp_config.get("store_aliases", {})

        for slug_oficial, variacoes in store_aliases.items():
            if loja_limpa in variacoes:
                return slug_oficial

        for slug_oficial, variacoes in store_aliases.items():
            if any(alias in loja_limpa for alias in variacoes):
                return slug_oficial

        loja_limpa = re.sub(r"[^\w\s-]", "", loja_limpa)
        return re.sub(r"[\s_]+", "-", loja_limpa)

    def _limpar_codigo(self, texto_codigo: str) -> str:
        """Limpa sujeiras do texto como 'Copiar', espaços extras ou quebras de linha."""
        if not texto_codigo:
            return "LINK ATIVADO"
        codigo_limpo = re.sub(r"\s+", " ", texto_codigo).strip()
        codigo_limpo = re.sub(r"\s*Copiar\s*", "", codigo_limpo, flags=re.IGNORECASE)
        return codigo_limpo if codigo_limpo else "LINK ATIVADO"

    def _formatar_relatorio(self, cupons: list, loja: str, origem: str) -> str:
        report = (
            f"  **Cupons Encontrados para {loja.title()}** *(Fonte:" f" {origem})*:\n\n"
        )
        for cupom in cupons:
            report += f"- **{cupom['titulo']}**\n"
            report += f"  Código: `{cupom['codigo']}`\n"
            if cupom.get("link"):
                report += f"    [Pegar Cupom]({cupom['link']})\n"
            report += "\n"
        return report.strip()

    async def buscar_cupons(self, loja: str) -> str:
        self.logger.info(f"Buscando cupons para a loja: {loja}")
        slug_loja = self._formatar_slug(loja)
        termo_busca = f"cupom {slug_loja}"

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
            return self._formatar_relatorio(
                cupons_formatados, slug_loja, "Cache Rápido"
            )

        self.logger.info("Buscando cupons ao vivo no Pelando...")
        url = f"{self.base_url}/{slug_loja}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.pelando.com.br",
            "Referer": "https://www.pelando.com.br/",
            "Upgrade-Insecure-Requests": "1",
        }
        client = NetworkManager.get_httpx_client()

        try:
            response = await client.get(
                url, headers=headers, timeout=self.scrape_timeout
            )

            # Fallback para busca genérica se o slug direto retornar 404
            if response.status_code == 404:
                url_busca = f"https://www.pelando.com.br/busca/{urllib.parse.quote('cupom ' + loja)}"
                response = await client.get(
                    url_busca, headers=headers, timeout=self.scrape_timeout
                )

            if response.status_code != 200:
                return f"Não consegui acessar os cupons para **{loja.title()}** no momento."

            parser = HTMLParser(response.text)
            cupons_extraidos = []

            articles = parser.css("article")
            for card in articles[: self.top_coupons_limit]:
                titulo_el = card.css_first("h2, h3, a[title]")
                codigo_el = card.css_first("[class*='coupon'], [class*='code'], button")
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

            if not cupons_extraidos:
                return f"Nenhum cupom ativo encontrado no momento para a loja **{loja.title()}**."

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
            return self._formatar_relatorio(
                cupons_extraidos, slug_loja, "Scraping Ao Vivo"
            )

        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            self.logger.warning(f"Falha de rede ao buscar cupons para {loja}: {e}")
            return "Ocorreu um erro ao pesquisar cupons. Tente novamente mais tarde."
        except Exception as e:
            self.logger.error(f"Erro inesperado no CupomFinder: {e}", exc_info=True)
            return "Ocorreu um erro ao pesquisar cupons. Tente novamente mais tarde."
