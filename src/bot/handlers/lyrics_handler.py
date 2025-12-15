import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

# В этом файле НЕ должно быть импорта из common
# или если нужны функции из common, то импортируйте их напрямую
from ..storage import user_tokens
from ..services import ym_service

router = Router()
logger = logging.getLogger(__name__)



@router.callback_query(F.data.startswith("lyrics:"))
async def lyrics_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    token = user_tokens.get(user_id)
    if not token:
        await callback.message.answer("❌ Нет токена. Используй /start и /auth.")
        return

    track_id = callback.data.split(":", 1)[1]

    try:
        # services.YandexMusicService: get_song_lyrics(token, user_id, track_id)
        lyrics = await ym_service.get_song_lyrics(token, user_id, track_id)
        if not lyrics:
            await callback.message.answer(
                "❌ Текст для этого трека не найден (в API он есть не у всех треков)."
            )
            return

        chunk = 3500
        for i in range(0, len(lyrics), chunk):
            await callback.message.answer(
                "📝 <b>Текст песни</b>\n\n" + lyrics[i : i + chunk]
            )

    except Exception as e:
        logger.error(f"Ошибка получения текста песни: {e}")
        await callback.message.answer(f"✗ Ошибка: {e}")