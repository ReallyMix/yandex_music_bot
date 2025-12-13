import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestMusicService:
    """Тесты для методов работы с музыкой"""

    @pytest.fixture
    def mock_playlist(self):
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
    def mock_account(self):
        """Фикстура для создания мокового аккаунта"""
        account_data = MagicMock()
        account_data.uid = 123456

        account = MagicMock()
        account.account = account_data

        return account

    @pytest.mark.asyncio
    async def test_get_user_playlists_success(
        self, music_service, mock_playlist, mock_account
    ):
        """Тест успешного получения плейлистов пользователя"""
        token = "test_token"
        user_id = 123
        expected_result = [
            {
                "kind": 12345,
                "title": "Test Playlist",
                "description": "Test Description",
                "track_count": 10,
                "created": "2023-01-01T12:00:00",
                "modified": "2023-01-02T12:00:00",
                "cover": "some://cover/uri",
            }
        ]

        mock_client = MagicMock()
        mock_client.account_status.return_value = mock_account
        mock_client.users_playlists.return_value = [mock_playlist]

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_user_playlists(token, user_id)

        assert result == expected_result
        mock_client.account_status.assert_called_once()
        mock_client.users_playlists.assert_called_once_with(123456)

    @pytest.mark.asyncio
    async def test_get_user_playlists_client_none(self, music_service):
        """Тест случая, когда клиент не получен"""
        token = "test_token"
        user_id = 123

        with patch.object(music_service, "get_client", return_value=None):
            result = await music_service.get_user_playlists(token, user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_playlists_account_none(self, music_service):
        """Тест случая, когда account_status возвращает None"""
        token = "test_token"
        user_id = 123

        mock_client = MagicMock()
        mock_client.account_status.return_value = None

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_user_playlists(token, user_id)

        assert result == []
        mock_client.account_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_playlists_exception_handling(self, music_service):
        """Тест обработки исключений при получении плейлистов"""
        token = "test_token"
        user_id = 123

        mock_client = MagicMock()
        mock_client.account_status.side_effect = Exception("Test error")

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_user_playlists(token, user_id)

        assert result == []

    @pytest.fixture
    def mock_track(self):
        """Фикстура для создания мокового трека с текстом"""
        lyrics = MagicMock()
        lyrics.full_lyrics = "Test lyrics\nLine 1\nLine 2"

        track = MagicMock()
        track.get_lyrics.return_value = lyrics

        return track

    @pytest.mark.asyncio
    async def test_get_song_lyrics_success(self, music_service, mock_track):
        """Тест успешного получения текста песни"""
        token = "test_token"
        user_id = 123
        track_id = "test_track_123"
        expected_lyrics = "Test lyrics\nLine 1\nLine 2"

        mock_client = MagicMock()
        mock_client.tracks.return_value = [mock_track]

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_song_lyrics(token, user_id, track_id)

        assert result == expected_lyrics
        mock_client.tracks.assert_called_once_with([track_id])
        mock_track.get_lyrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_song_lyrics_client_none(self, music_service):
        """Тест случая, когда клиент не получен"""
        token = "test_token"
        user_id = 123
        track_id = "test_track_123"

        with patch.object(music_service, "get_client", return_value=None):
            result = await music_service.get_song_lyrics(token, user_id, track_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_song_lyrics_track_not_found(self, music_service):
        """Тест случая, когда трек не найден"""
        token = "test_token"
        user_id = 123
        track_id = "test_track_123"

        mock_client = MagicMock()
        mock_client.tracks.return_value = []  # Пустой список

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_song_lyrics(token, user_id, track_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_song_lyrics_no_lyrics(self, music_service):
        """Тест случая, когда текст песни недоступен"""
        token = "test_token"
        user_id = 123
        track_id = "test_track_123"

        track = MagicMock()
        track.get_lyrics.return_value = None

        mock_client = MagicMock()
        mock_client.tracks.return_value = [track]

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_song_lyrics(token, user_id, track_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_song_lyrics_no_full_lyrics(self, music_service):
        """Тест случая, когда полный текст недоступен"""
        token = "test_token"
        user_id = 123
        track_id = "test_track_123"

        lyrics = MagicMock()
        lyrics.full_lyrics = None

        track = MagicMock()
        track.get_lyrics.return_value = lyrics

        mock_client = MagicMock()
        mock_client.tracks.return_value = [track]

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_song_lyrics(token, user_id, track_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_song_lyrics_exception_handling(self, music_service):
        """Тест обработки исключений при получении текста песни"""
        token = "test_token"
        user_id = 123
        track_id = "test_track_123"

        mock_client = MagicMock()
        mock_client.tracks.side_effect = Exception("Test error")

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_song_lyrics(token, user_id, track_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_song_lyrics_multiple_tracks(self, music_service, mock_track):
        """Тест получения текста при возврате нескольких треков"""
        token = "test_token"
        user_id = 123
        track_id = "test_track_123"
        expected_lyrics = "Test lyrics\nLine 1\nLine 2"

        mock_client = MagicMock()
        mock_client.tracks.return_value = [mock_track, MagicMock(), MagicMock()]

        with patch.object(music_service, "get_client", return_value=mock_client):
            result = await music_service.get_song_lyrics(token, user_id, track_id)

        assert result == expected_lyrics
        mock_track.get_lyrics.assert_called_once()
