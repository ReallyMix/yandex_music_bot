from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Iterable, Tuple
from yandex_music import Client
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
        """Добавляет треки по названию в плейлист. Создаёт плейлист, если его нет."""
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
        """Ставит лайк треку по ID или названию."""
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
    
    @staticmethod
    def _normalize_timestamp(value: Any) -> Optional[datetime]:
        """Пытаемся привести различные варианты времени к datetime в UTC."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value, tz=timezone.utc)
            except Exception:
                return None
        if isinstance(value, str):
            try:
                sanitized = value.replace("Z", "+00:00")
                return datetime.fromisoformat(sanitized)
            except Exception:
                return None
        return None

    @staticmethod
    def _format_track_id(track_like: Any) -> Optional[str]:
        """Преобразует объект трека/ссылки на трек в строковый идентификатор для client.tracks."""
        if isinstance(track_like, str):
            return track_like
        track_id = getattr(track_like, "id", None) or getattr(track_like, "track_id", None)
        album_id = getattr(track_like, "album_id", None) or getattr(track_like, "albumId", None)
        if track_id and album_id:
            return f"{track_id}:{album_id}"
        if track_id:
            return str(track_id)
        return None

    @staticmethod
    def _extract_artists(track: Any) -> List[str]:
        artists = []
        for artist in getattr(track, "artists", []) or []:
            name = getattr(artist, "name", None)
            if name:
                artists.append(name)
        return artists

    @staticmethod
    def _extract_genre(track: Any) -> Optional[str]:
        genre = getattr(track, "genre", None)
        if genre:
            return genre
        albums = getattr(track, "albums", []) or []
        for album in albums:
            album_genre = getattr(album, "genre", None)
            if album_genre:
                return album_genre
        return None

    @staticmethod
    def _extract_duration_ms(track: Any) -> Optional[int]:
        duration_ms = getattr(track, "duration_ms", None)
        if duration_ms is not None:
            return duration_ms
        duration_seconds = getattr(track, "duration", None)
        if duration_seconds is not None:
            try:
                return int(duration_seconds * 1000)
            except Exception:
                return None
        return None

    def _to_top_list(self, counter: Counter, limit: int = 5) -> List[Dict[str, Any]]:
        return [{"name": name, "count": count} for name, count in counter.most_common(limit)]

    def _search_track_id(self, client: Client, query: str) -> Optional[str]:
        """Ищет трек по текстовому запросу и возвращает track_id:album_id."""
        try:
            search_result = client.search(query, type_="track", page=0)
            tracks = getattr(search_result, "tracks", None)
            if tracks is None:
                return None
            items = getattr(tracks, "results", []) or []
            if not items:
                return None
            track = items[0]
            return self._format_track_id(track)
        except Exception as e:
            logger.warning(f"Не удалось найти трек по запросу '{query}': {e}")
            return None

    def _find_playlist_by_title(self, client: Client, uid: int, title: str) -> Optional[Any]:
        """Ищет плейлист пользователя по названию (без учёта регистра)."""
        try:
            playlists = client.users_playlists(uid)
            for playlist in playlists or []:
                if getattr(playlist, "title", "").lower() == title.lower():
                    return playlist
            return None
        except Exception as e:
            logger.error(f"Не удалось получить плейлисты для поиска '{title}': {e}")
            return None

    def _fetch_tracks(self, client: Client, track_refs: Iterable[Any]) -> List[Any]:
        track_ids = []
        for ref in track_refs:
            track_id = self._format_track_id(ref)
            if track_id:
                track_ids.append(track_id)
        if not track_ids:
            return []
        try:
            return [t for t in client.tracks(track_ids) if t is not None]
        except Exception as e:
            logger.error(f"Ошибка при получении треков {track_ids}: {e}")
            return []

    def _unwrap_history_items(self, history: Any) -> List[Any]:
        if history is None:
            return []
        if isinstance(history, dict) and "tracks" in history:
            return history.get("tracks") or []
        if hasattr(history, "tracks"):
            return getattr(history, "tracks")
        if isinstance(history, list):
            return history
        return []

    def _get_recent_history(self, client: Client) -> List[Any]:
        """Получаем историю прослушиваний любым доступным методом."""
        possible_calls = [
            ("recent_tracks", lambda: client.recent_tracks()),
            ("rotor_history", lambda: client.rotor_history()),
        ]
        for name, call in possible_calls:
            try:
                history = call()
                items = self._unwrap_history_items(history)
                if items:
                    logger.info(f"Получена история прослушиваний через {name}")
                    return items
            except Exception as e:
                logger.warning(f"Не удалось получить историю через {name}: {e}")
        return []

    def _collect_tracks_from_history(self, client: Client, history_items: List[Any]) -> List[Tuple[Any, Optional[datetime]]]:
        tracks_with_ts: List[Tuple[Any, Optional[datetime]]] = []
        missing_ids: List[Tuple[str, Optional[datetime]]] = []

        for item in history_items:
            timestamp = self._normalize_timestamp(
                getattr(item, "timestamp", None)
                or getattr(item, "play_ts", None)
                or getattr(item, "played", None)
            )
            track_obj = getattr(item, "track", None) or (item if hasattr(item, "artists") else None)
            if track_obj is not None:
                tracks_with_ts.append((track_obj, timestamp))
                continue

            track_id = self._format_track_id(item)
            if track_id:
                missing_ids.append((track_id, timestamp))

        if missing_ids:
            fetched = self._fetch_tracks(client, [tid for tid, _ in missing_ids])
            for fetched_track, (_, ts) in zip(fetched, missing_ids):
                if fetched_track:
                    tracks_with_ts.append((fetched_track, ts))
        return tracks_with_ts

    def _get_account_uid(self, client: Client) -> Optional[int]:
        try:
            account = client.account_status()
            if account and getattr(account, "account", None):
                return account.account.uid
        except Exception as e:
            logger.error(f"Не удалось получить uid пользователя: {e}")
        return None

    def _get_playlist_tracks(self, client: Client, uid: int) -> List[Any]:
        try:
            playlists = client.users_playlists(uid)
        except Exception as e:
            logger.error(f"Не удалось получить плейлисты для uid={uid}: {e}")
            return []

        playlist_track_refs = []
        for playlist in playlists or []:
            for track_ref in getattr(playlist, "tracks", []) or []:
                track_obj = getattr(track_ref, "track", None)
                if track_obj:
                    playlist_track_refs.append(track_obj)
                    continue
                track_id = self._format_track_id(track_ref)
                if track_id:
                    playlist_track_refs.append(track_id)
        return self._fetch_tracks(client, playlist_track_refs)

    async def get_liked_tracks_count(self, token: str, user_id: int) -> int:
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

    async def get_recent_likes_count(self, token: str, user_id: int, days: int = 30) -> int:
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

    async def get_top_genres_from_recent(self, token: str, user_id: int, limit: int = 5, days: int = 90) -> List[Dict[str, Any]]:
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

    async def get_listening_minutes(self, token: str, user_id: int, days: int = 7) -> int:
        """Сумма минут прослушивания за указанный период по истории."""
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

    async def get_top_artists(self, token: str, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
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

    async def get_top_genres_from_library(self, token: str, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Топ жанров из лайкнутых треков и треков из пользовательских плейлистов."""
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

    async def get_user_statistics(self, token: str, user_id: int) -> Dict[str, Any]:
        """Сводная статистика пользователя."""
        client = self.get_client(token, user_id)
        if client is None:
            return {}

        liked_tracks_count = await self.get_liked_tracks_count(token, user_id)
        recent_likes_month = await self.get_recent_likes_count(token, user_id, days=30)
        top_genres_recent = await self.get_top_genres_from_recent(token, user_id, limit=5, days=90)
        minutes_week = await self.get_listening_minutes(token, user_id, days=7)
        minutes_month = await self.get_listening_minutes(token, user_id, days=30)
        top_artists = await self.get_top_artists(token, user_id, limit=5)
        top_genres_library = await self.get_top_genres_from_library(token, user_id, limit=5)

        return {
            "liked_tracks_count": liked_tracks_count,
            "recent_likes_last_month": recent_likes_month,
            "top_genres_recent": top_genres_recent,
            "listening_minutes": {"week": minutes_week, "month": minutes_month},
            "top_artists": top_artists,
            "top_genres_library": top_genres_library,
        }
    