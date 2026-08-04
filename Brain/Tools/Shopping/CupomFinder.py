import httpx
import logging
import json
import re
import urllib.parse
import html as html_module
from selectolax.parser import HTMLParser


class CupomFinder:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Shopping.CupomFinder")
        self.base_url = "https://www.pelando.com.br/cupons-de-descontos"

    def _formatar_slug(self, loja: str) -> str:
        """Converte o termo pesquisado no slug oficial usado pelo Pelando."""
        loja_limpa = loja.lower().strip()

        apelidos = {
            "mercado livre": "mercado-livre",
            "mercadolivre": "mercado-livre",
            "ml": "mercado-livre",
            "amazon": "amazon",
            "aliexpress": "aliexpress",
            "ali": "aliexpress",
            "shopee": "shopee",
            "magalu": "magalu",
            "magazine luiza": "magalu",
        }

        if loja_limpa in apelidos:
            return apelidos[loja_limpa]

        loja_limpa = re.sub(r"[^\w\s-]", "", loja_limpa)
        return re.sub(r"[\s_]+", "-", loja_limpa)

    def _desembalar_astro_json(self, item):
        """Desembala a estrutura interna do Astro Framework: [0, valor] -> valor"""
        if isinstance(item, list):
            if len(item) == 2 and item[0] in (0, 1):
                return self._desembalar_astro_json(item[1])
            return [self._desembalar_astro_json(x) for x in item]
        elif isinstance(item, dict):
            return {k: self._desembalar_astro_json(v) for k, v in item.items()}
        return item

    async def buscar_cupons(self, loja: str) -> str:
        """Busca cupons ativos usando a URL fixa de /cupons-de-descontos/ e fallback se der 404."""
        self.logger.info(f"Buscando cupons para a loja: {loja}")
        slug_loja = self._formatar_slug(loja)
        url = f"{self.base_url}/{slug_loja}"

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

                # FALLBACK: Se o Pelando responder 404 para a página fixa (loja menor), faz a busca textual por cupons
                if response.status_code == 404:
                    self.logger.info(
                        f"Página fixa de cupons não encontrada para '{slug_loja}'. Redirecionando para busca geral..."
                    )
                    url_busca = f"https://www.pelando.com.br/busca/{urllib.parse.quote('cupom ' + loja)}"
                    response = await client.get(url_busca, headers=headers, timeout=8.0)

                if response.status_code != 200:
                    return f"Não consegui acessar os cupons para **{loja.title()}** no momento (Status: {response.status_code})."

                parser = HTMLParser(response.text)
                cupons_extraidos = []

                island_tag = parser.css_first(
                    "astro-island[component-export='CouponsFeedContent']"
                ) or parser.css_first(
                    "astro-island[component-export='SearchFeedContent']"
                )

                if island_tag and "props" in island_tag.attributes:
                    try:
                        raw_props = html_module.unescape(island_tag.attributes["props"])
                        props_json = json.loads(raw_props)
                        dados_limpos = self._desembalar_astro_json(props_json)
                        initial_data = dados_limpos.get("initialData", {})
                        raw_coupons = initial_data.get(
                            "coupons", []
                        ) or initial_data.get("deals", [])

                        if isinstance(raw_coupons, list) and len(raw_coupons) > 0:
                            items = (
                                raw_coupons[0].get("coupons", [])
                                if isinstance(raw_coupons[0], dict)
                                else raw_coupons[0].get("deals", [])
                            )
                            for item in items[:5]:
                                titulo = (
                                    item.get("title")
                                    or item.get("name")
                                    or "Desconto na loja"
                                )
                                codigo = (
                                    item.get("code")
                                    or item.get("couponCode")
                                    or "LINK ATIVADO"
                                )
                                slug_cupom = item.get("slug", "")
                                link = (
                                    f"https://www.pelando.com.br/c/{slug_cupom}"
                                    if slug_cupom
                                    else url
                                )
                                cupons_extraidos.append(
                                    {"titulo": titulo, "codigo": codigo, "link": link}
                                )
                    except Exception as err:
                        self.logger.debug(f"Falha ao ler JSON do Astro Island: {err}")

                if not cupons_extraidos:
                    cards = parser.css("article") or parser.css("[class*='deal-card']")
                    for card in cards[:5]:
                        titulo_el = card.css_first("h2, h3, a[title]")
                        codigo_el = card.css_first("[class*='coupon'], [class*='code']")
                        link_el = card.css_first("a[href*='/c/']") or card.css_first(
                            "a[href*='/d/']"
                        )
                        if titulo_el:
                            titulo = titulo_el.text().strip()
                            codigo = (
                                codigo_el.text().strip()
                                if codigo_el
                                else "LINK ATIVADO"
                            )
                            href = link_el.attributes.get("href", "") if link_el else ""
                            link = (
                                f"https://www.pelando.com.br{href}"
                                if href.startswith("/")
                                else href or url
                            )
                            cupons_extraidos.append(
                                {"titulo": titulo, "codigo": codigo, "link": link}
                            )

                if not cupons_extraidos:
                    return f"Nenhum cupom ativo encontrado no momento para a loja **{loja.title()}**."

                report = f"🏷️ **Cupons Encontrados para {loja.title()}:**\n\n"
                for cupom in cupons_extraidos:
                    report += f"- **{cupom['titulo']}**\n"
                    report += f"  Código: `{cupom['codigo']}`\n"
                    if cupom["link"] != url:
                        report += f"    [Pegar Cupom]({cupom['link']})\n"
                    report += "\n"
                return report.strip()
        except Exception as e:
            self.logger.warning(f"Falha ao buscar cupons para {loja}: {e}")
            return "Ocorreu um erro ao pesquisar cupons. Tente novamente mais tarde."
