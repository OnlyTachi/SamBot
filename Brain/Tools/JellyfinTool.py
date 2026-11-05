import difflib
import logging
import os
import re
import unicodedata
from typing import Any, Dict, List, Tuple

import discord
from Brain.Core.NetworkManager import NetworkManager
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Memory.LongTerm.VectorStore import vector_store
from Core.ConfigLoader import AppConfig

try:
    from rapidfuzz import fuzz

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class JellyfinTool:
    def __init__(self, bot=None):
        self.bot = bot
        self.logger = logging.getLogger("SamBot.JellyfinTool")
        self.base_url = (
            AppConfig.get("tools.jellyfin.url")
            or AppConfig.get("jellyfin.url")
            or AppConfig.get("JELLYFIN_URL", "")
        ).rstrip("/")
        self.api_key = os.getenv("JELLYFIN_API_KEY")
        self.headers = {"X-Emby-Token": self.api_key, "Accept": "application/json"}
        self.is_configured = bool(self.base_url and self.api_key)
        self.cache_key = "jellyfin_catalog"
        self.vector_collection = "jellyfin_midias"

        self.notif_channel_id = (
            AppConfig.get("tools.jellyfin.notif_channel_id")
            or AppConfig.get("jellyfin.notif_channel_id")
            or AppConfig.get("JELLYFIN_NOTIF_CHANNEL_ID")
        )

        if not self.is_configured:
            self.logger.warning(
                "JellyfinTool não configurado. Verifique JELLYFIN_URL e JELLYFIN_API_KEY no config.yaml/.env."
            )

    def _remover_acentos(self, texto: str) -> str:
        """Remove marcas de acentuação e converte para minúsculas."""
        if not texto:
            return ""
        nfkd = unicodedata.normalize("NFKD", texto)
        return (
            "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()
        )

    def _calcular_similaridade(self, query: str, alvo: str) -> float:
        """Calcula similaridade textual flexível (0 a 100)."""
        if query in alvo:
            return 100.0 if len(query) == len(alvo) else 90.0
        if RAPIDFUZZ_AVAILABLE:
            return float(fuzz.token_set_ratio(query, alvo))
        return difflib.SequenceMatcher(None, query, alvo).ratio() * 100.0

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

    async def sync_catalog(self) -> bool:
        """Busca o catálogo da API do Jellyfin, guarda em cache local e indexa no ChromaDB."""
        if not self.is_configured:
            return False

        self.logger.info("Sincronizando catálogo do Jellyfin...")
        catalog = {"filmes": [], "series": {}}

        # 1. Filmes
        params_movies = {
            "IncludeItemTypes": "Movie",
            "Recursive": "true",
            "Fields": "ProductionYear,Overview,CommunityRating,Genres",
        }
        data_movies = await self._fetch("/Items", params=params_movies)
        if data_movies:
            for item in data_movies.get("Items", []):
                nome = item.get("Name", "Desconhecido")
                ano = item.get("ProductionYear", "")
                sinopse = item.get("Overview", "Sem sinopse disponível.")
                sinopse_curta = (
                    (sinopse[:160] + "...") if len(sinopse) > 160 else sinopse
                )
                rating = item.get("CommunityRating")
                generos = item.get("Genres", [])

                catalog["filmes"].append(
                    {
                        "id": item.get("Id"),
                        "titulo": nome,
                        "ano": str(ano) if ano else "",
                        "sinopse": sinopse_curta,
                        "rating": f"{rating:.1f}" if rating else None,
                        "generos": generos,
                    }
                )

                # Indexação Semântica para pesquisa por enredo e género
                if vector_store:
                    texto_index = (
                        f"Filme: {nome}. Ano: {ano}. Géneros: {', '.join(generos)}. "
                        f"Sinopse: {sinopse}"
                    )
                    await vector_store.add_memory(
                        collection_name=self.vector_collection,
                        text=texto_index,
                        metadata={
                            "tipo": "filme",
                            "titulo": nome,
                            "ano": str(ano),
                            "rating": str(rating or ""),
                        },
                        doc_id=f"jelly_movie_{item.get('Id')}",
                    )

        # 2. Séries e Estrutura de Temporadas
        params_series = {
            "IncludeItemTypes": "Series",
            "Recursive": "true",
            "Fields": "ProductionYear,Overview,Genres",
        }
        data_series = await self._fetch("/Items", params=params_series)
        series_meta = {}
        if data_series:
            for s in data_series.get("Items", []):
                s_name = s.get("Name")
                if s_name:
                    series_meta[s_name] = {
                        "id": s.get("Id"),
                        "sinopse": s.get("Overview", "Sem sinopse disponível."),
                        "generos": s.get("Genres", []),
                        "ano": s.get("ProductionYear", ""),
                    }

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
                catalog["series"][serie][temporada] = (
                    catalog["series"][serie].get(temporada, 0) + 1
                )

        if vector_store:
            for serie_nome, info in series_meta.items():
                texto_index = (
                    f"Série: {serie_nome}. Ano: {info.get('ano', '')}. "
                    f"Géneros: {', '.join(info.get('generos', []))}. "
                    f"Sinopse: {info.get('sinopse', '')}"
                )
                await vector_store.add_memory(
                    collection_name=self.vector_collection,
                    text=texto_index,
                    metadata={"tipo": "serie", "titulo": serie_nome},
                    doc_id=f"jelly_series_{info.get('id')}",
                )

        data_manager.save_knowledge(self.cache_key, catalog)
        self.logger.info("Catálogo do Jellyfin sincronizados!")
        return True

    def _extrair_subqueries(self, raw_query: str) -> List[str]:
        """Separa termos compostos sem dividir palavras com conetivos legítimos."""
        partes = re.split(r"[,;]|\s+\be\b\s+", raw_query)
        queries = [p.strip() for p in partes if len(p.strip()) >= 2]
        return queries or [raw_query.strip()]

    async def _buscar_por_semantica(self, query: str) -> List[Tuple[float, str]]:
        """Pesquisa itens na VectorStore por proximidade de enredo ou contexto temático."""
        resultados: List[Tuple[float, str]] = []
        if not vector_store:
            return resultados

        try:
            docs = await vector_store.query_relevant(
                collection_name=self.vector_collection,
                query=query,
                n_results=3,
            )
            for doc in (docs if isinstance(docs, list) else [docs]):
                if not doc:
                    continue
                partes = doc.split(". ")
                cabecalho = partes[0] if partes else doc
                resumo = partes[-1] if len(partes) > 1 else ""
                card = f"💡 **{cabecalho}**\n  *Contexto/Sinopse:* {resumo[:150]}..."
                resultados.append((76.0, card))
        except Exception as e:
            self.logger.debug(f"Aviso na pesquisa vetorial do Jellyfin: {e}")

        return resultados

    async def search_content(self, query: str) -> str:
        """Combina correspondência literal/fuzzy com fallback semântico (RAG)."""
        if not self.is_configured:
            return "Serviço Jellyfin não configurado."

        catalog = data_manager.get_knowledge(self.cache_key)
        if not catalog:
            await self.sync_catalog()
            catalog = data_manager.get_knowledge(self.cache_key)
            if not catalog:
                return "Não foi possível aceder ao catálogo do Jellyfin de momento."

        queries = self._extrair_subqueries(query)
        candidatos: List[Tuple[float, str]] = []

        series_dict: Dict[str, Dict[str, int]] = catalog.get("series", {})
        filmes_list: List[Dict[str, Any]] = catalog.get("filmes", [])

        # 1. Correspondência por título (Fuzzy e tokens)
        for sub_q in queries:
            sub_norm = self._remover_acentos(sub_q)
            termos_busca = [t for t in sub_norm.split() if len(t) >= 3]

            # Séries
            for serie_nome, temporadas in series_dict.items():
                serie_norm = self._remover_acentos(serie_nome)
                score = self._calcular_similaridade(sub_norm, serie_norm)

                if termos_busca and all(t in serie_norm for t in termos_busca):
                    score = max(score, 88.0)

                if score >= 65.0:
                    detalhes_temps = [
                        f"{temp} ({qtd} eps)" for temp, qtd in temporadas.items()
                    ]
                    card = f"📺 **{serie_nome}**\n  *Estrutura:* {', '.join(detalhes_temps)}"
                    candidatos.append((score, card))

            # Filmes
            for filme in filmes_list:
                titulo = filme["titulo"]
                titulo_norm = self._remover_acentos(titulo)
                score = self._calcular_similaridade(sub_norm, titulo_norm)

                if termos_busca and all(t in titulo_norm for t in termos_busca):
                    score = max(score, 88.0)

                if score >= 65.0:
                    meta_info = []
                    if filme.get("ano"):
                        meta_info.append(filme["ano"])
                    if filme.get("rating"):
                        meta_info.append(f"★ {filme['rating']}")
                    meta_str = f" *({', '.join(meta_info)})*" if meta_info else ""

                    card = f"🎬 **{titulo}**{meta_str}\n  *Sinopse:* {filme['sinopse']}"
                    candidatos.append((score, card))

        # 2. Ativação da busca semântica se nenhuma correspondência forte de título for achada
        if not candidatos or max([s for s, _ in candidatos]) < 75.0:
            semanticos = await self._buscar_por_semantica(query)
            candidatos.extend(semanticos)

        if not candidatos:
            return f"Nenhum título correspondente a '{query}' foi encontrado no catálogo do servidor."

        # Ordenação por relevância e remoção de duplicados
        candidatos.sort(key=lambda x: x[0], reverse=True)
        vistos = set()
        unicos = []
        for _, card in candidatos:
            if card not in vistos:
                vistos.add(card)
                unicos.append(card)

        report = "**Resultados encontrados no Jellyfin:**\n\n"
        for item in unicos[:6]:
            report += f"{item}\n\n"

        return report.strip()

    async def handle_webhook_event(self, payload: dict) -> bool:
        """Processa eventos do webhook do Jellyfin: atualiza o catálogo e (opcionalmente) notifica."""
        event_name = payload.get("NotificationType") or payload.get("Event", "")
        item_name = payload.get("Name") or payload.get(
            "ItemName", "Título desconhecido"
        )
        item_type = payload.get("ItemType", "Mídia")
        overview = payload.get("Overview", "Sem sinopse disponível.")

        if event_name != "ItemAdded":
            return False

        self.logger.info(
            f"Webhook Jellyfin recebido: Nova mídia '{item_name}' ({item_type})"
        )

        await self.sync_catalog()

        if not self.notif_channel_id or not self.bot:
            return True

        try:
            channel_id = int(str(self.notif_channel_id).strip())
            canal = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(
                channel_id
            )
            if canal:
                embed = discord.Embed(
                    title="🍿 Novo Conteúdo Adicionado ao Jellyfin!",
                    description=f"**{item_name}** ({item_type})\n\n{overview[:250]}...",
                    color=discord.Color.from_rgb(170, 92, 195),
                )
                embed.set_footer(text="Servidor Jellyfin • SamBot")
                await canal.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Erro ao emitir aviso de novo conteúdo no Discord: {e}")

        return True
