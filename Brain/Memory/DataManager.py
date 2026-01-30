import json
import os
import glob
import logging
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional

# aqui e o dominio da bagunça dos dados do bot
class NeuralArchive:
    """
    Gestor Unificado de Dados (SamBot v3.0).
    Combina persistência em disco, cache em memória e thread-safety.
    """
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Archive")
        self._lock = threading.Lock() 
        
        self.base_dir = Path(__file__).resolve().parent
        
        self.root = self.base_dir.parent.parent / "Data"
        
        self.folders = {
            "config": self.root / "Config",
            "prompts": self.root / "Prompts",
            "knowledge": self.root / "Knowledge",
            "persistence": self.root / "Persistence"
        }

        for folder in self.folders.values():
            folder.mkdir(parents=True, exist_ok=True)

        self._cache = {
            "identity": None,
            "prompts": {},
            "nlp": None,
            "expressions": None,
            "channels": None
        }

    # --- NÚCLEO DE I/O (ENTRADA E SAÍDA) ---

    def _io_read_json(self, path: Path, default_type: Any = dict) -> Any:
        """Lê JSON com tratamento de erro e correção de estrutura."""
        if not path.exists():
            return default_type()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if default_type is dict and not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Erro ao ler JSON em {path.name}: {e}")
            return default_type()

    def _io_save_json(self, path: Path, data: Any):
        """Salva JSON de forma segura usando Thread Lock."""
        with self._lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Falha crítica ao salvar {path.name}: {e}")

    # --- IDENTIDADE E CONFIGURAÇÃO ---

    def get_identity(self) -> Dict:
        """Recupera os dados de identidade do bot."""
        if self._cache["identity"]:
            return self._cache["identity"]
            
        path = self.folders["config"] / "identity.json"
        data = self._io_read_json(path)
        
        if not data:
            data = {"name": "SamBot", "version": "3.0", "status": "online"}
            
        self._cache["identity"] = data
        return data

    # --- SISTEMA DE PROMPTS (PERSONAS) ---

    def get_prompt(self, persona: str = "padrao") -> str:
        """Lê a persona do disco ou do cache."""
        filename = f"{persona.replace('.txt', '')}.txt"
        
        if filename in self._cache["prompts"]:
            return self._cache["prompts"][filename]

        path = self.folders["prompts"] / filename
        
        if not path.exists():
            if persona != "padrao":
                self.logger.warning(f"Persona {persona} não encontrada, usando 'padrao'.")
                return self.get_prompt("padrao")
            return "Você é o SamBot, um assistente inteligente."

        try:
            content = path.read_text(encoding='utf-8').strip()
            self._cache["prompts"][filename] = content
            return content
        except Exception as e:
            self.logger.error(f"Erro ao carregar ficheiro de prompt: {e}")
            return "Erro interno ao carregar personalidade."

    def list_available_personalities(self) -> List[str]:
        """Lista todos os nomes de personas disponíveis."""
        files = self.folders["prompts"].glob("*.txt")
        return [f.stem for f in files]

    # --- CONHECIMENTO E NLP ---

    def get_knowledge(self, key: str) -> Any:
        """
        Acesso genérico a dados em Knowledge.
        Ex: get_knowledge('expressoes_data') ou get_knowledge('atividades')
        """
        if key == "nlp_data" and self._cache["nlp"]: return self._cache["nlp"]
        if key == "expressoes_data" and self._cache["expressions"]: return self._cache["expressions"]

        path = self.folders["knowledge"] / f"{key.replace('.json', '')}.json"
        data = self._io_read_json(path)

        if "nlp" in key: self._cache["nlp"] = data
        if "expressoes" in key: self._cache["expressions"] = data
        
        return data

    def save_knowledge(self, key: str, data: Any):
        """
        Salva dados na pasta Knowledge e atualiza o cache.
        Necessário para que save_music_preference funcione.
        """
        path = self.folders["knowledge"] / f"{key.replace('.json', '')}.json"
        
        self._io_save_json(path, data)
        
        if "nlp" in key: self._cache["nlp"] = data
        if "expressoes" in key: self._cache["expressions"] = data

    def get_expressions(self) -> Dict:
        """Atalho para recuperar dados de expressões."""
        return self.get_knowledge("expressoes_data")

    def save_music_preference(self, user_id, genre_or_artist):
        """Guarda um gosto musical específico do utilizador."""
        data = self.get_knowledge('nlp_data')
        
        if 'music_preferences' not in data:
            data['music_preferences'] = {}
        
        user_id_str = str(user_id)
        if user_id_str not in data['music_preferences']:
            data['music_preferences'][user_id_str] = []
            
        if genre_or_artist not in data['music_preferences'][user_id_str]:
            data['music_preferences'][user_id_str].append(genre_or_artist)
            self.save_knowledge('nlp_data', data)
            self.logger.info(f"Gosto musical '{genre_or_artist}' salvo para o usuário {user_id}")
    
    def get_user_music_context(self, user_id):
        """Retorna os gostos musicais conhecidos do utilizador para contextualizar a IA."""
        data = self.get_knowledge('nlp_data')
        prefs = data.get('music_preferences', {}).get(str(user_id), [])
        if prefs:
            return f"O utilizador gosta de: {', '.join(prefs)}."
        return ""

    # --- PERSISTÊNCIA DE CANAIS ---

    def load_active_channels(self) -> Dict:
        """Carrega canais onde o bot está ativo."""
        if self._cache["channels"]: return self._cache["channels"]
        
        path = self.folders["config"] / "channels.json"
        if not path.exists():
            path = self.folders["persistence"] / "channels.json"
            
        data = self._io_read_json(path, default_type=dict)
        self._cache["channels"] = data
        return data

    def save_active_channels(self, data: Dict):
        """Salva os canais ativos e atualiza o cache."""
        if not isinstance(data, dict): return
        
        path = self.folders["config"] / "channels.json"
        self._cache["channels"] = data
        self._io_save_json(path, data)

    # --- UTILITÁRIOS ---

    def reload_all(self):
        """Limpa todo o cache e força nova leitura do disco."""
        self._cache = {
            "identity": None,
            "prompts": {},
            "nlp": None,
            "expressions": None,
            "channels": None
        }
        self.logger.info("♻️ NeuralArchive: Cache limpo com sucesso.")

# Exporta a instância única
data_manager = NeuralArchive()