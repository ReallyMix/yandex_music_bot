import logging
from typing import Any, Dict, List, Optional, Tuple

from yandex_music import Client

from .helpers_mixin import YandexMusicHelperMixin
from .stats_mixin import YandexMusicStatsMixin
import requests
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
        from datetime import datetime
        from typing import Optional, Any, List, Dict
        
        def normalize_timestamp(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    return None
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value)
            return None

        try:
            client = self.get_client(token, user_id)
            if client is None:
                logger.error(f"Не удалось получить клиент для пользователя {user_id}")
                return []

            playlists = client.users_playlists_list() or []

            result: List[Dict[str, Any]] = []
            for pl in playlists:
                created_raw = getattr(pl, "created", None) if hasattr(pl, "created") else None
                modified_raw = getattr(pl, "modified", None) if hasattr(pl, "modified") else None

                created_dt = normalize_timestamp(created_raw)
                modified_dt = normalize_timestamp(modified_raw)

                created = created_dt.isoformat() if created_dt else None
                modified = modified_dt.isoformat() if modified_dt else None

                info = {
                    "kind": getattr(pl, "kind", None),
                    "title": getattr(pl, "title", None) or "Без названия",
                    "description": getattr(pl, "description", None)
                    if hasattr(pl, "description")
                    else None,
                    "track_count": getattr(pl, "track_count", None)
                    if hasattr(pl, "track_count")
                    else 0,
                    "created": created,
                    "modified": modified,
                    "cover": pl.cover.uri
                    if hasattr(pl, "cover") and getattr(pl, "cover", None)
                    else None,
                    "owner_login": getattr(getattr(pl, "owner", None), "login", None),
                }
                result.append(info)

            logger.info(f"Получено {len(result)} плейлистов для пользователя {user_id}")
            return result

        except Exception as e:
            logger.error(f"Ошибка при получении плейлистов для пользователя {user_id}: {e}")
            return []

    async def get_song_lyrics(self, token: str, userid: int, track_id: str) -> Optional[str]:
        logger.info(f"get_song_lyrics: START user={userid}, track_id={track_id}")
        try:
            client = self.get_client(token, userid)
            if client is None:
                logger.error(f"get_song_lyrics: no client for user={userid}")
                return None

            tracks = client.tracks([track_id])
            if not tracks:
                logger.warning(f"get_song_lyrics: track not found id={track_id}")
                return None

            track = tracks[0]
            logger.info(f"get_song_lyrics: track loaded: {getattr(track, 'title', 'NO TITLE')}")

            lyrics_obj = getattr(track, "lyrics", None)
            if lyrics_obj is None:
                try:
                    lyrics_obj = track.get_lyrics()
                    logger.info(f"get_song_lyrics: get_lyrics() returned: {lyrics_obj is not None}")
                except Exception as e_lyrics:
                    logger.warning(f"get_song_lyrics: get_lyrics() failed: {e_lyrics}")
                    lyrics_obj = None

            if lyrics_obj is None:
                logger.warning(f"get_song_lyrics: no lyrics object for {track_id}")
                return None

            for attr in ("full_lyrics", "lyrics", "lyrics_text", "text"):
                value = getattr(lyrics_obj, attr, None)
                if isinstance(value, str) and value.strip():
                    logger.info(f"get_song_lyrics: found text in '{attr}', len={len(value)}")
                    return value.strip()

            download_url = getattr(lyrics_obj, "download_url", None) or getattr(
                lyrics_obj, "downloadUrl", None
            )
            if download_url:
                logger.info(f"get_song_lyrics: downloading from {download_url}")
                try:
                    resp = requests.get(download_url, timeout=10)
                    resp.raise_for_status()
                    text_raw = resp.text

                    import re
                    lines = []
                    for line in text_raw.splitlines():
                        clean = re.sub(r"\[[0-9:\.\-]+\]", "", line).strip()
                        if clean:
                            lines.append(clean)

                    if lines:
                        text_clean = "\n".join(lines)
                        logger.info(f"get_song_lyrics: downloaded lyrics len={len(text_clean)}")
                        return text_clean

                    if text_raw.strip():
                        logger.info(
                            f"get_song_lyrics: raw downloaded lyrics used, len={len(text_raw)}"
                        )
                        return text_raw.strip()

                except Exception as e_dl:
                    logger.error(f"get_song_lyrics: download_url request failed: {e_dl}")

            logger.warning(f"get_song_lyrics: no text available for {track_id}")
            return None

        except Exception as e:
            logger.error(f"get_song_lyrics: id={track_id} error: {e}", exc_info=True)
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

    async def add_tracks_by_name(
    self,
    token: str,
    user_id: int,
    playlist_title: str,
    track_names: List[str],
) -> Dict[str, Any]:
        result: Dict[str, Any] = {"added": [], "failed": []}

        try:
            client = self.get_client(token, user_id)
            if client is None:
                return result

            playlists = client.users_playlists_list() or []
            playlist = None
            for pl in playlists:
                if getattr(pl, "title", "").lower() == playlist_title.lower():
                    playlist = pl
                    break

            if playlist is None:
                playlist = client.users_playlists_create(playlist_title)

            kind = getattr(playlist, "kind", None)
            if kind is None:
                logger.error(f"add_tracks_by_name: kind is None for playlist '{playlist_title}'")
                return result

            for raw_query in track_names:
                query = (raw_query or "").strip()
                if not query:
                    result["failed"].append({"query": raw_query, "reason": "empty"})
                    continue

                pair = self._soft_find_track(client, query)
                if pair is None:
                    result["failed"].append({"query": raw_query, "reason": "not_found"})
                    continue

                track_obj, track_id, album_id = pair

                try:
                    try:
                        playlist.insert_tracks([(track_id, album_id)])
                    except AttributeError:
                        playlist.insert_track(track_id, album_id)

                    artist_name = (
                        track_obj.artists[0].name
                        if getattr(track_obj, "artists", None)
                        else "Unknown"
                    )
                    title = f"{artist_name} - {track_obj.title}"
                    result["added"].append({"query": raw_query, "title": title})
                except Exception as e:
                    logger.warning(
                        f"add_tracks_by_name: failed to add '{raw_query}' "
                        f"({track_id}:{album_id}) to '{playlist_title}': {e}"
                    )
                    result["failed"].append({"query": raw_query, "reason": "api_error"})

            return result

        except Exception as e:
            logger.error(f"add_tracks_by_name fatal error for playlist '{playlist_title}': {e}")
            return result

    def _soft_find_track(
        self,
        client: Client,
        query: str,
    ) -> Optional[Tuple[Any, int, int]]:
        try:
            for ch in ['"', "'", "«", "»"]:
                query = query.replace(ch, "")
            query = " ".join(query.split())

            normalized = query
            for sep in [" - ", " : ", " | ", " – ", " — "]:
                normalized = normalized.replace(sep, " - ")
            for sep in [":", "|", "–", "—"]:
                normalized = normalized.replace(sep, " - ")
            normalized = " ".join(normalized.split())

            artist_part = None
            title_part = None
            if " - " in normalized:
                artist_part, title_part = normalized.split(" - ", 1)
                artist_part = artist_part.strip()
                title_part = title_part.strip()
            else:
                title_part = normalized

            queries: List[str] = []
            if artist_part and title_part:
                queries.append(f"{artist_part} {title_part}")
                queries.append(title_part)
                queries.append(artist_part)
            else:
                queries.append(title_part)

            for q in queries:
                q_clean = " ".join(q.split())
                if len(q_clean) < 2:
                    continue

                sr = client.search(q_clean, type_="track")
                tracks_block = getattr(sr, "tracks", None)
                items = getattr(tracks_block, "results", None) or [] if tracks_block else []
                if not items:
                    continue

                track = items[0]
                tid = getattr(track, "id", None)
                albums = getattr(track, "albums", None) or []
                aid = getattr(albums[0], "id", None) if albums else None
                if tid is None:
                    continue
                if aid is None:
                    aid = 0

                return track, int(tid), int(aid)

            return None

        except Exception as e:
            logger.warning(f"_soft_find_track error for '{query}': {e}")
            return None

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

        stats = {}

        try:
            stats["liked_tracks_count"] = await self._get_liked_tracks_count(token, user_id)
        except Exception as e:
            logger.warning(f"Не удалось получить лайки: {e}")

        try:
            stats["recent_likes_last_month"] = await self._get_recent_likes_count(token, user_id, days=30)
        except Exception as e:
            logger.warning(f"Не удалось получить недавние лайки: {e}")

        try:
            stats["top_artists"] = await self._get_top_artists(token, user_id, limit=5)
        except Exception as e:
            logger.warning(f"Не удалось получить топ артистов: {e}")

        try:
            stats["top_genres_recent"] = await self._get_top_genres_from_recent(token, user_id, limit=5, days=90)
        except Exception as e:
            logger.warning(f"Не удалось получить топ жанров: {e}")

        try:
            stats["top_genres_library"] = await self._get_top_genres_from_library(token, user_id, limit=5)
        except Exception as e:
            logger.warning(f"Не удалось получить жанры библиотеки: {e}")

        return stats