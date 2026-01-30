import json
import logging
import aiofiles
from Brain.Memory.DataManager import data_manager

class PlaylistManager:
    """
    Gerencia playlists salvas localmente em JSON de forma assíncrona.
    Usa o DataManager para garantir o caminho correto no Docker.
    """
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Modules.Audio.PlaylistManager")
        self.filepath = data_manager.folders["persistence"] / "playlists.json"

    async def _ensure_file(self):
        """Garante que o arquivo JSON exista com um objeto vazio."""
        if not self.filepath.exists():
            try:
                async with aiofiles.open(self.filepath, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps({}, indent=4))
            except Exception as e:
                self.logger.error(f"Erro ao criar arquivo de playlist: {e}")

    async def _load_data(self):
        """Carrega os dados do arquivo JSON de forma assíncrona."""
        await self._ensure_file()
        try:
            async with aiofiles.open(self.filepath, 'r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():
                    return {} 
                return json.loads(content)
        except Exception as e:
            self.logger.error(f"Erro ao carregar playlists: {e}")
            return {}

    async def _save_data(self, data):
        """Salva os dados no arquivo JSON."""
        try:
            async with aiofiles.open(self.filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=4, ensure_ascii=False))
        except Exception as e:
            self.logger.error(f"Erro ao salvar playlists: {e}")

    async def create_playlist(self, user_id: str, name: str, tracks: list):
        """Cria ou sobrescreve uma playlist para um usuário específico."""
        data = await self._load_data()
        uid = str(user_id)
        if uid not in data:
            data[uid] = {}
        
        clean_tracks = []
        for t in tracks:
            url = getattr(t, 'uri', None) or (t.get('url') if isinstance(t, dict) else None)
            title = getattr(t, 'title', None) or (t.get('title') if isinstance(t, dict) else None)
            
            if url: 
                clean_tracks.append({
                    "url": url, 
                    "title": title or "Desconhecido"
                })
        
        data[uid][name] = clean_tracks
        await self._save_data(data)
        return True

    async def get_playlist(self, user_id: str, name: str):
        """Retorna os dados de uma playlist específica."""
        data = await self._load_data()
        return data.get(str(user_id), {}).get(name, None)

    async def list_playlists(self, user_id: str):
        """Lista os nomes de todas as playlists de um usuário."""
        data = await self._load_data()
        return list(data.get(str(user_id), {}).keys())

    async def delete_playlist(self, user_id: str, name: str):
        """Remove uma playlist do armazenamento."""
        data = await self._load_data()
        uid = str(user_id)
        if uid in data and name in data[uid]:
            del data[uid][name]
            await self._save_data(data)
            return True
        return False

# Instância global para uso nos módulos de áudio
playlist_manager = PlaylistManager()