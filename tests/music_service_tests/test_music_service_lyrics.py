import pytest
from unittest.mock import MagicMock, patch


class TestMusicServiceLyrics:
    """Тесты для методов получения текстов песен"""

    @pytest.fixture
    def mock_track_with_lyrics(self):
        """Фикстура для создания мокового трека с текстом"""
        lyrics = MagicMock()
        lyrics.full_lyrics = "Test lyrics\nLine 1\nLine 2"

        track = MagicMock()
        track.get_lyrics.return_value = lyrics

        return track

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
        mock_client.tracks.return_value = []

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
