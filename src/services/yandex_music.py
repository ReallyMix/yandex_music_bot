import logging
from typing import Any, Dict, List, Optional

from yandex_music import Client

from .helpers_mixin import YandexMusicHelperMixin
from .stats_mixin import YandexMusicStatsMixin

logger = logging.getLogger(__name__)


class YandexMusicService(YandexMusicStatsMixin, YandexMusicHelperMixin):
    def __init__(self):
        self.clients: Dict[int, Client] = {}

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
                    "kind": playlist.kind,
                    "title": playlist.title,
                    "description": playlist.description if hasattr(playlist, "description") else None,
                    "track_count": playlist.track_count if hasattr(playlist, "track_count") else 0,
                    "created": playlist.created.isoformat() if hasattr(playlist, "created") and playlist.created else None,
                    "modified": playlist.modified.isoformat() if hasattr(playlist, "modified") and playlist.modified else None,
                    "cover": playlist.cover.uri if hasattr(playlist, "cover") and playlist.cover else None,
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

    async def create_playlist(self, token: str, user_id: int, title: str, tracks: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return None

            account_uid = self._get_account_uid(client)
            if account_uid is None:
                logger.error(f"Не удалось определить uid для пользователя {user_id}")
                return None

            playlist = client.users_playlists_create(title)
            if playlist is None:
                logger.error(f"Не удалось создать плейлист '{title}' для пользователя {user_id}")
                return None

            if tracks:
                added = 0
                for track_id in tracks:
                    formatted = self._format_track_id(track_id) or str(track_id)
                    try:
                        client.users_playlists_insert_track(account_uid, playlist.kind, formatted)
                        added += 1
                    except Exception as e:
                        logger.warning(f"Не удалось добавить трек {formatted} в плейлист '{title}': {e}")
                logger.info(f"Добавлено {added}/{len(tracks)} треков в плейлист '{title}'")

            logger.info(f"Создан плейлист '{title}' для пользователя {user_id}")
            return {
                "kind": getattr(playlist, "kind", None),
                "title": getattr(playlist, "title", title),
                "uid": account_uid,
            }
        except Exception as e:
            logger.error(f"Ошибка при создании плейлиста '{title}' для пользователя {user_id}: {e}")
            return None

    async def add_tracks_by_name(self, token: str, user_id: int, playlist_title: str, track_names: List[str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {"added": [], "failed": []}
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return result

            account_uid = self._get_account_uid(client)
            if account_uid is None:
                logger.error(f"Не удалось определить uid для пользователя {user_id}")
                return result

            playlist = self._find_playlist_by_title(client, account_uid, playlist_title)
            if playlist is None:
                playlist = client.users_playlists_create(playlist_title)
                if playlist is None:
                    logger.error(f"Не удалось создать плейлист '{playlist_title}'")
                    return result

            kind = getattr(playlist, "kind", None)
            if kind is None:
                logger.error(f"Не удалось получить kind плейлиста '{playlist_title}'")
                return result

            for name in track_names:
                track_id = self._search_track_id(client, name)
                if not track_id:
                    result["failed"].append({"query": name, "reason": "not_found"})
                    continue
                try:
                    client.users_playlists_insert_track(account_uid, kind, track_id)
                    result["added"].append({"query": name, "track_id": track_id})
                except Exception as e:
                    logger.warning(f"Не удалось добавить трек '{name}' ({track_id}) в плейлист '{playlist_title}': {e}")
                    result["failed"].append({"query": name, "reason": "api_error"})
            return result
        except Exception as e:
            logger.error(f"Ошибка при добавлении треков в плейлист '{playlist_title}': {e}")
            return result

    async def like_track(self, token: str, user_id: int, track_query: str) -> bool:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return False

            track_id = self._format_track_id(track_query) or self._search_track_id(client, track_query)
            if not track_id:
                logger.warning(f"Трек '{track_query}' не найден для лайка")
                return False

            client.users_likes_tracks_add(track_id)
            logger.info(f"Поставлен лайк треку {track_id} (запрос: {track_query}) для пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при попытке лайкнуть трек '{track_query}': {e}")
            return False

    async def get_user_statistics(self, token: str, user_id: int) -> Dict[str, Any]:
        client = self.get_client(token, user_id)
        if client is None:
            return {}

        liked_tracks_count = await self._get_liked_tracks_count(token, user_id)
        recent_likes_month = await self._get_recent_likes_count(token, user_id, days=30)
        top_genres_recent = await self._get_top_genres_from_recent(token, user_id, limit=5, days=90)
        minutes_week = await self._get_listening_minutes(token, user_id, days=7)
        minutes_month = await self._get_listening_minutes(token, user_id, days=30)
        top_artists = await self._get_top_artists(token, user_id, limit=5)
        top_genres_library = await self._get_top_genres_from_library(token, user_id, limit=5)

        return {
            "liked_tracks_count": liked_tracks_count,
            "recent_likes_last_month": recent_likes_month,
            "top_genres_recent": top_genres_recent,
            "listening_minutes": {"week": minutes_week, "month": minutes_month},
            "top_artists": top_artists,
            "top_genres_library": top_genres_library,
        }
