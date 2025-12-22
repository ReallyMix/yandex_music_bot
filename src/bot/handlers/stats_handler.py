import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from ...database.storage import get_token
from ..services import ym_service
from ..keyboards.main_menu import get_back_button

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "menu_stats")
async def stats_callback(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    token = get_token(user_id)

    if not token:
        await callback.message.edit_text(
            "❌ Вы не авторизованы. Используйте /auth",
            reply_markup=get_back_button()
        )
        return

    status_msg = await callback.message.edit_text("📊 Собираю статистику...")

    try:
        stats = await ym_service.get_user_statistics(token, user_id)

        if not stats:
            await status_msg.edit_text(
                "📊 <b>Статистика недоступна</b>\n\n"
                "Возможно, у вас мало активности или проблемы с доступом.",
                reply_markup=get_back_button()
            )
            return

        text = "📊 <b>Ваша статистика</b>\n\n"

        text += f"❤️ Лайкнутых треков: <b>{stats.get('liked_tracks_count', 0):,}</b>\n"
        text += f"📅 Лайков за месяц: <b>{stats.get('recent_likes_last_month', 0)}</b>\n\n"

        top_artists = stats.get('top_artists', [])
        if top_artists:
            text += "🎤 <b>Топ артистов:</b>\n"
            for i, artist in enumerate(top_artists[:5], 1):
                text += f"  {i}. {artist.get('name', '?')} — {artist.get('count', 0)} треков\n"
            text += "\n"

        top_genres_recent = stats.get('top_genres_recent', [])
        if top_genres_recent:
            text += "🎵 <b>Топ жанров (90 дней):</b>\n"
            for i, genre in enumerate(top_genres_recent[:5], 1):
                text += f"  {i}. {genre.get('name', '?')} — {genre.get('count', 0)} раз\n"
            text += "\n"

        top_genres_lib = stats.get('top_genres_library', [])
        if top_genres_lib:
            text += "📚 <b>Топ жанров (библиотека):</b>\n"
            for i, genre in enumerate(top_genres_lib[:5], 1):
                text += f"  {i}. {genre.get('name', '?')} — {genre.get('count', 0)} треков\n"

        await status_msg.edit_text(text, reply_markup=get_back_button(), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Ошибка</b>\n\n<code>{str(e)[:150]}</code>",
            reply_markup=get_back_button(),
            parse_mode="HTML"
        )