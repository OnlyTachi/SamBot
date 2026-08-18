import logging
import time
import re
import urllib.parse
from ..Connections.MeiliConnection import MeiliConnection


class ShoppingDataManager:
    """Responsável exclusivo pela camada de Cache de Ofertas e Ingestão."""

    def __init__(self, meili_db: MeiliConnection, db_sqlite=None, cache_ref=None):
        self.logger = logging.getLogger("SamBot.ShoppingData")
        self.meili = meili_db
        self.db = db_sqlite
        self.cache = cache_ref
        self.index = "/indexes/ofertas"
        self._index_setup_done = False

    def parse_telegram_offer(self, text: str, msg_id: int) -> dict | None:
        nlp_config = None
        if self.cache:
            nlp_config = self.cache.get("nlp_shopping")

        if not nlp_config:
            from ..Connections import data_manager

            nlp_config = data_manager.get_knowledge("nlp_shopping") or {}

        price_patterns = nlp_config.get("price_patterns", [])
        domain_map = nlp_config.get("domain_to_store", {})
        title_ignores = nlp_config.get("title_ignore_patterns", [])

        text_limpo = re.sub(
            r"^\[\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}\]\s*.*:\s*",
            "",
            text.strip(),
            flags=re.IGNORECASE,
        )

        all_links = re.findall(r"(https?://[^\s]+)", text_limpo)
        link = all_links[-1] if all_links else ""  # Link principal do produto (último)
        loja = "Desconhecida"

        for lk in all_links:
            link_clean = lk.lower()
            for domain, store_name in domain_map.items():
                if domain.lower() in link_clean:
                    loja = store_name
                    break
            if loja != "Desconhecida":
                break

        preco = 0.0
        texto_sem_emojis = re.sub(
            r"[\U00010000-\U0010ffff]", "", text_limpo, flags=re.UNICODE
        )
        texto_sem_precos_antigos = re.sub(
            r"~\s*R?\$\s*[\d.,]+\s*~|DE:?\s*R?\$\s*[\d.,]+",
            "",
            texto_sem_emojis,
            flags=re.IGNORECASE,
        )

        for pattern in price_patterns:
            match = re.search(pattern, texto_sem_precos_antigos, re.IGNORECASE)
            if not match:
                match = re.search(pattern, text_limpo, re.IGNORECASE)
            if match:
                raw_val = match.group(1) if match.groups() else match.group(0)
                try:
                    limpo = (
                        raw_val.replace(".", "").replace(",", ".")
                        if "," in raw_val
                        else (
                            raw_val.replace(".", "")
                            if raw_val.count(".") > 1
                            else raw_val
                        )
                    )
                    val_float = float(limpo)
                    if val_float > 0:
                        preco = val_float
                        break
                except ValueError:
                    continue

        if preco <= 0:
            match_fallback = re.search(
                r"POR:\s*(?:R\$\s*)?(\d+(?:[.,]\d+)*)", text_limpo, re.IGNORECASE
            )
            if match_fallback:
                try:
                    preco = float(match_fallback.group(1).replace(",", "."))
                except ValueError:
                    pass

        if not link or preco <= 0:
            return None

        linhas = [l.strip() for l in text_limpo.split("\n") if l.strip()]

        titulo_candidato = ""
        for linha in linhas:
            linha_testada = linha

            linha_testada = re.sub(
                r"\[\s*(Photo|Video|Imagem)\s*\]",
                "",
                linha_testada,
                flags=re.IGNORECASE,
            )
            for pattern in title_ignores:
                linha_testada = re.sub(pattern, "", linha_testada, flags=re.IGNORECASE)

            linha_testada = linha_testada.strip()

            if (
                linha_testada
                and "http" not in linha.lower()
                and not re.search(r"POR:", linha, re.IGNORECASE)
            ):
                titulo_candidato = linha_testada
                break

        titulo_final = (titulo_candidato if titulo_candidato else "Oferta em Promoção")[
            :150
        ]

        agora = int(time.time())
        return {
            "id": f"tg_{msg_id}_{agora}",
            "titulo": titulo_final,
            "preco": preco,
            "loja": loja,
            "link": link,
            "coletado_em": agora,
            "expira_em": agora + 172800,
            "ativo": True,
        }

    async def _ensure_setup(self):
        if not self._index_setup_done:
            await self.meili.setup_index()
            self._index_setup_done = True

    async def search_cached_offers(self, query: str, loja: str = None) -> list:
        await self._ensure_setup()
        timestamp_agora = int(time.time())
        filtros = [f"expira_em > {timestamp_agora}", "ativo = true"]
        if loja:
            filtros.append(f"loja = '{loja}'")
        payload = {
            "q": query,
            "filter": " AND ".join(filtros),
            "sort": ["preco:asc"],
            "limit": 5,
        }
        response = await self.meili.execute_request(
            "POST", f"{self.index}/search", payload
        )
        if response and "hits" in response:
            return response["hits"]
        return []

    async def save_offers(self, offers: list):
        if not offers:
            return
        await self._ensure_setup()
        response = await self.meili.execute_request(
            "POST", f"{self.index}/documents", offers
        )
        if response:
            self.logger.info(
                f"  {len(offers)} ofertas enviadas para ingestão (Task UID: {response.get('taskUid')})."
            )

    async def purge_expired_offers(self):
        await self._ensure_setup()
        timestamp_agora = int(time.time())
        payload = {"filter": f"expira_em <= {timestamp_agora}"}
        response = await self.meili.execute_request(
            "POST", f"{self.index}/documents/delete", payload
        )
        if response:
            self.logger.info("  Expurgo de ofertas expiradas acionado.")
