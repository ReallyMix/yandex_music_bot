from aiogram import Router

from . import (
    start_handler,
    help_handler,
    playlist_handler,
    lyrics_handler,
    create_playlist_handler,
    add_tracks_handler,
    like_track_handler,
    stats_handler
)


main_router = Router()


main_router.include_router(start_handler.router)
main_router.include_router(help_handler.router)
main_router.include_router(playlist_handler.router)
main_router.include_router(lyrics_handler.router)
main_router.include_router(create_playlist_handler.router)
main_router.include_router(add_tracks_handler.router)
main_router.include_router(like_track_handler.router)
main_router.include_router(stats_handler.router)

__all__ = ['main_router']