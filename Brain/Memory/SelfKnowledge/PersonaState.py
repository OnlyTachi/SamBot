from Brain.Memory.DataManager.Connections import data_manager


class PersonaState:
    """Gerencia traços de personalidade, humor e capacidades da Sam"""

    @staticmethod
    def get_base_identity() -> dict:
        return data_manager.get_identity()

    @staticmethod
    def get_capabilities() -> list:
        identity = data_manager.get_identity() or {}
        return identity.get("capabilities", [])

    @staticmethod
    def get_brain_architecture() -> dict:
        identity = data_manager.get_identity() or {}
        return identity.get("brain", {})

    @staticmethod
    def get_security_directives() -> list:
        identity = data_manager.get_identity() or {}
        return identity.get("security_directives", [])

    @staticmethod
    def get_community_traits() -> list:
        data = data_manager.get_knowledge("bot_milestones") or {}
        return data.get(
            "traits",
            [
                "Gosta de interagir com o pessoal do servidor",
                "Tem tom sarcástico porém prestativo",
            ],
        )
