import pytest
from unittest.mock import MagicMock, patch


class TestMusicServiceCreate:
    """Тесты для методов создания плейлистов"""

    @pytest.mark.asyncio
    async def test_create_playlist_success(self, music_service):
        """Тест успешного создания плейлиста без треков"""
        token = "test_token"
        user_id = 123
        title = "New Playlist"

        mock_client = MagicMock()
        mock_playlist = MagicMock()
        mock_playlist.kind = 789
        mock_playlist.title = title

        with patch.object(music_service, "get_client", return_value=mock_client):
            with patch.object(music_service, "_get_account_uid", return_value=123456):
                mock_client.users_playlists_create.return_value = mock_playlist

                result = await music_service.create_playlist(token, user_id, title)

                expected = {"kind": 789, "title": title, "uid": 123456}
                assert result == expected
                mock_client.users_playlists_create.assert_called_once_with(title)

    @pytest.mark.asyncio
    async def test_create_playlist_client_none(self, music_service):
        """Тест создания плейлиста, когда клиент не получен"""
        token = "test_token"
        user_id = 123
        title = "New Playlist"

        with patch.object(music_service, "get_client", return_value=None):
            result = await music_service.create_playlist(token, user_id, title)
            assert result is None

    @pytest.mark.asyncio
    async def test_create_playlist_account_uid_none(self, music_service):
        """Тест создания плейлиста, когда не удалось получить account_uid"""
        token = "test_token"
        user_id = 123
        title = "New Playlist"

        mock_client = MagicMock()

        with patch.object(music_service, "get_client", return_value=mock_client):
            with patch.object(music_service, "_get_account_uid", return_value=None):
                result = await music_service.create_playlist(token, user_id, title)
                assert result is None

    @pytest.mark.asyncio
    async def test_create_playlist_exception(self, music_service):
        """Тест обработки исключения при создании плейлиста"""
        token = "test_token"
        user_id = 123
        title = "New Playlist"

        mock_client = MagicMock()

        with patch.object(music_service, "get_client", return_value=mock_client):
            with patch.object(music_service, "_get_account_uid", return_value=123456):
                mock_client.users_playlists_create.side_effect = Exception("API Error")

                result = await music_service.create_playlist(token, user_id, title)
                assert result is None
