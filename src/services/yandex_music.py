from yandex_music import Client
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class YandexMusicService:
    def __init__(self):
        self.clients = {}
    
    def get_client(self, token: str, user_id: int) -> Optional[Client]:
        try:
            if user_id in self.clients:
                return self.clients[user_id]
            
            client = Client(token)
            self.clients[user_id] = client
            logger.info(f"Создан новый клиент для пользователя {user_id}")
            return client
        except Exception as e:
            logger.error(f"Ошибка при создании клиента для пользователя {user_id}: {e}")
            return None

    async def get_user_playlists(self, token: str, user_id: int) -> List[Dict[str, Any]]:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                logger.error(f"Не удалось получить клиент для пользователя {user_id}")
                return []
            
            account = client.account_status()
            if account is None:
                logger.error(f"Не удалось получить информацию об аккаунте для пользователя {user_id}")
                return []
            
            playlists = client.users_playlists(account.account.uid)
            
            result = []
            for playlist in playlists:
                playlist_info = {
                    'kind': playlist.kind,
                    'title': playlist.title,
                    'description': playlist.description if hasattr(playlist, 'description') else None,
                    'track_count': playlist.track_count if hasattr(playlist, 'track_count') else 0,
                    'created': playlist.created.isoformat() if hasattr(playlist, 'created') and playlist.created else None,
                    'modified': playlist.modified.isoformat() if hasattr(playlist, 'modified') and playlist.modified else None,
                    'cover': playlist.cover.uri if hasattr(playlist, 'cover') and playlist.cover else None,
                }
                result.append(playlist_info)
            
            logger.info(f"Получено {len(result)} плейлистов для пользователя {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении плейлистов для пользователя {user_id}: {e}")
            return []

    async def get_song_lyrics(self, token: str, user_id: int, track_id: str) -> Optional[str]:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                logger.error(f"Не удалось получить клиент для пользователя {user_id}")
                return None
            
            tracks = client.tracks([track_id])
            if not tracks or len(tracks) == 0:
                logger.error(f"Трек с ID {track_id} не найден")
                return None
            
            track = tracks[0]
            
            lyrics = track.get_lyrics()
            if lyrics is None:
                logger.warning(f"Текст песни недоступен для трека {track_id}")
                return None
            
            full_lyrics = lyrics.full_lyrics
            if full_lyrics is None:
                logger.warning(f"Полный текст песни недоступен для трека {track_id}")
                return None
            
            logger.info(f"Получен текст песни для трека {track_id}")
            return full_lyrics
            
        except Exception as e:
            logger.error(f"Ошибка при получении текста песни для трека {track_id}: {e}")
            return None

    async def create_playlist(self, token: str, user_id: int, title: str, tracks: List[str] = None) -> Optional[Dict[str, Any]]:
        pass
    