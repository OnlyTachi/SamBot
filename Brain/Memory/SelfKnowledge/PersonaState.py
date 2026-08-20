from Brain.Memory.DataManager.Connections import data_manager


class PersonaState:
    """Gerencia traços de personalidade, humor e memórias da bot."""

    @staticmethod
    def get_base_identity() -> dict:
        return data_manager.get_identity()

    @staticmethod
    def get_community_traits() -> list:
        """Fatos que a Sam assimilou sobre o servidor (gerados no NightCycle)."""
        data = data_manager.get_knowledge("bot_milestones") or {}
        return data.get(
            "traits",
            [
                "Gosta de interagir com o pessoal do servidor",
                "Tem tom sarcástico porém prestativo",
            ],
        )
