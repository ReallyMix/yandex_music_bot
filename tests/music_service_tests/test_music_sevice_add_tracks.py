import pytest
from unittest.mock import MagicMock, patch


class TestMusicServiceAddTracks:
    """Тесты для методов добавления треков"""

    @pytest.mark.asyncio
    async def test_add_tracks_by_name_create_new_playlist(self, music_service):
        """Тест добавления треков с созданием нового плейлиста"""
        token = "test_token"
        user_id = 123
        playlist_title = "New Playlist"
        track_names = ["Song 1"]

        mock_client = MagicMock()
        mock_playlist = MagicMock()
        mock_playlist.kind = 12345

        with patch.object(music_service, "get_client", return_value=mock_client):
            with patch.object(music_service, "_get_account_uid", return_value=123456):
                with patch.object(
                    music_service, "_find_playlist_by_title", return_value=None
                ):
                    mock_client.users_playlists_create.return_value = mock_playlist

                    with patch.object(
                        music_service, "_search_track_id", return_value="123:456"
                    ):
                        result = await music_service.add_tracks_by_name(
                            token, user_id, playlist_title, track_names
                        )

                        assert len(result["added"]) == 1
                        mock_client.users_playlists_create.assert_called_once_with(
                            playlist_title
                        )
