import hashlib
import json
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

        self.threshold = 0.74

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
        Sincroniza automaticamente os gatilhos no ChromaDB caso o JSON
        tenha sido alterado (comparação por Hash MD5).
        """
        col = self.vector_store.collections.get("rotas_intencoes")
        if not col:
            return

        triggers_dict = dict(data_manager.get_knowledge("router_triggers") or {})
        if not triggers_dict:
            return

        # 1. Calcula o hash MD5 atual do dicionário de rotas
        conteudo_canonico = json.dumps(
            triggers_dict, sort_keys=True, ensure_ascii=False
        )
        hash_atual = hashlib.md5(conteudo_canonico.encode("utf-8")).hexdigest()

        # 2. Recupera o último hash gravado
        hash_salvo_data = data_manager.get_knowledge("rotas_hash_state") or {}
        hash_salvo = hash_salvo_data.get("hash", "")

        # 3. Se não mudou nada e já existem registros, não faz nada
        if not force and col.count() > 0 and hash_salvo == hash_atual:
            self.logger.info(
                "Rotas semânticas atualizadas e consistentes. Nenhuma alteração necessária."
            )
            return

        self.logger.info(
            "Alteração no JSON detectada! Atualizando rotas no ChromaDB..."
        )

        # 4. Limpa os vetores antigos se existirem
        if col.count() > 0:
            ids_antigos = col.get()["ids"]
            if ids_antigos:
                col.delete(ids=ids_antigos)

        # 5. Indexa as novas frases
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

        # 6. Salva o novo hash para futuras comparações
        data_manager.save_knowledge("rotas_hash_state", {"hash": hash_atual})
        self.logger.info("Indexação automática do ChromaDB concluída com sucesso!")

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
