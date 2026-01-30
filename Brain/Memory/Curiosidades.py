# so fiz isso, pq nao ironicamente a sam pediu pra eu fazer
import random
from .DataManager import data_manager
class CuriosidadeManager:
    """
    Gerencia a injeção de curiosidades ou fatos no prompt do sistema.
    Não depende mais de arquivos locais em 'Recursos'.
    """
    def __init__(self):
        self.nlp_data = data_manager.get_nlp_data()

    def get_curiosity_instruction(self, user_content: str, has_persona: bool) -> str:
        """
        Gera uma instrução para o System Prompt sugerindo que a IA
        compartilhe uma curiosidade se o contexto permitir.
        """
        chance = 0.1 if has_persona else 0.3
        
        if random.random() < chance:
            return (
                "\n[INSTRUÇÃO OPCIONAL]: Se o assunto permitir, "
                "finalize sua resposta com uma curiosidade rápida ou fato interessante "
                "relacionado ao tema da conversa ('Você sabia que...')."
            )
        return ""