import pytest
from unittest.mock import MagicMock, patch


class TestMusicServiceLikes:
    """Тесты для методов работы с лайками"""

    @pytest.mark.asyncio
    async def test_like_track_success_by_id(self, music_service):
        """Тест успешного лайка трека по ID"""
        token = "test_token"
        user_id = 123
        track_query = "123:456"

        mock_client = MagicMock()

        with patch.object(music_service, "get_client", return_value=mock_client):
            with patch.object(
                music_service, "_format_track_id", return_value="123:456"
            ):
                result = await music_service.like_track(token, user_id, track_query)

                assert result is True
                mock_client.users_likes_tracks_add.assert_called_once_with("123:456")

    @pytest.mark.asyncio
    async def test_like_track_client_none(self, music_service):
        """Тест лайка трека, когда клиент не получен"""
        token = "test_token"
        user_id = 123
        track_query = "Song"

        with patch.object(music_service, "get_client", return_value=None):
            result = await music_service.like_track(token, user_id, track_query)
            assert result is False

    @pytest.mark.asyncio
    async def test_like_track_track_not_found(self, music_service):
        """Тест лайка трека, когда трек не найден"""
        token = "test_token"
        user_id = 123
        track_query = "Unknown Song"

        mock_client = MagicMock()

        with patch.object(music_service, "get_client", return_value=mock_client):
            with patch.object(music_service, "_format_track_id", return_value=None):
                with patch.object(music_service, "_search_track_id", return_value=None):
                    result = await music_service.like_track(token, user_id, track_query)

                    assert result is False
                    mock_client.users_likes_tracks_add.assert_not_called()
