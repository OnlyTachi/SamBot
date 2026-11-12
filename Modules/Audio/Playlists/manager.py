import logging
from typing import Any, Dict, List, Optional
from Brain.Memory.DataManager.Connections import data_manager


class PlaylistManager:
    """
    Gerencia playlists salvas por usuário de forma integrada ao DataManager (SQLite).
    Mantém a assinatura assíncrona para preservar total compatibilidade com os comandos.
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Playlists.Manager")

    async def create_playlist(self, user_id: str, name: str, tracks: list) -> bool:
        uid = str(user_id)
        playlists: Dict[str, Any] = data_manager.get_user_data(
            uid, "playlists", default_value={}
        )

        clean_tracks = []
        for t in tracks:
            url = getattr(t, "uri", None) or (
                t.get("url") if isinstance(t, dict) else None
            )
            title = getattr(t, "title", None) or (
                t.get("title") if isinstance(t, dict) else None
            )

            if url:
                clean_tracks.append({"url": url, "title": title or "Desconhecido"})

        playlists[name] = clean_tracks
        data_manager.set_user_data(uid, "playlists", playlists)
        return True

    async def get_playlist(
        self, user_id: str, name: str
    ) -> Optional[List[Dict[str, str]]]:
        playlists: Dict[str, Any] = data_manager.get_user_data(
            str(user_id), "playlists", default_value={}
        )
        return playlists.get(name, None)

    async def list_playlists(self, user_id: str) -> List[str]:
        playlists: Dict[str, Any] = data_manager.get_user_data(
            str(user_id), "playlists", default_value={}
        )
        return list(playlists.keys())

    async def delete_playlist(self, user_id: str, name: str) -> bool:
        uid = str(user_id)
        playlists: Dict[str, Any] = data_manager.get_user_data(
            uid, "playlists", default_value={}
        )
        if name in playlists:
            del playlists[name]
            data_manager.set_user_data(uid, "playlists", playlists)
            return True
        return False


playlist_manager = PlaylistManager()
