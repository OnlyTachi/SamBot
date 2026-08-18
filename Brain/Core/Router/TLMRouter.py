import os
import re
import logging
import math
import asyncio
from typing import List, Dict, Any
from ollama import AsyncClient
import unicodedata

from Brain.Memory.DataManager.Connections import data_manager
from Brain.Memory.LongTerm.VectorStore import vector_store


class TLMRouter:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.SemanticRouter")
        self.vector_store = vector_store

        self.threshold = 0.86

    def _limpar_argumentos(self, texto: str) -> str:
        ruidos = data_manager.get_router_triggers().get("config_ruidos", [])
        texto_limpo = texto.lower()
        for ruido in ruidos:
            texto_limpo = re.sub(
                rf"\b{re.escape(ruido)}\b", "", texto_limpo, flags=re.IGNORECASE
            )
        return re.sub(r"\s+", " ", texto_limpo).strip()

    async def sincronizar_base_rotas(self, force: bool = False):
        """
        Sincroniza os gatilhos no ChromaDB.
        Apaga os vetores antigos e reindexa com base no JSON atual.
        """
        col = self.vector_store.collections.get("rotas_intencoes")
        if not col:
            return

        if col.count() > 0:
            if not force:
                self.logger.info(
                    "Rotas semânticas já indexadas. Nenhuma alteração forçada."
                )
                return
            self.logger.info(
                "Atualização detectada! Limpando rotas antigas no ChromaDB..."
            )
            ids_antigos = col.get()["ids"]
            if ids_antigos:
                col.delete(ids=ids_antigos)

        self.logger.info("Indexando novas rotas semânticas no ChromaDB...")
        triggers_dict = dict(data_manager.get_knowledge("router_triggers") or {})

        for tool_name, utterances in triggers_dict.items():
            if utterances and isinstance(utterances, list):
                for idx, phrase in enumerate(utterances):
                    doc_id = f"route_{tool_name}_{idx}"
                    await self.vector_store.add_memory(
                        collection_name="rotas_intencoes",
                        text=phrase,
                        metadata={"tool": tool_name, "phrase": phrase},
                        doc_id=doc_id,
                    )
        self.logger.info("Indexação concluída com sucesso!")

    async def executar(
        self, content: str, ferramentas_ativas: list
    ) -> List[Dict[str, str]]:
        if not content.strip():
            return []

        col = self.vector_store.collections.get("rotas_intencoes")
        if not col or col.count() == 0:
            return []

        embedding = await self.vector_store.embedding_fn.get_single_embedding(content)

        res = col.query(query_embeddings=[embedding], n_results=1)

        if (
            res
            and res.get("metadatas")
            and res["metadatas"][0]
            and res.get("distances")
            and res["distances"][0]
        ):

            distance = res["distances"][0][0]

            score = 1.0 - distance

            self.logger.debug(
                f"Score calculado: {score:.4f} (Threshold: {self.threshold})"
            )

            if score >= self.threshold:
                best_tool = res["metadatas"][0][0].get("tool")

                if best_tool in ferramentas_ativas:
                    args_limpos = self._limpar_argumentos(content)
                    args_final = args_limpos if args_limpos else content.strip()

                    self.logger.info(
                        f"Rota aprovada: '{best_tool}' | Score: {score:.4f}"
                    )
                    return [{"tool": best_tool, "args": args_final}]
            else:
                self.logger.info(
                    f"Rota ignorada (Score {score:.4f} < {self.threshold}). Deixando LLM responder."
                )

        return []
