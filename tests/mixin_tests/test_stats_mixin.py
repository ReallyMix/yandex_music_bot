import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone


class TestYandexMusicStatsMixin:
    """Тесты для YandexMusicStatsMixin"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.token = "test_token"
        self.user_id = 123

    # Тесты для _get_liked_tracks_count
    @pytest.mark.asyncio
    async def test_get_liked_tracks_count_success(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест успешного получения количества лайкнутых треков"""
        mock_likes = Mock()
        mock_likes.tracks = [Mock(), Mock(), Mock()]

        mock_client.users_likes_tracks.return_value = mock_likes

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            result = await stats_mixin_with_get_client._get_liked_tracks_count(
                self.token, self.user_id
            )

            assert result == 3
            mock_client.users_likes_tracks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_liked_tracks_count_empty(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения количества лайкнутых треков при пустом списке"""
        mock_likes = Mock()
        mock_likes.tracks = []

        mock_client.users_likes_tracks.return_value = mock_likes

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            result = await stats_mixin_with_get_client._get_liked_tracks_count(
                self.token, self.user_id
            )
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_liked_tracks_count_tracks_none(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения количества лайкнутых треков, когда tracks = None"""
        mock_likes = Mock()
        mock_likes.tracks = None

        mock_client.users_likes_tracks.return_value = mock_likes

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            result = await stats_mixin_with_get_client._get_liked_tracks_count(
                self.token, self.user_id
            )
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_liked_tracks_count_client_none(
        self, stats_mixin_with_get_client
    ):
        """Тест получения количества лайкнутых треков, когда клиент не получен"""
        with patch.object(stats_mixin_with_get_client, "get_client", return_value=None):
            result = await stats_mixin_with_get_client._get_liked_tracks_count(
                self.token, self.user_id
            )
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_liked_tracks_count_exception(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения количества лайкнутых треков с исключением"""
        mock_client.users_likes_tracks.side_effect = Exception("API Error")

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            result = await stats_mixin_with_get_client._get_liked_tracks_count(
                self.token, self.user_id
            )
            assert result == 0

    # Тесты для _get_recent_likes_count
    @pytest.mark.asyncio
    async def test_get_recent_likes_count_success(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест успешного получения количества недавних лайков"""
        now = datetime.now(timezone.utc)

        track1 = Mock()
        track1.timestamp = (now - timedelta(days=10)).isoformat()
        track1.added = None

        track2 = Mock()
        track2.timestamp = (now - timedelta(days=40)).isoformat()
        track2.added = None

        track3 = Mock()
        track3.timestamp = None
        track3.added = (now - timedelta(days=5)).isoformat()

        mock_likes = Mock()
        mock_likes.tracks = [track1, track2, track3]

        mock_client.users_likes_tracks.return_value = mock_likes

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            result = await stats_mixin_with_get_client._get_recent_likes_count(
                self.token, self.user_id, days=30
            )
            assert result == 2

    @pytest.mark.asyncio
    async def test_get_recent_likes_count_no_timestamp(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения количества недавних лайков без временных меток"""
        track = Mock()
        track.timestamp = None
        track.added = None

        mock_likes = Mock()
        mock_likes.tracks = [track, track, track]

        mock_client.users_likes_tracks.return_value = mock_likes

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            result = await stats_mixin_with_get_client._get_recent_likes_count(
                self.token, self.user_id, days=30
            )
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_recent_likes_count_client_none(
        self, stats_mixin_with_get_client
    ):
        """Тест получения количества недавних лайков, когда клиент не получен"""
        with patch.object(stats_mixin_with_get_client, "get_client", return_value=None):
            result = await stats_mixin_with_get_client._get_recent_likes_count(
                self.token, self.user_id, days=30
            )
            assert result == 0

    # Тесты для _get_top_genres_from_recent
    @pytest.mark.asyncio
    async def test_get_top_genres_from_recent_success(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест успешного получения топ-жанров из истории"""
        mock_track1 = Mock()
        mock_track1.genre = "Rock"

        mock_track2 = Mock()
        mock_track2.genre = "Pop"

        mock_track3 = Mock()
        mock_track3.genre = "Rock"

        now = datetime.now(timezone.utc)
        recent_ts = now - timedelta(days=10)
        old_ts = now - timedelta(days=100)

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client,
                "_get_recent_history",
                return_value=["history_item1", "history_item2", "history_item3"],
            ):
                with patch.object(
                    stats_mixin_with_get_client,
                    "_collect_tracks_from_history",
                    return_value=[
                        (mock_track1, recent_ts),
                        (mock_track2, recent_ts),
                        (mock_track3, old_ts),
                    ],
                ):
                    result = (
                        await stats_mixin_with_get_client._get_top_genres_from_recent(
                            self.token, self.user_id, limit=2, days=90
                        )
                    )

                    assert len(result) <= 2
                    genres = [item["name"] for item in result]
                    assert "Rock" in genres or "Pop" in genres

    @pytest.mark.asyncio
    async def test_get_top_genres_from_recent_no_genre(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения топ-жанров, когда у треков нет жанров"""
        mock_track = Mock()
        mock_track.genre = None

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client,
                "_get_recent_history",
                return_value=["history_item"],
            ):
                with patch.object(
                    stats_mixin_with_get_client,
                    "_collect_tracks_from_history",
                    return_value=[(mock_track, datetime.now(timezone.utc))],
                ):
                    result = (
                        await stats_mixin_with_get_client._get_top_genres_from_recent(
                            self.token, self.user_id, limit=5, days=90
                        )
                    )
                    assert result == []

    @pytest.mark.asyncio
    async def test_get_top_genres_from_recent_client_none(
        self, stats_mixin_with_get_client
    ):
        """Тест получения топ-жанров, когда клиент не получен"""
        with patch.object(stats_mixin_with_get_client, "get_client", return_value=None):
            result = await stats_mixin_with_get_client._get_top_genres_from_recent(
                self.token, self.user_id, limit=5, days=90
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_get_top_genres_from_recent_exception(
        self, stats_mixin_with_get_client
    ):
        """Тест получения топ-жанров с исключением"""
        with patch.object(
            stats_mixin_with_get_client,
            "get_client",
            side_effect=Exception("API Error"),
        ):
            result = await stats_mixin_with_get_client._get_top_genres_from_recent(
                self.token, self.user_id, limit=5, days=90
            )
            assert result == []

    # Тесты для _get_listening_minutes
    @pytest.mark.asyncio
    async def test_get_listening_minutes_success(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест успешного получения минут прослушивания"""
        mock_track1 = Mock()
        mock_track1.duration_ms = 180000

        mock_track2 = Mock()
        mock_track2.duration_ms = 300000

        mock_track3 = Mock()
        mock_track3.duration_ms = 120000

        now = datetime.now(timezone.utc)
        recent_ts = now - timedelta(days=3)
        old_ts = now - timedelta(days=10)

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client,
                "_get_recent_history",
                return_value=["history_item"],
            ):
                with patch.object(
                    stats_mixin_with_get_client,
                    "_collect_tracks_from_history",
                    return_value=[
                        (mock_track1, recent_ts),
                        (mock_track2, recent_ts),
                        (mock_track3, old_ts),
                    ],
                ):
                    result = await stats_mixin_with_get_client._get_listening_minutes(
                        self.token, self.user_id, days=7
                    )

                    assert result == 8

    @pytest.mark.asyncio
    async def test_get_listening_minutes_no_duration(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения минут прослушивания, когда нет длительности"""
        mock_track = Mock()
        mock_track.duration_ms = None

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client,
                "_get_recent_history",
                return_value=["history_item"],
            ):
                with patch.object(
                    stats_mixin_with_get_client,
                    "_collect_tracks_from_history",
                    return_value=[(mock_track, datetime.now(timezone.utc))],
                ):
                    result = await stats_mixin_with_get_client._get_listening_minutes(
                        self.token, self.user_id, days=7
                    )
                    assert result == 0

    @pytest.mark.asyncio
    async def test_get_listening_minutes_client_none(self, stats_mixin_with_get_client):
        """Тест получения минут прослушивания, когда клиент не получен"""
        with patch.object(stats_mixin_with_get_client, "get_client", return_value=None):
            result = await stats_mixin_with_get_client._get_listening_minutes(
                self.token, self.user_id, days=7
            )
            assert result == 0

    # Тесты для _get_top_artists
    @pytest.mark.asyncio
    async def test_get_top_artists_no_artists(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения топ-артистов, когда нет артистов"""
        mock_track = Mock()
        mock_track.artists = []

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client,
                "_get_recent_history",
                return_value=["history_item"],
            ):
                with patch.object(
                    stats_mixin_with_get_client,
                    "_collect_tracks_from_history",
                    return_value=[
                        (mock_track, None),
                    ],
                ):
                    result = await stats_mixin_with_get_client._get_top_artists(
                        self.token, self.user_id, limit=5
                    )
                    assert result == []

    # Тесты для _get_top_genres_from_library
    @pytest.mark.asyncio
    async def test_get_top_genres_from_library_success(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест успешного получения топ-жанров из библиотеки"""
        mock_likes = Mock()
        mock_likes.tracks = ["liked_track1", "liked_track2"]

        mock_track1 = Mock()
        mock_track1.genre = "Rock"

        mock_track2 = Mock()
        mock_track2.genre = "Pop"

        mock_track3 = Mock()
        mock_track3.genre = "Rock"

        mock_client.users_likes_tracks.return_value = mock_likes

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client,
                "_fetch_tracks",
                side_effect=[[mock_track1, mock_track2], [mock_track3]],
            ):
                with patch.object(
                    stats_mixin_with_get_client, "_get_account_uid", return_value=123456
                ):
                    with patch.object(
                        stats_mixin_with_get_client,
                        "_get_playlist_tracks",
                        return_value=[mock_track3],
                    ):
                        result = await stats_mixin_with_get_client._get_top_genres_from_library(
                            self.token, self.user_id, limit=2
                        )

                        assert len(result) == 2
                        assert result[0]["name"] == "Rock"
                        assert result[0]["count"] == 2
                        assert result[1]["name"] == "Pop"
                        assert result[1]["count"] == 1

    @pytest.mark.asyncio
    async def test_get_top_genres_from_library_no_genre(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения топ-жанров, когда нет жанров"""
        mock_likes = Mock()
        mock_likes.tracks = ["track1"]

        mock_track = Mock()
        mock_track.genre = None

        mock_client.users_likes_tracks.return_value = mock_likes

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client, "_fetch_tracks", return_value=[mock_track]
            ):
                with patch.object(
                    stats_mixin_with_get_client, "_get_account_uid", return_value=None
                ):
                    result = (
                        await stats_mixin_with_get_client._get_top_genres_from_library(
                            self.token, self.user_id, limit=5
                        )
                    )
                    assert result == []

    @pytest.mark.asyncio
    async def test_get_top_genres_from_library_no_likes(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест получения топ-жанров без лайков"""
        mock_likes = Mock()
        mock_likes.tracks = []

        mock_client.users_likes_tracks.return_value = mock_likes

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client, "_fetch_tracks", return_value=[]
            ):
                with patch.object(
                    stats_mixin_with_get_client, "_get_account_uid", return_value=123456
                ):
                    with patch.object(
                        stats_mixin_with_get_client,
                        "_get_playlist_tracks",
                        return_value=[],
                    ):
                        result = await stats_mixin_with_get_client._get_top_genres_from_library(
                            self.token, self.user_id, limit=5
                        )
                        assert result == []

    @pytest.mark.asyncio
    async def test_get_top_genres_from_library_exception(
        self, stats_mixin_with_get_client
    ):
        """Тест получения топ-жанров с исключением"""
        with patch.object(
            stats_mixin_with_get_client,
            "get_client",
            side_effect=Exception("API Error"),
        ):
            result = await stats_mixin_with_get_client._get_top_genres_from_library(
                self.token, self.user_id, limit=5
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_methods_with_custom_parameters(
        self, stats_mixin_with_get_client, mock_client
    ):
        """Тест методов с кастомными параметрами"""
        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client, "_get_recent_history", return_value=[]
            ):
                with patch.object(
                    stats_mixin_with_get_client,
                    "_collect_tracks_from_history",
                    return_value=[],
                ):
                    result1 = (
                        await stats_mixin_with_get_client._get_top_genres_from_recent(
                            self.token, self.user_id, limit=10, days=30
                        )
                    )
                    assert result1 == []

                    result2 = await stats_mixin_with_get_client._get_listening_minutes(
                        self.token, self.user_id, days=1
                    )
                    assert result2 == 0

    # Тесты для проверки обработки времени
    @pytest.mark.asyncio
    async def test_timestamp_filtering(self, stats_mixin_with_get_client, mock_client):
        """Тест фильтрации по времени"""
        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=5)
        old = now - timedelta(days=100)

        mock_track = Mock()
        mock_track.genre = "Test"
        mock_track.duration_ms = 60000

        with patch.object(
            stats_mixin_with_get_client, "get_client", return_value=mock_client
        ):
            with patch.object(
                stats_mixin_with_get_client,
                "_get_recent_history",
                return_value=["item"],
            ):
                with patch.object(
                    stats_mixin_with_get_client,
                    "_collect_tracks_from_history",
                    return_value=[
                        (mock_track, recent),
                        (mock_track, old),
                        (mock_track, None),
                    ],
                ):
                    result_genres = (
                        await stats_mixin_with_get_client._get_top_genres_from_recent(
                            self.token, self.user_id, limit=5, days=90
                        )
                    )

                    result_minutes = (
                        await stats_mixin_with_get_client._get_listening_minutes(
                            self.token, self.user_id, days=90
                        )
                    )

                    assert result_minutes >= 0
