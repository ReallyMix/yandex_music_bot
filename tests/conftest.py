import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from unittest.mock import Mock
from src.services.stats_mixin import YandexMusicStatsMixin


@pytest.fixture
def stats_mixin_with_get_client():
    """Фикстура для создания миксина с методом get_client"""

    class MixinWithClient(YandexMusicStatsMixin):
        def get_client(self, token, user_id):
            return Mock()

    return MixinWithClient()


@pytest.fixture
def mock_client():
    return Mock()


@pytest.fixture
def mock_playlist():
    """Фикстура для создания мокового плейлиста"""
    playlist = MagicMock()
    playlist.kind = 12345
    playlist.title = "Test Playlist"
    playlist.description = "Test Description"
    playlist.track_count = 10
    playlist.created = datetime(2023, 1, 1, 12, 0, 0)
    playlist.modified = datetime(2023, 1, 2, 12, 0, 0)

    cover = MagicMock()
    cover.uri = "some://cover/uri"
    playlist.cover = cover

    return playlist


@pytest.fixture
def mock_account():
    """Фикстура для создания мокового аккаунта"""
    account_data = MagicMock()
    account_data.uid = 123456

    account = MagicMock()
    account.account = account_data

    return account


@pytest.fixture
def mock_track():
    """Фикстура для создания мокового трека с текстом"""
    lyrics = MagicMock()
    lyrics.full_lyrics = "Test lyrics\nLine 1\nLine 2"

    track = MagicMock()
    track.get_lyrics.return_value = lyrics

    return track


@pytest.fixture
def music_service():
    """Фикстура для создания сервиса музыки"""
    from src.services.yandex_music_service import YandexMusicService

    return YandexMusicService()
