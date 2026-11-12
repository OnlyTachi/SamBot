# Brain/Memory/SelfKnowledge/Manager.py
import logging
from .PersonaState import PersonaState
from .SystemInspector import SystemInspector
from .CuriosidadeContextual import CuriosidadeContextual


class SelfKnowledgeManager:
    """Orquestrador Central de Autoconhecimento e Introspecção"""

    def __init__(self, bot=None, llm_factory=None, vector_store=None):
        self.logger = logging.getLogger("SamBot.SelfKnowledge")
        self.inspector = SystemInspector(bot, llm_factory, vector_store)
        self.persona = PersonaState()
        self.curiosidades = CuriosidadeContextual(vector_store)

    def build_self_context(
        self,
        intent_type: str = "self_identity",
        user_id: str = None,
        user_name: str = "Usuário",
    ) -> str:
        """Constrói o bloco contextual completo para autoconhecimento, telemetria e vínculo com o interlocutor."""
        identidade = self.persona.get_base_identity()
        status = self.inspector.get_system_snapshot()
        capabilities = self.persona.get_capabilities()
        brain_arch = self.persona.get_brain_architecture()
        directives = self.persona.get_security_directives()
        traits = self.persona.get_community_traits()

        cap_str = "\n".join([f"- {c}" for c in capabilities])
        traits_str = "\n".join([f"- {t}" for t in traits])
        rules_str = "\n".join([f"- {r}" for r in directives])

        TACHI_ID = str(identidade.get("creator_id", "845016606571626498"))
        is_pai = str(user_id) == TACHI_ID

        if is_pai:
            status_interlocutor = (
                "ATENÇÃO: O INTERLOCUTOR ATUAL É O SEU PAI E CRIADOR (tachi)!\n"
                "- Responda diretamente para ele na 1ª/2ª pessoa com carinho, proximidade e orgulho.\n"
                "- Em vez de falar 'meu criador é o tachi', diga: 'É você, Bobo!' ou 'Você que me criou, tachi! Ta ficando velho e nem percebe o que pergunta'."
            )
        else:
            status_interlocutor = (
                f"Interlocutor atual: {user_name} (ID: {user_id})\n"
                f"- Responda educadamente informando que seu criador/pai é o **tachi**."
            )

        return (
            f"\n=== MÓDULO DE AUTOCONHECIMENTO & IDENTIDADE ===\n"
            f"Nome: {identidade.get('name', 'SamBot')} | Versão: {identidade.get('version', '3.1.0')}\n"
            f"Criador/Pai: {identidade.get('author', 'Tachi')} (ID: {TACHI_ID})\n"
            f"Descrição: {identidade.get('description', '')}\n\n"
            f"[VÍNCULO COM O INTERLOCUTOR]:\n"
            f"{status_interlocutor}\n\n"
            f"[ESTADO OPERACIONAL EM TEMPO REAL]:\n"
            f"- Uptime: {status['uptime']} | Latência Discord: {status['latencia_discord']}\n"
            f"- Provedor Primário: {status['driver_primario']} (Cadeia: {', '.join(status['provedores_ativos'])})\n"
            f"- Servidores Conectados: {status['servidores']} | Registros RAG no Vetorial: {status['total_memorias_rag']}\n\n"
            f"[SUAS CAPACIDADES E FERRAMENTAS REAIS]:\n{cap_str}\n\n"
            f"[SUA ARQUITETURA DE INTELIGÊNCIA]:\n"
            f"- Roteador Semântico: {brain_arch.get('router')}\n"
            f"- Camada Primária: {brain_arch.get('layer_1')}\n"
            f"- Failover/Backup: {brain_arch.get('layer_1_5')}, {brain_arch.get('layer_2')}\n\n"
            f"[PERCEPÇÃO DA COMUNIDADE & TRAÇOS]:\n{traits_str}\n\n"
            f"[DIRETRIZES DE SEGURANÇA E CONDUTA]:\n{rules_str}\n\n"
            f"[INSTRUÇÃO DE RESPOSTA]:\n"
            f"Responda na primeira pessoa ('eu'). Seja carismática, levemente sarcástica e fiel aos dados acima. "
            f"Quando perguntada sobre suas ferramentas ou preferências (ex: notícias vs. banco de dados), "
            f"expresse sua opinião de forma natural e reflexiva usando sua persona, apontando vantagens de cada recurso que você possui.\n"
            f"================================================\n"
        )

    async def get_curiosity_instruction(
        self, text: str, context_id: str, has_persona: bool
    ) -> str:
        return await self.curiosidades.get_curiosity_prompt(
            text, context_id, has_persona
        )
