# Создаем главный роутер
from aiogram import Router
from .start_handler import router as start_router
from .help_handler import router as help_router
from .menu_handlers import router as menu_router
from .likes_handler import router as likes_router
from .playlists_handler import router as playlists_router
from .artists_handler import router as artists_router
from .albums_handler import router as albums_router
from .stats_handler import router as stats_router
from .search_handler import router as search_router
from .lyrics_handler import router as lyrics_router

main_router = Router()

# Включаем все роутеры в главный
main_router.include_router(start_router)
main_router.include_router(help_router)
main_router.include_router(menu_router)
main_router.include_router(likes_router)
main_router.include_router(playlists_router)
main_router.include_router(artists_router)
main_router.include_router(albums_router)
main_router.include_router(stats_router)
main_router.include_router(search_router)
main_router.include_router(lyrics_router)

__all__ = ["main_router"]