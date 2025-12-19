# tests/test_music_service_playlists.py
import pytest
from unittest.mock import MagicMock, patch


class TestMusicServicePlaylists:
    """Тесты для методов получения плейлистов"""

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
