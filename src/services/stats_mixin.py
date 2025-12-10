import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from yandex_music import Client

from .helpers_mixin import YandexMusicHelperMixin

logger = logging.getLogger(__name__)


class YandexMusicStatsMixin(YandexMusicHelperMixin):
    async def _get_liked_tracks_count(self, token: str, user_id: int) -> int:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return 0
            likes = client.users_likes_tracks()
            tracks = getattr(likes, "tracks", []) or []
            return len(tracks)
        except Exception as e:
            logger.error(f"Ошибка при получении количества понравившихся треков пользователя {user_id}: {e}")
            return 0

    async def _get_recent_likes_count(self, token: str, user_id: int, days: int = 30) -> int:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return 0
            likes = client.users_likes_tracks()
            tracks = getattr(likes, "tracks", []) or []
            threshold = datetime.now(timezone.utc) - timedelta(days=days)
            count = 0
            for track_ref in tracks:
                ts = self._normalize_timestamp(getattr(track_ref, "timestamp", None) or getattr(track_ref, "added", None))
                if ts and ts >= threshold:
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Ошибка при подсчёте лайков за период у пользователя {user_id}: {e}")
            return 0

    async def _get_top_genres_from_recent(self, token: str, user_id: int, limit: int = 5, days: int = 90) -> List[Dict[str, Any]]:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return []
            history_items = self._get_recent_history(client)
            threshold = datetime.now(timezone.utc) - timedelta(days=days)
            tracks_with_ts = self._collect_tracks_from_history(client, history_items)
            counter: Counter = Counter()
            for track, ts in tracks_with_ts:
                if ts and ts < threshold:
                    continue
                genre = self._extract_genre(track)
                if genre:
                    counter[genre] += 1
            return self._to_top_list(counter, limit)
        except Exception as e:
            logger.error(f"Ошибка при получении топа жанров из истории пользователя {user_id}: {e}")
            return []

    async def _get_listening_minutes(self, token: str, user_id: int, days: int = 7) -> int:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return 0
            history_items = self._get_recent_history(client)
            threshold = datetime.now(timezone.utc) - timedelta(days=days)
            tracks_with_ts = self._collect_tracks_from_history(client, history_items)
            total_ms = 0
            for track, ts in tracks_with_ts:
                if ts and ts < threshold:
                    continue
                duration_ms = self._extract_duration_ms(track)
                if duration_ms:
                    total_ms += duration_ms
            return int(total_ms / 60000)
        except Exception as e:
            logger.error(f"Ошибка при вычислении времени прослушивания для пользователя {user_id}: {e}")
            return 0

    async def _get_top_artists(self, token: str, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return []

            history_items = self._get_recent_history(client)
            tracks_with_ts = self._collect_tracks_from_history(client, history_items)
            counter: Counter = Counter()
            for track, _ in tracks_with_ts:
                for artist_name in self._extract_artists(track):
                    counter[artist_name] += 1

            if not counter:
                likes = client.users_likes_tracks()
                liked_full_tracks = self._fetch_tracks(client, getattr(likes, "tracks", []) or [])
                for track in liked_full_tracks:
                    for artist_name in self._extract_artists(track):
                        counter[artist_name] += 1
            return self._to_top_list(counter, limit)
        except Exception as e:
            logger.error(f"Ошибка при получении топа артистов пользователя {user_id}: {e}")
            return []

    async def _get_top_genres_from_library(self, token: str, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            client = self.get_client(token, user_id)
            if client is None:
                return []

            counter: Counter = Counter()
            likes = client.users_likes_tracks()
            liked_tracks = self._fetch_tracks(client, getattr(likes, "tracks", []) or [])
            for track in liked_tracks:
                genre = self._extract_genre(track)
                if genre:
                    counter[genre] += 1

            uid = self._get_account_uid(client)
            if uid is not None:
                playlist_tracks = self._get_playlist_tracks(client, uid)
                for track in playlist_tracks:
                    genre = self._extract_genre(track)
                    if genre:
                        counter[genre] += 1

            return self._to_top_list(counter, limit)
        except Exception as e:
            logger.error(f"Ошибка при получении топа жанров библиотеки пользователя {user_id}: {e}")
            return []

