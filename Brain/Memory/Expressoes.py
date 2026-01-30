import random
from .DataManager import data_manager
class ExpressoesManager:
    """
    Gerencia reações e expressões idiomáticas do bot.
    Carrega dados de 'IA/Data/Knowledge/expressoes_data.json' via DataManager.
    """
    def __init__(self):
        # Carrega o dicionário de expressões via DataManager
        # Espera estrutura: {"padrao": ["hmm", "olha só"], "risada": ["haha", "kkk"]}
        self.data = data_manager.get_expressions()

    def get_reaction(self, content: str) -> str:
        """Retorna uma reação curta baseada no conteúdo ou aleatória"""
        if not self.data:
            return ""

        content_lower = content.lower()
        
        reaction_pool = []
        
        if any(w in content_lower for w in ['kkk', 'haha', 'lol', 'engraçado']):
            reaction_pool = self.data.get('risada', [])
        elif any(w in content_lower for w in ['triste', 'chorar', 'ruim']):
            reaction_pool = self.data.get('triste', [])
        elif any(w in content_lower for w in ['uau', 'nossa', 'incrivel']):
            reaction_pool = self.data.get('surpresa', [])
        else:
            reaction_pool = self.data.get('padrao', [])
        # err...

        if reaction_pool:
            return random.choice(reaction_pool)
        
        return ""