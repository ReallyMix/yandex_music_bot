import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .common import require_auth, _effective_user_id_from_message
from ..storage import user_tokens
from ..services import ym_service

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "show_stats")
async def show_stats_callback(callback: CallbackQuery):
    await callback.answer()
    await show_stats(callback.message, callback.from_user.id)

@router.message(Command("stats"))
@require_auth
async def stats_command(message: Message):
    await show_stats(message, _effective_user_id_from_message(message))

async def show_stats(message: Message, user_id: int):
    status_msg = await message.answer("📊 Собираю статистику...")

    token = user_tokens.get(user_id)
    if not token:
        await status_msg.edit_text("✗ Ошибка авторизации")
        return

    try:
        # services.YandexMusicService: get_user_statistics
        data = await ym_service.get_user_statistics(token, user_id)

        text = "📊 <b>Твоя статистика</b>\n"
        text += f"❤️ Лайкнутых треков: {data.get('liked_tracks_count', 0)}\n"
        text += f"🕐 Лайков за 30 дней: {data.get('recent_likes_last_month', 0)}\n"

        lm = data.get("listening_minutes", 0) or 0
        text += (
            f"🎧 Прослушивание: {lm.get('week', 0)} мин за неделю, "
            f"{lm.get('month', 0)} мин за месяц\n\n"
        )

        top_artists = data.get("top_artists") or []
        if top_artists:
            text += "👨‍🎤 <b>Топ артистов:</b>\n"
            for i, item in enumerate(top_artists, 1):
                text += f"{i}. {item.get('name')} — {item.get('count')} треков\n"
            text += "\n"

        top_genres_recent = data.get("top_genres_recent") or []
        if top_genres_recent:
            text += "🎵 <b>Жанры (недавние):</b>\n"
            for i, item in enumerate(top_genres_recent, 1):
                text += f"{i}. {item.get('name')} — {item.get('count')}\n"
            text += "\n"

        top_genres_library = data.get("top_genres_library") or []
        if top_genres_library:
            text += "🎵 <b>Жанры (библиотека):</b>\n"
            for i, item in enumerate(top_genres_library, 1):
                text += f"{i}. {item.get('name')} — {item.get('count')}\n"
            text += "\n"

        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка статистики: {e}")
        await status_msg.edit_text(f"✗ Ошибка: {e}")