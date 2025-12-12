import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional, Dict, Tuple

from yandex_music import Client

logger = logging.getLogger(__name__)


class YandexMusicHelperMixin:
    @staticmethod
    def _normalize_timestamp(value: Any) -> Optional[datetime]:
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
        for album in getattr(track, "albums", []) or []:
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

    def _search_track_id(self, client: Client, query: str) -> Optional[str]:
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
        try:
            playlists = client.users_playlists(uid)
            for playlist in playlists or []:
                if getattr(playlist, "title", "").lower() == title.lower():
                    return playlist
            return None
        except Exception as e:
            logger.error(f"Не удалось получить плейлисты для поиска '{title}': {e}")
            return None

