import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from .common import require_auth, _effective_user_id_from_message, get_client, _format_track_id_for_lyrics
router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text.regexp(r"^[^/].+"))
@require_auth
async def search_handler(message: Message):
    user_id = _effective_user_id_from_message(message)
    query = message.text.strip()
    if len(query) < 2:
        return



    status_msg = await message.answer(f"🔍 Ищу: <b>{query}</b>...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("✗ Ошибка авторизации")
            return

        result = client.search(query, type_="track")
        if not result.tracks or not result.tracks.results:
            await status_msg.edit_text(
                f"✗ По запросу \"<b>{query}</b>\" ничего не найдено."
            )
            return

        tracks = result.tracks.results[:10]

        text = f"🔍 <b>Результаты поиска: {query}</b>\n\n"
        text += f"Найдено: {result.tracks.total}\n"
        text += f"Показано: {len(tracks)}\n\n"

        kb = []

        for i, track in enumerate(tracks, 1):
            artists = ", ".join(a.name for a in track.artists)
            duration = f"{track.duration_ms // 60000}:{(track.duration_ms // 1000) % 60:02d}"
            text += f"{i}. <b>{track.title}</b>\n"
            text += f"   🎤 {artists}\n"
            text += f"   ⏳ {duration}\n\n"

            track_id = _format_track_id_for_lyrics(track)
            kb.append(
                [
                    InlineKeyboardButton(
                        text=f"📜 Текст #{i}",
                        callback_data=f"lyrics:{track_id}",
                    )
                ]
            )

        await status_msg.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await status_msg.edit_text(f"❌ Ошибка поиска: {e}")