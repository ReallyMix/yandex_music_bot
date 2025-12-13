import pytest
from yandex_music_service import YandexMusicService


@pytest.fixture
def music_service():
    """Фикстура для создания экземпляра сервиса"""
    return YandexMusicService()
