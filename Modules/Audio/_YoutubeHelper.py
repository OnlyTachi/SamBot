import os
import pickle
import datetime
import re
import logging
import asyncio
from functools import partial
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from Brain.Memory.DataManager import data_manager

class YoutubeHelper:
    """
    Wrapper para a API do YouTube (v3) com suporte a OAuth2 persistente.
    Usa o DataManager para localizar tokens e credenciais corretamente no Docker.
    """
    def __init__(self):
        self.logger = logging.getLogger("SamBot.YoutubeHelper")
        self.SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
        
        # --- CONFIGURAÇÃO DE CAMINHOS ---
        self.TOKEN_DIR = data_manager.folders["persistence"] / "Tokens"
        self.CLIENT_SECRET_FILE = data_manager.folders["config"] / "client_secret.json"
        self.youtube = None       
        self.TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        self._authenticate_default()

    def _authenticate_default(self):
        """Tenta carregar qualquer token existente para operar o bot."""
        token_files = list(self.TOKEN_DIR.glob('*.pickle'))
        
        if token_files:
            self.logger.info(f"Token de autenticação encontrado: {token_files[0].name}")
            self._load_service(token_files[0])
        else:
            self.logger.warning(f"Nenhum token (.pickle) encontrado em: {self.TOKEN_DIR}")

    def _load_service(self, token_path):
        """Carrega o serviço do YouTube usando um token específico."""
        creds = None
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("Token expirado. Tentando atualizar...")
                creds.refresh(Request())
                with open(token_path, 'wb') as token_update:
                    pickle.dump(creds, token_update)
                
            self.youtube = build('youtube', 'v3', credentials=creds)
            self.logger.info("API do YouTube conectada e pronta para uso.")
            
        except Exception as e:
            self.logger.error(f"Erro crítico ao carregar serviço do YouTube ({token_path.name}): {e}")
            self.youtube = None

    def auth_new_user(self, user_id):
        """Inicia fluxo de autenticação para um novo usuário (Geralmente Admin)."""
        if not self.CLIENT_SECRET_FILE.exists():
            self.logger.error(f"Arquivo de segredo não encontrado: {self.CLIENT_SECRET_FILE}")
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.CLIENT_SECRET_FILE), self.SCOPES)
            creds = flow.run_local_server(port=0)

            token_path = self.TOKEN_DIR / f'{user_id}.pickle'
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            
            self.youtube = build('youtube', 'v3', credentials=creds)
            self.logger.info(f"Novo token gerado e salvo para o usuário {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Erro no fluxo de autenticação: {e}")
            return False

    async def search(self, query: str, max_results: int = 10):
        """Busca vídeos no YouTube de forma assíncrona."""
        if not self.youtube:
            self.logger.error("Tentativa de busca ignorada: Serviço YouTube não autenticado.")
            return []

        try:
            loop = asyncio.get_event_loop()
            request = self.youtube.search().list(
                part="snippet",
                maxResults=max_results,
                q=query,
                type="video"
            )
            response = await loop.run_in_executor(None, request.execute)
            
            videos = []
            for item in response.get('items', []):
                videos.append({
                    'id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    'thumbnail': item['snippet']['thumbnails'].get('high', {}).get('url'),
                    'channel': item['snippet']['channelTitle']
                })
            
            return videos[0] if max_results == 1 and videos else videos
            
        except Exception as e:
            self.logger.error(f"Erro na busca do YouTube (query: {query}): {e}")
            return []

    def get_playlist_items(self, playlist_id: str, max_items: int = 50):
        """Recupera IDs de vídeos de uma playlist."""
        if not self.youtube: return []

        videos = []
        next_page_token = None
        
        try:
            while len(videos) < max_items:
                request = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=min(50, max_items - len(videos)),
                    pageToken=next_page_token
                )
                response = request.execute()
                
                for item in response.get('items', []):
                    vid_id = item['snippet']['resourceId']['videoId']
                    videos.append(f"https://www.youtube.com/watch?v={vid_id}")
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
            return videos
        except Exception as e:
            self.logger.error(f"Erro ao obter itens da playlist {playlist_id}: {e}")
            return videos

    def extract_playlist_id(self, url: str) -> str:
        """Extrai o ID da playlist de uma URL do YouTube."""
        match = re.search(r'list=([^&]+)', url)
        return match.group(1) if match else None

    # --- Helpers de UI e Formatação ---
    def create_progress_bar(self, current: int, total: int, length: int = 15) -> str:
        if total <= 0: return "🔘" + "▬" * (length - 1)
        percent = current / total
        filled = int(length * percent)
        filled = max(0, min(filled, length - 1))
        return "▬" * filled + "🔘" + "▬" * (length - filled - 1)

    def parse_duration(self, ms: int) -> str:
        """Converte milissegundos para o formato HH:MM:SS."""
        seconds = ms // 1000
        return str(datetime.timedelta(seconds=seconds))

# Instância global
youtube_helper = YoutubeHelper()