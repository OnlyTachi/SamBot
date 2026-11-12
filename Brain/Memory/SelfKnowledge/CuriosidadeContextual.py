import logging
import random
import time
from typing import Optional, Dict, Any
from Brain.Memory.DataManager.Connections import data_manager


class CuriosidadeContextual:
    """
    Gerencia curiosidades contextuais lendo diretamente do SQLite / Knowledge.
    Zero strings ou categorias hardcoded no código.
    """

    def __init__(self, vector_store=None):
        self.logger = logging.getLogger("SamBot.CuriosidadeContextual")
        self.vector_store = vector_store
        self._last_trigger: Dict[str, float] = {}
        self.cooldown_seconds = 180  # 3 minutos de cooldown por contexto

    def _obter_base(self) -> Dict[str, Any]:
        """Carrega a base de dados dinamicamente do SQLite."""
        dados = data_manager.get_knowledge("curiosidades_data")
        return dados if isinstance(dados, dict) else {}

    def _buscar_curiosidade_tematica(self, text: str) -> Optional[str]:
        """Varre os tópicos e palavras-chave registrados no banco de dados."""
        base = self._obter_base()
        if not base:
            return None

        text_lower = text.lower()

        for categoria, dados in base.items():
            # Suporta o formato estruturado {"keywords": [...], "facts": [...]}
            if isinstance(dados, dict):
                keywords = dados.get("keywords", [])
                facts = dados.get("facts", [])
                if any(k.lower() in text_lower for k in keywords) and facts:
                    return random.choice(facts)

            # Suporte a formato simplificado {"categoria": ["fato 1", "fato 2"]}
            elif isinstance(dados, list) and dados:
                if categoria.lower() in text_lower:
                    return random.choice(dados)

        return None

    async def _buscar_curiosidade_vetorial(self, text: str) -> Optional[str]:
        """Fallback semântico no ChromaDB se a coleção existir."""
        if not self.vector_store or not hasattr(self.vector_store, "query_relevant"):
            return None
        try:
            resultados = await self.vector_store.query_relevant(
                "curiosidades", text, n_results=1
            )
            if resultados and isinstance(resultados, list):
                return resultados[0]
        except Exception as e:
            self.logger.debug(f"Aviso na busca vetorial de curiosidade: {e}")
        return None

    async def get_curiosity_prompt(
        self,
        user_content: str,
        context_id: str,
        has_persona: bool = False,
        chance: float = 0.25,
    ) -> str:
        """Gera a instrução contextual respeitando probabilidade e cooldown."""
        if not user_content or len(user_content.strip()) < 8:
            return ""

        agora = time.time()
        if agora - self._last_trigger.get(context_id, 0) < self.cooldown_seconds:
            return ""

        probabilidade = chance * 0.5 if has_persona else chance
        if random.random() > probabilidade:
            return ""

        fato = await self._buscar_curiosidade_vetorial(user_content)

        if not fato:
            fato = self._buscar_curiosidade_tematica(user_content)

        if fato:
            self._last_trigger[context_id] = agora
            return (
                f"\n[INSTRUÇÃO DE CURIOSIDADE OPCIONAL]:\n"
                f"Se o tom da conversa permitir de forma natural e sem parecer forçado, "
                f"você pode incluir este fato interessante ao final da resposta ('Você sabia que...'):\n"
                f'"{fato}"\n'
            )

        return ""
