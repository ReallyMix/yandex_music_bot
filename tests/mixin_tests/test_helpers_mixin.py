import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from collections import Counter
import logging

from src.services.helpers_mixin import YandexMusicHelperMixin

logging.disable(logging.CRITICAL)


class TestYandexMusicHelperMixin:
    """Тесты для YandexMusicHelperMixin"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        from yandex_music import Client

        self.mixin = type("TestMixin", (YandexMusicHelperMixin,), {})()
        self.mock_client = Mock(spec=Client)

    # Тесты для _normalize_timestamp
    def test_normalize_timestamp_none(self):
        """Тест нормализации None timestamp"""
        assert self.mixin._normalize_timestamp(None) is None

    def test_normalize_timestamp_datetime_with_tz(self):
        """Тест нормализации datetime с часовым поясом"""
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert self.mixin._normalize_timestamp(dt) == dt

    def test_normalize_timestamp_datetime_without_tz(self):
        """Тест нормализации datetime без часового пояса"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = self.mixin._normalize_timestamp(dt)
        assert result.tzinfo == timezone.utc
        assert result.replace(tzinfo=None) == dt

    def test_normalize_timestamp_int(self):
        """Тест нормализации int timestamp"""
        timestamp = 1672574400  # 2023-01-01 12:00:00 UTC
        result = self.mixin._normalize_timestamp(timestamp)
        assert isinstance(result, datetime)
        assert result.timestamp() == timestamp

    def test_normalize_timestamp_float(self):
        """Тест нормализации float timestamp"""
        timestamp = 1672574400.5
        result = self.mixin._normalize_timestamp(timestamp)
        assert isinstance(result, datetime)
        assert result.timestamp() == timestamp

    def test_normalize_timestamp_string_iso(self):
        """Тест нормализации строки ISO формата"""
        iso_string = "2023-01-01T12:00:00+00:00"
        result = self.mixin._normalize_timestamp(iso_string)
        assert isinstance(result, datetime)
        assert result.isoformat() == iso_string

    def test_normalize_timestamp_string_with_z(self):
        """Тест нормализации строки с Z"""
        result = self.mixin._normalize_timestamp("2023-01-01T12:00:00Z")
        assert result.isoformat() == "2023-01-01T12:00:00+00:00"

    def test_normalize_timestamp_invalid_string(self):
        """Тест нормализации некорректной строки"""
        assert self.mixin._normalize_timestamp("invalid") is None

    def test_normalize_timestamp_invalid_type(self):
        """Тест нормализации неподдерживаемого типа"""
        assert self.mixin._normalize_timestamp({"key": "value"}) is None

    # Тесты для _format_track_id
    def test_format_track_id_string(self):
        """Тест форматирования строкового ID"""
        assert self.mixin._format_track_id("123") == "123"

    def test_format_track_id_empty_object(self):
        """Тест форматирования пустого объекта"""
        assert self.mixin._format_track_id(object()) is None

    # Тесты для _extract_artists
    def test_extract_artists_no_artists(self):
        """Тест извлечения артистов при их отсутствии"""
        track = Mock(artists=None)
        assert self.mixin._extract_artists(track) == []

    def test_extract_artists_empty_artists(self):
        """Тест извлечения артистов из пустого списка"""
        track = Mock(artists=[])
        assert self.mixin._extract_artists(track) == []

    # Тесты для _extract_genre
    def test_extract_genre_from_track(self):
        """Тест извлечения жанра из трека"""
        track = Mock(genre="Rock")
        assert self.mixin._extract_genre(track) == "Rock"

    def test_extract_genre_from_album(self):
        """Тест извлечения жанра из альбома"""
        album = Mock(genre="Pop")
        track = Mock(genre=None, albums=[album])
        assert self.mixin._extract_genre(track) == "Pop"

    def test_extract_genre_from_multiple_albums(self):
        """Тест извлечения жанра из первого альбома"""
        album1 = Mock(genre="Rock")
        album2 = Mock(genre="Pop")
        track = Mock(genre=None, albums=[album1, album2])
        assert self.mixin._extract_genre(track) == "Rock"

    def test_extract_genre_no_genre(self):
        """Тест извлечения жанра при его отсутствии"""
        track = Mock(genre=None, albums=[])
        assert self.mixin._extract_genre(track) is None

    def test_extract_genre_no_albums(self):
        """Тест извлечения жанра без альбомов"""
        track = Mock(genre=None, albums=None)
        assert self.mixin._extract_genre(track) is None

    # Тесты для _extract_duration_ms
    def test_extract_duration_ms_from_ms(self):
        """Тест извлечения длительности в миллисекундах"""
        track = Mock(duration_ms=180000)
        assert self.mixin._extract_duration_ms(track) == 180000

    def test_extract_duration_ms_from_seconds(self):
        """Тест извлечения длительности из секунд"""
        track = Mock(duration_ms=None, duration=180.5)
        assert self.mixin._extract_duration_ms(track) == 180500

    def test_extract_duration_ms_no_duration(self):
        """Тест извлечения длительности при ее отсутствии"""
        track = Mock(duration_ms=None, duration=None)
        assert self.mixin._extract_duration_ms(track) is None

    def test_extract_duration_ms_invalid_duration(self):
        """Тест извлечения длительности с невалидным значением"""
        track = Mock(duration_ms=None, duration="invalid")
        assert self.mixin._extract_duration_ms(track) is None

    # Тесты для _to_top_list
    def test_to_top_list(self):
        """Тест преобразования Counter в топ-список"""
        counter = Counter({"A": 5, "B": 3, "C": 2, "D": 1})
        result = self.mixin._to_top_list(counter, limit=3)

        assert len(result) == 3
        assert result[0] == {"name": "A", "count": 5}
        assert result[1] == {"name": "B", "count": 3}
        assert result[2] == {"name": "C", "count": 2}

    def test_to_top_list_empty(self):
        """Тест преобразования пустого Counter"""
        counter = Counter()
        result = self.mixin._to_top_list(counter)
        assert result == []

    def test_to_top_list_with_limit(self):
        """Тест преобразования с ограничением"""
        counter = Counter({"A": 5, "B": 3})
        result = self.mixin._to_top_list(counter, limit=1)
        assert len(result) == 1
        assert result[0]["name"] == "A"

    # Тесты для _fetch_tracks
    def test_fetch_tracks_success(self):
        """Тест успешного получения треков"""
        mock_track = Mock()
        self.mock_client.tracks.return_value = [mock_track]

        track_ref = Mock()
        track_ref.id = "123"
        track_ref.album_id = "456"

        result = self.mixin._fetch_tracks(self.mock_client, [track_ref])
        assert result == [mock_track]
        self.mock_client.tracks.assert_called_once_with(["123:456"])

    def test_fetch_tracks_empty_input(self):
        """Тест получения треков с пустым списком"""
        result = self.mixin._fetch_tracks(self.mock_client, [])
        assert result == []

    def test_fetch_tracks_no_valid_ids(self):
        """Тест получения треков без валидных ID"""
        track_ref = Mock()
        track_ref.id = None
        track_ref.album_id = None

        result = self.mixin._fetch_tracks(self.mock_client, [track_ref])
        assert result == []

    def test_fetch_tracks_client_error(self):
        """Тест получения треков с ошибкой клиента"""
        self.mock_client.tracks.side_effect = Exception("API Error")

        track_ref = Mock()
        track_ref.id = "123"

        result = self.mixin._fetch_tracks(self.mock_client, [track_ref])
        assert result == []

    # Тесты для _unwrap_history_items
    def test_unwrap_history_items_dict_with_tracks(self):
        """Тест развертывания истории из dict"""
        history = {"tracks": ["track1", "track2"]}
        result = self.mixin._unwrap_history_items(history)
        assert result == ["track1", "track2"]

    def test_unwrap_history_items_dict_empty_tracks(self):
        """Тест развертывания истории из dict с пустыми треками"""
        history = {"tracks": None}
        result = self.mixin._unwrap_history_items(history)
        assert result == []

    def test_unwrap_history_items_object_with_tracks(self):
        """Тест развертывания истории из объекта"""
        history = Mock(tracks=["track1", "track2"])
        result = self.mixin._unwrap_history_items(history)
        assert result == ["track1", "track2"]

    def test_unwrap_history_items_list(self):
        """Тест развертывания истории из списка"""
        history = ["track1", "track2"]
        result = self.mixin._unwrap_history_items(history)
        assert result == ["track1", "track2"]

    def test_unwrap_history_items_none(self):
        """Тест развертывания None истории"""
        result = self.mixin._unwrap_history_items(None)
        assert result == []

    def test_unwrap_history_items_invalid(self):
        """Тест развертывания невалидной истории"""
        result = self.mixin._unwrap_history_items("invalid")
        assert result == []

    # Тесты для _collect_tracks_from_history
    def test_collect_tracks_from_history_with_track_objects(self):
        """Тест сбора треков из истории с объектами треков"""
        mock_track = Mock()
        mock_track.artists = [Mock(name="Artist")]

        history_item = Mock()
        history_item.track = mock_track
        history_item.timestamp = "2023-01-01T12:00:00Z"

        result = self.mixin._collect_tracks_from_history(
            self.mock_client, [history_item]
        )

        assert len(result) == 1
        assert result[0][0] == mock_track
        assert isinstance(result[0][1], datetime)

    def test_collect_tracks_from_history_mixed(self):
        """Тест сбора треков из смешанной истории"""
        mock_track1 = Mock()
        mock_track1.artists = [Mock(name="Artist1")]

        history_item1 = Mock()
        history_item1.track = mock_track1
        history_item1.timestamp = "2023-01-01T12:00:00Z"

        history_item2 = Mock()
        history_item2.track = None
        history_item2.id = "123"
        history_item2.timestamp = "2023-01-01T13:00:00Z"

        mock_track2 = Mock()

        with patch.object(self.mixin, "_fetch_tracks", return_value=[mock_track2]):
            result = self.mixin._collect_tracks_from_history(
                self.mock_client, [history_item1, history_item2]
            )

        assert len(result) == 2

    # Тесты для _get_account_uid
    def test_get_account_uid_success(self):
        """Тест успешного получения UID"""
        mock_account = Mock()
        mock_account.account = Mock(uid=12345)
        self.mock_client.account_status.return_value = mock_account

        result = self.mixin._get_account_uid(self.mock_client)
        assert result == 12345

    def test_get_account_uid_no_account(self):
        """Тест получения UID при отсутствии аккаунта"""
        self.mock_client.account_status.return_value = None
        result = self.mixin._get_account_uid(self.mock_client)
        assert result is None

    def test_get_account_uid_error(self):
        """Тест получения UID с ошибкой"""
        self.mock_client.account_status.side_effect = Exception("API Error")
        result = self.mixin._get_account_uid(self.mock_client)
        assert result is None

    # Тесты для _get_playlist_tracks
    def test_get_playlist_tracks_success(self):
        """Тест успешного получения треков из плейлистов"""
        mock_track_ref1 = Mock(track=Mock(id="1", album_id="1"))
        mock_track_ref2 = Mock(track=None, id="2", album_id="2")

        mock_playlist = Mock(tracks=[mock_track_ref1, mock_track_ref2])
        self.mock_client.users_playlists.return_value = [mock_playlist]

        mock_fetched_track = Mock()
        with patch.object(
            self.mixin,
            "_fetch_tracks",
            return_value=[mock_fetched_track, mock_fetched_track],
        ):
            result = self.mixin._get_playlist_tracks(self.mock_client, 12345)

        assert len(result) == 2
        self.mock_client.users_playlists.assert_called_once_with(12345)

    def test_get_playlist_tracks_error(self):
        """Тест получения треков из плейлистов с ошибкой"""
        self.mock_client.users_playlists.side_effect = Exception("API Error")

        result = self.mixin._get_playlist_tracks(self.mock_client, 12345)
        assert result == []

    def test_get_playlist_tracks_no_playlists(self):
        """Тест получения треков при отсутствии плейлистов"""
        self.mock_client.users_playlists.return_value = None

        result = self.mixin._get_playlist_tracks(self.mock_client, 12345)
        assert result == []

    # Тесты для _search_track_id
    def test_search_track_id_no_results(self):
        """Тест поиска ID трека без результатов"""
        mock_search = Mock(tracks=None)
        self.mock_client.search.return_value = mock_search

        result = self.mixin._search_track_id(self.mock_client, "query")
        assert result is None

    def test_search_track_id_empty_results(self):
        """Тест поиска ID трека с пустыми результатами"""
        mock_tracks = Mock(results=[])
        mock_search = Mock(tracks=mock_tracks)
        self.mock_client.search.return_value = mock_search

        result = self.mixin._search_track_id(self.mock_client, "query")
        assert result is None

    def test_search_track_id_error(self):
        """Тест поиска ID трека с ошибкой"""
        self.mock_client.search.side_effect = Exception("API Error")

        result = self.mixin._search_track_id(self.mock_client, "query")
        assert result is None

    # Тесты для _find_playlist_by_title
    def test_find_playlist_by_title_found(self):
        """Тест успешного поиска плейлиста по названию"""
        mock_playlist1 = Mock(title="My Playlist")
        mock_playlist2 = Mock(title="Other Playlist")
        self.mock_client.users_playlists.return_value = [mock_playlist1, mock_playlist2]

        result = self.mixin._find_playlist_by_title(
            self.mock_client, 12345, "my playlist"
        )
        assert result == mock_playlist1

    def test_find_playlist_by_title_not_found(self):
        """Тест поиска плейлиста по названию (не найден)"""
        mock_playlist = Mock(title="Other Playlist")
        self.mock_client.users_playlists.return_value = [mock_playlist]

        result = self.mixin._find_playlist_by_title(
            self.mock_client, 12345, "my playlist"
        )
        assert result is None

    def test_find_playlist_by_title_case_insensitive(self):
        """Тест поиска плейлиста без учета регистра"""
        mock_playlist = Mock(title="My Playlist")
        self.mock_client.users_playlists.return_value = [mock_playlist]

        result = self.mixin._find_playlist_by_title(
            self.mock_client, 12345, "MY PLAYLIST"
        )
        assert result == mock_playlist

    def test_find_playlist_by_title_error(self):
        """Тест поиска плейлиста с ошибкой"""
        self.mock_client.users_playlists.side_effect = Exception("API Error")

        result = self.mixin._find_playlist_by_title(
            self.mock_client, 12345, "my playlist"
        )
        assert result is None

    def test_find_playlist_by_title_no_playlists(self):
        """Тест поиска плейлиста при их отсутствии"""
        self.mock_client.users_playlists.return_value = None

        result = self.mixin._find_playlist_by_title(
            self.mock_client, 12345, "my playlist"
        )
        assert result is None
