# Brain/Memory/SelfKnowledge/Manager.py
import logging
from .PersonaState import PersonaState
from .SystemInspector import SystemInspector
from .CuriosidadeContextual import CuriosidadeContextual


class SelfKnowledgeManager:
    """Orquestrador Central de Autoconhecimento"""

    def __init__(self, bot=None, llm_factory=None, vector_store=None):
        self.logger = logging.getLogger("SamBot.SelfKnowledge")
        self.inspector = SystemInspector(bot, llm_factory, vector_store)
        self.persona = PersonaState()
        self.curiosidades = CuriosidadeContextual(vector_store)

    def build_self_context(self) -> str:
        """Constrói o bloco contextual completo para autoconhecimento e telemetria."""
        identidade = self.persona.get_base_identity()
        status = self.inspector.get_system_snapshot()
        tracos = self.persona.get_community_traits()
        tracos_str = "\n".join([f"- {t}" for t in tracos])

        return (
            f"\n=== ESTADO INTERNO E IDENTIDADE ===\n"
            f"Nome: {identidade.get('name', 'SamBot')} (v{identidade.get('version', '3.0')})\n"
            f"Descrição: {identidade.get('description', '')}\n"
            f"• Uptime: {status['uptime']} | Latência Discord: {status['latencia_discord']}\n"
            f"• Servidores: {status['servidores']} | Usuários no Alcance: {status['usuarios_alcancados']}\n"
            f"• Mensagens Processadas: {status['mensagens_lidas']} | Comandos Usados: {status['comandos_executados']}\n"
            f"• Tempo em Canais de Voz: {status['tempo_voz_minutos']} minutos\n"
            f"• Motor de IA Ativo: {status['driver_primario']} (Cadeia: {', '.join(status['provedores_ativos'])})\n"
            f"• Memórias no Vector Store: {status['total_memorias_rag']} registros\n"
            f"Traços & Percepções do Servidor:\n{tracos_str}\n"
            f"====================================================\n"
        )

    async def get_curiosity_instruction(
        self, text: str, context_id: str, has_persona: bool
    ) -> str:
        """Repassa a geração de curiosidade contextual."""
        return await self.curiosidades.get_curiosity_prompt(
            text, context_id, has_persona
        )

    def is_self_inquiry(self, text: str) -> bool:
        gatilhos = [
            "quem é você",
            "quem e voce",
            "te criou",
            "seu autor",
            "sua tecnologia",
            "como você funciona",
            "seus status",
            "uptime",
        ]
        return any(g in text.lower() for g in gatilhos)

    def get_identity_prompt(self) -> str:
        return self.build_self_context()
