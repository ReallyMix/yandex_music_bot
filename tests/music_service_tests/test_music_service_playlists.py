# tests/test_music_service_playlists.py
import pytest
from unittest.mock import MagicMock, patch


class TestMusicServicePlaylists:
    """Тесты для методов получения плейлистов"""

    @pytest.mark.asyncio
    async def test_get_user_playlists_client_none(self, music_service):
        """Тест случая, когда клиент не получен"""
        token = "test_token"
        user_id = 123

        with patch.object(music_service, "get_client", return_value=None):
            result = await music_service.get_user_playlists(token, user_id)

        assert result == []

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
