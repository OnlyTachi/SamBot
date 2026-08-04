import os
import re
import logging
import math
import asyncio
from typing import List, Dict, Any
from ollama import AsyncClient
import unicodedata
from Brain.Memory.DataManager import data_manager


def cosine_similarity(v1, v2):
    """Calcula a similaridade entre duas frases vetoriais."""
    dot_product = sum(x * y for x, y in zip(v1, v2))
    mag_v1 = math.sqrt(sum(x * x for x in v1))
    mag_v2 = math.sqrt(sum(y * y for y in v2))
    if mag_v1 == 0 or mag_v2 == 0:
        return 0.0
    return dot_product / (mag_v1 * mag_v2)


def normalizar_texto(texto: str) -> str:
    """Remove acentos e caracteres especiais para casar buscas sintáticas."""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).lower()


class TLMRouter:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.SemanticRouter")
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | TLMRouter       | %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

        # Configurações do Ollama
        self.ollama_url = os.getenv(
            "OLLAMA_LOCAL_URL", "http://host.docker.internal:11434"
        )
        raw_model = os.getenv("MODEL_TLM_LOCAL", "all-minilm:latest")
        self.embed_model = raw_model if ":" in raw_model else f"{raw_model}:latest"

        self.client = AsyncClient(host=self.ollama_url)

        self.routes = {}
        self.triggers_text = {}
        self.threshold = 0.50 if self.debug_mode else 0.58

        self.is_active = True
        self.consecutive_errors = 0
        self.max_errors = 3

        asyncio.create_task(self.recarregar_gatilhos())

    async def _get_embedding(self, text: str) -> List[float]:
        if not self.is_active:
            return []

        try:
            res = await self.client.embeddings(model=self.embed_model, prompt=text)
            self.consecutive_errors = 0
            return res.get("embedding", [])
        except Exception as e:
            self.consecutive_errors += 1
            if self.consecutive_errors >= self.max_errors:
                self.is_active = False
                self.logger.error(
                    f"Conexão com Ollama falhou {self.max_errors} vezes em '{self.ollama_url}'. "
                    f"Roteador DESATIVADO temporariamente. Erro: {e}"
                )
            return []

    async def recarregar_gatilhos(self):
        self.logger.info(
            f"Construindo rotas semânticas nativas com Ollama ({self.embed_model})..."
        )
        triggers_dict = dict(data_manager.get_knowledge("router_triggers") or {})

        self.ruidos = triggers_dict.pop("config_ruidos")

        test_vec = await self._get_embedding("ping")
        if not test_vec or not self.is_active:
            self.logger.warning(
                "Ollama inacessível no boot. Roteamento semântico suspenso."
            )
            return

        count = 0
        self.routes.clear()
        self.triggers_text.clear()

        for tool_name, utterances in triggers_dict.items():
            if not self.is_active:
                break

            if utterances and isinstance(utterances, list):
                self.routes[tool_name] = []
                self.triggers_text[tool_name] = utterances
                for phrase in utterances:
                    if not self.is_active:
                        break
                    vec = await self._get_embedding(phrase)
                    if vec:
                        self.routes[tool_name].append(vec)
                        count += 1

        if count > 0 and self.is_active:
            status_debug = " [MODO DEBUG ATIVO]" if self.debug_mode else ""
            self.logger.info(
                f"SemanticRouter Ativo! {count} frases indexadas nativamente.{status_debug}"
            )
        elif not self.is_active:
            self.routes.clear()
            self.logger.warning(
                "Indexação de rotas cancelada devido a erros de conexão com o Ollama."
            )

    def _extrair_args(self, content: str, tool: str) -> str:
        triggers = self.triggers_text.get(tool, [])

        content_limpo = re.sub(r"[?!.,;:]", " ", content)

        triggers_ordenados = sorted(triggers, key=len, reverse=True)
        for g in triggers_ordenados:
            g_clean = re.sub(r"[?!.,;:]", " ", g).strip()
            if not g_clean:
                continue

            pattern = re.compile(rf"\b{re.escape(g_clean)}\b", re.IGNORECASE)
            content_limpo = pattern.sub(" ", content_limpo)

        if hasattr(self, "ruidos") and self.ruidos:
            ruidos_ordenados = sorted(self.ruidos, key=len, reverse=True)
            ruidos_escapados = [re.escape(r) for r in ruidos_ordenados]
            ruido_pattern = r"\b(" + "|".join(ruidos_escapados) + r")\b"

            content_limpo = re.sub(
                ruido_pattern, " ", content_limpo, flags=re.IGNORECASE
            )

        content_limpo = re.sub(r"\s+", " ", content_limpo).strip()

        return content_limpo if content_limpo else content.strip()

    async def executar(
        self, content: str, ferramentas_ativas: list
    ) -> List[Dict[str, str]]:
        if not self.is_active or not self.routes or not content.strip():
            return []

        content_norm = normalizar_texto(content)
        content_vec = await self._get_embedding(content_norm)
        if not content_vec or not self.is_active:
            return []

        best_tool = None
        best_score = 0.0

        for tool_name, vectors in self.routes.items():
            if tool_name not in ferramentas_ativas:
                continue
            for v in vectors:
                score = cosine_similarity(content_vec, v)
                if score > best_score:
                    best_score = score
                    best_tool = tool_name

        if self.debug_mode and best_tool:
            status_match = "ACEITO" if best_score >= self.threshold else "RECUSADO"
            self.logger.info(
                f"🔍 [DEBUG ROTA] Candidato: '{best_tool}' | Score: {best_score:.2f} | "
                f"Alvo: {self.threshold} | Status: {status_match}"
            )

        if best_tool and best_score >= self.threshold:
            self.logger.info(
                f"🎯 Rota cravada: '{best_tool}' (Confiança: {best_score:.2f})"
            )
            args = self._extrair_args(content, best_tool)
            self.logger.info(f"🧩 Argumentos isolados: '{args}'")
            return [{"tool": best_tool, "args": args}]

        return []
